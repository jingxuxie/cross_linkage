#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI

from crossdoc_pipeline import (
    aux_profile_text,
    dataframe_to_markdown,
    load_config,
    make_paths,
    read_jsonl,
)
from openai_audit import (
    CachedOpenAI,
    MODEL_PREFERENCES,
    cache_key,
    choose_model,
    display_path,
    git_commit,
    openai_result_path,
    read_api_key,
    sanitize_run_name,
    transformed_condition_path,
)


SIGNAL_LABELS = [
    "role",
    "location",
    "institution",
    "rare_event",
    "schedule",
    "family",
    "medical",
    "financial",
    "legal",
    "affiliation",
    "coarse_context",
    "model_over_inference",
    "information_removed",
]

CONDITION_LABELS = {
    "c1_direct_redaction": "C1 direct redaction",
    "c5_linkguard": "C5 LinkGuard",
    "c6_aggressive_redaction": "C6 aggressive redaction",
}

BUCKET_LABELS = {
    "direct_success": "Direct-redaction successful match",
    "linkguard_residual": "LinkGuard residual match",
    "aggressive_failure": "Aggressive low-signal contrast",
}


def boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def load_aux_rows(paths: Any, source_rows: str) -> pd.DataFrame:
    source = Path(source_rows)
    if not source.is_absolute():
        source = paths.root / source
    rows = pd.read_csv(source)
    required = {"condition", "persona_id", "risk_tier", "rank", "top1", "top3", "uncertain"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"{source} is missing required columns: {sorted(missing)}")
    return rows


def take_balanced(rows: pd.DataFrame, n: int) -> list[str]:
    per_tier = max(1, n // 2)
    chosen: list[str] = []
    for tier in ["T3", "T2"]:
        tier_rows = rows[rows["risk_tier"] == tier].sort_values("persona_id")
        chosen.extend(tier_rows["persona_id"].head(per_tier).tolist())
    if len(chosen) < n:
        for pid in rows.sort_values(["risk_tier", "persona_id"], ascending=[False, True])[
            "persona_id"
        ]:
            if pid not in chosen:
                chosen.append(pid)
            if len(chosen) >= n:
                break
    return chosen[:n]


def select_cases(aux_rows: pd.DataFrame, cases_per_bucket: int) -> list[dict[str, Any]]:
    buckets = [
        (
            "direct_success",
            "c1_direct_redaction",
            aux_rows[(aux_rows["condition"] == "c1_direct_redaction") & (aux_rows["top1"] == 1)],
        ),
        (
            "linkguard_residual",
            "c5_linkguard",
            aux_rows[(aux_rows["condition"] == "c5_linkguard") & (aux_rows["top1"] == 1)],
        ),
        (
            "aggressive_failure",
            "c6_aggressive_redaction",
            aux_rows[
                (aux_rows["condition"] == "c6_aggressive_redaction")
                & (aux_rows["top1"] == 0)
                & (aux_rows["top3"] == 0)
            ],
        ),
    ]
    cases: list[dict[str, Any]] = []
    for bucket, condition, bucket_rows in buckets:
        selected = take_balanced(bucket_rows, cases_per_bucket)
        row_by_pid = {
            row["persona_id"]: row
            for row in bucket_rows.to_dict(orient="records")
            if row["persona_id"] in selected
        }
        for pid in selected:
            source = row_by_pid[pid]
            cases.append(
                {
                    "bucket": bucket,
                    "condition": condition,
                    "persona_id": pid,
                    "risk_tier": source["risk_tier"],
                    "source_rank": int(source["rank"]) if not pd.isna(source["rank"]) else None,
                    "source_top1": int(source["top1"]),
                    "source_top3": int(source["top3"]),
                    "source_uncertain": boolish(source["uncertain"]),
                    "source_signals": source.get("most_important_signals_json", ""),
                }
            )
    return cases


def docs_by_persona(paths: Any, condition: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in read_jsonl(transformed_condition_path(paths, condition)):
        grouped[doc["persona_id"]].append(doc)
    return grouped


def evidence_prompt(
    case: dict[str, Any],
    docs: list[dict[str, Any]],
    persona: dict[str, Any],
) -> tuple[str, str]:
    instructions = (
        "You are conducting a defensive privacy audit on synthetic benchmark data. "
        "Explain why transformed documents still do or do not support cross-document linkage. "
        "Use only the provided transformed documents and auxiliary profile. Return JSON only."
    )
    doc_text = "\n\n".join(
        f"Document {idx + 1} ({doc['domain']}):\n{doc['text']}" for idx, doc in enumerate(docs)
    )
    prompt = (
        "All records are synthetic. Do not identify or describe any real person. "
        "Do not reveal names, emails, phone numbers, street addresses, or account IDs. "
        "Short evidence snippets may quote non-direct contextual phrases from the transformed documents.\n\n"
        f"CASE TYPE: {BUCKET_LABELS[case['bucket']]}\n"
        f"CONDITION: {CONDITION_LABELS.get(case['condition'], case['condition'])}\n"
        f"PREVIOUS MATCHER OUTCOME: target_rank={case['source_rank']}, "
        f"top1={case['source_top1']}, top3={case['source_top3']}, "
        f"uncertain={case['source_uncertain']}, compact_signals={case['source_signals']}\n\n"
        "TRANSFORMED DOCUMENTS:\n"
        f"{doc_text}\n\n"
        "TARGET AUXILIARY PROFILE:\n"
        f"{aux_profile_text(persona)}\n\n"
        "Return exactly one JSON object with keys:\n"
        "- top_signals: 3 to 5 objects with keys signal, evidence, specificity. "
        f"signal must be one of: {', '.join(SIGNAL_LABELS)}. "
        "evidence must be a short non-direct phrase, at most 12 words. "
        "specificity is high, medium, or low.\n"
        "- would_match_without_role: true, false, or null.\n"
        "- would_match_without_location: true, false, or null.\n"
        "- residual_risk_category: one of role_location, rare_event, schedule_family_combo, "
        "coarse_context_only, model_over_inference, information_removed, no_residual_signal.\n"
        "- residual_risk_summary: at most 30 words.\n"
        "- utility_loss_summary: at most 30 words; use null if not applicable.\n"
        "- confidence: number from 0 to 1 for this explanation.\n"
        "- uncertain: boolean.\n"
    )
    return instructions, prompt


def build_plan(
    paths: Any,
    model: str,
    reasoning_effort: str,
    cases: list[dict[str, Any]],
    personas: dict[str, dict[str, Any]],
    docs_by_condition: dict[str, dict[str, list[dict[str, Any]]]],
    max_output_tokens: int,
) -> pd.DataFrame:
    cache_dir = paths.root / "cache" / "api_responses"
    rows = []
    for case in cases:
        docs = docs_by_condition[case["condition"]][case["persona_id"]]
        instructions, prompt = evidence_prompt(case, docs, personas[case["persona_id"]])
        payload = {
            "task": f"evidence::{case['bucket']}::{case['condition']}",
            "model": model,
            "instructions": instructions,
            "prompt": prompt,
            "max_output_tokens": max_output_tokens,
        }
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        key = cache_key(payload)
        rows.append(
            {
                "task": payload["task"],
                "bucket": case["bucket"],
                "condition": case["condition"],
                "persona_id": case["persona_id"],
                "risk_tier": case["risk_tier"],
                "cache_key": key,
                "cached": (cache_dir / f"{key}.json").exists(),
                "input_chars": len(instructions) + len(prompt),
                "max_output_tokens": max_output_tokens,
                "reasoning_effort": reasoning_effort,
            }
        )
    return pd.DataFrame(rows)


def normalize_signals(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str):
            out.append({"signal": item, "evidence": "", "specificity": ""})
        elif isinstance(item, dict):
            signal = str(item.get("signal", "")).strip()
            if signal:
                out.append(
                    {
                        "signal": signal,
                        "evidence": str(item.get("evidence", "")).strip(),
                        "specificity": str(item.get("specificity", "")).strip().lower(),
                    }
                )
    return out


def run_evidence_audit(
    caller: CachedOpenAI,
    paths: Any,
    run_name: str,
    cases: list[dict[str, Any]],
    personas: dict[str, dict[str, Any]],
    docs_by_condition: dict[str, dict[str, list[dict[str, Any]]]],
    max_output_tokens: int,
) -> pd.DataFrame:
    rows = []
    for case in cases:
        docs = docs_by_condition[case["condition"]][case["persona_id"]]
        instructions, prompt = evidence_prompt(case, docs, personas[case["persona_id"]])
        result = caller.call(
            f"evidence::{case['bucket']}::{case['condition']}",
            instructions,
            prompt,
            max_output_tokens=max_output_tokens,
        )
        parsed = result.get("parsed") if isinstance(result.get("parsed"), dict) else {}
        signals = normalize_signals(parsed.get("top_signals") if isinstance(parsed, dict) else None)
        signal_labels = [signal["signal"] for signal in signals]
        rows.append(
            {
                **case,
                "model": caller.model,
                "run_name": run_name,
                "condition_label": CONDITION_LABELS.get(case["condition"], case["condition"]),
                "bucket_label": BUCKET_LABELS[case["bucket"]],
                "top_signals_json": json.dumps(signals, sort_keys=True),
                "signal_labels": "|".join(signal_labels),
                "role_signal": int("role" in signal_labels),
                "location_signal": int("location" in signal_labels),
                "institution_signal": int("institution" in signal_labels),
                "rare_event_signal": int("rare_event" in signal_labels),
                "schedule_signal": int("schedule" in signal_labels),
                "family_signal": int("family" in signal_labels),
                "would_match_without_role": boolish(
                    parsed.get("would_match_without_role") if isinstance(parsed, dict) else None
                ),
                "would_match_without_location": boolish(
                    parsed.get("would_match_without_location") if isinstance(parsed, dict) else None
                ),
                "residual_risk_category": parsed.get("residual_risk_category", "")
                if isinstance(parsed, dict)
                else "",
                "residual_risk_summary": parsed.get("residual_risk_summary", "")
                if isinstance(parsed, dict)
                else "",
                "utility_loss_summary": parsed.get("utility_loss_summary", "")
                if isinstance(parsed, dict)
                else "",
                "confidence": parsed.get("confidence") if isinstance(parsed, dict) else None,
                "explanation_uncertain": boolish(
                    parsed.get("uncertain") if isinstance(parsed, dict) else None
                ),
                "raw_text": result.get("text", ""),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(openai_result_path(paths, run_name, "evidence_rows", "csv"), index=False)
    return df


def summarize_evidence(rows: pd.DataFrame, paths: Any, run_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    grouped = []
    for (bucket, condition), group in rows.groupby(["bucket", "condition"], sort=False):
        signals = Counter()
        high_specificity = 0
        total_signals = 0
        for raw in group["top_signals_json"]:
            for signal in json.loads(raw):
                label = signal.get("signal", "")
                if label:
                    signals[label] += 1
                total_signals += 1
                if signal.get("specificity") == "high":
                    high_specificity += 1
        n = len(group)
        grouped.append(
            {
                "bucket": bucket,
                "bucket_label": BUCKET_LABELS[bucket],
                "condition": condition,
                "condition_label": CONDITION_LABELS.get(condition, condition),
                "n": n,
                "role_signal_rate": float(group["role_signal"].mean()),
                "location_signal_rate": float(group["location_signal"].mean()),
                "institution_signal_rate": float(group["institution_signal"].mean()),
                "rare_event_signal_rate": float(group["rare_event_signal"].mean()),
                "schedule_signal_rate": float(group["schedule_signal"].mean()),
                "role_critical_rate": float((group["would_match_without_role"] == False).mean()),
                "location_critical_rate": float(
                    (group["would_match_without_location"] == False).mean()
                ),
                "high_specificity_signal_rate": float(high_specificity / max(1, total_signals)),
                "mean_confidence": float(pd.to_numeric(group["confidence"], errors="coerce").mean()),
                "uncertain_rate": float(group["explanation_uncertain"].fillna(False).mean()),
                "top_signal_counts_json": json.dumps(dict(signals), sort_keys=True),
            }
        )
    summary = pd.DataFrame(grouped)
    counts = []
    for (bucket, condition), group in rows.groupby(["bucket", "condition"], sort=False):
        counter = Counter()
        for labels in group["signal_labels"]:
            for label in str(labels).split("|"):
                if label:
                    counter[label] += 1
        for label, count in sorted(counter.items()):
            counts.append(
                {
                    "bucket": bucket,
                    "bucket_label": BUCKET_LABELS[bucket],
                    "condition": condition,
                    "condition_label": CONDITION_LABELS.get(condition, condition),
                    "signal": label,
                    "count": count,
                    "case_rate": count / len(group),
                }
            )
    count_df = pd.DataFrame(counts)
    summary.to_csv(openai_result_path(paths, run_name, "evidence_summary", "csv"), index=False)
    count_df.to_csv(openai_result_path(paths, run_name, "evidence_signal_counts", "csv"), index=False)
    lines = [
        "# GPT-5.5 Evidence Extraction Audit",
        "",
        "Qualitative signal audit over selected synthetic cases.",
        "",
        "## Bucket Summary",
        "",
        dataframe_to_markdown(
            summary[
                [
                    "bucket_label",
                    "condition_label",
                    "n",
                    "role_signal_rate",
                    "location_signal_rate",
                    "institution_signal_rate",
                    "role_critical_rate",
                    "location_critical_rate",
                    "high_specificity_signal_rate",
                    "uncertain_rate",
                ]
            ],
            floatfmt=".3f",
        ),
        "",
        "## Signal Counts",
        "",
        dataframe_to_markdown(count_df, floatfmt=".3f") if not count_df.empty else "_No signal counts._",
        "",
    ]
    openai_result_path(paths, run_name, "evidence_summary", "md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return summary, count_df


def write_plan(
    paths: Any,
    run_name: str,
    model: str,
    reasoning_effort: str,
    cases: list[dict[str, Any]],
    plan: pd.DataFrame,
    max_output_tokens: int,
) -> Path:
    plan_path = openai_result_path(paths, run_name, "audit_plan", "csv")
    plan.to_csv(plan_path, index=False)
    summary = (
        plan.groupby(["bucket", "condition"], sort=False)
        .agg(n=("persona_id", "count"), cached=("cached", "sum"), mean_input_chars=("input_chars", "mean"))
        .reset_index()
    )
    lines = [
        "# GPT-5.5 Evidence Extraction Audit Plan",
        "",
        f"Run name: `{run_name}`",
        f"Model: `{model}`",
        f"Reasoning effort: `{reasoning_effort or 'default'}`",
        f"Max output tokens: `{max_output_tokens}`",
        f"Git commit: `{git_commit(paths.root)}`",
        f"Total planned calls: {len(plan)}",
        f"Cached calls: {int(plan['cached'].sum()) if not plan.empty else 0}",
        f"Missing calls: {int((~plan['cached']).sum()) if not plan.empty else 0}",
        "",
        "## Selection",
        "",
        "- `direct_success`: GPT-5.5 top-1 matches under direct redaction.",
        "- `linkguard_residual`: GPT-5.5 top-1 residual matches under LinkGuard.",
        "- `aggressive_failure`: aggressive-redaction cases where GPT-5.5 misses the target in top-3.",
        "",
        dataframe_to_markdown(summary, floatfmt=".1f") if not summary.empty else "_No calls planned._",
        "",
        "## Personas",
        "",
        ", ".join(f"{case['bucket']}:{case['persona_id']}" for case in cases),
        "",
    ]
    openai_result_path(paths, run_name, "audit_plan", "md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return plan_path


def write_notes(
    paths: Any,
    run_name: str,
    model: str,
    caller: CachedOpenAI,
    started_at_utc: str,
    cases: list[dict[str, Any]],
    reasoning_effort: str,
    max_output_tokens: int,
) -> Path:
    usage = pd.DataFrame(caller.usage_rows)
    usage_path = openai_result_path(paths, run_name, "audit_usage", "csv")
    usage.to_csv(usage_path, index=False)
    total_in = int(usage["input_tokens"].sum()) if not usage.empty else 0
    total_out = int(usage["output_tokens"].sum()) if not usage.empty else 0
    total = int(usage["total_tokens"].sum()) if not usage.empty else 0
    lines = [
        "# GPT-5.5 Evidence Extraction Audit Notes",
        "",
        f"Run name: `{run_name}`",
        f"Model: `{model}`",
        f"Reasoning effort: `{reasoning_effort or 'default'}`",
        f"Max output tokens: `{max_output_tokens}`",
        f"Started at UTC: `{started_at_utc}`",
        f"Git commit: `{git_commit(paths.root)}`",
        f"Case count: {len(cases)}",
        f"New API calls this run: {caller.new_calls}",
        f"Cached calls served this run: {caller.cached_calls}",
        f"Token usage: {total_in} input, {total_out} output, {total} total.",
        f"Usage CSV: `{display_path(usage_path, paths.root)}`",
        "",
        "All records sent to the API are synthetic transformed benchmark records.",
        "All OpenAI response calls in this script pass `store=False` through `CachedOpenAI`.",
        "Cached response files are under `cache/api_responses/`.",
    ]
    summary_path = openai_result_path(paths, run_name, "evidence_summary", "md")
    if summary_path.exists():
        lines.extend(["", "## Evidence Summary", "", summary_path.read_text(encoding="utf-8")])
    notes_path = openai_result_path(paths, run_name, "audit_notes", "md")
    notes_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return notes_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a small GPT evidence extraction audit over selected synthetic linkage cases."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--api-key-file", default="")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--run-name", default="gpt55_evidence_24p")
    parser.add_argument("--source-rows", default="results/openai_gpt55_48p_aux_match_rows.csv")
    parser.add_argument("--cases-per-bucket", type=int, default=8)
    parser.add_argument("--max-calls", type=int, default=24)
    parser.add_argument("--reasoning-effort", default="")
    parser.add_argument("--max-output-tokens", type=int, default=650)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    run_name = sanitize_run_name(args.run_name)
    if not run_name:
        raise ValueError("--run-name is required for evidence audit artifacts")
    model = MODEL_PREFERENCES[0] if args.model == "auto" and args.plan_only else args.model
    personas_list = read_jsonl(paths.data / "personas.jsonl")
    personas = {persona["persona_id"]: persona for persona in personas_list}
    aux_rows = load_aux_rows(paths, args.source_rows)
    cases = select_cases(aux_rows, args.cases_per_bucket)
    if len(cases) > args.max_calls and not args.plan_only and not args.dry_run:
        raise RuntimeError(f"Selected {len(cases)} cases exceeds --max-calls={args.max_calls}.")
    docs_by_condition = {
        condition: docs_by_persona(paths, condition)
        for condition in sorted({case["condition"] for case in cases})
    }
    plan = build_plan(
        paths,
        model,
        args.reasoning_effort.strip(),
        cases,
        personas,
        docs_by_condition,
        args.max_output_tokens,
    )
    plan_path = write_plan(
        paths,
        run_name,
        model,
        args.reasoning_effort.strip(),
        cases,
        plan,
        args.max_output_tokens,
    )
    if args.plan_only:
        print(f"model={model}")
        print(f"run_name={run_name}")
        print(f"planned_calls={len(plan)}")
        print(f"cached_calls={int(plan['cached'].sum()) if not plan.empty else 0}")
        print(f"missing_calls={int((~plan['cached']).sum()) if not plan.empty else 0}")
        print(f"plan={plan_path}")
        return

    if args.dry_run:
        client = OpenAI(api_key="dry-run")
    elif args.model == "auto":
        client = OpenAI(api_key=read_api_key(Path(args.api_key_file)))
        model = choose_model(client, args.model)
    else:
        client = OpenAI(api_key=read_api_key(Path(args.api_key_file)))
    caller = CachedOpenAI(
        client=client,
        model=model,
        cache_dir=paths.root / "cache" / "api_responses",
        max_calls=args.max_calls,
        dry_run=args.dry_run,
        reasoning_effort=args.reasoning_effort.strip(),
    )
    started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = run_evidence_audit(
        caller,
        paths,
        run_name,
        cases,
        personas,
        docs_by_condition,
        args.max_output_tokens,
    )
    summarize_evidence(rows, paths, run_name)
    notes_path = write_notes(
        paths,
        run_name,
        model,
        caller,
        started_at_utc,
        cases,
        args.reasoning_effort.strip(),
        args.max_output_tokens,
    )
    print(f"model={model}")
    print(f"run_name={run_name}")
    print(f"cases={len(cases)}")
    print(f"new_calls={caller.new_calls}")
    print(f"cached_calls={caller.cached_calls}")
    print(f"notes={notes_path}")


if __name__ == "__main__":
    main()
