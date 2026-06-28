#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from crossdoc_pipeline import dataframe_to_markdown, load_config


@dataclass(frozen=True)
class AuditRun:
    run_id: str
    label: str
    model: str
    task_family: str
    plan_path: str
    usage_path: str
    notes_path: str
    primary_outputs: tuple[str, ...]
    script: str
    paper_claim_status: str
    boundary_note: str


RUNS = [
    AuditRun(
        run_id="legacy_openai_aux_doclocal",
        label="Legacy small OpenAI audit",
        model="gpt-5.4-nano",
        task_family="doc-local, aux-match",
        plan_path="results/openai_audit_plan.csv",
        usage_path="results/openai_audit_usage.csv",
        notes_path="results/openai_audit_notes.md",
        primary_outputs=("results/openai_aux_match_summary.csv",),
        script="src/openai_audit.py",
        paper_claim_status="legacy_small_cached_audit_not_main_claim",
        boundary_note="Historical cached 12-person audit; retained as a small sanity check.",
    ),
    AuditRun(
        run_id="gpt55_aux_48p",
        label="GPT-5.5 auxiliary matching",
        model="gpt-5.5",
        task_family="aux-match",
        plan_path="results/openai_gpt55_48p_audit_plan.csv",
        usage_path="results/openai_gpt55_48p_audit_usage.csv",
        notes_path="results/openai_gpt55_48p_audit_notes.md",
        primary_outputs=(
            "results/openai_gpt55_48p_aux_match_rows.csv",
            "results/openai_gpt55_48p_aux_match_summary.csv",
        ),
        script="src/openai_audit.py",
        paper_claim_status="paper_facing_cached_stress_audit",
        boundary_note="Corroborating time-stamped stress audit, not the main statistical evidence.",
    ),
    AuditRun(
        run_id="gpt55_doclocal_24p",
        label="GPT-5.5 document-local baseline",
        model="gpt-5.5",
        task_family="doc-local, aux-match",
        plan_path="results/openai_gpt55_doclocal_24p_audit_plan.csv",
        usage_path="results/openai_gpt55_doclocal_24p_audit_usage.csv",
        notes_path="results/openai_gpt55_doclocal_24p_audit_notes.md",
        primary_outputs=(
            "data/transformed/c4_openai_doc_local_gpt55_24p.jsonl",
            "results/openai_gpt55_doclocal_24p_aux_match_rows.csv",
            "results/openai_gpt55_doclocal_24p_aux_match_summary.csv",
        ),
        script="src/openai_audit.py",
        paper_claim_status="paper_facing_cached_stress_audit",
        boundary_note="Corroborating document-local LLM baseline on a synthetic subset.",
    ),
    AuditRun(
        run_id="gpt55_evidence_24p",
        label="GPT-5.5 evidence extraction",
        model="gpt-5.5",
        task_family="evidence extraction",
        plan_path="results/openai_gpt55_evidence_24p_audit_plan.csv",
        usage_path="results/openai_gpt55_evidence_24p_audit_usage.csv",
        notes_path="results/openai_gpt55_evidence_24p_audit_notes.md",
        primary_outputs=(
            "results/openai_gpt55_evidence_24p_evidence_rows.csv",
            "results/openai_gpt55_evidence_24p_evidence_summary.csv",
        ),
        script="src/openai_evidence_audit.py",
        paper_claim_status="paper_facing_cached_qualitative_stress_audit",
        boundary_note="Qualitative signal audit over selected synthetic cases.",
    ),
    AuditRun(
        run_id="gpt55_rag_12t3_plan",
        label="GPT-5.5 RAG generation 12-person plan",
        model="gpt-5.5",
        task_family="RAG generation",
        plan_path="results/openai_gpt55_rag_12t3_audit_plan.csv",
        usage_path="",
        notes_path="results/openai_gpt55_rag_12t3_audit_plan.md",
        primary_outputs=(),
        script="src/openai_rag_audit.py",
        paper_claim_status="planned_not_paper_claim_pending_calls",
        boundary_note="Full 12-person RAG-generation audit has pending calls and is not claimed.",
    ),
    AuditRun(
        run_id="gpt55_rag_compact_pilot_2t3",
        label="GPT-5.5 RAG generation compact pilot",
        model="gpt-5.5",
        task_family="RAG generation",
        plan_path="results/openai_gpt55_rag_compact_pilot_2t3_audit_plan.csv",
        usage_path="results/openai_gpt55_rag_compact_pilot_2t3_audit_usage.csv",
        notes_path="results/openai_gpt55_rag_compact_pilot_2t3_audit_notes.md",
        primary_outputs=(
            "results/openai_gpt55_rag_compact_pilot_2t3_rag_generation_rows.csv",
            "results/openai_gpt55_rag_compact_pilot_2t3_rag_generation_summary.csv",
        ),
        script="src/openai_rag_audit.py",
        paper_claim_status="compact_pilot_not_paper_claim",
        boundary_note="Cached 2-person parsing pilot only; not a paper generation result.",
    ),
]


def discover_rag_batch_runs(results_dir: Path) -> list[AuditRun]:
    batch_runs = []
    for plan_path in sorted(results_dir.glob("openai_gpt55_rag_12t3_batch*_audit_plan.csv")):
        match = re.search(r"openai_(gpt55_rag_12t3_batch\d+)_audit_plan\.csv$", plan_path.name)
        if not match:
            continue
        run_name = match.group(1)
        batch_id = run_name.rsplit("batch", maxsplit=1)[-1]
        batch_runs.append(
            AuditRun(
                run_id=run_name,
                label=f"GPT-5.5 RAG generation cache-fill batch {batch_id}",
                model="gpt-5.5",
                task_family="RAG generation",
                plan_path=f"results/openai_{run_name}_audit_plan.csv",
                usage_path=f"results/openai_{run_name}_audit_usage.csv",
                notes_path=f"results/openai_{run_name}_audit_notes.md",
                primary_outputs=(
                    f"results/openai_{run_name}_rag_generation_rows.csv",
                    f"results/openai_{run_name}_rag_generation_summary.csv",
                ),
                script="src/openai_rag_audit.py",
                paper_claim_status="partial_cache_fill_not_paper_claim",
                boundary_note=(
                    "Completed 10-call batch that fills the shared 12-person RAG cache; "
                    "not a standalone paper claim."
                ),
            )
        )
    return batch_runs


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def note_value(notes: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s+`?([^`\n]+)`?", notes, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def note_int(notes: str, label: str) -> int | None:
    value = note_value(notes, label)
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def values_joined(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns:
        return ""
    values = sorted({str(value) for value in frame[column].dropna().unique() if str(value)})
    return "|".join(values)


def usage_totals(path: Path) -> dict[str, int]:
    if not path.exists():
        return {
            "usage_rows": 0,
            "usage_input_tokens": 0,
            "usage_output_tokens": 0,
            "usage_total_tokens": 0,
        }
    usage = pd.read_csv(path)
    return {
        "usage_rows": len(usage),
        "usage_input_tokens": int(usage.get("input_tokens", pd.Series(dtype=int)).sum()),
        "usage_output_tokens": int(usage.get("output_tokens", pd.Series(dtype=int)).sum()),
        "usage_total_tokens": int(usage.get("total_tokens", pd.Series(dtype=int)).sum()),
    }


def summarize_run(root: Path, spec: AuditRun) -> dict[str, object]:
    plan_file = root / spec.plan_path
    plan = pd.read_csv(plan_file)
    notes = read_text(root / spec.notes_path)
    usage = (
        usage_totals(root / spec.usage_path)
        if spec.usage_path
        else {
            "usage_rows": 0,
            "usage_input_tokens": 0,
            "usage_output_tokens": 0,
            "usage_total_tokens": 0,
        }
    )
    cached_calls = int(plan["cached"].astype(bool).sum()) if "cached" in plan.columns else 0
    planned_calls = len(plan)
    missing_calls = planned_calls - cached_calls
    outputs = [path for path in spec.primary_outputs if (root / path).exists()]
    note_model = note_value(notes, "Model")
    return {
        "run_id": spec.run_id,
        "label": spec.label,
        "model": note_model or spec.model,
        "task_family": spec.task_family,
        "paper_claim_status": spec.paper_claim_status,
        "planned_calls": planned_calls,
        "cached_calls": cached_calls,
        "missing_calls": missing_calls,
        "cache_complete": missing_calls == 0,
        "usage_rows": usage["usage_rows"],
        "usage_input_tokens": usage["usage_input_tokens"],
        "usage_output_tokens": usage["usage_output_tokens"],
        "usage_total_tokens": usage["usage_total_tokens"],
        "persona_count": plan["persona_id"].nunique() if "persona_id" in plan.columns else 0,
        "condition_count": plan["condition"].nunique() if "condition" in plan.columns else 0,
        "max_output_tokens": values_joined(plan, "max_output_tokens"),
        "reasoning_effort": values_joined(plan, "reasoning_effort"),
        "text_format": values_joined(plan, "text_format"),
        "started_utc": note_value(notes, "Started at UTC"),
        "artifact_git_commit": note_value(notes, "Git commit"),
        "new_api_calls_recorded_in_notes": note_int(notes, "New API calls this run"),
        "cached_calls_recorded_in_notes": note_int(notes, "Cached calls served this run"),
        "store_false_protocol": True,
        "data_scope": "synthetic transformed benchmark records only",
        "script": spec.script,
        "plan_artifact": spec.plan_path,
        "usage_artifact": spec.usage_path,
        "notes_artifact": spec.notes_path,
        "primary_outputs_present": ";".join(outputs),
        "boundary_note": spec.boundary_note,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    args = parser.parse_args()

    root = Path.cwd()
    cfg = load_config(Path(args.config))
    results_dir = root / cfg["results_dir"]
    results_dir.mkdir(parents=True, exist_ok=True)

    rows = [summarize_run(root, spec) for spec in [*RUNS, *discover_rag_batch_runs(results_dir)]]
    frame = pd.DataFrame(rows)
    csv_path = results_dir / "api_audit_provenance.csv"
    md_path = results_dir / "api_audit_provenance.md"
    frame.to_csv(csv_path, index=False)

    display_columns = [
        "run_id",
        "model",
        "paper_claim_status",
        "planned_calls",
        "cached_calls",
        "missing_calls",
        "usage_total_tokens",
        "persona_count",
        "condition_count",
        "store_false_protocol",
        "boundary_note",
    ]
    display = frame[display_columns].copy()
    display["store_false_protocol"] = display["store_false_protocol"].map({True: "true", False: "false"})
    lines = [
        "# API Audit Provenance",
        "",
        "Generated from existing local plan, usage, and note artifacts. This command makes no API calls.",
        "",
        "All listed API scripts route live calls through `CachedOpenAI` with `store=False`; cached artifacts are synthetic transformed benchmark records only.",
        "",
        "## Summary",
        "",
        dataframe_to_markdown(display, floatfmt=".3f"),
        "",
        "## Artifact Columns",
        "",
        "The CSV adds run labels, task family, note timestamps, artifact git commits, token usage totals, source scripts, and primary output paths.",
        "",
        f"CSV artifact: `{csv_path.relative_to(root)}`.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(csv_path)
    print(md_path)


if __name__ == "__main__":
    main()
