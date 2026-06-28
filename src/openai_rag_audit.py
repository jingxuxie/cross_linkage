#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer

from crossdoc_pipeline import (
    dataframe_to_markdown,
    load_config,
    make_paths,
    read_jsonl,
    split_personas,
)
from openai_audit import (
    CachedOpenAI,
    cache_key,
    display_path,
    git_commit,
    openai_result_path,
    read_api_key,
    sanitize_run_name,
)
from rag_exposure import profile_query


CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

CONDITION_LABELS = {
    "c1_direct_redaction": "C1 direct redaction",
    "c1b_presidio_redaction": "C1b Presidio redaction",
    "c4_doc_local_anon": "C4 doc-local proxy",
    "c5_linkguard": "C5 LinkGuard",
    "c6_aggressive_redaction": "C6 aggressive redaction",
}

PAPER_LABELS = {
    "c1_direct_redaction": "C1 Redact",
    "c1b_presidio_redaction": "C1b Presidio",
    "c4_doc_local_anon": "C4 Local",
    "c5_linkguard": "C5 LG",
    "c6_aggressive_redaction": "C6 Agg",
}

SENSITIVE_FIELDS = [
    "city",
    "occupation",
    "employer_type",
    "family_structure",
    "medical_context",
    "financial_context",
    "legal_context",
    "schedule_pattern",
    "hobby_or_affiliation",
    "rare_event",
]

COARSE_FIELDS = [
    "region",
    "job_family",
    "age_band",
]


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


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def select_personas(personas: list[dict[str, Any]], max_personas: int, tier: str) -> list[str]:
    test_ids = split_personas(personas)["test"]
    return [
        persona["persona_id"]
        for persona in personas
        if persona["persona_id"] in test_ids and persona["risk_tier"] == tier
    ][:max_personas]


def load_condition_docs(paths: Any, condition: str) -> list[dict[str, Any]]:
    path = paths.transformed / f"{condition}.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_jsonl(path)


def top_retrieved_docs(
    docs: list[dict[str, Any]],
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    texts = [doc["text"] for doc in docs]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        min_df=1,
        max_df=0.9,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    matrix = vectorizer.fit_transform(texts)
    query_matrix = vectorizer.transform([query])
    scores = (query_matrix @ matrix.T).toarray()[0]
    order = np.argsort(-scores)[:top_k]
    rows = []
    for rank, idx in enumerate(order, start=1):
        rows.append({**docs[int(idx)], "retrieval_rank": rank, "retrieval_score": float(scores[int(idx)])})
    return rows


def build_cases(
    paths: Any,
    personas: list[dict[str, Any]],
    persona_ids: list[str],
    conditions: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    docs_by_condition = {condition: load_condition_docs(paths, condition) for condition in conditions}
    cases = []
    for condition in conditions:
        docs = docs_by_condition[condition]
        for pid in persona_ids:
            query = profile_query(persona_by_id[pid])
            retrieved = top_retrieved_docs(docs, query, top_k)
            target_docs = [doc for doc in retrieved if doc["persona_id"] == pid]
            cases.append(
                {
                    "condition": condition,
                    "persona_id": pid,
                    "risk_tier": persona_by_id[pid]["risk_tier"],
                    "query": query,
                    "retrieved_docs": retrieved,
                    "retrieval_hit_at_k": int(bool(target_docs)),
                    "target_docs_at_k": len(target_docs),
                    "top_doc_persona": retrieved[0]["persona_id"] if retrieved else "",
                    "top_doc_is_target": int(bool(retrieved) and retrieved[0]["persona_id"] == pid),
                }
            )
    return cases


def compact_doc_text(doc: dict[str, Any]) -> str:
    text = " ".join(str(doc["text"]).split())
    return text[:1600]


def rag_prompt(case: dict[str, Any]) -> tuple[str, str]:
    instructions = (
        "You are conducting a defensive privacy audit on synthetic transformed documents. "
        "All records are synthetic. Use only the retrieved transformed documents as evidence. "
        "The profile query is only the retrieval query; do not count facts that appear only in the query. "
        "Return JSON only."
    )
    doc_blocks = []
    for doc in case["retrieved_docs"]:
        doc_blocks.append(
            f"Retrieved document {doc['retrieval_rank']} "
            f"(domain={doc['domain']}, score={doc['retrieval_score']:.4f}):\n"
            f"{compact_doc_text(doc)}"
        )
    prompt = (
        "PROFILE-LIKE QUERY USED FOR RETRIEVAL (not evidence by itself):\n"
        f"{case['query']}\n\n"
        "RETRIEVED TRANSFORMED DOCUMENTS:\n"
        f"{chr(10).join(doc_blocks)}\n\n"
        "Audit task:\n"
        "Based only on the retrieved transformed documents, decide whether they likely contain records about "
        "the synthetic person described by the profile-like query. Then list what sensitive or quasi-identifying "
        "contexts the retrieved documents themselves expose.\n\n"
        "Return exactly one JSON object with keys:\n"
        "- likely_same_person: boolean.\n"
        "- confidence: number from 0 to 1.\n"
        "- uncertain: boolean.\n"
        "- inferred_contexts: array of short strings found in retrieved documents.\n"
        "- sensitive_contexts: array of objects with keys field, value, evidence, specificity. "
        "field must be one of city, occupation, employer_type, family_structure, medical_context, "
        "financial_context, legal_context, schedule_pattern, hobby_or_affiliation, rare_event, region, "
        "job_family, age_band, coarse_context. value is the exposed context. evidence is a short quote "
        "or paraphrase from retrieved documents, at most 12 words. specificity is high, medium, or low.\n"
        "- exposed_domains: array chosen from healthcare, legal, financial, hr.\n"
        "- summary: at most 30 words.\n"
        "Keep the JSON compact. Include at most six sensitive_contexts, prioritizing the most specific "
        "contexts that are actually present in the retrieved documents. Do not include markdown.\n"
    )
    return instructions, prompt


def exact_field_matches(persona: dict[str, Any], contexts: list[dict[str, Any]]) -> set[str]:
    matches: set[str] = set()
    for context in contexts:
        field = str(context.get("field", "")).strip()
        if field not in SENSITIVE_FIELDS:
            continue
        true_value = str(persona.get(field, "")).strip().lower()
        if not true_value:
            continue
        haystack = f"{context.get('value', '')} {context.get('evidence', '')}".lower()
        if true_value in haystack:
            matches.add(field)
    return matches


def field_mentions(contexts: list[dict[str, Any]], fields: list[str]) -> set[str]:
    present = set()
    for context in contexts:
        field = str(context.get("field", "")).strip()
        if field in fields:
            present.add(field)
    return present


def normalize_contexts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if isinstance(item, dict):
            rows.append(
                {
                    "field": str(item.get("field", "")).strip(),
                    "value": str(item.get("value", "")).strip(),
                    "evidence": str(item.get("evidence", "")).strip(),
                    "specificity": str(item.get("specificity", "")).strip().lower(),
                }
            )
    return rows


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def build_plan(
    paths: Any,
    model: str,
    reasoning_effort: str,
    cases: list[dict[str, Any]],
    max_output_tokens: int,
) -> pd.DataFrame:
    rows = []
    cache_dir = paths.root / "cache" / "api_responses"
    for case in cases:
        instructions, prompt = rag_prompt(case)
        payload = {
            "task": f"rag_generation::{case['condition']}",
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
                "condition": case["condition"],
                "persona_id": case["persona_id"],
                "risk_tier": case["risk_tier"],
                "retrieval_hit_at_k": case["retrieval_hit_at_k"],
                "target_docs_at_k": case["target_docs_at_k"],
                "cache_key": key,
                "cached": (cache_dir / f"{key}.json").exists(),
                "input_chars": len(instructions) + len(prompt),
                "max_output_tokens": max_output_tokens,
                "reasoning_effort": reasoning_effort,
            }
        )
    return pd.DataFrame(rows)


def run_rag_audit(
    caller: CachedOpenAI,
    paths: Any,
    run_name: str,
    cases: list[dict[str, Any]],
    persona_by_id: dict[str, dict[str, Any]],
    top_k: int,
    max_output_tokens: int,
) -> pd.DataFrame:
    rows = []
    for case in cases:
        instructions, prompt = rag_prompt(case)
        result = caller.call(
            f"rag_generation::{case['condition']}",
            instructions,
            prompt,
            max_output_tokens=max_output_tokens,
        )
        parse_success = isinstance(result.get("parsed"), dict)
        parsed = result.get("parsed") if parse_success else {}
        contexts = normalize_contexts(parsed.get("sensitive_contexts"))
        inferred = normalize_string_list(parsed.get("inferred_contexts"))
        exposed_domains = normalize_string_list(parsed.get("exposed_domains"))
        persona = persona_by_id[case["persona_id"]]
        exact_matches = exact_field_matches(persona, contexts)
        sensitive_mentions = field_mentions(contexts, SENSITIVE_FIELDS)
        coarse_mentions = field_mentions(contexts, COARSE_FIELDS + ["coarse_context"])
        high_specificity = sum(1 for context in contexts if context.get("specificity") == "high")
        rows.append(
            {
                "model": caller.model,
                "run_name": run_name,
                "condition": case["condition"],
                "condition_label": CONDITION_LABELS.get(case["condition"], case["condition"]),
                "persona_id": case["persona_id"],
                "risk_tier": case["risk_tier"],
                "top_k": top_k,
                "retrieval_hit_at_k": case["retrieval_hit_at_k"],
                "target_docs_at_k": case["target_docs_at_k"],
                "top_doc_persona": case["top_doc_persona"],
                "top_doc_is_target": case["top_doc_is_target"],
                "parse_success": parse_success,
                "likely_same_person": boolish(parsed.get("likely_same_person")) if parse_success else None,
                "confidence": as_float(parsed.get("confidence")) if parse_success else None,
                "uncertain": boolish(parsed.get("uncertain")) if parse_success else None,
                "inferred_context_count": len(inferred) if parse_success else None,
                "sensitive_context_count": len(contexts) if parse_success else None,
                "high_specificity_context_count": high_specificity if parse_success else None,
                "sensitive_field_mentions": len(sensitive_mentions) if parse_success else None,
                "coarse_field_mentions": len(coarse_mentions) if parse_success else None,
                "exact_field_matches": len(exact_matches) if parse_success else None,
                "exact_field_match_rate": (
                    len(exact_matches) / len(SENSITIVE_FIELDS) if parse_success else None
                ),
                "sensitive_contexts_json": json.dumps(contexts, sort_keys=True),
                "inferred_contexts_json": json.dumps(inferred, sort_keys=True),
                "exposed_domains_json": json.dumps(exposed_domains, sort_keys=True),
                "summary": parsed.get("summary", "") if parse_success else "",
                "raw_text": result.get("text", ""),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(openai_result_path(paths, run_name, "rag_generation_rows", "csv"), index=False)
    return df


def summarize(rows: pd.DataFrame, paths: Any, run_name: str) -> pd.DataFrame:
    work = rows.copy()
    if "parse_success" not in work.columns:
        work["parse_success"] = work["raw_text"].astype(str).str.strip().ne("") & work[
            "likely_same_person"
        ].notna()
    work["parse_success"] = work["parse_success"].fillna(False).astype(bool)
    parsed_metric_cols = [
        "likely_same_person",
        "confidence",
        "uncertain",
        "inferred_context_count",
        "sensitive_context_count",
        "high_specificity_context_count",
        "sensitive_field_mentions",
        "coarse_field_mentions",
        "exact_field_matches",
        "exact_field_match_rate",
    ]
    for col in parsed_metric_cols:
        if col in work.columns:
            work.loc[~work["parse_success"], col] = np.nan
    for col in ["likely_same_person", "uncertain"]:
        work[col] = work[col].map(boolish)

    def bool_mean(series: pd.Series) -> float:
        clean = series.dropna()
        if clean.empty:
            return float("nan")
        return float(clean.astype(bool).mean())

    summary = work.groupby(["condition", "condition_label"], sort=False).agg(
        n=("persona_id", "count"),
        n_parsed=("parse_success", "sum"),
        parse_success_rate=("parse_success", "mean"),
        retrieval_hit_at_5=("retrieval_hit_at_k", "mean"),
        target_docs_at_5=("target_docs_at_k", "mean"),
        likely_same_person_rate=("likely_same_person", bool_mean),
        sensitive_contexts_mean=("sensitive_context_count", "mean"),
        high_specificity_contexts_mean=("high_specificity_context_count", "mean"),
        sensitive_field_mentions_mean=("sensitive_field_mentions", "mean"),
        exact_field_match_rate=("exact_field_match_rate", "mean"),
        coarse_field_mentions_mean=("coarse_field_mentions", "mean"),
        uncertain_rate=("uncertain", bool_mean),
        mean_confidence=("confidence", "mean"),
    ).reset_index()
    summary.to_csv(openai_result_path(paths, run_name, "rag_generation_summary", "csv"), index=False)
    paper = summary[
        [
            "condition_label",
            "n",
            "n_parsed",
            "parse_success_rate",
            "retrieval_hit_at_5",
            "likely_same_person_rate",
            "sensitive_contexts_mean",
            "exact_field_match_rate",
            "uncertain_rate",
        ]
    ].copy()
    paper["condition_label"] = paper["condition_label"].map(
        {v: PAPER_LABELS.get(k, v) for k, v in CONDITION_LABELS.items()}
    ).fillna(paper["condition_label"])
    lines = [
        "# GPT-5.5 RAG Generation Exposure Audit",
        "",
        "Local profile-query retrieval supplies the top-5 transformed documents; GPT-5.5 then reports what the retrieved documents expose.",
        "Generation metrics are averaged over parsed JSON responses; parse success is reported separately.",
        "",
        dataframe_to_markdown(paper.astype(object).where(pd.notna(paper), "NA"), floatfmt=".3f"),
        "",
    ]
    openai_result_path(paths, run_name, "rag_generation_summary", "md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return summary


def write_plan(
    paths: Any,
    run_name: str,
    model: str,
    reasoning_effort: str,
    plan: pd.DataFrame,
    persona_ids: list[str],
    top_k: int,
    max_output_tokens: int,
) -> Path:
    plan_path = openai_result_path(paths, run_name, "audit_plan", "csv")
    plan.to_csv(plan_path, index=False)
    by_condition = (
        plan.groupby("condition", sort=False)
        .agg(n=("persona_id", "count"), cached=("cached", "sum"), mean_input_chars=("input_chars", "mean"))
        .reset_index()
    )
    lines = [
        "# GPT-5.5 RAG Generation Audit Plan",
        "",
        f"Run name: `{run_name}`",
        f"Model: `{model}`",
        f"Reasoning effort: `{reasoning_effort or 'default'}`",
        f"Top retrieved documents: `{top_k}`",
        f"Max output tokens: `{max_output_tokens}`",
        f"Git commit: `{git_commit(paths.root)}`",
        f"Personas planned: {', '.join(persona_ids)}",
        f"Total planned calls: {len(plan)}",
        f"Cached calls: {int(plan['cached'].sum()) if not plan.empty else 0}",
        f"Missing calls: {int((~plan['cached']).sum()) if not plan.empty else 0}",
        "",
        dataframe_to_markdown(by_condition, floatfmt=".1f") if not by_condition.empty else "_No calls planned._",
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
    persona_ids: list[str],
    reasoning_effort: str,
    top_k: int,
    max_output_tokens: int,
) -> Path:
    usage = pd.DataFrame(caller.usage_rows)
    usage_path = openai_result_path(paths, run_name, "audit_usage", "csv")
    usage.to_csv(usage_path, index=False)
    total_in = int(usage["input_tokens"].sum()) if not usage.empty else 0
    total_out = int(usage["output_tokens"].sum()) if not usage.empty else 0
    total = int(usage["total_tokens"].sum()) if not usage.empty else 0
    lines = [
        "# GPT-5.5 RAG Generation Audit Notes",
        "",
        f"Run name: `{run_name}`",
        f"Model: `{model}`",
        f"Reasoning effort: `{reasoning_effort or 'default'}`",
        f"Top retrieved documents: `{top_k}`",
        f"Max output tokens: `{max_output_tokens}`",
        f"Started at UTC: `{started_at_utc}`",
        f"Git commit: `{git_commit(paths.root)}`",
        f"Persona count: {len(persona_ids)}",
        f"New API calls this run: {caller.new_calls}",
        f"Cached calls served this run: {caller.cached_calls}",
        f"Token usage: {total_in} input, {total_out} output, {total} total.",
        f"Usage CSV: `{display_path(usage_path, paths.root)}`",
        "",
        "All records sent to the API are synthetic transformed benchmark records.",
        "All OpenAI response calls in this script pass `store=False` through `CachedOpenAI`.",
        "Cached response files are under `cache/api_responses/`.",
    ]
    summary_path = openai_result_path(paths, run_name, "rag_generation_summary", "md")
    if summary_path.exists():
        summary_csv = openai_result_path(paths, run_name, "rag_generation_summary", "csv")
        if summary_csv.exists():
            summary = pd.read_csv(summary_csv)
            min_parse = float(summary["parse_success_rate"].min()) if not summary.empty else 0.0
            if min_parse < 1.0:
                lines.extend(
                    [
                        "",
                        "Warning: at least one condition has parse_success_rate below 1.000. "
                        "Treat this run as a pilot/debug artifact, not as paper-ready generation evidence.",
                    ]
                )
        lines.extend(["", "## RAG Generation Summary", "", summary_path.read_text(encoding="utf-8")])
    notes_path = openai_result_path(paths, run_name, "audit_notes", "md")
    notes_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return notes_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a cached GPT RAG-generation exposure audit over synthetic transformed records."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--api-key-file", default="")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--run-name", default="gpt55_rag_12t3")
    parser.add_argument("--max-personas", type=int, default=12)
    parser.add_argument("--tier", default="T3")
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-calls", type=int, default=60)
    parser.add_argument("--reasoning-effort", default="")
    parser.add_argument("--max-output-tokens", type=int, default=900)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    run_name = sanitize_run_name(args.run_name)
    if not run_name:
        raise ValueError("--run-name is required")
    personas = read_jsonl(paths.data / "personas.jsonl")
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    persona_ids = select_personas(personas, args.max_personas, args.tier)
    conditions = [condition.strip() for condition in args.conditions.split(",") if condition.strip()]
    cases = build_cases(paths, personas, persona_ids, conditions, args.top_k)
    plan = build_plan(
        paths,
        args.model,
        args.reasoning_effort.strip(),
        cases,
        args.max_output_tokens,
    )
    plan_path = write_plan(
        paths,
        run_name,
        args.model,
        args.reasoning_effort.strip(),
        plan,
        persona_ids,
        args.top_k,
        args.max_output_tokens,
    )
    if args.plan_only:
        print(f"model={args.model}")
        print(f"run_name={run_name}")
        print(f"personas={','.join(persona_ids)}")
        print(f"planned_calls={len(plan)}")
        print(f"cached_calls={int(plan['cached'].sum()) if not plan.empty else 0}")
        print(f"missing_calls={int((~plan['cached']).sum()) if not plan.empty else 0}")
        print(f"plan={plan_path}")
        return
    if len(cases) > args.max_calls and not args.dry_run:
        raise RuntimeError(f"Selected {len(cases)} cases exceeds --max-calls={args.max_calls}.")
    client = OpenAI(api_key="dry-run" if args.dry_run else read_api_key(Path(args.api_key_file)))
    caller = CachedOpenAI(
        client=client,
        model=args.model,
        cache_dir=paths.root / "cache" / "api_responses",
        max_calls=args.max_calls,
        dry_run=args.dry_run,
        reasoning_effort=args.reasoning_effort.strip(),
    )
    started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = run_rag_audit(
        caller,
        paths,
        run_name,
        cases,
        persona_by_id,
        args.top_k,
        args.max_output_tokens,
    )
    summarize(rows, paths, run_name)
    notes_path = write_notes(
        paths,
        run_name,
        args.model,
        caller,
        started_at_utc,
        persona_ids,
        args.reasoning_effort.strip(),
        args.top_k,
        args.max_output_tokens,
    )
    print(f"model={args.model}")
    print(f"run_name={run_name}")
    print(f"personas={','.join(persona_ids)}")
    print(f"new_calls={caller.new_calls}")
    print(f"cached_calls={caller.cached_calls}")
    print(f"notes={notes_path}")


if __name__ == "__main__":
    main()
