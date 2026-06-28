#!/usr/bin/env python
from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "cache/matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from attack_sensitivity import aux_match_with_attack
from crossdoc_pipeline import (
    dataframe_to_markdown,
    evaluate_condition,
    linkguard_replacements,
    load_config,
    make_paths,
    read_jsonl,
    replace_many,
    split_personas,
    train_utility_classifiers,
    write_jsonl,
)


def transform_for_target_k(
    docs: list[dict],
    replacements_by_pid: dict[str, list[tuple[str, str]]],
    condition: str,
) -> tuple[list[dict], float]:
    rows = []
    edit_ratios = []
    for doc in docs:
        text = replace_many(doc["text"], replacements_by_pid[doc["persona_id"]])
        rows.append({**doc, "text": text, "condition": condition})
        edit_ratios.append(1.0 - difflib.SequenceMatcher(None, doc["text"], text).ratio())
    return rows, float(np.mean(edit_ratios))


def summarize_log(log_rows: list[dict]) -> dict[str, float]:
    estimated = np.array([row["estimated_k"] for row in log_rows], dtype=float)
    edits = np.array([len(row["generalized_fields"]) for row in log_rows], dtype=float)
    return {
        "min_estimated_k": float(estimated.min()),
        "median_estimated_k": float(np.median(estimated)),
        "mean_steps": float(edits.mean()),
        "max_steps": float(edits.max()),
    }


def make_plot(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(7.2, 4.6))
    ax1.plot(df["target_k"], df["aux_top1"], marker="o", color="#2ca02c", label="Aux top-1")
    if "field_aux_top1" in df.columns:
        ax1.plot(
            df["target_k"],
            df["field_aux_top1"],
            marker="D",
            color="#d62728",
            label="Field Aux top-1",
        )
    ax1.plot(df["target_k"], df["pair_f1"], marker="s", color="#1f77b4", label="Pair F1")
    ax1.set_xlabel("LinkGuard target k")
    ax1.set_ylabel("Attack success (lower is better)")
    attack_cols = [col for col in ["aux_top1", "field_aux_top1", "pair_f1"] if col in df.columns]
    ax1.set_ylim(0, max(0.8, float(df[attack_cols].max().max()) + 0.05))
    ax1.grid(alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(df["target_k"], df["edit_ratio"], marker="^", color="#7f7f7f", label="Edit ratio")
    ax2.set_ylabel("Edit ratio")
    ax2.set_ylim(0, min(1.0, float(df["edit_ratio"].max()) + 0.15))

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="center right", fontsize=8)
    plt.title("LinkGuard sensitivity to target k", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def run_sensitivity(config_path: Path, target_ks: list[int]) -> None:
    cfg = load_config(config_path)
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    docs = read_jsonl(paths.data / "original_docs.jsonl")
    candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    split = split_personas(personas)
    utility_clf = train_utility_classifiers(read_jsonl(paths.data / "original_docs.jsonl"))

    rows = []
    tier_rows = []
    field_rows = []
    for target_k in target_ks:
        condition = f"c5_linkguard_k{target_k}"
        log_name = f"linkguard_sensitivity_k{target_k}_log.jsonl"
        replacements = linkguard_replacements(personas, target_k, paths, log_name=log_name)
        transformed, edit_ratio = transform_for_target_k(docs, replacements, condition)
        write_jsonl(paths.transformed / f"{condition}.jsonl", transformed)
        row, _, by_tier, _ = evaluate_condition(
            condition,
            transformed,
            personas,
            candidates,
            split,
            utility_clf,
            paths,
        )
        field_metrics, field_detail = aux_match_with_attack(
            transformed,
            personas,
            candidates,
            split["test"],
            "field_weighted",
        )
        row["edit_ratio"] = edit_ratio
        row["target_k"] = target_k
        row.update({f"field_{key}": value for key, value in field_metrics.items()})
        row.update(summarize_log(read_jsonl(paths.results / log_name)))
        rows.append(row)
        for field_row in field_detail:
            field_row["target_k"] = target_k
            field_row["condition"] = condition
        field_rows.extend(field_detail)
        for tier_row in by_tier:
            tier_row["target_k"] = target_k
        tier_rows.extend(by_tier)

    df = pd.DataFrame(rows).sort_values("target_k")
    tier_df = pd.DataFrame(tier_rows).sort_values(["target_k", "risk_tier"])
    df.to_csv(paths.results / "linkguard_sensitivity.csv", index=False)
    tier_df.to_csv(paths.results / "linkguard_sensitivity_by_tier.csv", index=False)
    pd.DataFrame(field_rows).sort_values(["target_k", "persona_id"]).to_csv(
        paths.results / "linkguard_sensitivity_field_rows.csv",
        index=False,
    )
    compact_cols = [
        "target_k",
        "min_estimated_k",
        "median_estimated_k",
        "mean_steps",
        "edit_ratio",
        "pair_f1",
        "aux_top1",
        "aux_top3",
        "field_aux_top1",
        "field_aux_top3",
        "attr_exact_recovery",
        "attr_coarse_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
        "fact_preservation",
    ]
    compact = df[compact_cols].copy()
    (paths.results / "linkguard_sensitivity.md").write_text(
        dataframe_to_markdown(compact, floatfmt=".3f") + "\n",
        encoding="utf-8",
    )
    make_plot(compact, paths.results / "linkguard_sensitivity.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--target-ks", default="1,2,3,5,8,12,20")
    args = parser.parse_args()
    target_ks = [int(value) for value in args.target_ks.split(",") if value.strip()]
    run_sensitivity(Path(args.config), target_ks)


if __name__ == "__main__":
    main()
