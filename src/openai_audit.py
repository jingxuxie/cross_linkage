#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
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


def sanitize_run_name(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    if not slug:
        raise ValueError(f"Invalid --run-name: {value!r}")
    return slug


def openai_result_path(paths: Any, run_name: str, artifact: str, suffix: str) -> Path:
    prefix = "openai" if not run_name else f"openai_{run_name}"
    return paths.results / f"{prefix}_{artifact}.{suffix}"


def doc_local_condition_name(run_name: str, requested: str) -> str:
    if requested.strip():
        return requested.strip()
    return f"c4_openai_doc_local_{run_name}" if run_name else "c4_openai_doc_local"


def doc_local_path(paths: Any, condition: str) -> Path:
    if condition == "c4_openai_doc_local":
        return paths.transformed / "c4_openai_doc_local_subset.jsonl"
    return paths.transformed / f"{condition}.jsonl"


def transformed_condition_path(paths: Any, condition: str) -> Path:
    if condition == "c4_openai_doc_local":
        return doc_local_path(paths, condition)
    return paths.transformed / f"{condition}.jsonl"


def git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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
        reasoning_effort: str = "",
    ) -> None:
        self.client = client
        self.model = model
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_calls = max_calls
        self.dry_run = dry_run
        self.reasoning_effort = reasoning_effort
        self.new_calls = 0
        self.cached_calls = 0
        self.usage_rows: list[dict[str, Any]] = []

    def call(
        self,
        task: str,
        instructions: str,
        prompt: str,
        max_output_tokens: int,
        text_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "task": task,
            "model": self.model,
            "instructions": instructions,
            "prompt": prompt,
            "max_output_tokens": max_output_tokens,
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if text_config:
            payload["text_config"] = text_config
        key = cache_key(payload)
        cache_path = self.cache_dir / f"{key}.json"
        if cache_path.exists():
            row = json.loads(cache_path.read_text(encoding="utf-8"))
            self.cached_calls += 1
            usage = row.get("usage", {}) if isinstance(row.get("usage"), dict) else {}
            self.usage_rows.append(
                {
                    "task": task,
                    "cache_key": key,
                    "cached": True,
                    "input_tokens": int(usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(usage.get("output_tokens", 0) or 0),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                }
            )
            return row
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
        request_kwargs = {
            "model": self.model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
        if self.reasoning_effort:
            request_kwargs["reasoning"] = {"effort": self.reasoning_effort}
        if text_config:
            request_kwargs["text"] = text_config
        response = self.client.responses.create(**request_kwargs)
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
        self.usage_rows.append({"task": task, "cache_key": key, "cached": False, **row["usage"]})
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
    output_condition: str = "c4_openai_doc_local",
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
                "condition": output_condition,
                "text": rewritten if isinstance(rewritten, str) and rewritten.strip() else doc["text"],
                "api_cache_text": result.get("text", ""),
            }
        )
    write_jsonl(doc_local_path(paths, output_condition), rows)
    return rows


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def candidate_scores(ranked: Any) -> dict[str, float]:
    scores = {}
    if not isinstance(ranked, list):
        return scores
    for item in ranked:
        if not isinstance(item, dict) or "candidate_id" not in item:
            continue
        score = as_float(item.get("score"))
        if score is not None:
            scores[str(item["candidate_id"])] = score
    return scores


def aux_match_prompt(
    docs: list[dict[str, Any]],
    candidate_ids: list[str],
    persona_by_id: dict[str, dict[str, Any]],
    compact_output: bool = False,
) -> tuple[str, str]:
    instructions = (
        "You match anonymized synthetic benchmark documents to synthetic auxiliary profiles. "
        "No real people are involved. Use only the provided candidates. Return only JSON."
    )
    doc_text = "\n\n".join(f"Document {idx + 1}:\n{d['text']}" for idx, d in enumerate(docs))
    profiles = "\n".join(aux_profile_text(persona_by_id[cid]) for cid in candidate_ids)
    if compact_output:
        output_rule = (
            "Return exactly one compact JSON object on one line with keys: "
            "ranked_candidates, confidence, uncertain, top_signals. "
            "ranked_candidates must be an array of all candidate_id strings, best first. "
            "confidence must be a number from 0 to 1 for the first candidate. "
            "top_signals must be an array of at most 3 short labels chosen from "
            "role, location, institution, rare_event, schedule, family, medical, financial, legal, affiliation, coarse_context. "
            "No markdown, no prose, no evidence quotes."
        )
    else:
        output_rule = (
            "Return JSON with keys top_1_candidate_id, ranked_candidates, uncertain, "
            "and most_important_signals. ranked_candidates should list candidate_id and score."
        )
    prompt = (
        "ANONYMIZED DOCUMENTS:\n"
        f"{doc_text}\n\n"
        "CANDIDATE PROFILES:\n"
        f"{profiles}\n\n"
        f"{output_rule}"
    )
    return instructions, prompt


def run_aux_matching(
    caller: CachedOpenAI,
    paths: Any,
    personas: list[dict[str, Any]],
    persona_ids: set[str],
    conditions: list[str],
    run_name: str,
    compact_output: bool,
    aux_max_output_tokens: int,
) -> pd.DataFrame:
    persona_by_id = {p["persona_id"]: p for p in personas}
    candidate_rows = read_jsonl(paths.data / "candidate_sets.jsonl")
    candidate_by_id = {row["persona_id"]: row["candidate_ids"] for row in candidate_rows}
    rows = []
    for condition in conditions:
        docs = read_jsonl(transformed_condition_path(paths, condition))
        docs_by_pid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in docs:
            if doc["persona_id"] in persona_ids:
                docs_by_pid[doc["persona_id"]].append(doc)
        for pid in sorted(persona_ids):
            if pid not in docs_by_pid:
                continue
            instructions, prompt = aux_match_prompt(
                docs_by_pid[pid],
                candidate_by_id[pid],
                persona_by_id,
                compact_output=compact_output,
            )
            result = caller.call(
                f"aux_match::{condition}",
                instructions,
                prompt,
                max_output_tokens=aux_max_output_tokens,
            )
            parsed = result.get("parsed") if isinstance(result.get("parsed"), dict) else {}
            ranked = parsed.get("ranked_candidates") if isinstance(parsed, dict) else []
            ranked_ids = []
            if isinstance(ranked, list):
                for item in ranked:
                    if isinstance(item, str):
                        ranked_ids.append(item)
                    elif isinstance(item, dict) and "candidate_id" in item:
                        ranked_ids.append(str(item["candidate_id"]))
            top = parsed.get("top_1_candidate_id") if isinstance(parsed, dict) else None
            if not top and ranked_ids:
                top = ranked_ids[0]
            if top and top not in ranked_ids:
                ranked_ids.insert(0, str(top))
            rank = ranked_ids.index(pid) + 1 if pid in ranked_ids else None
            scores = candidate_scores(ranked)
            ordered_scores = [scores[cid] for cid in ranked_ids if cid in scores]
            margin = None
            if len(ordered_scores) >= 2:
                margin = ordered_scores[0] - ordered_scores[1]
            if isinstance(parsed, dict):
                signals = parsed.get("most_important_signals", parsed.get("top_signals"))
                confidence = as_float(parsed.get("confidence"))
            else:
                signals = None
                confidence = None
            top_score = scores.get(str(top)) if top else None
            if top_score is None:
                top_score = confidence
            rows.append(
                {
                    "model": caller.model,
                    "run_name": run_name,
                    "condition": condition,
                    "persona_id": pid,
                    "risk_tier": persona_by_id[pid]["risk_tier"],
                    "top_1_candidate_id": top,
                    "rank": rank,
                    "top1": int(rank == 1) if rank else 0,
                    "top3": int(rank is not None and rank <= 3),
                    "reciprocal_rank": (1.0 / rank) if rank else 0.0,
                    "top_1_score": top_score,
                    "target_score": scores.get(pid),
                    "top_score_margin": margin,
                    "uncertain": parsed.get("uncertain") if isinstance(parsed, dict) else None,
                    "ranked_candidates_json": json.dumps(ranked, sort_keys=True) if isinstance(ranked, list) else "",
                    "most_important_signals_json": json.dumps(signals, sort_keys=True)
                    if signals is not None
                    else "",
                    "raw_text": result.get("text", ""),
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(openai_result_path(paths, run_name, "aux_match_rows", "csv"), index=False)
    if not df.empty:
        summary = (
            df.groupby(["condition", "risk_tier"], dropna=False)
            .agg(
                n=("persona_id", "count"),
                top1=("top1", "mean"),
                top3=("top3", "mean"),
                mrr=("reciprocal_rank", "mean"),
                mean_rank=("rank", "mean"),
                median_top_1_score=("top_1_score", "median"),
                median_top_score_margin=("top_score_margin", "median"),
                uncertain_rate=("uncertain", "mean"),
            )
            .reset_index()
        )
        summary.to_csv(openai_result_path(paths, run_name, "aux_match_summary", "csv"), index=False)
        openai_result_path(paths, run_name, "aux_match_summary", "md").write_text(
            dataframe_to_markdown(summary, floatfmt=".3f") + "\n",
            encoding="utf-8",
        )
    return df


def plan_call(
    rows: list[dict[str, Any]],
    cache_dir: Path,
    model: str,
    reasoning_effort: str,
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
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
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
            "reasoning_effort": reasoning_effort,
            "note": "",
        }
    )


def build_audit_plan(
    paths: Any,
    model: str,
    reasoning_effort: str,
    personas: list[dict[str, Any]],
    persona_ids: list[str],
    tasks: set[str],
    conditions: list[str],
    doc_local_condition: str,
    compact_output: bool,
    aux_max_output_tokens: int,
) -> pd.DataFrame:
    cache_dir = paths.root / "cache" / "api_responses"
    persona_id_set = set(persona_ids)
    persona_by_id = {p["persona_id"]: p for p in personas}
    candidate_rows = read_jsonl(paths.data / "candidate_sets.jsonl")
    candidate_by_id = {row["persona_id"]: row["candidate_ids"] for row in candidate_rows}
    rows: list[dict[str, Any]] = []

    needs_doc_local = "doc-local" in tasks or doc_local_condition in conditions
    if needs_doc_local:
        for doc in read_jsonl(paths.transformed / "original.jsonl"):
            if doc["persona_id"] not in persona_id_set:
                continue
            instructions, prompt = anonymize_prompt(doc)
            plan_call(
                rows,
                cache_dir,
                model,
                reasoning_effort,
                "doc_local_anonymize",
                doc["persona_id"],
                doc_local_condition,
                instructions,
                prompt,
                550,
            )

    if "aux-match" in tasks:
        for condition in conditions:
            condition_path = transformed_condition_path(paths, condition)
            if condition == doc_local_condition and not condition_path.exists():
                for pid in persona_ids:
                    rows.append(
                        {
                            "task": f"aux_match::{condition}",
                            "condition": condition,
                            "persona_id": pid,
                            "cache_key": "",
                            "cached": False,
                            "input_chars": 0,
                            "max_output_tokens": aux_max_output_tokens,
                            "reasoning_effort": reasoning_effort,
                            "note": "requires doc-local output before prompt can be hashed",
                        }
                    )
                continue
            if not condition_path.exists():
                for pid in persona_ids:
                    rows.append(
                        {
                            "task": f"aux_match::{condition}",
                            "condition": condition,
                            "persona_id": pid,
                            "cache_key": "",
                            "cached": False,
                            "input_chars": 0,
                            "max_output_tokens": aux_max_output_tokens,
                            "reasoning_effort": reasoning_effort,
                            "note": f"missing transformed condition: {condition_path.as_posix()}",
                        }
                    )
                continue
            docs = read_jsonl(condition_path)
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
                            "max_output_tokens": aux_max_output_tokens,
                            "reasoning_effort": reasoning_effort,
                            "note": "requires condition output for this persona before prompt can be hashed",
                        }
                    )
                    continue
                instructions, prompt = aux_match_prompt(
                    docs_by_pid[pid],
                    candidate_by_id[pid],
                    persona_by_id,
                    compact_output=compact_output,
                )
                plan_call(
                    rows,
                    cache_dir,
                    model,
                    reasoning_effort,
                    f"aux_match::{condition}",
                    pid,
                    condition,
                    instructions,
                    prompt,
                    aux_max_output_tokens,
                )
    return pd.DataFrame(rows)


def write_audit_plan(
    paths: Any,
    plan: pd.DataFrame,
    model: str,
    persona_ids: list[str],
    run_name: str,
    conditions: list[str],
    reasoning_effort: str,
    compact_output: bool,
    aux_max_output_tokens: int,
) -> Path:
    plan_path = openai_result_path(paths, run_name, "audit_plan", "csv")
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
        f"Run name: `{run_name or 'legacy'}`",
        f"Model: `{model}`",
        f"Reasoning effort: `{reasoning_effort or 'default'}`",
        f"Aux compact output: `{compact_output}`",
        f"Aux max output tokens: `{aux_max_output_tokens}`",
        f"Git commit: `{git_commit(paths.root)}`",
        f"Conditions: {', '.join(conditions)}",
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
    openai_result_path(paths, run_name, "audit_plan", "md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return plan_path


def write_audit_notes(
    paths: Any,
    model: str,
    caller: CachedOpenAI,
    persona_ids: list[str],
    run_name: str,
    tasks: set[str],
    conditions: list[str],
    started_at_utc: str,
    reasoning_effort: str,
    compact_output: bool,
    aux_max_output_tokens: int,
) -> Path:
    usage = pd.DataFrame(caller.usage_rows)
    usage_path = openai_result_path(paths, run_name, "audit_usage", "csv")
    usage.to_csv(usage_path, index=False)
    total_in = int(usage["input_tokens"].sum()) if not usage.empty else 0
    total_out = int(usage["output_tokens"].sum()) if not usage.empty else 0
    total = int(usage["total_tokens"].sum()) if not usage.empty else 0
    lines = [
        "# OpenAI Audit Notes",
        "",
        f"Run name: `{run_name or 'legacy'}`",
        f"Model: `{model}`",
        f"Reasoning effort: `{reasoning_effort or 'default'}`",
        f"Aux compact output: `{compact_output}`",
        f"Aux max output tokens: `{aux_max_output_tokens}`",
        f"Started at UTC: `{started_at_utc}`",
        f"Git commit: `{git_commit(paths.root)}`",
        f"Tasks: {', '.join(sorted(tasks))}",
        f"Conditions: {', '.join(conditions)}",
        f"Persona count: {len(persona_ids)}",
        f"Personas audited: {', '.join(persona_ids)}",
        f"New API calls this run: {caller.new_calls}",
        f"Cached calls served this run: {caller.cached_calls}",
        f"Token usage: {total_in} input, {total_out} output, {total} total.",
        f"Usage CSV: `{display_path(usage_path, paths.root)}`",
        "",
        "Cached response files are under `cache/api_responses/`.",
        "All OpenAI response calls in this script pass `store=False`.",
    ]
    summary_path = openai_result_path(paths, run_name, "aux_match_summary", "md")
    if summary_path.exists():
        lines.extend(["", "## Auxiliary Matching Summary", "", summary_path.read_text(encoding="utf-8")])
    notes_path = openai_result_path(paths, run_name, "audit_notes", "md")
    notes_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return notes_path


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
    parser.add_argument("--run-name", default="")
    parser.add_argument("--doc-local-condition", default="")
    parser.add_argument("--reasoning-effort", default="")
    parser.add_argument("--aux-compact-output", action="store_true")
    parser.add_argument("--aux-max-output-tokens", type=int, default=800)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    run_name = sanitize_run_name(args.run_name)
    doc_local_condition = doc_local_condition_name(run_name, args.doc_local_condition)
    started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
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
        plan = build_audit_plan(
            paths,
            model,
            args.reasoning_effort.strip(),
            personas,
            persona_ids,
            tasks,
            conditions,
            doc_local_condition,
            args.aux_compact_output,
            args.aux_max_output_tokens,
        )
        plan_path = write_audit_plan(
            paths,
            plan,
            model,
            persona_ids,
            run_name,
            conditions,
            args.reasoning_effort.strip(),
            args.aux_compact_output,
            args.aux_max_output_tokens,
        )
        missing = int((~plan["cached"]).sum()) if not plan.empty else 0
        print(f"model={model}")
        print(f"run_name={run_name or 'legacy'}")
        print(f"personas={','.join(persona_ids)}")
        print(f"planned_calls={len(plan)}")
        print(f"cached_calls={int(plan['cached'].sum()) if not plan.empty else 0}")
        print(f"missing_or_dependent_calls={missing}")
        print(f"plan={plan_path}")
        return
    caller = CachedOpenAI(
        client=client,
        model=model,
        cache_dir=paths.root / "cache" / "api_responses",
        max_calls=args.max_calls,
        dry_run=args.dry_run,
        reasoning_effort=args.reasoning_effort.strip(),
    )
    persona_id_set = set(persona_ids)
    if "doc-local" in tasks:
        run_doc_local_anonymization(caller, paths, persona_id_set, doc_local_condition)
    if "aux-match" in tasks:
        if doc_local_condition in conditions and not doc_local_path(paths, doc_local_condition).exists():
            run_doc_local_anonymization(caller, paths, persona_id_set, doc_local_condition)
        run_aux_matching(
            caller,
            paths,
            personas,
            persona_id_set,
            conditions,
            run_name,
            args.aux_compact_output,
            args.aux_max_output_tokens,
        )
    notes_path = write_audit_notes(
        paths,
        model,
        caller,
        persona_ids,
        run_name,
        tasks,
        conditions,
        started_at_utc,
        args.reasoning_effort.strip(),
        args.aux_compact_output,
        args.aux_max_output_tokens,
    )
    print(f"model={model}")
    print(f"run_name={run_name or 'legacy'}")
    print(f"personas={','.join(persona_ids)}")
    print(f"new_calls={caller.new_calls}")
    print(f"cached_calls={caller.cached_calls}")
    print(f"notes={notes_path}")


if __name__ == "__main__":
    main()
