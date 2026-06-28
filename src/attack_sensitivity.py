#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

os.environ.setdefault("MPLCONFIGDIR", "cache/matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from crossdoc_pipeline import (
    ATTRIBUTE_FIELDS,
    SPECIFICITY_PRIOR,
    aux_profile_text,
    dataframe_to_markdown,
    field_generalization,
    load_config,
    make_paths,
    phrase_in_text,
    read_jsonl,
    split_personas,
)


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

FOCUS_CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
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

ATTACK_LABELS = {
    "word_tfidf": "Word TF-IDF",
    "char_tfidf": "Char TF-IDF",
    "hybrid_tfidf": "Hybrid",
    "field_weighted": "Field-weighted",
}


def word_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        min_df=1,
        max_df=0.9,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )


def char_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )


def cosine_scores(texts: list[str], vectorizer_factory: Callable[[], TfidfVectorizer]) -> np.ndarray:
    matrix = vectorizer_factory().fit_transform(texts)
    return (matrix[0] @ matrix[1:].T).toarray().ravel()


def attack_scores(texts: list[str], attack: str) -> np.ndarray:
    if attack == "word_tfidf":
        return cosine_scores(texts, word_vectorizer)
    if attack == "char_tfidf":
        return cosine_scores(texts, char_vectorizer)
    if attack == "hybrid_tfidf":
        return 0.5 * cosine_scores(texts, word_vectorizer) + 0.5 * cosine_scores(texts, char_vectorizer)
    raise KeyError(f"Unknown attack: {attack}")


def field_weighted_scores(text: str, candidate_personas: list[dict[str, Any]]) -> np.ndarray:
    """Schema-aware attacker that looks for exact and generalized quasi-identifiers."""
    normalized = re_normalize(text)
    scores = []
    for persona in candidate_personas:
        score = 0.0
        for field in ATTRIBUTE_FIELDS:
            exact_value = str(persona[field]).lower()
            coarse_value = field_generalization(persona, field).lower()
            specificity = float(SPECIFICITY_PRIOR[field])
            if phrase_in_text(normalized, exact_value):
                score += 2.0 * specificity
            elif phrase_in_text(normalized, coarse_value):
                score += 0.7 * specificity
        scores.append(score)
    return np.array(scores, dtype=float)


def re_normalize(text: str) -> str:
    return " ".join(text.lower().split())


def aux_match_with_attack(
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    ids: set[str],
    attack: str,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    docs_by_persona: dict[str, list[str]] = defaultdict(list)
    for doc in docs:
        if doc["persona_id"] in ids:
            docs_by_persona[doc["persona_id"]].append(doc["text"])

    persona_by_id = {p["persona_id"]: p for p in personas}
    candidate_by_pid = {c["persona_id"]: c["candidate_ids"] for c in candidates}
    rows = []
    reciprocal_ranks = []
    top1 = 0
    top3 = 0
    for pid, doc_texts in docs_by_persona.items():
        candidate_ids = candidate_by_pid[pid]
        if attack == "field_weighted":
            scores = field_weighted_scores(
                "\n".join(doc_texts),
                [persona_by_id[cid] for cid in candidate_ids],
            )
        else:
            texts = ["\n".join(doc_texts)] + [
                aux_profile_text(persona_by_id[cid]) for cid in candidate_ids
            ]
            scores = attack_scores(texts, attack)
        ranked = [
            cid
            for _, _, cid in sorted(
                zip(scores, range(len(candidate_ids)), candidate_ids),
                key=lambda item: (-item[0], item[1]),
            )
        ]
        rank = ranked.index(pid) + 1
        reciprocal_ranks.append(1.0 / rank)
        top1 += int(rank == 1)
        top3 += int(rank <= 3)
        rows.append(
            {
                "attack": attack,
                "persona_id": pid,
                "risk_tier": persona_by_id[pid]["risk_tier"],
                "rank": rank,
                "top1": int(rank == 1),
                "top3": int(rank <= 3),
                "score_true": float(scores[candidate_ids.index(pid)]),
                "top_candidate": ranked[0],
            }
        )
    n = max(len(rows), 1)
    return {
        "aux_top1": top1 / n,
        "aux_top3": top3 / n,
        "aux_mrr": float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0,
    }, rows


def evaluate_attacks(config_path: Path, attacks: list[str], conditions: list[str]) -> None:
    cfg = load_config(config_path)
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    split = split_personas(personas)

    rows = []
    detail_rows = []
    for attack in attacks:
        for condition in conditions:
            doc_path = paths.transformed / f"{condition}.jsonl"
            if not doc_path.exists():
                raise FileNotFoundError(
                    f"Missing transformed documents for {condition}: {doc_path}. "
                    "Run src/crossdoc_pipeline.py first."
                )
            docs = read_jsonl(doc_path)
            metrics, per_persona = aux_match_with_attack(
                docs, personas, candidates, split["test"], attack
            )
            rows.append({"attack": attack, "condition": condition, **metrics})
            detail_rows.extend({"condition": condition, **row} for row in per_persona)

    df = pd.DataFrame(rows).sort_values(["attack", "condition"])
    detail = pd.DataFrame(detail_rows).sort_values(["attack", "condition", "persona_id"])
    df.to_csv(paths.results / "attack_sensitivity.csv", index=False)
    detail.to_csv(paths.results / "attack_sensitivity_rows.csv", index=False)
    write_markdown(df, paths.results / "attack_sensitivity.md")
    make_plot(df, paths.results / "attack_sensitivity.png")
    print(paths.results / "attack_sensitivity.md")


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    compact = df[["attack", "condition", "aux_top1", "aux_top3", "aux_mrr"]].copy()
    path.write_text(dataframe_to_markdown(compact, floatfmt=".3f") + "\n", encoding="utf-8")


def make_plot(df: pd.DataFrame, out_path: Path) -> None:
    focus = df[df["condition"].isin(FOCUS_CONDITIONS)].copy()
    attacks = [attack for attack in ATTACK_LABELS if attack in set(focus["attack"])]
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    x = np.arange(len(FOCUS_CONDITIONS))
    width = min(0.2, 0.82 / max(len(attacks), 1))
    offsets = (np.arange(len(attacks)) - (len(attacks) - 1) / 2.0) * width
    for idx, attack in enumerate(attacks):
        group = focus[focus["attack"] == attack].set_index("condition")
        values = [
            float(group.loc[condition, "aux_top1"]) if condition in group.index else 0.0
            for condition in FOCUS_CONDITIONS
        ]
        ax.bar(x + offsets[idx], values, width=width, label=ATTACK_LABELS[attack])
    ax.set_xticks(x)
    ax.set_xticklabels([PLOT_LABELS[c] for c in FOCUS_CONDITIONS], rotation=18, ha="right")
    ax.set_ylabel("Auxiliary top-1 match rate")
    ax.set_ylim(0, min(1.0, float(focus["aux_top1"].max()) + 0.12))
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    ax.set_title("Auxiliary matching sensitivity to local attacker family", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def parse_list(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def parse_conditions(raw: str) -> list[str]:
    if raw.strip() == "all":
        return CONDITIONS
    return parse_list(raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--attacks", default="word_tfidf,char_tfidf,hybrid_tfidf,field_weighted")
    parser.add_argument("--conditions", default="all")
    args = parser.parse_args()
    evaluate_attacks(
        Path(args.config),
        parse_list(args.attacks),
        parse_conditions(args.conditions),
    )


if __name__ == "__main__":
    main()
