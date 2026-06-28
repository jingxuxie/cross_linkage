#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from crossdoc_pipeline import (
    ISSUE_PHRASES,
    dataframe_to_markdown,
    load_config,
    make_paths,
    read_jsonl,
)


DIRECT_FIELDS = ["synthetic_name", "email", "phone", "address", "account_id"]
DECOY_OVERLAP_FIELDS = [
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
UTILITY_RETENTION_CONDITIONS = {
    "original",
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c2_consistent_pseudonym",
    "c3_per_doc_pseudonym",
    "c4_doc_local_anon",
    "c5_linkguard",
}


@dataclass
class Check:
    check_id: str
    status: str
    detail: str
    source: str
    expected: str = ""
    observed: str = ""


def add_check(
    checks: list[Check],
    check_id: str,
    ok: bool,
    detail: str,
    source: str,
    expected: str = "",
    observed: str = "",
) -> None:
    checks.append(
        Check(
            check_id=check_id,
            status="PASS" if ok else "FAIL",
            detail=detail,
            source=source,
            expected=expected,
            observed=observed,
        )
    )


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def direct_identifier_hits(text: str, persona: dict[str, Any]) -> list[str]:
    lower = text.lower()
    hits = []
    for field in DIRECT_FIELDS:
        value = str(persona.get(field, "")).strip().lower()
        if value and value in lower:
            hits.append(field)
    return hits


def issue_phrase_rate(docs: list[dict[str, Any]]) -> float:
    if not docs:
        return 0.0
    hits = 0
    for doc in docs:
        phrase = ISSUE_PHRASES[doc["utility_labels"]["issue"]].lower()
        hits += int(phrase in doc["text"].lower())
    return hits / len(docs)


def validate_corpus(
    cfg: dict[str, Any],
    paths: Any,
    personas: list[dict[str, Any]],
    original_docs: list[dict[str, Any]],
    checks: list[Check],
) -> None:
    expected_docs = int(cfg["num_personas"]) * int(cfg["docs_per_persona"])
    add_check(
        checks,
        "corpus:persona_count",
        len(personas) == int(cfg["num_personas"]),
        "persona count matches config",
        "data/personas.jsonl",
        expected=str(cfg["num_personas"]),
        observed=str(len(personas)),
    )
    add_check(
        checks,
        "corpus:document_count",
        len(original_docs) == expected_docs,
        "original document count matches config",
        "data/original_docs.jsonl",
        expected=str(expected_docs),
        observed=str(len(original_docs)),
    )

    domains = set(cfg["domains"])
    per_persona = Counter(doc["persona_id"] for doc in original_docs)
    domain_sets: dict[str, set[str]] = {}
    for doc in original_docs:
        domain_sets.setdefault(doc["persona_id"], set()).add(doc["domain"])
    add_check(
        checks,
        "corpus:docs_per_persona",
        all(count == int(cfg["docs_per_persona"]) for count in per_persona.values())
        and len(per_persona) == len(personas),
        "each persona has the configured number of documents",
        "data/original_docs.jsonl",
        expected=str(cfg["docs_per_persona"]),
        observed=str(dict(sorted(Counter(per_persona.values()).items()))),
    )
    add_check(
        checks,
        "corpus:domains_per_persona",
        all(value == domains for value in domain_sets.values()),
        "each persona has exactly one document for every configured domain",
        "data/original_docs.jsonl",
        expected=",".join(sorted(domains)),
        observed=f"{sum(value == domains for value in domain_sets.values())}/{len(personas)}",
    )

    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    original_direct_docs = 0
    for doc in original_docs:
        hits = direct_identifier_hits(doc["text"], persona_by_id[doc["persona_id"]])
        original_direct_docs += int(len(hits) == len(DIRECT_FIELDS))
    add_check(
        checks,
        "corpus:original_direct_ids_present",
        original_direct_docs == len(original_docs),
        "original synthetic documents contain the direct identifiers used by redaction baselines",
        "data/original_docs.jsonl",
        expected=str(len(original_docs)),
        observed=str(original_direct_docs),
    )


def validate_transforms(
    cfg: dict[str, Any],
    paths: Any,
    personas: list[dict[str, Any]],
    checks: list[Check],
) -> None:
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    expected_docs = int(cfg["num_personas"]) * int(cfg["docs_per_persona"])
    for condition in cfg["conditions"]:
        path = paths.transformed / f"{condition}.jsonl"
        docs = read_jsonl(path)
        add_check(
            checks,
            f"transform:{condition}:document_count",
            len(docs) == expected_docs,
            "transformed condition has one row per original document",
            display_path(path, paths.root),
            expected=str(expected_docs),
            observed=str(len(docs)),
        )
        if condition == "original":
            continue
        leaked_docs = []
        leaked_fields: Counter[str] = Counter()
        for doc in docs:
            hits = direct_identifier_hits(doc["text"], persona_by_id[doc["persona_id"]])
            if hits:
                leaked_docs.append(doc["doc_id"])
                leaked_fields.update(hits)
        add_check(
            checks,
            f"transform:{condition}:no_exact_direct_ids",
            not leaked_docs,
            "transformed condition contains no exact synthetic direct identifiers",
            display_path(path, paths.root),
            expected="0",
            observed=f"{len(leaked_docs)} docs; fields={dict(leaked_fields)}",
        )

    for condition in sorted(UTILITY_RETENTION_CONDITIONS):
        path = paths.transformed / f"{condition}.jsonl"
        if not path.exists():
            continue
        docs = read_jsonl(path)
        rate = issue_phrase_rate(docs)
        add_check(
            checks,
            f"utility:{condition}:issue_phrase_retention",
            rate >= 0.99,
            "task issue phrase is retained in conditions that should preserve triage labels",
            display_path(path, paths.root),
            expected=">=0.990",
            observed=f"{rate:.3f}",
        )


def validate_candidate_sets(
    cfg: dict[str, Any],
    paths: Any,
    personas: list[dict[str, Any]],
    checks: list[Check],
) -> None:
    path = paths.data / "candidate_sets.jsonl"
    candidate_sets = read_jsonl(path)
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    known_ids = set(persona_by_id)
    expected_size = int(cfg["candidate_set_size"])

    structural_ok = True
    max_overlaps = []
    avg_overlaps = []
    same_region_sets = 0
    same_occupation_sets = 0
    for row in candidate_sets:
        pid = row["persona_id"]
        candidate_ids = row["candidate_ids"]
        structural_ok = structural_ok and pid in known_ids
        structural_ok = structural_ok and len(candidate_ids) == expected_size
        structural_ok = structural_ok and len(set(candidate_ids)) == expected_size
        structural_ok = structural_ok and pid in candidate_ids
        structural_ok = structural_ok and set(candidate_ids).issubset(known_ids)
        if not structural_ok or pid not in persona_by_id:
            continue
        target = persona_by_id[pid]
        decoys = [candidate for candidate in candidate_ids if candidate != pid]
        overlaps = [
            sum(target[field] == persona_by_id[candidate][field] for field in DECOY_OVERLAP_FIELDS)
            for candidate in decoys
        ]
        if overlaps:
            max_overlaps.append(max(overlaps))
            avg_overlaps.append(sum(overlaps) / len(overlaps))
            same_region_sets += int(
                any(target["region"] == persona_by_id[candidate]["region"] for candidate in decoys)
            )
            same_occupation_sets += int(
                any(target["occupation"] == persona_by_id[candidate]["occupation"] for candidate in decoys)
            )

    add_check(
        checks,
        "candidates:structural_integrity",
        structural_ok and len(candidate_sets) == len(personas),
        "candidate sets have expected size, include the target, and contain unique known persona IDs",
        display_path(path, paths.root),
        expected=f"{len(personas)} sets of {expected_size}",
        observed=f"{len(candidate_sets)} sets",
    )
    add_check(
        checks,
        "candidates:decoy_overlap",
        bool(max_overlaps) and min(max_overlaps) >= 2 and (sum(max_overlaps) / len(max_overlaps)) >= 3.0,
        "each target has at least one nontrivial decoy and average max overlap is substantial",
        display_path(path, paths.root),
        expected="min_max_overlap>=2, mean_max_overlap>=3.0",
        observed=f"min_max_overlap={min(max_overlaps) if max_overlaps else 0}, mean_max_overlap={(sum(max_overlaps) / len(max_overlaps)) if max_overlaps else 0:.3f}",
    )
    add_check(
        checks,
        "candidates:shared_context_decoys",
        same_region_sets == len(personas) and same_occupation_sets >= int(0.6 * len(personas)),
        "decoy sets include shared-context profiles, not only random negatives",
        display_path(path, paths.root),
        expected=f"same_region={len(personas)}, same_occupation>={int(0.6 * len(personas))}",
        observed=f"same_region={same_region_sets}, same_occupation={same_occupation_sets}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated synthetic benchmark artifacts.")
    parser.add_argument("--config", default="configs/sprint.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    personas = read_jsonl(paths.data / "personas.jsonl")
    original_docs = read_jsonl(paths.data / "original_docs.jsonl")

    checks: list[Check] = []
    validate_corpus(cfg, paths, personas, original_docs, checks)
    validate_transforms(cfg, paths, personas, checks)
    validate_candidate_sets(cfg, paths, personas, checks)

    rows = [check.__dict__ for check in checks]
    df = pd.DataFrame(rows)
    out_csv = paths.results / "benchmark_validation.csv"
    out_json = paths.results / "benchmark_validation.json"
    out_md = paths.results / "benchmark_validation.md"
    df.to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")

    summary = df.groupby("status").size().reset_index(name="n")
    failed = df[df["status"] != "PASS"]
    lines = [
        "# Benchmark Validation Report",
        "",
        "This audit checks corpus cardinality, transformed-condition completeness, exact synthetic direct-identifier removal, candidate-set sanity, and utility-label retention.",
        "",
        "## Summary",
        "",
        dataframe_to_markdown(summary, floatfmt=".0f"),
        "",
        "## Checks",
        "",
        dataframe_to_markdown(df, floatfmt=".3f"),
    ]
    if not failed.empty:
        lines.extend(["", "## Failures", "", dataframe_to_markdown(failed, floatfmt=".3f")])
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    n_fail = int((df["status"] != "PASS").sum())
    print(out_md)
    print(f"checks={len(df)} failures={n_fail}")
    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
