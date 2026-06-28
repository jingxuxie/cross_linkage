#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from crossdoc_pipeline import (
    ATTRIBUTE_FIELDS,
    dataframe_to_markdown,
    field_generalization,
    load_config,
    make_paths,
    phrase_in_text,
    read_jsonl,
    split_personas,
)
from rag_exposure import CONDITION_LABELS, CONDITION_ORDER, profile_query


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def top_docs_for_query(docs: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    texts = [doc["text"] for doc in docs]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        min_df=1,
        max_df=0.9,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    matrix = vectorizer.fit_transform(texts)
    scores = (vectorizer.transform([query]) @ matrix.T).toarray()[0]
    order = np.argsort(-scores)[:top_k]
    return [{**docs[int(idx)], "retrieval_rank": rank, "retrieval_score": float(scores[int(idx)])} for rank, idx in enumerate(order, start=1)]


def field_recovery(
    retrieved_docs: list[dict[str, Any]], persona: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    combined = compact_text("\n".join(doc["text"] for doc in retrieved_docs))
    rows = []
    exact_hits = []
    coarse_hits = []
    for field in ATTRIBUTE_FIELDS:
        exact_value = str(persona[field])
        coarse_value = field_generalization(persona, field)
        exact = phrase_in_text(combined, exact_value)
        coarse = exact or phrase_in_text(combined, coarse_value)
        exact_hits.append(float(exact))
        coarse_hits.append(float(coarse))
        rows.append(
            {
                "field": field,
                "exact_value": exact_value,
                "coarse_value": coarse_value,
                "exact_recovered": int(exact),
                "coarse_recovered": int(coarse),
            }
        )
    metrics = {
        "exact_field_recovery": float(np.mean(exact_hits)) if exact_hits else 0.0,
        "coarse_field_recovery": float(np.mean(coarse_hits)) if coarse_hits else 0.0,
        "exact_fields_recovered": float(np.sum(exact_hits)),
        "coarse_fields_recovered": float(np.sum(coarse_hits)),
    }
    return rows, metrics


def evaluate_condition(
    condition: str,
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    test_ids: set[str],
    top_k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    rows = []
    field_rows = []
    for pid in sorted(test_ids):
        persona = persona_by_id[pid]
        retrieved = top_docs_for_query(docs, profile_query(persona), top_k)
        retrieved_personas = [doc["persona_id"] for doc in retrieved]
        target_docs_at_k = sum(1 for candidate_pid in retrieved_personas if candidate_pid == pid)
        field_detail, metrics = field_recovery(retrieved, persona)
        rows.append(
            {
                "condition": condition,
                "condition_label": CONDITION_LABELS.get(condition, condition),
                "persona_id": pid,
                "risk_tier": persona["risk_tier"],
                "top_k": top_k,
                "retrieval_hit_at_k": int(target_docs_at_k > 0),
                "target_docs_at_k": target_docs_at_k,
                "top_doc_persona": retrieved_personas[0] if retrieved_personas else "",
                "top_doc_is_target": int(bool(retrieved_personas) and retrieved_personas[0] == pid),
                **metrics,
            }
        )
        for field_row in field_detail:
            field_rows.append(
                {
                    "condition": condition,
                    "condition_label": CONDITION_LABELS.get(condition, condition),
                    "persona_id": pid,
                    "risk_tier": persona["risk_tier"],
                    "top_k": top_k,
                    **field_row,
                }
            )
    return rows, field_rows


def summarize(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [
        "retrieval_hit_at_k",
        "target_docs_at_k",
        "top_doc_is_target",
        "exact_field_recovery",
        "coarse_field_recovery",
        "exact_fields_recovered",
        "coarse_fields_recovered",
    ]
    summary = rows.groupby(["condition", "condition_label"], sort=False)[metrics].mean().reset_index()
    summary.insert(2, "n_personas", rows.groupby(["condition", "condition_label"], sort=False).size().to_numpy())
    by_tier = (
        rows.groupby(["condition", "condition_label", "risk_tier"], sort=False)[metrics]
        .mean()
        .reset_index()
    )
    by_tier.insert(
        3,
        "n_personas",
        rows.groupby(["condition", "condition_label", "risk_tier"], sort=False).size().to_numpy(),
    )
    return summary, by_tier


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure exact/coarse quasi-identifier recovery in top-k profile-query RAG retrieval results."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--conditions", default=",".join(CONDITION_ORDER))
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    test_ids = split_personas(personas)["test"]
    conditions = [condition.strip() for condition in args.conditions.split(",") if condition.strip()]

    all_rows: list[dict[str, Any]] = []
    all_field_rows: list[dict[str, Any]] = []
    for condition in conditions:
        path = paths.transformed / f"{condition}.jsonl"
        if not path.exists():
            continue
        rows, field_rows = evaluate_condition(condition, read_jsonl(path), personas, test_ids, args.top_k)
        all_rows.extend(rows)
        all_field_rows.extend(field_rows)

    rows_df = pd.DataFrame(all_rows)
    field_df = pd.DataFrame(all_field_rows)
    summary_df, by_tier = summarize(rows_df)

    rows_path = paths.results / "rag_context_recovery_rows.csv"
    field_path = paths.results / "rag_context_recovery_field_rows.csv"
    summary_path = paths.results / "rag_context_recovery.csv"
    by_tier_path = paths.results / "rag_context_recovery_by_tier.csv"
    md_path = paths.results / "rag_context_recovery.md"
    rows_df.to_csv(rows_path, index=False)
    field_df.to_csv(field_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    by_tier.to_csv(by_tier_path, index=False)

    focus = by_tier[by_tier["risk_tier"] == "T3"][
        [
            "condition_label",
            "n_personas",
            "retrieval_hit_at_k",
            "exact_field_recovery",
            "coarse_field_recovery",
            "exact_fields_recovered",
            "coarse_fields_recovered",
        ]
    ]
    lines = [
        "# RAG Context Recovery",
        "",
        f"Profile-query retrieval supplies the top {args.top_k} transformed documents. This deterministic audit scans those retrieved documents for exact and coarse quasi-identifier recovery for the target persona.",
        "",
        "## Overall",
        "",
        dataframe_to_markdown(
            summary_df[
                [
                    "condition_label",
                    "n_personas",
                    "retrieval_hit_at_k",
                    "exact_field_recovery",
                    "coarse_field_recovery",
                    "exact_fields_recovered",
                    "coarse_fields_recovered",
                ]
            ],
            floatfmt=".3f",
        ),
        "",
        "## T3 Focus",
        "",
        dataframe_to_markdown(focus, floatfmt=".3f"),
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(summary_path)
    print(dataframe_to_markdown(focus, floatfmt=".3f"))


if __name__ == "__main__":
    main()
