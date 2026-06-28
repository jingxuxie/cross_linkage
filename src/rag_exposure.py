#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from crossdoc_pipeline import dataframe_to_markdown, load_config, make_paths, read_jsonl, split_personas


CONDITION_ORDER = [
    "original",
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c2_consistent_pseudonym",
    "c3_per_doc_pseudonym",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

CONDITION_LABELS = {
    "original": "C0 original",
    "c1_direct_redaction": "C1 direct redaction",
    "c1b_presidio_redaction": "C1b Presidio redaction",
    "c2_consistent_pseudonym": "C2 consistent pseudonym",
    "c3_per_doc_pseudonym": "C3 per-doc pseudonym",
    "c4_doc_local_anon": "C4 doc-local proxy",
    "c5_linkguard": "C5 LinkGuard",
    "c6_aggressive_redaction": "C6 aggressive redaction",
}


def profile_query(persona: dict[str, Any]) -> str:
    fields = [
        "city",
        "region",
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
    values = [str(persona[field]) for field in fields]
    issues = [str(issue).replace("_", " ") for issue in persona["utility_labels"].values()]
    return " ".join(values + issues + ["support request records"])


def load_condition_docs(paths: Any, condition: str) -> list[dict[str, Any]]:
    return read_jsonl(paths.transformed / f"{condition}.jsonl")


def evaluate_condition(
    condition: str,
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    test_ids: set[str],
    top_small: int,
    top_large: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    eval_ids = sorted(test_ids)
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
    query_matrix = vectorizer.transform([profile_query(persona_by_id[pid]) for pid in eval_ids])
    scores = (query_matrix @ doc_matrix.T).toarray()

    rows: list[dict[str, Any]] = []
    for query_idx, pid in enumerate(eval_ids):
        ranking = np.argsort(-scores[query_idx])
        target_positions = [rank for rank, doc_idx in enumerate(ranking, start=1) if docs[doc_idx]["persona_id"] == pid]
        top_small_personas = [docs[idx]["persona_id"] for idx in ranking[:top_small]]
        top_large_personas = [docs[idx]["persona_id"] for idx in ranking[:top_large]]
        target_docs_small = sum(1 for candidate_pid in top_small_personas if candidate_pid == pid)
        target_docs_large = sum(1 for candidate_pid in top_large_personas if candidate_pid == pid)
        rows.append(
            {
                "condition": condition,
                "persona_id": pid,
                "risk_tier": persona_by_id[pid]["risk_tier"],
                "top1_doc_hit": int(top_small_personas[0] == pid),
                f"hit_at_{top_small}": int(target_docs_small > 0),
                f"hit_at_{top_large}": int(target_docs_large > 0),
                f"multi_doc_at_{top_large}": int(target_docs_large >= 2),
                f"target_docs_at_{top_large}": target_docs_large,
                f"target_doc_recall_at_{top_large}": target_docs_large
                / max(1, sum(1 for doc in docs if doc["persona_id"] == pid)),
                "first_target_rank": int(target_positions[0]) if target_positions else 0,
                "mrr": 1.0 / target_positions[0] if target_positions else 0.0,
                "top_doc_persona": top_small_personas[0],
            }
        )

    row_df = pd.DataFrame(rows)
    summary = {
        "condition": condition,
        "n_personas": len(row_df),
        "top1_doc_hit": float(row_df["top1_doc_hit"].mean()),
        f"hit_at_{top_small}": float(row_df[f"hit_at_{top_small}"].mean()),
        f"hit_at_{top_large}": float(row_df[f"hit_at_{top_large}"].mean()),
        f"multi_doc_at_{top_large}": float(row_df[f"multi_doc_at_{top_large}"].mean()),
        f"target_doc_recall_at_{top_large}": float(row_df[f"target_doc_recall_at_{top_large}"].mean()),
        "mrr": float(row_df["mrr"].mean()),
    }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate profile-query RAG exposure over transformed synthetic corpora."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--top-small", type=int, default=5)
    parser.add_argument("--top-large", type=int, default=10)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    test_ids = split_personas(personas)["test"]

    summaries = []
    all_rows: list[dict[str, Any]] = []
    for condition in CONDITION_ORDER:
        path = paths.transformed / f"{condition}.jsonl"
        if not path.exists():
            continue
        docs = load_condition_docs(paths, condition)
        summary, rows = evaluate_condition(
            condition,
            docs,
            personas,
            test_ids,
            args.top_small,
            args.top_large,
        )
        summaries.append(summary)
        all_rows.extend(rows)

    summary_df = pd.DataFrame(summaries)
    summary_df["condition_label"] = summary_df["condition"].map(CONDITION_LABELS).fillna(summary_df["condition"])
    cols = ["condition", "condition_label"] + [c for c in summary_df.columns if c not in {"condition", "condition_label"}]
    summary_df = summary_df[cols]
    rows_df = pd.DataFrame(all_rows)

    out_csv = paths.results / "rag_exposure.csv"
    out_rows = paths.results / "rag_exposure_rows.csv"
    out_by_tier = paths.results / "rag_exposure_by_tier.csv"
    out_md = paths.results / "rag_exposure.md"
    summary_df.to_csv(out_csv, index=False)
    rows_df.to_csv(out_rows, index=False)
    by_tier = (
        rows_df.groupby(["condition", "risk_tier"], sort=False)
        [
            [
                "top1_doc_hit",
                f"hit_at_{args.top_small}",
                f"hit_at_{args.top_large}",
                f"multi_doc_at_{args.top_large}",
                f"target_doc_recall_at_{args.top_large}",
                "mrr",
            ]
        ]
        .mean()
        .reset_index()
    )
    by_tier.insert(
        1,
        "condition_label",
        by_tier["condition"].map(CONDITION_LABELS).fillna(by_tier["condition"]),
    )
    by_tier.to_csv(out_by_tier, index=False)

    paper_cols = [
        "condition_label",
        "top1_doc_hit",
        f"hit_at_{args.top_small}",
        f"multi_doc_at_{args.top_large}",
        f"target_doc_recall_at_{args.top_large}",
        "mrr",
    ]
    lines = [
        "# RAG Exposure Diagnostic",
        "",
        "Exact synthetic auxiliary-profile queries are issued against each transformed corpus.",
        f"`Hit@{args.top_small}` asks whether any target document appears in the top {args.top_small}.",
        f"`Multi@{args.top_large}` asks whether at least two documents from the target persona appear in the top {args.top_large}.",
        "",
        dataframe_to_markdown(summary_df[paper_cols], floatfmt=".3f"),
        "",
        "## By Risk Tier",
        "",
        dataframe_to_markdown(
            by_tier[
                [
                    "condition_label",
                    "risk_tier",
                    "top1_doc_hit",
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
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(out_csv)
    print(dataframe_to_markdown(summary_df[paper_cols], floatfmt=".3f"))


if __name__ == "__main__":
    main()
