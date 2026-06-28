#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from crossdoc_pipeline import (
    dataframe_to_markdown,
    evaluate_all,
    generate_all,
    load_config,
    make_paths,
    validate_outputs,
)


KEY_METRICS = [
    "pair_f1",
    "fixedk_ari",
    "aux_top1",
    "aux_top3",
    "attr_exact_recovery",
    "attr_coarse_recovery",
    "issue_acc",
    "retrieval_recall_at_5",
    "fact_preservation",
    "edit_ratio",
]


FOCUS_CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]


def seed_config(base_cfg: dict[str, Any], seed: int, out_dir: Path) -> dict[str, Any]:
    cfg = dict(base_cfg)
    cfg["seed"] = seed
    run_root = out_dir / "work" / f"seed_{seed}"
    cfg["data_dir"] = str(run_root / "data")
    cfg["results_dir"] = str(run_root / "results")
    return cfg


def run_one_seed(base_cfg: dict[str, Any], seed: int, out_dir: Path) -> pd.DataFrame:
    cfg = seed_config(base_cfg, seed, out_dir)
    paths = make_paths(cfg)
    generate_all(cfg, paths)
    validate_outputs(cfg, paths)
    evaluate_all(cfg, paths)
    df = pd.read_csv(paths.results / "main_results.csv")
    df.insert(0, "seed", seed)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("condition", sort=False)[KEY_METRICS]
        .agg(["mean", "std"])
        .reset_index()
    )
    summary.columns = [
        col[0] if col[1] == "" else f"{col[0]}_{col[1]}"
        for col in summary.columns.to_flat_index()
    ]
    return summary


def claim_summary(summary: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition",
        "aux_top1_mean",
        "aux_top1_std",
        "attr_exact_recovery_mean",
        "attr_exact_recovery_std",
        "issue_acc_mean",
        "retrieval_recall_at_5_mean",
        "edit_ratio_mean",
    ]
    return summary[summary["condition"].isin(FOCUS_CONDITIONS)][cols].copy()


def write_outputs(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(df)
    claims = claim_summary(summary)

    df.to_csv(out_dir / "main_results_by_seed.csv", index=False)
    summary.to_csv(out_dir / "main_results_summary.csv", index=False)
    claims.to_csv(out_dir / "claim_summary.csv", index=False)

    lines = [
        "# Multi-Seed Robustness Sweep",
        "",
        f"Seeds: {', '.join(str(seed) for seed in sorted(df['seed'].unique()))}.",
        "",
        "## Claim-Focused Summary",
        "",
        dataframe_to_markdown(claims, floatfmt=".3f"),
        "",
        "## Full Summary",
        "",
        dataframe_to_markdown(summary, floatfmt=".3f"),
    ]
    (out_dir / "multiseed_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_seeds(raw: str) -> list[int]:
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--seeds", default="20260627,20260628,20260629")
    parser.add_argument("--out-dir", default="results/multiseed")
    args = parser.parse_args()

    base_cfg = load_config(Path(args.config))
    out_dir = Path(args.out_dir)
    rows = [run_one_seed(base_cfg, seed, out_dir) for seed in parse_seeds(args.seeds)]
    df = pd.concat(rows, ignore_index=True)
    write_outputs(df, out_dir)
    print(out_dir / "multiseed_summary.md")


if __name__ == "__main__":
    main()
