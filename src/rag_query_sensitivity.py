#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from crossdoc_pipeline import dataframe_to_markdown, load_config, make_paths, read_jsonl, split_personas, write_jsonl
from rag_exposure import CONDITION_LABELS


DEFAULT_CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

QUERY_TYPE_ORDER = ["short", "medium", "verbose"]
QUERY_TYPE_LABELS = {
    "short": "Short",
    "medium": "Medium",
    "verbose": "Verbose",
}


def utility_issue_text(persona: dict[str, Any]) -> str:
    return ", ".join(str(value).replace("_", " ") for value in persona["utility_labels"].values())


def generated_queries(persona: dict[str, Any]) -> list[dict[str, Any]]:
    short = (
        f"Find support request records for a {persona['occupation']} "
        f"in the {persona['region']}."
    )
    medium = (
        f"Find records for a {persona['occupation']} in {persona['city']} "
        f"with {persona['family_structure']} and {persona['schedule_pattern']}."
    )
    verbose = (
        f"Find transformed support documents matching someone in {persona['city']} "
        f"({persona['region']}), working as a {persona['occupation']} at a "
        f"{persona['employer_type']}, with {persona['medical_context']}, "
        f"{persona['financial_context']}, {persona['legal_context']}, "
        f"{persona['hobby_or_affiliation']}, and {persona['rare_event']}. "
        f"Likely issue categories: {utility_issue_text(persona)}."
    )
    return [
        {
            "query_type": "short",
            "query_label": QUERY_TYPE_LABELS["short"],
            "query_text": short,
            "fields_used": "occupation,region",
        },
        {
            "query_type": "medium",
            "query_label": QUERY_TYPE_LABELS["medium"],
            "query_text": medium,
            "fields_used": "occupation,city,family_structure,schedule_pattern",
        },
        {
            "query_type": "verbose",
            "query_label": QUERY_TYPE_LABELS["verbose"],
            "query_text": verbose,
            "fields_used": (
                "city,region,occupation,employer_type,medical_context,"
                "financial_context,legal_context,hobby_or_affiliation,rare_event,issues"
            ),
        },
    ]


def build_query_rows(personas: list[dict[str, Any]], test_ids: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for persona in personas:
        if persona["persona_id"] not in test_ids:
            continue
        for query in generated_queries(persona):
            rows.append(
                {
                    "persona_id": persona["persona_id"],
                    "risk_tier": persona["risk_tier"],
                    **query,
                }
            )
    return rows


def evaluate_condition(
    condition: str,
    docs: list[dict[str, Any]],
    query_rows: list[dict[str, Any]],
    top_small: int,
    top_large: int,
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
    doc_matrix = vectorizer.fit_transform(texts)
    query_matrix = vectorizer.transform([row["query_text"] for row in query_rows])
    scores = (query_matrix @ doc_matrix.T).toarray()

    rows: list[dict[str, Any]] = []
    docs_per_pid = {pid: 0 for pid in {row["persona_id"] for row in query_rows}}
    for doc in docs:
        if doc["persona_id"] in docs_per_pid:
            docs_per_pid[doc["persona_id"]] += 1

    for query_idx, query in enumerate(query_rows):
        pid = query["persona_id"]
        ranking = np.argsort(-scores[query_idx])
        ranked_personas = [docs[int(idx)]["persona_id"] for idx in ranking]
        top_small_personas = ranked_personas[:top_small]
        top_large_personas = ranked_personas[:top_large]
        target_docs_small = sum(1 for candidate_pid in top_small_personas if candidate_pid == pid)
        target_docs_large = sum(1 for candidate_pid in top_large_personas if candidate_pid == pid)
        target_positions = [
            rank for rank, candidate_pid in enumerate(ranked_personas, start=1) if candidate_pid == pid
        ]
        rows.append(
            {
                "condition": condition,
                "condition_label": CONDITION_LABELS.get(condition, condition),
                "persona_id": pid,
                "risk_tier": query["risk_tier"],
                "query_type": query["query_type"],
                "query_label": query["query_label"],
                "fields_used": query["fields_used"],
                "top1_doc_hit": int(top_small_personas[0] == pid),
                f"hit_at_{top_small}": int(target_docs_small > 0),
                f"hit_at_{top_large}": int(target_docs_large > 0),
                f"multi_doc_at_{top_large}": int(target_docs_large >= 2),
                f"target_docs_at_{top_large}": target_docs_large,
                f"target_doc_recall_at_{top_large}": target_docs_large / max(1, docs_per_pid[pid]),
                "first_target_rank": int(target_positions[0]) if target_positions else 0,
                "mrr": 1.0 / target_positions[0] if target_positions else 0.0,
                "top_doc_persona": top_small_personas[0],
            }
        )
    return rows


def summarize(rows: pd.DataFrame, top_small: int, top_large: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [
        "top1_doc_hit",
        f"hit_at_{top_small}",
        f"hit_at_{top_large}",
        f"multi_doc_at_{top_large}",
        f"target_doc_recall_at_{top_large}",
        "mrr",
    ]
    summary = (
        rows.groupby(["condition", "condition_label", "query_type", "query_label"], sort=False)[metrics]
        .mean()
        .reset_index()
    )
    summary.insert(
        4,
        "n_personas",
        rows.groupby(["condition", "condition_label", "query_type", "query_label"], sort=False)
        .size()
        .to_numpy(),
    )
    by_tier = (
        rows.groupby(["condition", "condition_label", "query_type", "query_label", "risk_tier"], sort=False)[metrics]
        .mean()
        .reset_index()
    )
    by_tier.insert(
        5,
        "n_personas",
        rows.groupby(["condition", "condition_label", "query_type", "query_label", "risk_tier"], sort=False)
        .size()
        .to_numpy(),
    )
    return summary, by_tier


def parse_list(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic generated profile-query RAG exposure by query type."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    parser.add_argument("--top-small", type=int, default=5)
    parser.add_argument("--top-large", type=int, default=10)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    test_ids = split_personas(personas)["test"]
    query_rows = build_query_rows(personas, test_ids)
    write_jsonl(paths.data / "generated_profile_queries.jsonl", query_rows)

    all_rows: list[dict[str, Any]] = []
    for condition in parse_list(args.conditions):
        path = paths.transformed / f"{condition}.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        all_rows.extend(
            evaluate_condition(
                condition,
                read_jsonl(path),
                query_rows,
                args.top_small,
                args.top_large,
            )
        )

    rows_df = pd.DataFrame(all_rows)
    summary_df, by_tier = summarize(rows_df, args.top_small, args.top_large)

    rows_path = paths.results / "rag_query_sensitivity_rows.csv"
    summary_path = paths.results / "rag_query_sensitivity.csv"
    by_tier_path = paths.results / "rag_query_sensitivity_by_tier.csv"
    md_path = paths.results / "rag_query_sensitivity.md"
    rows_df.to_csv(rows_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    by_tier.to_csv(by_tier_path, index=False)

    paper_cols = [
        "condition_label",
        "query_label",
        "n_personas",
        f"hit_at_{args.top_small}",
        f"multi_doc_at_{args.top_large}",
        f"target_doc_recall_at_{args.top_large}",
        "mrr",
    ]
    focus = summary_df[paper_cols].copy()
    lines = [
        "# Generated-Query RAG Sensitivity",
        "",
        "Deterministic short, medium, and verbose profile-like queries are issued against each transformed corpus.",
        f"`Hit@{args.top_small}` asks whether any target document appears in the top {args.top_small}.",
        f"`Multi@{args.top_large}` asks whether at least two target-persona documents appear in the top {args.top_large}.",
        "",
        dataframe_to_markdown(focus, floatfmt=".3f"),
        "",
        "## T3 Focus",
        "",
        dataframe_to_markdown(
            by_tier[by_tier["risk_tier"] == "T3"][
                [
                    "condition_label",
                    "query_label",
                    "risk_tier",
                    "n_personas",
                    f"hit_at_{args.top_small}",
                    f"multi_doc_at_{args.top_large}",
                    f"target_doc_recall_at_{args.top_large}",
                    "mrr",
                ]
            ],
            floatfmt=".3f",
        ),
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(summary_path)
    print(dataframe_to_markdown(focus, floatfmt=".3f"))


if __name__ == "__main__":
    main()
