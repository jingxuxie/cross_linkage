#!/usr/bin/env python
from __future__ import annotations

import argparse
import difflib
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from crossdoc_pipeline import (
    DOMAINS,
    ISSUE_PHRASES,
    Paths,
    aggressive_replacements,
    dataframe_to_markdown,
    direct_replacements,
    display_values,
    doc_local_replacements,
    evaluate_condition,
    get_presidio_analyzer,
    linkguard_replacements,
    load_config,
    make_paths,
    presidio_redact_text,
    read_jsonl,
    replace_many,
    split_personas,
    train_utility_classifiers,
    with_indefinite_article,
    write_jsonl,
)


CONDITION_ORDER = [
    "noisy_original",
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

CONDITION_LABELS = {
    "noisy_original": "N0 noisy original",
    "c1_direct_redaction": "C1 direct redaction",
    "c1b_presidio_redaction": "C1b Presidio redaction",
    "c4_doc_local_anon": "C4 doc-local proxy",
    "c5_linkguard": "C5 LinkGuard",
    "c6_aggressive_redaction": "C6 aggressive redaction",
}


def issue_phrase(persona: dict[str, Any], domain: str) -> str:
    return ISSUE_PHRASES[persona["utility_labels"][domain]]


def direct_line(persona: dict[str, Any], domain: str, rng: random.Random) -> str:
    options = [
        (
            f"Contact trail: {persona['synthetic_name']} / {persona['email']} / "
            f"{persona['phone']} / {persona['address']} / {persona['account_id']}."
        ),
        (
            f"Roster note lists {persona['synthetic_name']}; email {persona['email']}; "
            f"callback {persona['phone']}; address {persona['address']}; account {persona['account_id']}."
        ),
        (
            f"Header copied from the system: {persona['synthetic_name']} "
            f"({persona['email']}, {persona['phone']}), {persona['address']}, {persona['account_id']}."
        ),
    ]
    prefix = {
        "healthcare": "Portal metadata",
        "legal": "Intake metadata",
        "financial": "Support metadata",
        "hr": "HR metadata",
    }[domain]
    return f"{prefix}: {rng.choice(options)}"


def noisy_domain_fragments(
    persona: dict[str, Any],
    domain: str,
    vals: dict[str, str],
) -> list[str]:
    phrase = issue_phrase(persona, domain)
    phrase_np = with_indefinite_article(phrase)
    common = [
        f"Location context appears as {vals['location']}.",
        f"Scheduling is constrained by {vals['schedule']}.",
        f"The writer also mentions {vals['family']}.",
    ]
    if domain == "healthcare":
        return [
            f"Request type: {phrase}.",
            f"The note asks for help with {phrase_np}, but the story starts with {vals['medical']}.",
            f"Work is described as {with_indefinite_article(vals['role'])}.",
            *common,
        ]
    if domain == "legal":
        return [
            f"Request type: {phrase}.",
            f"The legal question is framed as {phrase_np} connected to {vals['legal']}.",
            f"Workplace or institution context: {with_indefinite_article(vals['employer'])}.",
            f"Background event: {vals['rare']}.",
            f"Availability note: {vals['schedule']}.",
        ]
    if domain == "financial":
        return [
            f"Request type: {phrase}.",
            f"The account issue is {phrase_np}, with pressure from {vals['financial']}.",
            f"Household context: {vals['family']}.",
            f"The location clue is {vals['location']}.",
            "The writer is trying to keep the account current.",
        ]
    if domain == "hr":
        return [
            f"Request type: {phrase}.",
            f"The HR request is {phrase_np}.",
            f"Role and workplace context: {vals['role']} at {with_indefinite_article(vals['employer'])}.",
            f"Training or education clue: {vals['education']}.",
            f"Other context: {vals['medical']} and {vals['hobby']}.",
            f"Timing clue: {vals['schedule']}.",
        ]
    raise KeyError(domain)


def render_noisy_documents(
    personas: list[dict[str, Any]],
    original_docs: list[dict[str, Any]],
    seed: int,
) -> list[dict[str, Any]]:
    original_by_id = {doc["doc_id"]: doc for doc in original_docs}
    docs: list[dict[str, Any]] = []
    openings = [
        "Free-form note pasted from a support thread.",
        "Short intake summary with details out of chronological order.",
        "Internal triage note, lightly edited by a coordinator.",
        "Message excerpt with copied background details.",
        "Case note assembled from two brief follow-ups.",
    ]
    closings = [
        "Please route this to the right team.",
        "The writer asks for a practical next step.",
        "They want a response that accounts for the constraints above.",
        "The note is not an emergency but needs follow-up.",
    ]
    for persona in personas:
        vals = display_values(persona)
        pid_num = int(persona["persona_id"].replace("P", ""))
        for doc_idx, domain in enumerate(DOMAINS):
            rng = random.Random(seed + pid_num * 97 + doc_idx * 17)
            doc_id = f"{persona['persona_id']}_D{doc_idx + 1:02d}"
            fragments = noisy_domain_fragments(persona, domain, vals)
            rng.shuffle(fragments)
            opening = rng.choice(openings)
            closing = rng.choice(closings)
            bullet_prefixes = rng.sample(["- ", "* ", "  - ", ""], 3)
            body = [
                f"Subject: {domain} / {issue_phrase(persona, domain)} / follow-up",
                direct_line(persona, domain, rng),
                opening,
            ]
            for idx, fragment in enumerate(fragments):
                prefix = bullet_prefixes[idx % len(bullet_prefixes)]
                body.append(f"{prefix}{fragment}")
            body.append(closing)
            original = original_by_id[doc_id]
            docs.append(
                {
                    **original,
                    "text": "\n".join(body),
                    "condition": "noisy_original",
                    "style_variant": "noisy_freeform",
                }
            )
    return docs


def style_diagnostics(noisy_docs: list[dict[str, Any]], original_docs: list[dict[str, Any]]) -> pd.DataFrame:
    original_by_id = {doc["doc_id"]: doc for doc in original_docs}
    rows = []
    for doc in noisy_docs:
        text = doc["text"]
        original = original_by_id[doc["doc_id"]]["text"]
        tokens = re.findall(r"(?u)\b\w+\b", text.lower())
        rows.append(
            {
                "doc_id": doc["doc_id"],
                "persona_id": doc["persona_id"],
                "domain": doc["domain"],
                "risk_tier": doc["risk_tier"],
                "chars": len(text),
                "tokens": len(tokens),
                "type_token_ratio": len(set(tokens)) / max(len(tokens), 1),
                "template_similarity": difflib.SequenceMatcher(None, original, text).ratio(),
                "first_line": text.splitlines()[0] if text.splitlines() else "",
            }
        )
    return pd.DataFrame(rows)


def transform_noisy_docs(
    cfg: dict[str, Any],
    paths: Paths,
    stress_paths: Paths,
    personas: list[dict[str, Any]],
    noisy_docs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    p_by_id = {p["persona_id"]: p for p in personas}
    linkguard = linkguard_replacements(
        personas,
        int(cfg["target_k"]),
        stress_paths,
        log_name="noisy_linkguard_generalization_log.jsonl",
    )
    presidio_analyzer = get_presidio_analyzer()
    condition_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    condition_rows["noisy_original"] = [
        {**doc, "condition": "noisy_original"} for doc in noisy_docs
    ]
    edit_rows = []
    transform_fns = {
        "c1_direct_redaction": direct_replacements,
        "c4_doc_local_anon": doc_local_replacements,
        "c5_linkguard": lambda persona: linkguard[persona["persona_id"]],
        "c6_aggressive_redaction": aggressive_replacements,
    }
    for doc in noisy_docs:
        persona = p_by_id[doc["persona_id"]]
        for condition, replacement_fn in transform_fns.items():
            new_text = replace_many(doc["text"], replacement_fn(persona))
            condition_rows[condition].append({**doc, "text": new_text, "condition": condition})
            edit_rows.append(
                {
                    "condition": condition,
                    "doc_id": doc["doc_id"],
                    "edit_ratio": 1.0 - difflib.SequenceMatcher(None, doc["text"], new_text).ratio(),
                    "char_delta": len(new_text) - len(doc["text"]),
                }
            )
        presidio_text = replace_many(
            presidio_redact_text(doc["text"], presidio_analyzer),
            direct_replacements(persona),
        )
        condition = "c1b_presidio_redaction"
        condition_rows[condition].append({**doc, "text": presidio_text, "condition": condition})
        edit_rows.append(
            {
                "condition": condition,
                "doc_id": doc["doc_id"],
                "edit_ratio": 1.0 - difflib.SequenceMatcher(None, doc["text"], presidio_text).ratio(),
                "char_delta": len(presidio_text) - len(doc["text"]),
            }
        )
    for condition, rows in condition_rows.items():
        write_jsonl(stress_paths.transformed / f"{condition}.jsonl", rows)
    pd.DataFrame(edit_rows).to_csv(stress_paths.results / "edit_ratios.csv", index=False)
    return condition_rows


def evaluate_noisy_conditions(
    stress_paths: Paths,
    personas: list[dict[str, Any]],
    original_docs: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    condition_rows: dict[str, list[dict[str, Any]]],
) -> None:
    split = split_personas(personas)
    utility_clf = train_utility_classifiers(condition_rows["noisy_original"])
    rows = []
    aux_all = []
    by_tier_all = []
    attr_all = []
    for condition in CONDITION_ORDER:
        row, aux_rows, by_tier_rows, attr_rows = evaluate_condition(
            condition,
            condition_rows[condition],
            personas,
            candidates,
            split,
            utility_clf,
            stress_paths,
        )
        rows.append(row)
        for aux in aux_rows:
            aux["condition"] = condition
        for attr in attr_rows:
            attr["condition"] = condition
        aux_all.extend(aux_rows)
        by_tier_all.extend(by_tier_rows)
        attr_all.extend(attr_rows)

    df = pd.DataFrame(rows)
    df["condition_label"] = df["condition"].map(CONDITION_LABELS).fillna(df["condition"])
    cols = ["condition", "condition_label"] + [
        col for col in df.columns if col not in {"condition", "condition_label"}
    ]
    df = df[cols]
    df.to_csv(stress_paths.results / "noisy_style_results.csv", index=False)
    pd.DataFrame(aux_all).to_csv(stress_paths.results / "noisy_aux_match_rows.csv", index=False)
    pd.DataFrame(by_tier_all).to_csv(stress_paths.results / "noisy_by_tier.csv", index=False)
    pd.DataFrame(attr_all).to_csv(stress_paths.results / "noisy_attribute_leakage_rows.csv", index=False)
    write_summary(stress_paths, df)


def compact_results(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        [
            "condition_label",
            "pair_f1",
            "aux_top1",
            "aux_top3",
            "attr_exact_recovery",
            "issue_acc",
            "retrieval_recall_at_5",
            "fact_preservation",
            "edit_ratio",
        ]
    ].rename(
        columns={
            "condition_label": "condition",
            "pair_f1": "pair_f1",
            "aux_top1": "aux_top1",
            "aux_top3": "aux_top3",
            "attr_exact_recovery": "exact",
            "issue_acc": "issue",
            "retrieval_recall_at_5": "ret5",
            "fact_preservation": "facts",
            "edit_ratio": "edit",
        }
    )


def write_summary(stress_paths: Paths, df: pd.DataFrame) -> None:
    by_condition = {row["condition"]: row for _, row in df.iterrows()}
    direct = by_condition["c1_direct_redaction"]
    presidio = by_condition["c1b_presidio_redaction"]
    local = by_condition["c4_doc_local_anon"]
    linkguard = by_condition["c5_linkguard"]
    aggressive = by_condition["c6_aggressive_redaction"]
    diag = pd.read_csv(stress_paths.results / "noisy_style_diagnostics.csv")
    diagnostic_summary = pd.DataFrame(
        [
            {
                "n_docs": len(diag),
                "mean_chars": float(diag["chars"].mean()),
                "mean_type_token_ratio": float(diag["type_token_ratio"].mean()),
                "mean_template_similarity": float(diag["template_similarity"].mean()),
                "unique_first_lines": int(diag["first_line"].nunique()),
            }
        ]
    )
    diagnostic_summary.to_csv(stress_paths.results / "noisy_style_diagnostic_summary.csv", index=False)
    compact = compact_results(df)
    compact.to_csv(stress_paths.results / "noisy_style_compact_results.csv", index=False)
    lines = [
        "# Noisy Synthetic Style Stress Test",
        "",
        "This is a synthetic-only external-validity stress test. It re-renders the same 120 personas and 480 documents as less template-aligned support notes, while preserving persona IDs, candidate sets, direct identifiers, quasi-identifiers, utility labels, and ground truth.",
        "",
        "## Style Diagnostics",
        "",
        dataframe_to_markdown(diagnostic_summary, floatfmt=".3f"),
        "",
        "## Main Result",
        "",
        f"- Direct redaction remains highly matchable at Aux@1 {direct['aux_top1']:.3f}; Presidio-style redaction is {presidio['aux_top1']:.3f}; the document-local proxy is {local['aux_top1']:.3f}.",
        f"- LinkGuard reduces noisy-style Aux@1 to {linkguard['aux_top1']:.3f} with issue accuracy {linkguard['issue_acc']:.3f} and retrieval Recall@5 {linkguard['retrieval_recall_at_5']:.3f}.",
        f"- Aggressive redaction has Aux@1 {aggressive['aux_top1']:.3f}, but issue accuracy {aggressive['issue_acc']:.3f} and retrieval Recall@5 {aggressive['retrieval_recall_at_5']:.3f}.",
        "",
        dataframe_to_markdown(compact, floatfmt=".3f"),
    ]
    (stress_paths.results / "noisy_style_stress.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a deterministic noisy-style synthetic stress test."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--out-dir", default="results/noisy_style_stress")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    out_dir = paths.root / args.out_dir
    stress_paths = Paths(
        root=paths.root,
        data=paths.data,
        transformed=out_dir / "transformed",
        results=out_dir,
    )
    stress_paths.transformed.mkdir(parents=True, exist_ok=True)
    stress_paths.results.mkdir(parents=True, exist_ok=True)

    personas = read_jsonl(paths.data / "personas.jsonl")
    original_docs = read_jsonl(paths.data / "original_docs.jsonl")
    candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    noisy_docs = render_noisy_documents(personas, original_docs, int(cfg["seed"]) + 777)
    write_jsonl(stress_paths.results / "noisy_original_docs.jsonl", noisy_docs)
    style_diagnostics(noisy_docs, original_docs).to_csv(
        stress_paths.results / "noisy_style_diagnostics.csv",
        index=False,
    )
    condition_rows = transform_noisy_docs(cfg, paths, stress_paths, personas, noisy_docs)
    evaluate_noisy_conditions(stress_paths, personas, original_docs, candidates, condition_rows)
    print(stress_paths.results / "noisy_style_stress.md")


if __name__ == "__main__":
    main()
