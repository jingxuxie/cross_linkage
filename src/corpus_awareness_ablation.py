#!/usr/bin/env python
from __future__ import annotations

import argparse
import difflib
import math
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "cache/matplotlib")

import numpy as np
import pandas as pd

from attack_sensitivity import aux_match_with_attack
from crossdoc_pipeline import (
    ATTRIBUTE_FIELDS,
    SPECIFICITY_PRIOR,
    UTILITY_COST,
    dataframe_to_markdown,
    estimate_k_for_levels,
    evaluate_condition,
    load_config,
    make_paths,
    read_jsonl,
    region_for_city,
    replace_many,
    replacements_for_linkguard_levels,
    split_personas,
    train_utility_classifiers,
    write_jsonl,
)


TARGET_K_DEFAULT = 5

VARIANT_LABELS = {
    "true_corpus_linkguard": "True corpus LinkGuard",
    "shuffled_corpus_stats": "Shuffled corpus stats",
    "global_l1_generalization": "Global L1 generalization",
    "direct_targetk_suppression": "Target-k suppression",
}

VARIANT_DESCRIPTIONS = {
    "true_corpus_linkguard": "Per-person field levels are selected with true corpus co-occurrence statistics.",
    "shuffled_corpus_stats": "Per-person field levels are selected after independently shuffling quasi-identifier fields across personas, preserving marginals but breaking co-occurrence.",
    "global_l1_generalization": "Every persona receives the same level-1 quasi-identifier generalization, with no per-person uniqueness estimate.",
    "direct_targetk_suppression": "Corpus-aware target-k field selection is retained, but selected fields are suppressed directly instead of using progressive generalization.",
}


def shuffled_planning_personas(personas: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    shuffled_by_field: dict[str, list[Any]] = {}
    for field in ATTRIBUTE_FIELDS:
        values = [persona[field] for persona in personas]
        rng.shuffle(values)
        shuffled_by_field[field] = values

    planned = []
    for idx, persona in enumerate(personas):
        row = dict(persona)
        for field, values in shuffled_by_field.items():
            row[field] = values[idx]
        row["region"] = region_for_city(row["city"])
        planned.append(row)
    return planned


def choose_levels(
    target_persona: dict[str, Any],
    real_personas: list[dict[str, Any]],
    planning_personas: list[dict[str, Any]],
    target_k: int,
    *,
    suppression_only: bool = False,
) -> tuple[dict[str, int], dict[str, Any]]:
    fields = list(ATTRIBUTE_FIELDS)
    levels = {field: 0 for field in fields}
    value_counts: dict[str, Counter[str]] = {
        field: Counter(str(persona[field]) for persona in planning_personas)
        for field in fields
    }
    n = len(planning_personas)
    chosen: list[str] = []
    current_k = estimate_k_for_levels(planning_personas, levels, target_persona)

    while current_k < target_k:
        candidates = []
        for field in fields:
            if levels[field] >= 2:
                continue
            count = value_counts[field][str(target_persona[field])]
            rarity = -math.log((count + 0.5) / (n + 0.5 * max(len(value_counts[field]), 1)))
            next_level = 2 if suppression_only else levels[field] + 1
            utility_penalty = UTILITY_COST[field] * (1.0 + 0.8 * (next_level - 1))
            score = (rarity + SPECIFICITY_PRIOR[field] + 1.0) / max(utility_penalty, 0.1)
            candidates.append((score, field, next_level))
        if not candidates:
            break
        _, field, next_level = max(candidates)
        levels[field] = next_level
        chosen.append(f"{field}:L{next_level}")
        current_k = estimate_k_for_levels(planning_personas, levels, target_persona)

    true_estimated_k = estimate_k_for_levels(real_personas, levels, target_persona)
    planning_estimated_k = estimate_k_for_levels(planning_personas, levels, target_persona)
    meta = {
        "persona_id": target_persona["persona_id"],
        "risk_tier": target_persona["risk_tier"],
        "planning_estimated_k": planning_estimated_k,
        "true_estimated_k": true_estimated_k,
        "generalized_fields": chosen,
        "field_levels": levels,
        "n_level1_fields": sum(1 for level in levels.values() if level == 1),
        "n_level2_fields": sum(1 for level in levels.values() if level == 2),
    }
    return levels, meta


def transform_docs(
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    levels_by_pid: dict[str, dict[str, int]],
    condition: str,
) -> tuple[list[dict[str, Any]], float]:
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    rows = []
    edit_ratios = []
    for doc in docs:
        persona = persona_by_id[doc["persona_id"]]
        replacements = replacements_for_linkguard_levels(persona, levels_by_pid[doc["persona_id"]])
        text = replace_many(doc["text"], replacements)
        rows.append({**doc, "text": text, "condition": condition})
        edit_ratios.append(1.0 - difflib.SequenceMatcher(None, doc["text"], text).ratio())
    return rows, float(np.mean(edit_ratios)) if edit_ratios else 0.0


def fixed_global_levels(level: int = 1) -> dict[str, int]:
    return {field: level for field in ATTRIBUTE_FIELDS}


def summarize_logs(log_rows: list[dict[str, Any]], target_k: int) -> dict[str, float]:
    planning = np.array([row["planning_estimated_k"] for row in log_rows], dtype=float)
    true = np.array([row["true_estimated_k"] for row in log_rows], dtype=float)
    level1 = np.array([row["n_level1_fields"] for row in log_rows], dtype=float)
    level2 = np.array([row["n_level2_fields"] for row in log_rows], dtype=float)
    return {
        "target_k": float(target_k),
        "min_planning_estimated_k": float(planning.min()),
        "median_planning_estimated_k": float(np.median(planning)),
        "min_true_estimated_k": float(true.min()),
        "median_true_estimated_k": float(np.median(true)),
        "target_k_coverage": float(np.mean(true >= target_k)),
        "mean_l1_fields": float(level1.mean()),
        "mean_l2_fields": float(level2.mean()),
    }


def evaluate_variant(
    condition: str,
    label: str,
    description: str,
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    split: dict[str, set[str]],
    utility_clf: dict[str, Any],
    paths: Any,
    edit_ratio: float,
    log_rows: list[dict[str, Any]],
    target_k: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    row, _, tier_rows, _ = evaluate_condition(
        condition,
        docs,
        personas,
        candidates,
        split,
        utility_clf,
        paths,
    )
    field_metrics, _ = aux_match_with_attack(
        docs,
        personas,
        candidates,
        split["test"],
        "field_weighted",
    )
    row["ablation"] = condition
    row["label"] = label
    row["description"] = description
    row["edit_ratio"] = edit_ratio
    row.update({f"field_{key}": value for key, value in field_metrics.items()})
    row.update(summarize_logs(log_rows, target_k))
    return row, tier_rows


def run_ablation(config_path: Path, target_k: int, shuffle_seed: int) -> None:
    cfg = load_config(config_path)
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    docs = read_jsonl(paths.data / "original_docs.jsonl")
    candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    split = split_personas(personas)
    utility_clf = train_utility_classifiers(docs)
    shuffled_personas = shuffled_planning_personas(personas, shuffle_seed)

    variant_specs = [
        ("true_corpus_linkguard", personas, False, None),
        ("shuffled_corpus_stats", shuffled_personas, False, None),
        ("global_l1_generalization", personas, False, fixed_global_levels(1)),
        ("direct_targetk_suppression", personas, True, None),
    ]

    rows = []
    tier_rows_all = []
    log_rows_all = []
    for variant, planning_personas, suppression_only, fixed_levels in variant_specs:
        condition = f"ca_{variant}"
        levels_by_pid: dict[str, dict[str, int]] = {}
        log_rows = []
        for persona in personas:
            if fixed_levels is None:
                levels, log = choose_levels(
                    persona,
                    personas,
                    planning_personas,
                    target_k,
                    suppression_only=suppression_only,
                )
            else:
                levels = dict(fixed_levels)
                log = {
                    "persona_id": persona["persona_id"],
                    "risk_tier": persona["risk_tier"],
                    "planning_estimated_k": estimate_k_for_levels(planning_personas, levels, persona),
                    "true_estimated_k": estimate_k_for_levels(personas, levels, persona),
                    "generalized_fields": [f"{field}:L{level}" for field, level in levels.items() if level > 0],
                    "field_levels": levels,
                    "n_level1_fields": sum(1 for level in levels.values() if level == 1),
                    "n_level2_fields": sum(1 for level in levels.values() if level == 2),
                }
            levels_by_pid[persona["persona_id"]] = levels
            log_rows.append({"ablation": variant, **log})

        transformed, edit_ratio = transform_docs(docs, personas, levels_by_pid, condition)
        write_jsonl(paths.transformed / f"{condition}.jsonl", transformed)
        row, tier_rows = evaluate_variant(
            condition,
            VARIANT_LABELS[variant],
            VARIANT_DESCRIPTIONS[variant],
            transformed,
            personas,
            candidates,
            split,
            utility_clf,
            paths,
            edit_ratio,
            log_rows,
            target_k,
        )
        rows.append(row)
        log_rows_all.extend(log_rows)
        for tier_row in tier_rows:
            tier_row["ablation"] = variant
            tier_row["label"] = VARIANT_LABELS[variant]
        tier_rows_all.extend(tier_rows)

    df = pd.DataFrame(rows)
    order = {f"ca_{variant}": idx for idx, (variant, *_rest) in enumerate(variant_specs)}
    df["_order"] = df["condition"].map(order)
    df = df.sort_values("_order").drop(columns=["_order"])
    df.to_csv(paths.results / "corpus_awareness_ablation.csv", index=False)
    pd.DataFrame(tier_rows_all).sort_values(["ablation", "risk_tier"]).to_csv(
        paths.results / "corpus_awareness_ablation_by_tier.csv",
        index=False,
    )
    pd.DataFrame(log_rows_all).sort_values(["ablation", "persona_id"]).to_json(
        paths.results / "corpus_awareness_ablation_log.jsonl",
        orient="records",
        lines=True,
    )

    compact_cols = [
        "label",
        "min_true_estimated_k",
        "median_true_estimated_k",
        "target_k_coverage",
        "mean_l1_fields",
        "mean_l2_fields",
        "edit_ratio",
        "aux_top1",
        "field_aux_top1",
        "attr_exact_recovery",
        "attr_coarse_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
    ]
    compact = df[compact_cols].copy()
    (paths.results / "corpus_awareness_ablation.md").write_text(
        "# Corpus-Awareness Ablation\n\n"
        + dataframe_to_markdown(compact, floatfmt=".3f")
        + "\n",
        encoding="utf-8",
    )
    print(paths.results / "corpus_awareness_ablation.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--target-k", type=int, default=TARGET_K_DEFAULT)
    parser.add_argument("--shuffle-seed", type=int, default=20260630)
    args = parser.parse_args()
    run_ablation(Path(args.config), args.target_k, args.shuffle_seed)


if __name__ == "__main__":
    main()
