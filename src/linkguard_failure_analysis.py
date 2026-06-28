#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from crossdoc_pipeline import (
    ATTRIBUTE_FIELDS,
    aux_profile_text,
    dataframe_to_markdown,
    field_generalization,
    load_config,
    make_paths,
    phrase_in_text,
    read_jsonl,
    split_personas,
)


def aux_scores_for_persona(
    pid: str,
    docs_by_persona: dict[str, list[str]],
    personas_by_id: dict[str, dict[str, Any]],
    candidate_ids: list[str],
) -> list[tuple[str, float]]:
    texts = ["\n".join(docs_by_persona[pid])] + [
        aux_profile_text(personas_by_id[cid]) for cid in candidate_ids
    ]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        min_df=1,
        max_df=0.9,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    matrix = vectorizer.fit_transform(texts)
    scores = (matrix[0] @ matrix[1:].T).toarray().ravel()
    return sorted(zip(candidate_ids, scores), key=lambda item: item[1], reverse=True)


def residual_fields(
    combined_text: str,
    persona: dict[str, Any],
) -> tuple[list[str], list[str]]:
    exact = []
    coarse = []
    normalized = " ".join(combined_text.lower().split())
    for field in ATTRIBUTE_FIELDS:
        exact_hit = phrase_in_text(normalized, str(persona[field]).lower())
        coarse_hit = exact_hit or phrase_in_text(
            normalized, field_generalization(persona, field).lower()
        )
        if exact_hit:
            exact.append(field)
        if coarse_hit:
            coarse.append(field)
    return exact, coarse


def shared_fields(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    return [field for field in ATTRIBUTE_FIELDS if a[field] == b[field]]


def load_log_by_persona(path: Path) -> dict[str, dict[str, Any]]:
    return {row["persona_id"]: row for row in read_jsonl(path)}


def analyze(config_path: Path, condition: str) -> None:
    cfg = load_config(config_path)
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    personas_by_id = {p["persona_id"]: p for p in personas}
    docs = read_jsonl(paths.transformed / f"{condition}.jsonl")
    candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    candidates_by_id = {c["persona_id"]: c["candidate_ids"] for c in candidates}
    log_by_id = load_log_by_persona(paths.results / "linkguard_generalization_log.jsonl")
    split = split_personas(personas)

    docs_by_persona: dict[str, list[str]] = defaultdict(list)
    issues_by_persona: dict[str, list[str]] = defaultdict(list)
    for doc in docs:
        if doc["persona_id"] in split["test"]:
            docs_by_persona[doc["persona_id"]].append(doc["text"])
            issues_by_persona[doc["persona_id"]].append(doc["utility_labels"]["issue"])

    rows = []
    for pid in sorted(docs_by_persona):
        ranked = aux_scores_for_persona(
            pid, docs_by_persona, personas_by_id, candidates_by_id[pid]
        )
        ranked_ids = [cid for cid, _ in ranked]
        rank = ranked_ids.index(pid) + 1
        if rank > 3:
            continue
        score_by_id = dict(ranked)
        runner_up = ranked[1][0] if rank == 1 else ranked[0][0]
        runner_score = ranked[1][1] if rank == 1 else ranked[0][1]
        exact, coarse = residual_fields("\n".join(docs_by_persona[pid]), personas_by_id[pid])
        log = log_by_id.get(pid, {})
        rows.append(
            {
                "analysis_set": "top1" if rank == 1 else "top3_not_top1",
                "persona_id": pid,
                "risk_tier": personas_by_id[pid]["risk_tier"],
                "rank": rank,
                "score_true": float(score_by_id[pid]),
                "nearest_wrong_candidate": runner_up,
                "nearest_wrong_score": float(runner_score),
                "score_margin": float(score_by_id[pid] - runner_score),
                "estimated_k": int(log.get("estimated_k", -1)),
                "generalization_steps": len(log.get("generalized_fields", [])),
                "residual_exact_fields": ",".join(exact) if exact else "none",
                "residual_coarse_fields": ",".join(coarse) if coarse else "none",
                "shared_fields_with_nearest_wrong": ",".join(
                    shared_fields(personas_by_id[pid], personas_by_id[runner_up])
                )
                or "none",
                "utility_issues": ",".join(sorted(set(issues_by_persona[pid]))),
            }
        )

    df = pd.DataFrame(rows).sort_values(["analysis_set", "rank", "persona_id"])
    out_csv = paths.results / "linkguard_failure_analysis.csv"
    out_md = paths.results / "linkguard_failure_analysis.md"
    df.to_csv(out_csv, index=False)
    write_markdown(df, out_md)
    print(out_md)


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    top1 = df[df["analysis_set"] == "top1"]
    top3 = df[df["analysis_set"] == "top3_not_top1"]
    lines = [
        "# LinkGuard Residual Match Analysis",
        "",
        f"Top-1 residual matches: {len(top1)}.",
        f"Additional top-3 residual matches: {len(top3)}.",
    ]
    if not top1.empty:
        lines.append(
            f"Median top-1 score margin: {float(top1['score_margin'].median()):.4f}."
        )
        lines.append(
            f"Median estimated k among top-1 residuals: {float(top1['estimated_k'].median()):.1f}."
        )
    lines.extend(
        [
            "",
            "## Top-1 Residual Matches",
            "",
            dataframe_to_markdown(compact_rows(top1), floatfmt=".3f") if not top1.empty else "None.",
            "",
            "## Top-3 Non-Top-1 Residual Matches",
            "",
            dataframe_to_markdown(compact_rows(top3), floatfmt=".3f") if not top3.empty else "None.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compact_rows(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "persona_id",
        "risk_tier",
        "rank",
        "score_true",
        "score_margin",
        "estimated_k",
        "residual_exact_fields",
        "residual_coarse_fields",
        "shared_fields_with_nearest_wrong",
    ]
    return df[cols].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--condition", default="c5_linkguard")
    args = parser.parse_args()
    analyze(Path(args.config), args.condition)


if __name__ == "__main__":
    main()
