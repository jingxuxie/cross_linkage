#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "cache/matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from crossdoc_pipeline import (
    ISSUE_PHRASES,
    dataframe_to_markdown,
    load_config,
    make_paths,
    read_jsonl,
    split_personas,
)


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

DOMAIN_CONTEXT_TERMS = {
    "healthcare": [
        "appointment",
        "care",
        "health",
        "insurance",
        "medical",
        "medication",
        "patient",
        "refill",
        "symptom",
        "treatment",
    ],
    "legal": [
        "administrative",
        "appeal",
        "benefits",
        "case",
        "complaint",
        "consumer",
        "dispute",
        "guidance",
        "housing",
        "legal",
        "records",
    ],
    "financial": [
        "account",
        "billing",
        "current",
        "deferral",
        "expense",
        "financial",
        "fraud",
        "hardship",
        "income",
        "payment",
        "reimbursement",
    ],
    "hr": [
        "accommodation",
        "benefits",
        "employee",
        "hr",
        "job",
        "leave",
        "request",
        "role",
        "schedule",
        "work",
    ],
}

CONSTRAINT_TERMS = [
    "availability",
    "billing",
    "care",
    "childcare",
    "community",
    "constraint",
    "context",
    "education",
    "expense",
    "family",
    "financial",
    "health",
    "issue",
    "legal",
    "medical",
    "payment",
    "records",
    "request",
    "schedule",
    "support",
    "timing",
]


def body_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    body_lines = [
        line
        for line in lines
        if not line.lower().startswith("subject:")
        and "contact" not in line.lower()
        and "identity line" not in line.lower()
        and "profile contact" not in line.lower()
    ]
    return "\n".join(body_lines)


def fit_body_classifiers(original_docs: list[dict[str, Any]], train_ids: set[str]) -> dict[str, Any]:
    train_docs = [doc for doc in original_docs if doc["persona_id"] in train_ids]
    texts = [body_text(doc["text"]) for doc in train_docs]
    domains = [doc["utility_labels"]["domain"] for doc in train_docs]
    issues = [doc["utility_labels"]["issue"] for doc in train_docs]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.9,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    x = vectorizer.fit_transform(texts)
    domain_clf = LogisticRegression(max_iter=2000, random_state=0)
    issue_clf = LogisticRegression(max_iter=2000, random_state=0)
    domain_clf.fit(x, domains)
    issue_clf.fit(x, issues)
    return {"vectorizer": vectorizer, "domain": domain_clf, "issue": issue_clf}


def body_retrieval_metrics(docs: list[dict[str, Any]]) -> dict[str, float]:
    texts = [body_text(doc["text"]) for doc in docs]
    labels = [(doc["utility_labels"]["domain"], doc["utility_labels"]["issue"]) for doc in docs]
    queries = [
        f"{domain.replace('_', ' ')} {ISSUE_PHRASES[issue]} support request"
        for domain, issue in labels
    ]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.9,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    doc_matrix = vectorizer.fit_transform(texts)
    query_matrix = vectorizer.transform(queries)
    scores = (query_matrix @ doc_matrix.T).toarray()
    recall5 = []
    reciprocal_ranks = []
    for idx, label in enumerate(labels):
        ranking = np.argsort(-scores[idx])
        relevant = [j for j in ranking if labels[j] == label]
        if not relevant:
            recall5.append(0.0)
            reciprocal_ranks.append(0.0)
            continue
        top5 = set(ranking[:5])
        first_rank = int(np.where(ranking == relevant[0])[0][0]) + 1
        recall5.append(float(any(labels[j] == label for j in top5)))
        reciprocal_ranks.append(1.0 / first_rank)
    return {
        "body_retrieval_recall_at_5": float(np.mean(recall5)),
        "body_retrieval_mrr": float(np.mean(reciprocal_ranks)),
    }


def issue_phrase_present(doc: dict[str, Any]) -> float:
    phrase = ISSUE_PHRASES[doc["utility_labels"]["issue"]].lower()
    return float(phrase in body_text(doc["text"]).lower())


def semantic_slot_score(doc: dict[str, Any]) -> float:
    body = body_text(doc["text"]).lower()
    body_without_placeholders = re.sub(r"\[[A-Z_]+\]", " ", body)
    issue_hit = issue_phrase_present(doc)
    domain_terms = DOMAIN_CONTEXT_TERMS[doc["utility_labels"]["domain"]]
    domain_hit = float(any(term in body_without_placeholders for term in domain_terms))
    constraint_hit = float(any(term in body_without_placeholders for term in CONSTRAINT_TERMS))
    support_hit = float(any(term in body_without_placeholders for term in ["help", "support", "request", "guidance"]))
    return float(np.mean([issue_hit, domain_hit, constraint_hit, support_hit]))


def placeholder_rate(doc: dict[str, Any]) -> float:
    body = body_text(doc["text"])
    placeholders = re.findall(r"\[[A-Z_]+\]", body)
    tokens = re.findall(r"\b\w+\b|\[[A-Z_]+\]", body)
    return len(placeholders) / max(len(tokens), 1)


def evaluate_condition(
    condition: str,
    docs: list[dict[str, Any]],
    clf: dict[str, Any],
    test_ids: set[str],
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    test_docs = [doc for doc in docs if doc["persona_id"] in test_ids]
    x = clf["vectorizer"].transform([body_text(doc["text"]) for doc in test_docs])
    domain_true = [doc["utility_labels"]["domain"] for doc in test_docs]
    issue_true = [doc["utility_labels"]["issue"] for doc in test_docs]
    domain_pred = clf["domain"].predict(x)
    issue_pred = clf["issue"].predict(x)
    issue_hits = [issue_phrase_present(doc) for doc in test_docs]
    slot_scores = [semantic_slot_score(doc) for doc in test_docs]
    placeholder_rates = [placeholder_rate(doc) for doc in test_docs]
    retrieval = body_retrieval_metrics(test_docs)

    rows = []
    for doc, domain_hat, issue_hat, issue_hit, slot_score, ph_rate in zip(
        test_docs, domain_pred, issue_pred, issue_hits, slot_scores, placeholder_rates
    ):
        rows.append(
            {
                "condition": condition,
                "doc_id": doc["doc_id"],
                "persona_id": doc["persona_id"],
                "risk_tier": doc["risk_tier"],
                "domain": doc["utility_labels"]["domain"],
                "issue": doc["utility_labels"]["issue"],
                "domain_pred": domain_hat,
                "issue_pred": issue_hat,
                "issue_phrase_present": issue_hit,
                "semantic_slot_score": slot_score,
                "placeholder_rate": ph_rate,
            }
        )

    metrics = {
        "condition": condition,
        "body_domain_acc": float(accuracy_score(domain_true, domain_pred)),
        "body_issue_acc": float(accuracy_score(issue_true, issue_pred)),
        "body_issue_phrase_rate": float(np.mean(issue_hits)),
        "semantic_slot_score": float(np.mean(slot_scores)),
        "placeholder_rate": float(np.mean(placeholder_rates)),
        **retrieval,
    }
    metrics["stress_utility_score"] = float(
        np.mean(
            [
                metrics["body_domain_acc"],
                metrics["body_issue_acc"],
                metrics["body_issue_phrase_rate"],
                metrics["semantic_slot_score"],
                metrics["body_retrieval_recall_at_5"],
            ]
        )
    )
    return metrics, rows


def make_plot(df: pd.DataFrame, out_path: Path) -> None:
    focus = df[
        df["condition"].isin(
            [
                "c1_direct_redaction",
                "c1b_presidio_redaction",
                "c4_doc_local_anon",
                "c5_linkguard",
                "c6_aggressive_redaction",
            ]
        )
    ].copy()
    labels = [CONDITION_LABELS[c].replace("C1 ", "").replace("C5 ", "") for c in focus["condition"]]
    x = np.arange(len(focus))
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.bar(x - 0.16, focus["stress_utility_score"], width=0.32, label="Stress utility")
    ax.bar(x + 0.16, 1.0 - focus["placeholder_rate"], width=0.32, label="1 - placeholder rate")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    ax.set_title("Body-only utility stress test", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def run(config_path: Path) -> None:
    cfg = load_config(config_path)
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    split = split_personas(personas)
    original_docs = read_jsonl(paths.data / "original_docs.jsonl")
    clf = fit_body_classifiers(original_docs, split["val"])

    metrics_rows = []
    detail_rows = []
    for condition in cfg["conditions"]:
        docs = read_jsonl(paths.transformed / f"{condition}.jsonl")
        metrics, detail = evaluate_condition(condition, docs, clf, split["test"])
        metrics_rows.append(metrics)
        detail_rows.extend(detail)

    df = pd.DataFrame(metrics_rows)
    detail = pd.DataFrame(detail_rows)
    df.to_csv(paths.results / "utility_stress.csv", index=False)
    detail.to_csv(paths.results / "utility_stress_rows.csv", index=False)
    compact = df[
        [
            "condition",
            "body_domain_acc",
            "body_issue_acc",
            "body_issue_phrase_rate",
            "semantic_slot_score",
            "body_retrieval_recall_at_5",
            "placeholder_rate",
            "stress_utility_score",
        ]
    ].copy()
    (paths.results / "utility_stress.md").write_text(
        dataframe_to_markdown(compact, floatfmt=".3f") + "\n",
        encoding="utf-8",
    )
    make_plot(df, paths.results / "utility_stress.png")
    print(paths.results / "utility_stress.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    args = parser.parse_args()
    run(Path(args.config))


if __name__ == "__main__":
    main()
