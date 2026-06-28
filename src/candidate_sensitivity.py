#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "cache/matplotlib")

import matplotlib.pyplot as plt
import pandas as pd

from crossdoc_pipeline import (
    aux_match_metrics,
    dataframe_to_markdown,
    load_config,
    make_paths,
    read_jsonl,
    split_personas,
)


FIELDS = [
    "age_band",
    "region",
    "city",
    "occupation",
    "employer_type",
    "education",
    "family_structure",
    "medical_context",
    "financial_context",
    "legal_context",
    "schedule_pattern",
    "hobby_or_affiliation",
    "rare_event",
]

CONDITIONS = [
    "original",
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c2_consistent_pseudonym",
    "c3_per_doc_pseudonym",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

PLOT_LABELS = {
    "c1_direct_redaction": "Direct redaction",
    "c1b_presidio_redaction": "Presidio",
    "c4_doc_local_anon": "Doc-local",
    "c5_linkguard": "LinkGuard",
    "c6_aggressive_redaction": "Aggressive",
}


def tie_break(seed: int, target_pid: str, other_pid: str) -> float:
    raw = f"{seed}:{target_pid}:{other_pid}".encode("utf-8")
    value = int(hashlib.sha256(raw).hexdigest()[:12], 16)
    return value / float(16**12)


def decoy_score(seed: int, target: dict[str, Any], other: dict[str, Any]) -> float:
    overlap = sum(target[field] == other[field] for field in FIELDS)
    same_region = int(target["region"] == other["region"])
    return overlap + same_region * 0.5 + tie_break(seed, target["persona_id"], other["persona_id"]) * 0.01


def extend_candidate_sets(
    personas: list[dict[str, Any]],
    base_candidates: list[dict[str, Any]],
    requested_size: int,
    seed: int,
) -> tuple[list[dict[str, Any]], int]:
    persona_by_id = {p["persona_id"]: p for p in personas}
    base_by_id = {c["persona_id"]: c["candidate_ids"] for c in base_candidates}
    effective_size = min(requested_size, len(personas))
    if effective_size < 2:
        raise ValueError("candidate set size must be at least 2")

    extended = []
    for persona in personas:
        pid = persona["persona_id"]
        base_ids = [cid for cid in base_by_id[pid] if cid in persona_by_id]
        if pid not in base_ids:
            base_ids.insert(0, pid)
        selected = list(dict.fromkeys(base_ids[:effective_size]))
        selected_set = set(selected)
        if len(selected) < effective_size:
            scored = []
            for other in personas:
                other_pid = other["persona_id"]
                if other_pid == pid or other_pid in selected_set:
                    continue
                scored.append((decoy_score(seed, persona, other), other_pid))
            scored.sort(reverse=True)
            for _, other_pid in scored:
                selected.append(other_pid)
                selected_set.add(other_pid)
                if len(selected) == effective_size:
                    break
        extended.append(
            {
                "persona_id": pid,
                "candidate_set_size": effective_size,
                "candidate_ids": selected,
            }
        )
    return extended, effective_size


def evaluate_candidate_sizes(
    config_path: Path,
    candidate_sizes: list[int],
    conditions: list[str],
) -> None:
    cfg = load_config(config_path)
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    base_candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    split = split_personas(personas)

    rows = []
    detail_rows = []
    for requested_size in candidate_sizes:
        candidates, effective_size = extend_candidate_sets(
            personas, base_candidates, requested_size, int(cfg["seed"])
        )
        chance_top1 = 1.0 / effective_size
        chance_top3 = min(3, effective_size) / effective_size
        for condition in conditions:
            doc_path = paths.transformed / f"{condition}.jsonl"
            if not doc_path.exists():
                raise FileNotFoundError(
                    f"Missing transformed documents for {condition}: {doc_path}. "
                    "Run src/crossdoc_pipeline.py first."
                )
            docs = read_jsonl(doc_path)
            metrics, per_persona = aux_match_metrics(docs, personas, candidates, split["test"])
            rows.append(
                {
                    "requested_candidate_set_size": requested_size,
                    "candidate_set_size": effective_size,
                    "condition": condition,
                    "chance_top1": chance_top1,
                    "chance_top3": chance_top3,
                    **metrics,
                }
            )
            for row in per_persona:
                detail_rows.append(
                    {
                        "requested_candidate_set_size": requested_size,
                        "candidate_set_size": effective_size,
                        "condition": condition,
                        **row,
                    }
                )

    df = pd.DataFrame(rows).sort_values(["candidate_set_size", "condition"])
    detail = pd.DataFrame(detail_rows).sort_values(
        ["candidate_set_size", "condition", "persona_id"]
    )
    df.to_csv(paths.results / "candidate_sensitivity.csv", index=False)
    detail.to_csv(paths.results / "candidate_sensitivity_rows.csv", index=False)
    write_markdown(df, paths.results / "candidate_sensitivity.md")
    make_plot(df, paths.results / "candidate_sensitivity.png")
    print(paths.results / "candidate_sensitivity.md")


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    compact = df[
        [
            "candidate_set_size",
            "condition",
            "chance_top1",
            "aux_top1",
            "aux_top3",
            "aux_mrr",
        ]
    ].copy()
    path.write_text(dataframe_to_markdown(compact, floatfmt=".3f") + "\n", encoding="utf-8")


def make_plot(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    focus = df[df["condition"].isin(PLOT_LABELS)].copy()
    for condition, group in focus.groupby("condition", sort=False):
        ax.plot(
            group["candidate_set_size"],
            group["aux_top1"],
            marker="o",
            linewidth=2.0,
            label=PLOT_LABELS[condition],
        )
    chance = df[["candidate_set_size", "chance_top1"]].drop_duplicates().sort_values(
        "candidate_set_size"
    )
    ax.plot(
        chance["candidate_set_size"],
        chance["chance_top1"],
        linestyle="--",
        color="#555555",
        linewidth=1.4,
        label="Chance top-1",
    )
    ax.set_xlabel("Auxiliary candidate set size")
    ax.set_ylabel("Auxiliary top-1 match rate")
    ax.set_ylim(0, min(1.0, float(focus["aux_top1"].max()) + 0.1))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    ax.set_title("Auxiliary matching sensitivity to candidate set size", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def parse_ints(raw: str) -> list[int]:
    return [int(value.strip()) for value in raw.split(",") if value.strip()]


def parse_conditions(raw: str) -> list[str]:
    if raw.strip() == "all":
        return CONDITIONS
    return [value.strip() for value in raw.split(",") if value.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--candidate-sizes", default="10,20,50")
    parser.add_argument("--conditions", default="all")
    args = parser.parse_args()
    evaluate_candidate_sizes(
        Path(args.config),
        parse_ints(args.candidate_sizes),
        parse_conditions(args.conditions),
    )


if __name__ == "__main__":
    main()
