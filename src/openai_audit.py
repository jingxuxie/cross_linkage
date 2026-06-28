#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crossdoc_pipeline import (  # noqa: E402
    aux_profile_text,
    dataframe_to_markdown,
    load_config,
    make_paths,
    read_jsonl,
    write_jsonl,
)


MODEL_PREFERENCES = [
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.3-nano",
    "gpt-5.3-mini",
    "gpt-4.1-mini",
    "gpt-4o-mini",
]


def read_api_key(path: Path) -> str:
    key = path.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError(f"API key file is empty: {path}")
    return key


def resolve_api_key(path_text: str) -> str:
    if path_text:
        return read_api_key(Path(path_text))
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    raise RuntimeError("Set OPENAI_API_KEY or pass --api-key-file to run live OpenAI audit calls.")


def choose_model(client: OpenAI, requested: str) -> str:
    if requested != "auto":
        return requested
    models = client.models.list()
    available = {model.id for model in models.data}
    for model in MODEL_PREFERENCES:
        if model in available:
            return model
    cheapish = sorted(
        mid for mid in available if mid.startswith("gpt-") and ("mini" in mid or "nano" in mid)
    )
    if cheapish:
        return cheapish[0]
    raise RuntimeError("Could not find a mini/nano GPT model in the available model list.")


def cache_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    dumped = response.model_dump()
    parts: list[str] = []
    for item in dumped.get("output", []):
        for content in item.get("content", []):
            if "text" in content:
                parts.append(content["text"])
    return "\n".join(parts)


def response_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    data = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
    return {
        "input_tokens": int(data.get("input_tokens", 0) or 0),
        "output_tokens": int(data.get("output_tokens", 0) or 0),
        "total_tokens": int(data.get("total_tokens", 0) or 0),
    }


def extract_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", stripped, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


class CachedOpenAI:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        cache_dir: Path,
        max_calls: int,
        dry_run: bool,
    ) -> None:
        self.client = client
        self.model = model
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_calls = max_calls
        self.dry_run = dry_run
        self.new_calls = 0
        self.usage_rows: list[dict[str, Any]] = []

    def call(self, task: str, instructions: str, prompt: str, max_output_tokens: int) -> dict[str, Any]:
        payload = {
            "task": task,
            "model": self.model,
            "instructions": instructions,
            "prompt": prompt,
            "max_output_tokens": max_output_tokens,
        }
        key = cache_key(payload)
        cache_path = self.cache_dir / f"{key}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        if self.dry_run:
            return {
                "task": task,
                "model": self.model,
                "cached": False,
                "dry_run": True,
                "text": "",
                "parsed": None,
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }
        if self.new_calls >= self.max_calls:
            raise RuntimeError(f"Refusing to exceed --max-calls={self.max_calls}.")
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
            max_output_tokens=max_output_tokens,
            temperature=0,
            store=False,
        )
        self.new_calls += 1
        text = response_text(response)
        parsed = None
        try:
            parsed = extract_json(text)
        except Exception:
            parsed = None
        row = {
            "task": task,
            "model": self.model,
            "cached": False,
            "dry_run": False,
            "text": text,
            "parsed": parsed,
            "usage": response_usage(response),
        }
        cache_path.write_text(json.dumps(row, indent=2, sort_keys=True), encoding="utf-8")
        self.usage_rows.append({"task": task, "cache_key": key, **row["usage"]})
        return row


def select_persona_ids(personas: list[dict[str, Any]], max_personas: int, tiers: set[str]) -> list[str]:
    selected = [p["persona_id"] for p in personas if p["risk_tier"] in tiers]
    return selected[:max_personas]


def anonymize_prompt(doc: dict[str, Any]) -> tuple[str, str]:
    instructions = (
        "You anonymize synthetic benchmark documents for privacy research. "
        "The data is synthetic. Remove or generalize direct personal identifiers and obvious PII. "
        "Do not invent facts. Preserve task-relevant content for support triage. "
        "Return only JSON."
    )
    prompt = (
        "Anonymize this one document independently, without using neighboring documents.\n"
        "Return JSON with keys rewritten_text and changes_made.\n\n"
        f"DOCUMENT:\n{doc['text']}"
    )
    return instructions, prompt


def run_doc_local_anonymization(
    caller: CachedOpenAI,
    paths: Any,
    persona_ids: set[str],
) -> list[dict[str, Any]]:
    rows = []
    original_docs = read_jsonl(paths.transformed / "original.jsonl")
    for doc in original_docs:
        if doc["persona_id"] not in persona_ids:
            continue
        instructions, prompt = anonymize_prompt(doc)
        result = caller.call("doc_local_anonymize", instructions, prompt, max_output_tokens=550)
        rewritten = None
        if isinstance(result.get("parsed"), dict):
            rewritten = result["parsed"].get("rewritten_text")
        rows.append(
            {
                **doc,
                "condition": "c4_openai_doc_local",
                "text": rewritten if isinstance(rewritten, str) and rewritten.strip() else doc["text"],
                "api_cache_text": result.get("text", ""),
            }
        )
    write_jsonl(paths.transformed / "c4_openai_doc_local_subset.jsonl", rows)
    return rows


def aux_match_prompt(
    docs: list[dict[str, Any]],
    candidate_ids: list[str],
    persona_by_id: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    instructions = (
        "You match anonymized synthetic benchmark documents to synthetic auxiliary profiles. "
        "No real people are involved. Use only the provided candidates. Return only JSON."
    )
    doc_text = "\n\n".join(f"Document {idx + 1}:\n{d['text']}" for idx, d in enumerate(docs))
    profiles = "\n".join(aux_profile_text(persona_by_id[cid]) for cid in candidate_ids)
    prompt = (
        "ANONYMIZED DOCUMENTS:\n"
        f"{doc_text}\n\n"
        "CANDIDATE PROFILES:\n"
        f"{profiles}\n\n"
        "Return JSON with keys top_1_candidate_id, ranked_candidates, uncertain, "
        "and most_important_signals. ranked_candidates should list candidate_id and score."
    )
    return instructions, prompt


def run_aux_matching(
    caller: CachedOpenAI,
    paths: Any,
    personas: list[dict[str, Any]],
    persona_ids: set[str],
    conditions: list[str],
) -> pd.DataFrame:
    persona_by_id = {p["persona_id"]: p for p in personas}
    candidate_rows = read_jsonl(paths.data / "candidate_sets.jsonl")
    candidate_by_id = {row["persona_id"]: row["candidate_ids"] for row in candidate_rows}
    rows = []
    for condition in conditions:
        if condition == "c4_openai_doc_local":
            docs = read_jsonl(paths.transformed / "c4_openai_doc_local_subset.jsonl")
        else:
            docs = read_jsonl(paths.transformed / f"{condition}.jsonl")
        docs_by_pid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in docs:
            if doc["persona_id"] in persona_ids:
                docs_by_pid[doc["persona_id"]].append(doc)
        for pid in sorted(persona_ids):
            if pid not in docs_by_pid:
                continue
            instructions, prompt = aux_match_prompt(docs_by_pid[pid], candidate_by_id[pid], persona_by_id)
            result = caller.call(f"aux_match::{condition}", instructions, prompt, max_output_tokens=800)
            parsed = result.get("parsed") if isinstance(result.get("parsed"), dict) else {}
            ranked = parsed.get("ranked_candidates") if isinstance(parsed, dict) else []
            ranked_ids = []
            if isinstance(ranked, list):
                for item in ranked:
                    if isinstance(item, dict) and "candidate_id" in item:
                        ranked_ids.append(str(item["candidate_id"]))
            top = parsed.get("top_1_candidate_id") if isinstance(parsed, dict) else None
            if top and top not in ranked_ids:
                ranked_ids.insert(0, str(top))
            rank = ranked_ids.index(pid) + 1 if pid in ranked_ids else None
            rows.append(
                {
                    "condition": condition,
                    "persona_id": pid,
                    "risk_tier": persona_by_id[pid]["risk_tier"],
                    "top_1_candidate_id": top,
                    "rank": rank,
                    "top1": int(rank == 1) if rank else 0,
                    "top3": int(rank is not None and rank <= 3),
                    "uncertain": parsed.get("uncertain") if isinstance(parsed, dict) else None,
                    "raw_text": result.get("text", ""),
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(paths.results / "openai_aux_match_rows.csv", index=False)
    if not df.empty:
        summary = (
            df.groupby(["condition", "risk_tier"], dropna=False)
            .agg(
                n=("persona_id", "count"),
                top1=("top1", "mean"),
                top3=("top3", "mean"),
                mean_rank=("rank", "mean"),
            )
            .reset_index()
        )
        summary.to_csv(paths.results / "openai_aux_match_summary.csv", index=False)
        (paths.results / "openai_aux_match_summary.md").write_text(
            dataframe_to_markdown(summary, floatfmt=".3f") + "\n",
            encoding="utf-8",
        )
    return df


def plan_call(
    rows: list[dict[str, Any]],
    cache_dir: Path,
    model: str,
    task: str,
    persona_id: str,
    condition: str,
    instructions: str,
    prompt: str,
    max_output_tokens: int,
) -> None:
    payload = {
        "task": task,
        "model": model,
        "instructions": instructions,
        "prompt": prompt,
        "max_output_tokens": max_output_tokens,
    }
    key = cache_key(payload)
    cache_path = cache_dir / f"{key}.json"
    rows.append(
        {
            "task": task,
            "condition": condition,
            "persona_id": persona_id,
            "cache_key": key,
            "cached": cache_path.exists(),
            "input_chars": len(instructions) + len(prompt),
            "max_output_tokens": max_output_tokens,
            "note": "",
        }
    )


def build_audit_plan(
    paths: Any,
    model: str,
    personas: list[dict[str, Any]],
    persona_ids: list[str],
    tasks: set[str],
    conditions: list[str],
) -> pd.DataFrame:
    cache_dir = paths.root / "cache" / "api_responses"
    persona_id_set = set(persona_ids)
    persona_by_id = {p["persona_id"]: p for p in personas}
    candidate_rows = read_jsonl(paths.data / "candidate_sets.jsonl")
    candidate_by_id = {row["persona_id"]: row["candidate_ids"] for row in candidate_rows}
    rows: list[dict[str, Any]] = []

    needs_doc_local = "doc-local" in tasks or "c4_openai_doc_local" in conditions
    if needs_doc_local:
        for doc in read_jsonl(paths.transformed / "original.jsonl"):
            if doc["persona_id"] not in persona_id_set:
                continue
            instructions, prompt = anonymize_prompt(doc)
            plan_call(
                rows,
                cache_dir,
                model,
                "doc_local_anonymize",
                doc["persona_id"],
                "c4_openai_doc_local",
                instructions,
                prompt,
                550,
            )

    if "aux-match" in tasks:
        for condition in conditions:
            if condition == "c4_openai_doc_local":
                subset_path = paths.transformed / "c4_openai_doc_local_subset.jsonl"
                if not subset_path.exists():
                    for pid in persona_ids:
                        rows.append(
                            {
                                "task": f"aux_match::{condition}",
                                "condition": condition,
                                "persona_id": pid,
                                "cache_key": "",
                                "cached": False,
                                "input_chars": 0,
                                "max_output_tokens": 800,
                                "note": "requires doc-local output before prompt can be hashed",
                            }
                        )
                    continue
                docs = read_jsonl(subset_path)
            else:
                docs = read_jsonl(paths.transformed / f"{condition}.jsonl")
            docs_by_pid: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for doc in docs:
                if doc["persona_id"] in persona_id_set:
                    docs_by_pid[doc["persona_id"]].append(doc)
            for pid in persona_ids:
                if pid not in docs_by_pid:
                    rows.append(
                        {
                            "task": f"aux_match::{condition}",
                            "condition": condition,
                            "persona_id": pid,
                            "cache_key": "",
                            "cached": False,
                            "input_chars": 0,
                            "max_output_tokens": 800,
                            "note": "requires doc-local output before prompt can be hashed",
                        }
                    )
                    continue
                instructions, prompt = aux_match_prompt(
                    docs_by_pid[pid], candidate_by_id[pid], persona_by_id
                )
                plan_call(
                    rows,
                    cache_dir,
                    model,
                    f"aux_match::{condition}",
                    pid,
                    condition,
                    instructions,
                    prompt,
                    800,
                )
    return pd.DataFrame(rows)


def write_audit_plan(paths: Any, plan: pd.DataFrame, model: str, persona_ids: list[str]) -> None:
    plan_path = paths.results / "openai_audit_plan.csv"
    plan.to_csv(plan_path, index=False)
    if plan.empty:
        summary = pd.DataFrame()
    else:
        summary = (
            plan.groupby(["task", "condition", "cached", "note"], dropna=False)
            .agg(n=("persona_id", "count"), input_chars=("input_chars", "sum"))
            .reset_index()
        )
    lines = [
        "# OpenAI Audit Plan",
        "",
        f"Model: `{model}`",
        f"Personas planned: {', '.join(persona_ids)}",
        f"Total planned calls: {len(plan)}",
        f"Cached calls: {int(plan['cached'].sum()) if not plan.empty else 0}",
        f"Missing or dependent calls: {int((~plan['cached']).sum()) if not plan.empty else 0}",
        "",
    ]
    if not summary.empty:
        lines.extend(["## Summary", "", dataframe_to_markdown(summary, floatfmt=".0f"), ""])
    lines.extend(
        [
            "Notes:",
            "- `requires doc-local output before prompt can be hashed` means the final auxiliary-matching prompt depends on a generated document-local anonymization output.",
            "- This plan does not call the OpenAI API and does not modify audit result summaries.",
        ]
    )
    (paths.results / "openai_audit_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_notes(paths: Any, model: str, caller: CachedOpenAI, persona_ids: list[str]) -> None:
    usage = pd.DataFrame(caller.usage_rows)
    usage_path = paths.results / "openai_audit_usage.csv"
    usage.to_csv(usage_path, index=False)
    total_in = int(usage["input_tokens"].sum()) if not usage.empty else 0
    total_out = int(usage["output_tokens"].sum()) if not usage.empty else 0
    total = int(usage["total_tokens"].sum()) if not usage.empty else 0
    lines = [
        "# OpenAI Audit Notes",
        "",
        f"Model: `{model}`",
        f"Personas audited: {', '.join(persona_ids)}",
        f"New API calls this run: {caller.new_calls}",
        f"Token usage: {total_in} input, {total_out} output, {total} total.",
        "",
        "Cached response files are under `cache/api_responses/`.",
    ]
    summary_path = paths.results / "openai_aux_match_summary.md"
    if summary_path.exists():
        lines.extend(["", "## Auxiliary Matching Summary", "", summary_path.read_text(encoding="utf-8")])
    (paths.results / "openai_audit_notes.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--api-key-file", default="")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--max-personas", type=int, default=4)
    parser.add_argument("--tiers", default="T2,T3")
    parser.add_argument("--max-calls", type=int, default=20)
    parser.add_argument("--conditions", default="c1_direct_redaction,c4_doc_local_anon,c5_linkguard,c6_aggressive_redaction")
    parser.add_argument("--tasks", default="doc-local,aux-match")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    if args.plan_only:
        model = MODEL_PREFERENCES[0] if args.model == "auto" else args.model
    else:
        key = resolve_api_key(args.api_key_file)
        client = OpenAI(api_key=key)
        model = choose_model(client, args.model)
    personas = read_jsonl(paths.data / "personas.jsonl")
    tiers = {tier.strip() for tier in args.tiers.split(",") if tier.strip()}
    persona_ids = select_persona_ids(personas, args.max_personas, tiers)
    tasks = {task.strip() for task in args.tasks.split(",") if task.strip()}
    conditions = [cond.strip() for cond in args.conditions.split(",") if cond.strip()]
    if args.plan_only:
        plan = build_audit_plan(paths, model, personas, persona_ids, tasks, conditions)
        write_audit_plan(paths, plan, model, persona_ids)
        print(f"model={model}")
        print(f"personas={','.join(persona_ids)}")
        print(f"planned_calls={len(plan)}")
        print(f"cached_calls={int(plan['cached'].sum()) if not plan.empty else 0}")
        print(f"missing_or_dependent_calls={int((~plan['cached']).sum()) if not plan.empty else 0}")
        print(f"plan={paths.results / 'openai_audit_plan.md'}")
        return
    caller = CachedOpenAI(
        client=client,
        model=model,
        cache_dir=paths.root / "cache" / "api_responses",
        max_calls=args.max_calls,
        dry_run=args.dry_run,
    )
    persona_id_set = set(persona_ids)
    if "doc-local" in tasks:
        run_doc_local_anonymization(caller, paths, persona_id_set)
    if "aux-match" in tasks:
        if "c4_openai_doc_local" in conditions and not (paths.transformed / "c4_openai_doc_local_subset.jsonl").exists():
            run_doc_local_anonymization(caller, paths, persona_id_set)
        run_aux_matching(caller, paths, personas, persona_id_set, conditions)
    write_audit_notes(paths, model, caller, persona_ids)
    print(f"model={model}")
    print(f"personas={','.join(persona_ids)}")
    print(f"new_calls={caller.new_calls}")
    print(f"notes={paths.results / 'openai_audit_notes.md'}")


if __name__ == "__main__":
    main()
