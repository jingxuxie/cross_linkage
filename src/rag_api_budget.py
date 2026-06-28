#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from crossdoc_pipeline import dataframe_to_markdown, load_config


DEFAULT_RUN_NAME = "gpt55_rag_12t3"
DEFAULT_PILOT_RUN = "gpt55_rag_compact_pilot_2t3"
BATCH_COLUMNS = [
    "batch_id",
    "batch_run_name",
    "persona_ids",
    "new_calls",
    "selected_calls",
    "conditions",
    "estimated_input_tokens",
    "estimated_output_tokens",
    "estimated_total_tokens",
    "mean_input_chars",
    "command",
]


def artifact(results_dir: Path, run_name: str, suffix: str) -> Path:
    return results_dir / f"openai_{run_name}_{suffix}"


def command_for_batch(
    persona_ids: list[str],
    batch_run_name: str,
    model: str,
    tier: str,
    max_calls: int,
) -> str:
    return (
        "conda run -n cross_linkage python src/openai_rag_audit.py "
        "--config configs/sprint.yaml "
        "--api-key-file /path/to/apikey.txt "
        f"--model {model} "
        f"--run-name {batch_run_name} "
        f"--persona-ids {','.join(persona_ids)} "
        f"--tier {tier} "
        f"--max-calls {max_calls} "
        "--reasoning-effort none "
        "--max-output-tokens 250"
    )


def estimate_tokens(plan: pd.DataFrame, pilot_plan: pd.DataFrame, pilot_usage: pd.DataFrame) -> pd.DataFrame:
    usage = pilot_usage.merge(
        pilot_plan[["cache_key", "condition", "input_chars"]],
        on="cache_key",
        how="left",
    )
    usage["input_tokens_per_char"] = usage["input_tokens"] / usage["input_chars"].clip(lower=1)
    by_condition = usage.groupby("condition", sort=False).agg(
        input_tokens_per_char=("input_tokens_per_char", "mean"),
        output_tokens_per_call=("output_tokens", "mean"),
        total_tokens_per_call=("total_tokens", "mean"),
    )
    global_ratio = float(usage["input_tokens"].sum() / usage["input_chars"].clip(lower=1).sum())
    global_output = float(usage["output_tokens"].mean())
    rows = []
    for _, row in plan.iterrows():
        condition = row["condition"]
        if condition in by_condition.index:
            input_ratio = float(by_condition.loc[condition, "input_tokens_per_char"])
            output_tokens = float(by_condition.loc[condition, "output_tokens_per_call"])
        else:
            input_ratio = global_ratio
            output_tokens = global_output
        input_tokens = float(row["input_chars"]) * input_ratio
        rows.append(
            {
                **row.to_dict(),
                "estimated_input_tokens": round(input_tokens),
                "estimated_output_tokens": round(output_tokens),
                "estimated_total_tokens": round(input_tokens + output_tokens),
            }
        )
    return pd.DataFrame(rows)


def build_batches(
    estimated: pd.DataFrame,
    batch_personas: int,
    baseline_cached_personas: set[str],
) -> pd.DataFrame:
    persona_order = [
        persona_id
        for persona_id in dict.fromkeys(estimated["persona_id"].tolist())
        if persona_id not in baseline_cached_personas
    ]
    batch_rows = []
    for batch_index, start in enumerate(range(0, len(persona_order), batch_personas), start=1):
        personas = persona_order[start : start + batch_personas]
        group = estimated[estimated["persona_id"].isin(personas)]
        pending_group = group[~group["cached"].astype(bool)]
        if pending_group.empty:
            continue
        batch_rows.append(
            {
                "batch_id": f"batch{batch_index:02d}",
                "batch_run_name": f"{DEFAULT_RUN_NAME}_batch{batch_index:02d}",
                "persona_ids": ",".join(personas),
                "new_calls": len(pending_group),
                "selected_calls": len(group),
                "conditions": group["condition"].nunique(),
                "estimated_input_tokens": int(pending_group["estimated_input_tokens"].sum()),
                "estimated_output_tokens": int(pending_group["estimated_output_tokens"].sum()),
                "estimated_total_tokens": int(pending_group["estimated_total_tokens"].sum()),
                "mean_input_chars": round(float(pending_group["input_chars"].mean()), 1),
                "command": command_for_batch(
                    personas,
                    f"{DEFAULT_RUN_NAME}_batch{batch_index:02d}",
                    str(group["model"].iloc[0]) if "model" in group.columns else "gpt-5.5",
                    str(group["risk_tier"].iloc[0]),
                    len(group),
                ),
            }
        )
    return pd.DataFrame(batch_rows, columns=BATCH_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--pilot-run-name", default=DEFAULT_PILOT_RUN)
    parser.add_argument("--batch-personas", type=int, default=2)
    parser.add_argument("--model", default="gpt-5.5")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    root = Path.cwd()
    results_dir = root / cfg["results_dir"]
    plan_path = artifact(results_dir, args.run_name, "audit_plan.csv")
    pilot_plan_path = artifact(results_dir, args.pilot_run_name, "audit_plan.csv")
    pilot_usage_path = artifact(results_dir, args.pilot_run_name, "audit_usage.csv")
    plan = pd.read_csv(plan_path)
    plan["model"] = args.model
    pilot_plan = pd.read_csv(pilot_plan_path)
    pilot_usage = pd.read_csv(pilot_usage_path)
    estimated = estimate_tokens(plan, pilot_plan, pilot_usage)
    pending = estimated[~estimated["cached"].astype(bool)].copy()
    baseline_cached_personas = set(pilot_plan["persona_id"].astype(str).unique())
    batches = build_batches(estimated, args.batch_personas, baseline_cached_personas)

    out_csv = artifact(results_dir, args.run_name, "budget.csv")
    out_md = artifact(results_dir, args.run_name, "budget.md")
    batches.to_csv(out_csv, index=False)

    display = batches.drop(columns=["command"], errors="ignore").copy()
    lines = [
        "# GPT-5.5 RAG Generation Budget Plan",
        "",
        "This report makes no API calls. It uses the full RAG-generation plan and the cached compact pilot usage to estimate the remaining cache-fill batches.",
        "",
        f"Full run: `{args.run_name}`.",
        f"Pilot usage source: `{pilot_usage_path.relative_to(root)}`.",
        f"Cached calls in full plan: {int(plan['cached'].astype(bool).sum())}/{len(plan)}.",
        f"Remaining calls: {len(pending)}.",
        f"Recommended batches: {len(batches)} batches of at most {int(batches['new_calls'].max()) if not batches.empty else 0} new calls.",
        f"Estimated remaining total tokens: {int(batches['estimated_total_tokens'].sum()) if not batches.empty else 0}.",
        "",
        dataframe_to_markdown(display, floatfmt=".1f") if not display.empty else "_No pending calls._",
        "",
        "## Batch Commands",
        "",
        "Use one command at a time only after explicit approval for paid API calls. Each batch uses a batch-specific run name while filling the shared response cache; after all batches are cached, rerun the full `gpt55_rag_12t3` command to produce the paper-facing 60-call summary from cache.",
        "",
    ]
    for _, row in batches.iterrows():
        lines.extend(
            [
                f"### {row['batch_id']}",
                "",
                "```bash",
                row["command"],
                "```",
                "",
            ]
        )
    out_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(out_csv)
    print(out_md)


if __name__ == "__main__":
    main()
