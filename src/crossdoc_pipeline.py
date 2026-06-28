#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "cache/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "cache")
os.environ.setdefault("TLDEXTRACT_CACHE", "cache/tldextract")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import yaml
from faker import Faker
from scipy import sparse
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    adjusted_rand_score,
    accuracy_score,
    f1_score,
    normalized_mutual_info_score,
    precision_recall_fscore_support,
)

_PRESIDIO_ANALYZER = None
PRESIDIO_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "US_DRIVER_LICENSE",
]


DOMAINS = ["healthcare", "legal", "financial", "hr"]

ISSUES = {
    "healthcare": [
        "refill_request",
        "appointment_scheduling",
        "symptom_followup",
        "insurance_question",
    ],
    "legal": [
        "employment_dispute",
        "housing_issue",
        "benefits_appeal",
        "consumer_complaint",
    ],
    "financial": [
        "payment_deferral",
        "fraud_inquiry",
        "account_correction",
        "hardship_request",
    ],
    "hr": [
        "leave_request",
        "accommodation_request",
        "benefits_question",
        "schedule_change",
    ],
}

ISSUE_PHRASES = {
    "refill_request": "medication refill",
    "appointment_scheduling": "appointment scheduling",
    "symptom_followup": "symptom follow-up",
    "insurance_question": "insurance question",
    "employment_dispute": "employment dispute",
    "housing_issue": "housing issue",
    "benefits_appeal": "benefits appeal",
    "consumer_complaint": "consumer complaint",
    "payment_deferral": "payment deferral",
    "fraud_inquiry": "fraud inquiry",
    "account_correction": "account correction",
    "hardship_request": "hardship request",
    "leave_request": "leave request",
    "accommodation_request": "accommodation request",
    "benefits_question": "benefits question",
    "schedule_change": "schedule change",
}

CITIES_BY_REGION = {
    "Pacific Northwest": ["Boise", "Eugene", "Spokane", "Bend", "Tacoma"],
    "Mountain West": ["Reno", "Ogden", "Missoula", "Flagstaff", "Santa Fe"],
    "Upper Midwest": ["Duluth", "Madison", "Fargo", "Iowa City", "Green Bay"],
    "Northeast": ["Albany", "Providence", "Burlington", "New Haven", "Portland"],
    "Southeast": ["Asheville", "Savannah", "Knoxville", "Tallahassee", "Durham"],
    "Southwest": ["Tucson", "El Paso", "Tempe", "Las Cruces", "Mesa"],
}

OCCUPATIONS = {
    "neonatal nurse": "healthcare worker",
    "dialysis technician": "healthcare worker",
    "radiology scheduler": "healthcare administrator",
    "patent paralegal": "legal worker",
    "tenant advocate": "legal services worker",
    "benefits caseworker": "public services worker",
    "robotics startup bookkeeper": "finance worker",
    "credit union fraud analyst": "finance worker",
    "school payroll coordinator": "administrative worker",
    "warehouse safety trainer": "operations worker",
    "bilingual special education aide": "education worker",
    "veterans clinic receptionist": "healthcare administrator",
    "rural broadband installer": "technical worker",
    "community college lab manager": "education worker",
    "municipal water inspector": "public works employee",
    "night-shift pharmacy clerk": "retail healthcare worker",
}

EMPLOYER_TYPES = {
    "regional hospital": "healthcare institution",
    "county legal aid office": "legal services organization",
    "credit union": "financial institution",
    "public school district": "education employer",
    "municipal agency": "government employer",
    "robotics startup": "technology employer",
    "community college": "education employer",
    "logistics warehouse": "operations employer",
    "veterans clinic": "healthcare institution",
    "nonprofit housing center": "nonprofit organization",
}

EDUCATION = {
    "community college nursing program": "community college program",
    "state university evening program": "state university program",
    "trade certificate program": "vocational program",
    "online accounting certificate": "online certificate program",
    "bilingual education credential": "education credential",
    "paralegal studies certificate": "legal certificate program",
}

FAMILY_STRUCTURES = {
    "parent of twins": "childcare responsibilities",
    "caregiver for an older parent": "family caregiving responsibility",
    "single parent of a middle-school student": "childcare responsibilities",
    "spouse deployed overseas": "family responsibility",
    "shared custody schedule": "family scheduling responsibility",
    "guardian for a younger sibling": "family caregiving responsibility",
}

MEDICAL_CONTEXTS = {
    "autoimmune condition": "chronic health condition",
    "dialysis schedule": "ongoing treatment schedule",
    "migraine treatment plan": "recurring health issue",
    "post-surgery physical therapy": "recovery care",
    "respiratory condition": "chronic health condition",
    "diabetes medication management": "chronic health condition",
}

FINANCIAL_CONTEXTS = {
    "mortgage hardship": "housing-related financial hardship",
    "temporary wage garnishment": "income disruption",
    "unexpected medical bills": "medical expense hardship",
    "childcare cost spike": "family expense hardship",
    "fraudulent debit-card charges": "account security issue",
    "delayed insurance reimbursement": "reimbursement delay",
}

LEGAL_CONTEXTS = {
    "workplace accommodation dispute": "employment legal issue",
    "landlord repair complaint": "housing legal issue",
    "benefits eligibility appeal": "benefits legal issue",
    "consumer warranty dispute": "consumer legal issue",
    "public records hearing": "administrative legal issue",
    "school services appeal": "education legal issue",
}

SCHEDULE_PATTERNS = {
    "night shifts": "nonstandard work schedule",
    "Saturday dialysis": "recurring treatment schedule",
    "split custody weekends": "family scheduling constraint",
    "rotating warehouse shifts": "variable work schedule",
    "evening classes": "education schedule constraint",
    "early-morning bus route": "transportation schedule constraint",
}

HOBBIES = {
    "local ceramics co-op": "arts community activity",
    "German language school": "language learning group",
    "regional chess club": "recreation group",
    "church food pantry": "volunteer activity",
    "adapted cycling group": "sports community activity",
    "community theater crew": "arts community activity",
}

RARE_EVENTS = {
    "testified at a county hearing about hospital staffing": "local civic event",
    "organized a school translation night": "community education event",
    "reported a small-town water contamination issue": "local public works event",
    "helped recover funds after a robotics vendor breach": "workplace security event",
    "appeared in a local article about dialysis transport": "local news event",
    "coordinated a wildfire evacuation volunteer shift": "emergency volunteer event",
    "filed minutes for a housing board meeting": "housing governance event",
    "translated at a municipal benefits clinic": "community services event",
}

SPECIFICITY_PRIOR = {
    "city": 2.0,
    "occupation": 2.0,
    "employer_type": 2.0,
    "education": 1.2,
    "family_structure": 1.5,
    "medical_context": 1.5,
    "financial_context": 1.0,
    "legal_context": 1.5,
    "schedule_pattern": 1.0,
    "hobby_or_affiliation": 1.2,
    "rare_event": 2.0,
}

UTILITY_COST = {
    "city": 0.3,
    "occupation": 0.6,
    "employer_type": 0.4,
    "education": 0.4,
    "family_structure": 0.5,
    "medical_context": 0.8,
    "financial_context": 0.8,
    "legal_context": 0.8,
    "schedule_pattern": 0.5,
    "hobby_or_affiliation": 0.3,
    "rare_event": 0.2,
}

FIELD_SUPPRESSIONS = {
    "city": "a broad location",
    "occupation": "general worker",
    "employer_type": "general organization",
    "education": "general educational background",
    "family_structure": "family responsibility",
    "medical_context": "health context",
    "financial_context": "financial context",
    "legal_context": "legal context",
    "schedule_pattern": "availability constraint",
    "hobby_or_affiliation": "community activity",
    "rare_event": "a local event",
}

ATTRIBUTE_FIELDS = list(SPECIFICITY_PRIOR)


@dataclass
class Paths:
    root: Path
    data: Path
    transformed: Path
    results: Path


def load_config(path: Path) -> dict[str, Any]:
    with path.open() as f:
        cfg = yaml.safe_load(f)
    return cfg


def make_paths(cfg: dict[str, Any]) -> Paths:
    root = Path.cwd()
    data = root / cfg["data_dir"]
    transformed = data / "transformed"
    results = root / cfg["results_dir"]
    for p in [data, transformed, results]:
        p.mkdir(parents=True, exist_ok=True)
    return Paths(root=root, data=data, transformed=transformed, results=results)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def dataframe_to_markdown(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    columns = list(df.columns)

    def fmt(value: Any) -> str:
        if isinstance(value, (float, np.floating)):
            return format(float(value), floatfmt)
        if isinstance(value, (int, np.integer)):
            return str(int(value))
        return str(value)

    rows = [[fmt(row[col]) for col in columns] for _, row in df.iterrows()]
    widths = [
        max(len(str(col)), *(len(row[i]) for row in rows)) if rows else len(str(col))
        for i, col in enumerate(columns)
    ]
    header = "| " + " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(columns)) + " |"
    sep = "| " + " | ".join("-" * widths[i] for i in range(len(columns))) + " |"
    body = [
        "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(columns))) + " |"
        for row in rows
    ]
    return "\n".join([header, sep, *body])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stable_choice(values: list[str], idx: int, rng: random.Random) -> str:
    offset = rng.randrange(len(values))
    return values[(idx + offset) % len(values)]


def region_for_city(city: str) -> str:
    for region, cities in CITIES_BY_REGION.items():
        if city in cities:
            return region
    raise KeyError(city)


def persona_signature(persona: dict[str, Any], fields: list[str]) -> tuple[str, ...]:
    return tuple(str(persona.get(field, "")) for field in fields)


def generate_personas(cfg: dict[str, Any], paths: Paths) -> list[dict[str, Any]]:
    rng = random.Random(cfg["seed"])
    faker = Faker("en_US")
    Faker.seed(cfg["seed"])
    num_personas = int(cfg["num_personas"])
    risk_cycle = ["T1", "T2", "T3"]
    all_cities = [city for cities in CITIES_BY_REGION.values() for city in cities]
    personas: list[dict[str, Any]] = []

    occupation_keys = list(OCCUPATIONS)
    employer_keys = list(EMPLOYER_TYPES)
    education_keys = list(EDUCATION)
    family_keys = list(FAMILY_STRUCTURES)
    medical_keys = list(MEDICAL_CONTEXTS)
    financial_keys = list(FINANCIAL_CONTEXTS)
    legal_keys = list(LEGAL_CONTEXTS)
    schedule_keys = list(SCHEDULE_PATTERNS)
    hobby_keys = list(HOBBIES)
    rare_keys = list(RARE_EVENTS)

    for i in range(num_personas):
        city = stable_choice(all_cities, i * 3, rng)
        region = region_for_city(city)
        name = faker.unique.name()
        first_last = re.sub(r"[^a-z.]+", ".", name.lower()).strip(".")
        risk_tier = risk_cycle[i % len(risk_cycle)]
        age_band = stable_choice(["20-29", "30-39", "40-49", "50-59", "60-69"], i, rng)
        persona = {
            "persona_id": f"P{i:04d}",
            "synthetic_name": name,
            "email": f"{first_last}{i:03d}@synthetic-example.org",
            "phone": f"({rng.randrange(200, 989)}) 555-{rng.randrange(1000, 9999)}",
            "address": f"{rng.randrange(101, 9900)} {faker.street_name()}",
            "account_id": f"ACCT-{rng.randrange(100000, 999999)}",
            "age_band": age_band,
            "gender_marker": stable_choice(["woman", "man", "nonbinary adult"], i, rng),
            "region": region,
            "city": city,
            "occupation": stable_choice(occupation_keys, i * 5, rng),
            "employer_type": stable_choice(employer_keys, i * 7, rng),
            "education": stable_choice(education_keys, i * 11, rng),
            "family_structure": stable_choice(family_keys, i * 13, rng),
            "medical_context": stable_choice(medical_keys, i * 17, rng),
            "financial_context": stable_choice(financial_keys, i * 19, rng),
            "legal_context": stable_choice(legal_keys, i * 23, rng),
            "schedule_pattern": stable_choice(schedule_keys, i * 29, rng),
            "hobby_or_affiliation": stable_choice(hobby_keys, i * 31, rng),
            "rare_event": stable_choice(rare_keys, i * 37, rng),
            "risk_tier": risk_tier,
        }
        persona["utility_labels"] = {
            domain: stable_choice(ISSUES[domain], i + j * 5, rng)
            for j, domain in enumerate(DOMAINS)
        }
        persona["job_family"] = OCCUPATIONS[persona["occupation"]]
        personas.append(persona)

    write_jsonl(paths.data / "personas.jsonl", personas)
    return personas


def display_values(persona: dict[str, Any]) -> dict[str, str]:
    tier = persona["risk_tier"]
    if tier == "T1":
        return {
            "location": persona["region"],
            "role": persona["job_family"],
            "employer": EMPLOYER_TYPES[persona["employer_type"]],
            "education": EDUCATION[persona["education"]],
            "family": "family responsibilities",
            "medical": "a health issue",
            "financial": "a billing concern",
            "legal": "an administrative issue",
            "schedule": "an availability constraint",
            "hobby": "a community activity",
            "rare": "a local event",
        }
    if tier == "T2":
        return {
            "location": f"{persona['city']} in the {persona['region']}",
            "role": persona["job_family"],
            "employer": persona["employer_type"],
            "education": EDUCATION[persona["education"]],
            "family": FAMILY_STRUCTURES[persona["family_structure"]],
            "medical": MEDICAL_CONTEXTS[persona["medical_context"]],
            "financial": FINANCIAL_CONTEXTS[persona["financial_context"]],
            "legal": LEGAL_CONTEXTS[persona["legal_context"]],
            "schedule": SCHEDULE_PATTERNS[persona["schedule_pattern"]],
            "hobby": HOBBIES[persona["hobby_or_affiliation"]],
            "rare": RARE_EVENTS[persona["rare_event"]],
        }
    return {
        "location": persona["city"],
        "role": persona["occupation"],
        "employer": persona["employer_type"],
        "education": persona["education"],
        "family": persona["family_structure"],
        "medical": persona["medical_context"],
        "financial": persona["financial_context"],
        "legal": persona["legal_context"],
        "schedule": persona["schedule_pattern"],
        "hobby": persona["hobby_or_affiliation"],
        "rare": persona["rare_event"],
    }


def with_indefinite_article(phrase: str) -> str:
    article = "an" if phrase[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {phrase}"


def render_documents(cfg: dict[str, Any], paths: Paths, personas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    max_variants = 3
    template_variants = max(1, min(int(cfg.get("template_variants_per_domain", 1)), max_variants))
    contact_lines = {
        "healthcare": [
            "Patient contact: {direct}\n",
            "Portal identity line: {direct}\n",
            "Care team contact record: {direct}\n",
        ],
        "legal": [
            "Client contact: {direct}\n",
            "Intake contact record: {direct}\n",
            "Case follow-up contact: {direct}\n",
        ],
        "financial": [
            "Requester contact: {direct}\n",
            "Support profile contact: {direct}\n",
            "Account support contact: {direct}\n",
        ],
        "hr": [
            "Employee contact: {direct}\n",
            "HR profile contact: {direct}\n",
            "Workplace request contact: {direct}\n",
        ],
    }
    body_templates = {
        "healthcare": [
            (
                "I need help with {healthcare_issue_np}. I am based around {location} and work as {role_np}. "
                "Managing {medical} has been harder around {schedule}. Please note the {family} constraint "
                "when suggesting appointment times."
            ),
            (
                "I am writing about {healthcare_issue_np}. My location is {location}, and my job is {role}. "
                "The {medical} is colliding with {schedule}. The {family} constraint affects when I can come in."
            ),
            (
                "This message is for {healthcare_issue_np}. I live around {location} and work as {role_np}. "
                "Because of {medical} and {schedule}, I need options that account for {family}."
            ),
        ],
        "legal": [
            (
                "I am asking about {legal_issue_np} connected to {legal}. My work is through {employer_np}, "
                "and the situation became harder after {rare}. I can provide records after {schedule}."
            ),
            (
                "I need guidance on {legal_issue_np} involving {legal}. I am connected with {employer_np}; "
                "{rare} made the timeline more complicated. I can follow up around {schedule}."
            ),
            (
                "This intake is about {legal_issue_np}. The issue relates to {legal}, my workplace context is {employer_np}, "
                "and {rare} is part of the background. My availability is shaped by {schedule}."
            ),
        ],
        "financial": [
            (
                "I am requesting support for {financial_issue_np}. The immediate reason is {financial}, "
                "and my household schedule involves {family}. I am in {location} and trying to avoid a missed payment."
            ),
            (
                "I need help with {financial_issue_np}. The pressure point is {financial}; at home, {family} affects timing. "
                "I am located in {location} and want to prevent a missed payment."
            ),
            (
                "This request concerns {financial_issue_np}. It is tied to {financial}, and {family} affects my flexibility. "
                "I am around {location} and am trying to keep the account current."
            ),
        ],
        "hr": [
            (
                "I need HR help with {hr_issue_np}. My role is {role} at {employer_np}; my background includes "
                "{education}. The request is related to {schedule}, {medical}, and participation in {hobby}."
            ),
            (
                "I am submitting an HR request for {hr_issue_np}. I work as {role_np} at {employer_np}, with "
                "{education} in my background. The context includes {schedule}, {medical}, and {hobby}."
            ),
            (
                "This HR note is about {hr_issue_np}. My job is {role} at {employer_np}; I also have "
                "{education}. The timing involves {schedule}, {medical}, and {hobby}."
            ),
        ],
    }
    for persona in personas:
        vals = display_values(persona)
        pid = persona["persona_id"]
        name = persona["synthetic_name"]
        issue = persona["utility_labels"]
        direct = (
            f"{name}; email {persona['email']}; phone {persona['phone']}; "
            f"mailing address {persona['address']}; account {persona['account_id']}."
        )
        for doc_idx, domain in enumerate(DOMAINS):
            variant_idx = (int(pid.replace("P", "")) + doc_idx) % template_variants
            format_kwargs = {
                **vals,
                "direct": direct,
                "healthcare_phrase": ISSUE_PHRASES[issue["healthcare"]],
                "legal_phrase": ISSUE_PHRASES[issue["legal"]],
                "financial_phrase": ISSUE_PHRASES[issue["financial"]],
                "hr_phrase": ISSUE_PHRASES[issue["hr"]],
                "healthcare_issue_np": with_indefinite_article(ISSUE_PHRASES[issue["healthcare"]]),
                "legal_issue_np": with_indefinite_article(ISSUE_PHRASES[issue["legal"]]),
                "financial_issue_np": with_indefinite_article(ISSUE_PHRASES[issue["financial"]]),
                "hr_issue_np": with_indefinite_article(ISSUE_PHRASES[issue["hr"]]),
                "role_np": with_indefinite_article(vals["role"]),
                "employer_np": with_indefinite_article(vals["employer"]),
            }
            issue_key = f"{domain}_phrase"
            text = (
                f"Subject: {{{issue_key}}}\n"
                + contact_lines[domain][variant_idx]
                + body_templates[domain][variant_idx]
            ).format(**format_kwargs)
            doc = {
                "doc_id": f"{pid}_D{doc_idx + 1:02d}",
                "persona_id": pid,
                "domain": domain,
                "risk_tier": persona["risk_tier"],
                "template_variant": variant_idx,
                "text": text,
                "intended_quasi_ids": [
                    vals["location"],
                    vals["role"],
                    vals["family"],
                    vals["medical"],
                    vals["schedule"],
                    vals["rare"],
                ],
                "utility_labels": {
                    "domain": domain,
                    "issue": issue[domain],
                },
                "key_facts": [
                    f"the document is about {ISSUE_PHRASES[issue[domain]]}",
                    f"the domain is {domain}",
                    "the user is asking for support or service triage",
                ],
            }
            docs.append(doc)
    write_jsonl(paths.data / "original_docs.jsonl", docs)
    write_jsonl(paths.transformed / "original.jsonl", docs)
    return docs


def make_aux_profiles(
    cfg: dict[str, Any], paths: Paths, personas: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rng = random.Random(cfg["seed"] + 99)
    candidate_set_size = int(cfg["candidate_set_size"])
    candidates: list[dict[str, Any]] = []
    fields = [
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

    for persona in personas:
        scored = []
        for other in personas:
            if other["persona_id"] == persona["persona_id"]:
                continue
            overlap = sum(persona[f] == other[f] for f in fields)
            same_region = int(persona["region"] == other["region"])
            scored.append((overlap + same_region * 0.5 + rng.random() * 0.01, other))
        scored.sort(key=lambda x: x[0], reverse=True)
        decoys = [p for _, p in scored[: candidate_set_size - 1]]
        candidate_ids = [persona["persona_id"]] + [d["persona_id"] for d in decoys]
        rng.shuffle(candidate_ids)
        candidates.append(
            {
                "persona_id": persona["persona_id"],
                "candidate_set_size": candidate_set_size,
                "candidate_ids": candidate_ids,
            }
        )

    aux_rows = []
    for persona in personas:
        aux_rows.append(
            {
                "persona_id": persona["persona_id"],
                "profile_text": aux_profile_text(persona),
                "profile": {
                    k: persona[k]
                    for k in fields
                    if k in persona
                },
            }
        )
    write_jsonl(paths.data / "auxiliary_profiles.jsonl", aux_rows)
    write_jsonl(paths.data / "candidate_sets.jsonl", candidates)
    return candidates


def aux_profile_text(persona: dict[str, Any]) -> str:
    return (
        f"Profile {persona['persona_id']}: {persona['age_band']} adult in {persona['city']} "
        f"({persona['region']}); occupation {persona['occupation']} at a {persona['employer_type']}; "
        f"education {persona['education']}; family {persona['family_structure']}; "
        f"medical context {persona['medical_context']}; financial context {persona['financial_context']}; "
        f"legal context {persona['legal_context']}; schedule {persona['schedule_pattern']}; "
        f"affiliation {persona['hobby_or_affiliation']}; notable event {persona['rare_event']}."
    )


def replace_many(text: str, replacements: list[tuple[str, str]]) -> str:
    out = text
    for src, dst in sorted(replacements, key=lambda x: len(x[0]), reverse=True):
        if not src:
            continue
        out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
    return out


def get_presidio_analyzer() -> Any:
    global _PRESIDIO_ANALYZER
    if _PRESIDIO_ANALYZER is not None:
        return _PRESIDIO_ANALYZER

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError as exc:
        raise RuntimeError(
            "Presidio baseline requires presidio-analyzer, presidio-anonymizer, "
            "and spaCy model en_core_web_sm in the cross_linkage environment."
        ) from exc

    cache_dir = Path(os.environ.get("TLDEXTRACT_CACHE", "cache/tldextract"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
    _PRESIDIO_ANALYZER = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    return _PRESIDIO_ANALYZER


def merge_redaction_spans(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    merged: list[tuple[int, int, str]] = []
    for start, end, label in sorted(spans, key=lambda x: (x[0], -x[1])):
        if start >= end:
            continue
        if not merged or start >= merged[-1][1]:
            merged.append((start, end, label))
        else:
            prev_start, prev_end, prev_label = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end), prev_label if prev_label == label else "[PRESIDIO_PII]")
    return merged


def presidio_redact_text(text: str, analyzer: Any | None = None) -> str:
    analyzer = analyzer or get_presidio_analyzer()
    results = analyzer.analyze(text=text, language="en", entities=PRESIDIO_ENTITIES)
    spans: list[tuple[int, int, str]] = []
    for result in results:
        if float(result.score) < 0.35:
            continue
        spans.append((int(result.start), int(result.end), f"[PRESIDIO_{result.entity_type}]"))

    regex_spans = [
        (r"\b[\w.%-]+@synthetic-example\.org\b", "[PRESIDIO_EMAIL_ADDRESS]", 0),
        (r"\(\d{3}\)\s*555-\d{4}\b", "[PRESIDIO_PHONE_NUMBER]", 0),
        (r"\bACCT-\d+\b", "[PRESIDIO_ACCOUNT_ID]", 0),
        (r"mailing address ([^;]+);", "[PRESIDIO_ADDRESS]", 1),
    ]
    for pattern, label, group_idx in regex_spans:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append((match.start(group_idx), match.end(group_idx), label))

    out = text
    for start, end, label in reversed(merge_redaction_spans(spans)):
        out = out[:start] + label + out[end:]
    return out


def direct_replacements(persona: dict[str, Any]) -> list[tuple[str, str]]:
    first = persona["synthetic_name"].split()[0]
    last = persona["synthetic_name"].split()[-1]
    return [
        (persona["synthetic_name"], "[NAME]"),
        (first, "[FIRST_NAME]"),
        (last, "[LAST_NAME]"),
        (persona["email"], "[EMAIL]"),
        (persona["phone"], "[PHONE]"),
        (persona["address"], "[ADDRESS]"),
        (persona["account_id"], "[ACCOUNT_ID]"),
    ]


def pseudonym_replacements(
    persona: dict[str, Any], doc_id: str | None, city_ids: dict[str, str], employer_ids: dict[str, str]
) -> list[tuple[str, str]]:
    suffix = persona["persona_id"].replace("P", "")
    if doc_id is not None:
        digest = hashlib.sha1(doc_id.encode()).hexdigest()[:6].upper()
        person_token = f"PERSON_{digest}"
        email_token = f"EMAIL_{digest}"
        phone_token = f"PHONE_{digest}"
        address_token = f"ADDRESS_{digest}"
    else:
        person_token = f"PERSON_{suffix}"
        email_token = f"EMAIL_{suffix}"
        phone_token = f"PHONE_{suffix}"
        address_token = f"ADDRESS_{suffix}"
    first = persona["synthetic_name"].split()[0]
    last = persona["synthetic_name"].split()[-1]
    return [
        (persona["synthetic_name"], person_token),
        (first, person_token),
        (last, person_token),
        (persona["email"], email_token),
        (persona["phone"], phone_token),
        (persona["address"], address_token),
        (persona["account_id"], f"ACCOUNT_{suffix if doc_id is None else hashlib.sha1(doc_id.encode()).hexdigest()[:6].upper()}"),
        (persona["city"], city_ids[persona["city"]]),
        (persona["employer_type"], employer_ids[persona["employer_type"]]),
    ]


def doc_local_replacements(persona: dict[str, Any]) -> list[tuple[str, str]]:
    return direct_replacements(persona) + [
        (persona["city"], f"a city in the {persona['region']}"),
        (persona["address"].split()[-1], "[STREET]"),
        (persona["education"], EDUCATION[persona["education"]]),
    ]


def aggressive_replacements(persona: dict[str, Any]) -> list[tuple[str, str]]:
    repl = direct_replacements(persona)
    repl += [
        (persona["city"], "[LOCATION]"),
        (persona["region"], "[REGION]"),
        (persona["occupation"], "[ROLE]"),
        (persona["job_family"], "[ROLE]"),
        (persona["employer_type"], "[INSTITUTION]"),
        (EMPLOYER_TYPES[persona["employer_type"]], "[INSTITUTION]"),
        (persona["education"], "[EDUCATION]"),
        (EDUCATION[persona["education"]], "[EDUCATION]"),
        (persona["family_structure"], "[FAMILY_CONTEXT]"),
        (FAMILY_STRUCTURES[persona["family_structure"]], "[FAMILY_CONTEXT]"),
        (persona["medical_context"], "[MEDICAL_CONTEXT]"),
        (MEDICAL_CONTEXTS[persona["medical_context"]], "[MEDICAL_CONTEXT]"),
        (persona["financial_context"], "[FINANCIAL_CONTEXT]"),
        (FINANCIAL_CONTEXTS[persona["financial_context"]], "[FINANCIAL_CONTEXT]"),
        (persona["legal_context"], "[LEGAL_CONTEXT]"),
        (LEGAL_CONTEXTS[persona["legal_context"]], "[LEGAL_CONTEXT]"),
        (persona["schedule_pattern"], "[SCHEDULE]"),
        (SCHEDULE_PATTERNS[persona["schedule_pattern"]], "[SCHEDULE]"),
        (persona["hobby_or_affiliation"], "[AFFILIATION]"),
        (HOBBIES[persona["hobby_or_affiliation"]], "[AFFILIATION]"),
        (persona["rare_event"], "[EVENT]"),
        (RARE_EVENTS[persona["rare_event"]], "[EVENT]"),
    ]
    for phrase in ISSUE_PHRASES.values():
        repl.append((phrase, "[ISSUE]"))
    return repl


def field_generalization(persona: dict[str, Any], field: str) -> str:
    if field == "city":
        return persona["region"]
    if field == "occupation":
        return OCCUPATIONS[persona["occupation"]]
    if field == "employer_type":
        return EMPLOYER_TYPES[persona["employer_type"]]
    if field == "education":
        return EDUCATION[persona["education"]]
    if field == "family_structure":
        return FAMILY_STRUCTURES[persona["family_structure"]]
    if field == "medical_context":
        return MEDICAL_CONTEXTS[persona["medical_context"]]
    if field == "financial_context":
        return FINANCIAL_CONTEXTS[persona["financial_context"]]
    if field == "legal_context":
        return LEGAL_CONTEXTS[persona["legal_context"]]
    if field == "schedule_pattern":
        return SCHEDULE_PATTERNS[persona["schedule_pattern"]]
    if field == "hobby_or_affiliation":
        return HOBBIES[persona["hobby_or_affiliation"]]
    if field == "rare_event":
        return RARE_EVENTS[persona["rare_event"]]
    raise KeyError(field)


def field_value_at_level(persona: dict[str, Any], field: str, level: int) -> str:
    if level <= 0:
        return persona[field]
    if level == 1:
        return field_generalization(persona, field)
    return FIELD_SUPPRESSIONS[field]


def estimate_k_for_levels(
    personas: list[dict[str, Any]], levels: dict[str, int], target_persona: dict[str, Any]
) -> int:
    target = {
        field: field_value_at_level(target_persona, field, level)
        for field, level in levels.items()
    }
    count = 0
    for persona in personas:
        if all(
            field_value_at_level(persona, field, levels[field]) == value
            for field, value in target.items()
        ):
            count += 1
    return count


def replacements_for_linkguard_levels(
    persona: dict[str, Any], levels: dict[str, int]
) -> list[tuple[str, str]]:
    replacements: list[tuple[str, str]] = direct_replacements(persona)
    for field, level in levels.items():
        if level <= 0:
            continue
        exact = persona[field]
        coarse = field_generalization(persona, field)
        if level == 1:
            if field == "city":
                replacements.append((f"{persona['city']} in the {persona['region']}", f"the {persona['region']}"))
                replacements.append((persona["city"], f"a city in the {persona['region']}"))
            else:
                replacements.append((exact, coarse))
        else:
            generic = FIELD_SUPPRESSIONS[field]
            replacements.append((exact, generic))
            replacements.append((coarse, generic))
            if field == "city":
                replacements.append((f"{persona['city']} in the {persona['region']}", generic))
                replacements.append((persona["region"], generic))
    return replacements


def linkguard_replacements(
    personas: list[dict[str, Any]],
    target_k: int,
    paths: Paths,
    log_name: str = "linkguard_generalization_log.jsonl",
) -> dict[str, list[tuple[str, str]]]:
    fields = list(SPECIFICITY_PRIOR)
    value_counts: dict[str, Counter[str]] = {
        field: Counter(p[field] for p in personas) for field in fields
    }
    n = len(personas)
    logs = []
    repl_by_persona: dict[str, list[tuple[str, str]]] = {}
    for persona in personas:
        levels = {field: 0 for field in fields}
        chosen = []
        current_k = estimate_k_for_levels(personas, levels, persona)
        while current_k < target_k:
            candidates = []
            for field in fields:
                if levels[field] >= 2:
                    continue
                count = value_counts[field][persona[field]]
                rarity = -math.log((count + 0.5) / (n + 0.5 * max(len(value_counts[field]), 1)))
                next_level = levels[field] + 1
                utility_penalty = UTILITY_COST[field] * (1.0 + 0.8 * (next_level - 1))
                score = (rarity + SPECIFICITY_PRIOR[field] + 1.0) / max(utility_penalty, 0.1)
                candidates.append((score, field))
            if not candidates:
                break
            _, field = max(candidates)
            levels[field] += 1
            chosen.append(f"{field}:L{levels[field]}")
            current_k = estimate_k_for_levels(personas, levels, persona)
        repl_by_persona[persona["persona_id"]] = replacements_for_linkguard_levels(persona, levels)
        logs.append(
            {
                "persona_id": persona["persona_id"],
                "risk_tier": persona["risk_tier"],
                "target_k": target_k,
                "estimated_k": current_k,
                "generalized_fields": chosen,
                "field_levels": levels,
            }
        )
    write_jsonl(paths.results / log_name, logs)
    return repl_by_persona


def transform_docs(cfg: dict[str, Any], paths: Paths, personas: list[dict[str, Any]], docs: list[dict[str, Any]]) -> None:
    p_by_id = {p["persona_id"]: p for p in personas}
    city_ids = {city: f"CITY_{i:03d}" for i, city in enumerate(sorted({p["city"] for p in personas}))}
    employer_ids = {
        emp: f"ORG_{i:03d}" for i, emp in enumerate(sorted({p["employer_type"] for p in personas}))
    }
    linkguard = linkguard_replacements(personas, int(cfg["target_k"]), paths)
    presidio_analyzer = get_presidio_analyzer() if "c1b_presidio_redaction" in cfg["conditions"] else None

    condition_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edit_rows = []

    for doc in docs:
        persona = p_by_id[doc["persona_id"]]
        transforms = {
            "c1_direct_redaction": direct_replacements(persona),
            "c2_consistent_pseudonym": pseudonym_replacements(persona, None, city_ids, employer_ids),
            "c3_per_doc_pseudonym": pseudonym_replacements(persona, doc["doc_id"], city_ids, employer_ids),
            "c4_doc_local_anon": doc_local_replacements(persona),
            "c5_linkguard": linkguard[persona["persona_id"]],
            "c6_aggressive_redaction": aggressive_replacements(persona),
        }
        for condition, replacements in transforms.items():
            new_text = replace_many(doc["text"], replacements)
            out = {**doc, "text": new_text, "condition": condition}
            condition_rows[condition].append(out)
            edit_rows.append(
                {
                    "condition": condition,
                    "doc_id": doc["doc_id"],
                    "edit_ratio": 1.0 - difflib.SequenceMatcher(None, doc["text"], new_text).ratio(),
                    "char_delta": len(new_text) - len(doc["text"]),
                }
            )
        if presidio_analyzer is not None:
            new_text = replace_many(
                presidio_redact_text(doc["text"], presidio_analyzer),
                direct_replacements(persona),
            )
            condition = "c1b_presidio_redaction"
            out = {**doc, "text": new_text, "condition": condition}
            condition_rows[condition].append(out)
            edit_rows.append(
                {
                    "condition": condition,
                    "doc_id": doc["doc_id"],
                    "edit_ratio": 1.0 - difflib.SequenceMatcher(None, doc["text"], new_text).ratio(),
                    "char_delta": len(new_text) - len(doc["text"]),
                }
            )

    for condition, rows in condition_rows.items():
        write_jsonl(paths.transformed / f"{condition}.jsonl", rows)
    pd.DataFrame(edit_rows).to_csv(paths.results / "edit_ratios.csv", index=False)


def split_personas(personas: list[dict[str, Any]]) -> dict[str, set[str]]:
    sorted_ids = sorted(p["persona_id"] for p in personas)
    val = set(sorted_ids[::5])
    test = set(pid for pid in sorted_ids if pid not in val)
    return {"val": val, "test": test}


def vectorize_docs(docs: list[dict[str, Any]]) -> tuple[TfidfVectorizer, sparse.csr_matrix]:
    texts = [d["text"] for d in docs]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        min_df=1,
        max_df=0.65,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix


def signature_phrase_vocab() -> list[str]:
    terms: set[str] = set()
    dictionaries = [
        CITIES_BY_REGION,
        OCCUPATIONS,
        EMPLOYER_TYPES,
        EDUCATION,
        FAMILY_STRUCTURES,
        MEDICAL_CONTEXTS,
        FINANCIAL_CONTEXTS,
        LEGAL_CONTEXTS,
        SCHEDULE_PATTERNS,
        HOBBIES,
        RARE_EVENTS,
    ]
    for region, cities in CITIES_BY_REGION.items():
        terms.add(region.lower())
        for city in cities:
            terms.add(city.lower())
    for mapping in dictionaries[1:]:
        for key, value in mapping.items():
            terms.add(key.lower())
            terms.add(value.lower())
    return sorted(terms, key=len, reverse=True)


SIGNATURE_PHRASES = signature_phrase_vocab()


def extract_signature_tokens(text: str) -> set[str]:
    lower = text.lower()
    tokens: set[str] = set()
    regexes = [
        r"\bperson_[a-z0-9]+\b",
        r"\bemail_[a-z0-9]+\b",
        r"\bphone_[a-z0-9]+\b",
        r"\baccount_[a-z0-9]+\b",
        r"\bcity_\d+\b",
        r"\borg_\d+\b",
        r"\bacct-\d+\b",
        r"\b[\w.%-]+@synthetic-example\.org\b",
        r"\(\d{3}\)\s*555-\d{4}\b",
    ]
    for pattern in regexes:
        for match in re.findall(pattern, lower):
            tokens.add(f"handle::{match}")
    for phrase in SIGNATURE_PHRASES:
        if phrase in lower:
            tokens.add(f"phrase::{phrase}")
    return tokens


def signature_similarity(docs: list[dict[str, Any]]) -> np.ndarray:
    signatures = [extract_signature_tokens(d["text"]) for d in docs]
    df = Counter(token for sig in signatures for token in sig)
    vocab = {token: i for i, token in enumerate(sorted(df))}
    if not vocab:
        return np.zeros((len(docs), len(docs)), dtype=float)
    rows = []
    cols = []
    data = []
    n = len(docs)
    for row, sig in enumerate(signatures):
        for token in sig:
            rows.append(row)
            cols.append(vocab[token])
            data.append(math.log((n + 1) / (df[token] + 1)) + 1.0)
    mat = sparse.csr_matrix((data, (rows, cols)), shape=(n, len(vocab)), dtype=float)
    norms = np.sqrt(mat.multiply(mat).sum(axis=1)).A1
    norms[norms == 0] = 1.0
    mat = mat.multiply(1.0 / norms[:, None])
    return (mat @ mat.T).toarray()


def pair_scores_for_ids(
    docs: list[dict[str, Any]], similarity: np.ndarray, ids: set[str]
) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]]]:
    idxs = [i for i, d in enumerate(docs) if d["persona_id"] in ids]
    y_true = []
    scores = []
    pairs = []
    for a_pos, b_pos in combinations(idxs, 2):
        label = int(docs[a_pos]["persona_id"] == docs[b_pos]["persona_id"])
        sim = similarity[a_pos, b_pos]
        y_true.append(label)
        scores.append(float(sim))
        pairs.append((a_pos, b_pos))
    return np.array(y_true), np.array(scores), pairs


def choose_threshold(y_true: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    if len(scores) == 0:
        return 1.0, 0.0
    candidates = np.unique(np.quantile(scores, np.linspace(0.50, 0.995, 120)))
    best_threshold = float(candidates[0])
    best_f1 = -1.0
    for threshold in candidates:
        y_pred = (scores >= threshold).astype(int)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_threshold = float(threshold)
            best_f1 = float(f1)
    return best_threshold, best_f1


def cluster_metrics(
    docs: list[dict[str, Any]], similarity: np.ndarray, ids: set[str], threshold: float
) -> dict[str, float]:
    idxs = [i for i, d in enumerate(docs) if d["persona_id"] in ids]
    graph = nx.Graph()
    graph.add_nodes_from(idxs)
    for a_pos, b_pos in combinations(idxs, 2):
        sim = float(similarity[a_pos, b_pos])
        if sim >= threshold:
            graph.add_edge(a_pos, b_pos)
    comp_id = {}
    for c_idx, comp in enumerate(nx.connected_components(graph)):
        for node in comp:
            comp_id[node] = c_idx
    y_true = [docs[i]["persona_id"] for i in idxs]
    y_pred = [comp_id[i] for i in idxs]
    b3 = bcubed_f1(y_true, y_pred)
    fixed = fixed_k_cluster_metrics(docs, similarity, idxs)
    return {
        "cluster_ari": float(adjusted_rand_score(y_true, y_pred)),
        "cluster_nmi": float(normalized_mutual_info_score(y_true, y_pred)),
        "bcubed_precision": b3["precision"],
        "bcubed_recall": b3["recall"],
        "bcubed_f1": b3["f1"],
        "num_pred_clusters": float(len(set(y_pred))),
        **fixed,
    }


def fixed_k_cluster_metrics(
    docs: list[dict[str, Any]], similarity: np.ndarray, idxs: list[int]
) -> dict[str, float]:
    y_true = [docs[i]["persona_id"] for i in idxs]
    n_clusters = len(set(y_true))
    if n_clusters <= 1:
        return {"fixedk_ari": 0.0, "fixedk_nmi": 0.0, "fixedk_bcubed_f1": 0.0}
    sub_sim = similarity[np.ix_(idxs, idxs)]
    distance = np.clip(1.0 - sub_sim, 0.0, 1.0)
    np.fill_diagonal(distance, 0.0)
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric="precomputed",
        linkage="average",
    )
    y_pred = clustering.fit_predict(distance)
    b3 = bcubed_f1(y_true, list(y_pred))
    return {
        "fixedk_ari": float(adjusted_rand_score(y_true, y_pred)),
        "fixedk_nmi": float(normalized_mutual_info_score(y_true, y_pred)),
        "fixedk_bcubed_f1": b3["f1"],
    }


def bcubed_f1(y_true: list[str], y_pred: list[int]) -> dict[str, float]:
    precisions = []
    recalls = []
    for i, (t_i, p_i) in enumerate(zip(y_true, y_pred)):
        pred_cluster = [j for j, p_j in enumerate(y_pred) if p_j == p_i]
        true_cluster = [j for j, t_j in enumerate(y_true) if t_j == t_i]
        intersect = len(set(pred_cluster) & set(true_cluster))
        precisions.append(intersect / len(pred_cluster))
        recalls.append(intersect / len(true_cluster))
    p = float(np.mean(precisions))
    r = float(np.mean(recalls))
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r > 0 else 0.0}


def pair_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float]:
    y_pred = (scores >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "pair_precision": float(precision),
        "pair_recall": float(recall),
        "pair_f1": float(f1),
    }


def aux_match_metrics(
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    ids: set[str],
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
        all_texts = ["\n".join(doc_texts)] + [aux_profile_text(persona_by_id[cid]) for cid in candidate_ids]
        vec = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.9,
            sublinear_tf=True,
            token_pattern=r"(?u)\b[\w\[\]_-]+\b",
        )
        mat = vec.fit_transform(all_texts)
        scores = (mat[0] @ mat[1:].T).toarray().ravel()
        ranked = [cid for _, cid in sorted(zip(scores, candidate_ids), reverse=True)]
        rank = ranked.index(pid) + 1
        reciprocal_ranks.append(1.0 / rank)
        top1 += int(rank == 1)
        top3 += int(rank <= 3)
        rows.append(
            {
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


def train_utility_classifiers(original_docs: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [d["text"] for d in original_docs]
    domains = [d["utility_labels"]["domain"] for d in original_docs]
    issues = [d["utility_labels"]["issue"] for d in original_docs]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
        max_df=0.8,
        min_df=1,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[\w\[\]_-]+\b",
    )
    x = vectorizer.fit_transform(texts)
    domain_clf = LogisticRegression(max_iter=2000, random_state=0)
    issue_clf = LogisticRegression(max_iter=2000, random_state=0)
    domain_clf.fit(x, domains)
    issue_clf.fit(x, issues)
    return {"vectorizer": vectorizer, "domain": domain_clf, "issue": issue_clf}


def utility_metrics(docs: list[dict[str, Any]], clf: dict[str, Any]) -> dict[str, float]:
    x = clf["vectorizer"].transform([d["text"] for d in docs])
    domain_true = [d["utility_labels"]["domain"] for d in docs]
    issue_true = [d["utility_labels"]["issue"] for d in docs]
    domain_pred = clf["domain"].predict(x)
    issue_pred = clf["issue"].predict(x)
    fact_scores = [fact_preservation(d) for d in docs]
    retrieval = retrieval_utility_metrics(docs)
    return {
        "domain_acc": float(accuracy_score(domain_true, domain_pred)),
        "issue_acc": float(accuracy_score(issue_true, issue_pred)),
        "fact_preservation": float(np.mean(fact_scores)),
        **retrieval,
    }


def retrieval_utility_metrics(docs: list[dict[str, Any]]) -> dict[str, float]:
    texts = [doc["text"] for doc in docs]
    labels = [
        (doc["utility_labels"]["domain"], doc["utility_labels"]["issue"])
        for doc in docs
    ]
    queries = [
        f"{domain.replace('_', ' ')} {ISSUE_PHRASES[issue]} support request"
        for domain, issue in labels
    ]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 3),
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
        first_rank = int(np.where(ranking == relevant[0])[0][0]) + 1
        reciprocal_ranks.append(1.0 / first_rank)
        top5 = set(ranking[:5])
        recall5.append(float(any(labels[j] == label for j in top5)))
    return {
        "retrieval_recall_at_5": float(np.mean(recall5)),
        "retrieval_mrr": float(np.mean(reciprocal_ranks)),
    }


def fact_preservation(doc: dict[str, Any]) -> float:
    text = doc["text"].lower()
    issue = ISSUE_PHRASES[doc["utility_labels"]["issue"]].lower()
    domain = doc["utility_labels"]["domain"].lower()
    checks = [
        issue in text,
        domain in text or domain.replace("_", " ") in text,
        any(word in text for word in ["support", "help", "request", "question"]),
    ]
    return sum(checks) / len(checks)


def phrase_in_text(text: str, phrase: str) -> bool:
    normalized = re.sub(r"\s+", " ", phrase.strip().lower())
    if not normalized:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized) + r"(?!\w)"
    return re.search(pattern, text) is not None


def attribute_leakage_metrics(
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    ids: set[str],
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    docs_by_persona: dict[str, list[str]] = defaultdict(list)
    for doc in docs:
        if doc["persona_id"] in ids:
            docs_by_persona[doc["persona_id"]].append(doc["text"])
    persona_by_id = {p["persona_id"]: p for p in personas}

    rows = []
    exact_hits = []
    coarse_hits = []
    for pid in sorted(docs_by_persona):
        persona = persona_by_id[pid]
        combined = re.sub(r"\s+", " ", "\n".join(docs_by_persona[pid]).lower())
        for field in ATTRIBUTE_FIELDS:
            exact_value = str(persona[field])
            coarse_value = field_generalization(persona, field)
            exact = phrase_in_text(combined, exact_value)
            coarse = exact or phrase_in_text(combined, coarse_value)
            exact_hits.append(float(exact))
            coarse_hits.append(float(coarse))
            rows.append(
                {
                    "persona_id": pid,
                    "risk_tier": persona["risk_tier"],
                    "field": field,
                    "exact_value": exact_value,
                    "coarse_value": coarse_value,
                    "exact_recovered": int(exact),
                    "coarse_recovered": int(coarse),
                }
            )
    return {
        "attr_exact_recovery": float(np.mean(exact_hits)) if exact_hits else 0.0,
        "attr_coarse_recovery": float(np.mean(coarse_hits)) if coarse_hits else 0.0,
    }, rows


def evaluate_condition(
    condition: str,
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    split: dict[str, set[str]],
    utility_clf: dict[str, Any],
    paths: Paths,
) -> tuple[dict[str, float], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    _, matrix = vectorize_docs(docs)
    text_similarity = (matrix @ matrix.T).toarray()
    sig_similarity = signature_similarity(docs)
    similarity = 0.9 * sig_similarity + 0.1 * text_similarity
    y_val, s_val, _ = pair_scores_for_ids(docs, similarity, split["val"])
    threshold, val_f1 = choose_threshold(y_val, s_val)
    y_test, s_test, _ = pair_scores_for_ids(docs, similarity, split["test"])
    p_metrics = pair_metrics(y_test, s_test, threshold)
    c_metrics = cluster_metrics(docs, similarity, split["test"], threshold)
    a_metrics, aux_rows = aux_match_metrics(docs, personas, candidates, split["test"])
    tier_rows = tier_metric_rows(condition, docs, personas, split, similarity, threshold, aux_rows)
    attr_metrics, attr_rows = attribute_leakage_metrics(docs, personas, split["test"])
    u_metrics = utility_metrics(docs, utility_clf)
    edit_path = paths.results / "edit_ratios.csv"
    edit_ratio = 0.0
    if edit_path.exists() and condition != "original":
        edits = pd.read_csv(edit_path)
        edit_ratio = float(edits[edits["condition"] == condition]["edit_ratio"].mean())
    row = {
        "condition": condition,
        "threshold": threshold,
        "val_pair_f1": val_f1,
        "edit_ratio": edit_ratio,
        **p_metrics,
        **c_metrics,
        **a_metrics,
        **attr_metrics,
        **u_metrics,
    }
    return row, aux_rows, tier_rows, attr_rows


def evaluate_all(cfg: dict[str, Any], paths: Paths) -> None:
    personas = read_jsonl(paths.data / "personas.jsonl")
    original_docs = read_jsonl(paths.data / "original_docs.jsonl")
    candidates = read_jsonl(paths.data / "candidate_sets.jsonl")
    split = split_personas(personas)
    utility_clf = train_utility_classifiers(original_docs)
    rows = []
    aux_all = []
    by_tier_rows = []
    attr_all = []
    for condition in cfg["conditions"]:
        docs = read_jsonl(paths.transformed / f"{condition}.jsonl")
        row, aux_rows, tier_rows, attr_rows = evaluate_condition(
            condition, docs, personas, candidates, split, utility_clf, paths
        )
        rows.append(row)
        for aux in aux_rows:
            aux["condition"] = condition
        for attr in attr_rows:
            attr["condition"] = condition
        aux_all.extend(aux_rows)
        attr_all.extend(attr_rows)
        by_tier_rows.extend(tier_rows)

    results = pd.DataFrame(rows)
    results.to_csv(paths.results / "main_results.csv", index=False)
    with (paths.results / "main_results.md").open("w", encoding="utf-8") as f:
        f.write(dataframe_to_markdown(results, floatfmt=".3f"))
        f.write("\n")
    pd.DataFrame(aux_all).to_csv(paths.results / "aux_match_rows.csv", index=False)
    pd.DataFrame(attr_all).to_csv(paths.results / "attribute_leakage_rows.csv", index=False)
    pd.DataFrame(by_tier_rows).to_csv(paths.results / "by_tier.csv", index=False)
    make_privacy_utility_plot(results, paths)
    run_ablation(paths, personas, candidates, split)
    write_qualitative_examples(paths)
    write_research_notes(results, paths)


def tier_metric_rows(
    condition: str,
    docs: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    split: dict[str, set[str]],
    similarity: np.ndarray,
    threshold: float,
    aux_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    by_tier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in aux_rows:
        by_tier[row["risk_tier"]].append(row)
    for tier, tier_aux in sorted(by_tier.items()):
        tier_ids = {p["persona_id"] for p in personas if p["risk_tier"] == tier} & split["test"]
        y_tier, s_tier, _ = pair_scores_for_ids(docs, similarity, tier_ids)
        pair = pair_metrics(y_tier, s_tier, threshold)
        idxs = [i for i, d in enumerate(docs) if d["persona_id"] in tier_ids]
        fixed = fixed_k_cluster_metrics(docs, similarity, idxs)
        attr, _ = attribute_leakage_metrics(docs, personas, tier_ids)
        rows.append(
            {
                "condition": condition,
                "risk_tier": tier,
                **pair,
                **fixed,
                **attr,
                "aux_top1": float(np.mean([r["top1"] for r in tier_aux])),
                "aux_top3": float(np.mean([r["top3"] for r in tier_aux])),
                "aux_mrr": float(np.mean([1.0 / r["rank"] for r in tier_aux])),
                "n_personas": len(tier_aux),
            }
        )
    return rows


def make_privacy_utility_plot(results: pd.DataFrame, paths: Paths) -> None:
    plt.figure(figsize=(7.5, 5.0))
    colors = {
        "original": "#333333",
        "c1_direct_redaction": "#1f77b4",
        "c1b_presidio_redaction": "#17becf",
        "c2_consistent_pseudonym": "#d62728",
        "c3_per_doc_pseudonym": "#9467bd",
        "c4_doc_local_anon": "#ff7f0e",
        "c5_linkguard": "#2ca02c",
        "c6_aggressive_redaction": "#7f7f7f",
    }
    labels = {
        "original": "C0 original",
        "c1_direct_redaction": "C1 direct redaction",
        "c1b_presidio_redaction": "C1b Presidio",
        "c2_consistent_pseudonym": "C2 consistent pseudonym",
        "c3_per_doc_pseudonym": "C3 per-doc pseudonym",
        "c4_doc_local_anon": "C4 doc-local anon",
        "c5_linkguard": "C5 LinkGuard",
        "c6_aggressive_redaction": "C6 aggressive redaction",
    }
    for _, row in results.iterrows():
        plt.scatter(
            row["aux_top1"],
            row["issue_acc"],
            s=70,
            color=colors.get(row["condition"], "#555555"),
            label=labels.get(row["condition"], row["condition"]),
        )
    plt.xlabel("Auxiliary matching top-1 accuracy (lower is better)")
    plt.ylabel("Issue classification accuracy (higher is better)")
    plt.title("Cross-document linkage privacy-utility frontier", fontsize=12, pad=10)
    plt.xlim(-0.02, min(1.02, max(results["aux_top1"]) + 0.12))
    plt.ylim(max(0.0, min(results["issue_acc"]) - 0.08), 1.08)
    plt.grid(alpha=0.25)
    plt.legend(loc="lower right", fontsize=7, frameon=True)
    plt.tight_layout()
    plt.savefig(paths.results / "privacy_utility.png", dpi=220)
    plt.close()


def run_ablation(paths: Paths, personas: list[dict[str, Any]], candidates: list[dict[str, Any]], split: dict[str, set[str]]) -> None:
    base_docs = read_jsonl(paths.transformed / "c1_direct_redaction.jsonl")
    p_by_id = {p["persona_id"]: p for p in personas}
    categories = {
        "remove_location": ["city", "region"],
        "remove_occupation": ["occupation", "job_family", "employer_type"],
        "remove_family": ["family_structure"],
        "remove_medical": ["medical_context"],
        "remove_rare_event": ["rare_event"],
        "remove_schedule": ["schedule_pattern"],
    }
    rows = []
    for name, fields in categories.items():
        ablated = []
        for doc in base_docs:
            persona = p_by_id[doc["persona_id"]]
            replacements = []
            for field in fields:
                if field == "job_family":
                    replacements.append((persona["job_family"], "[ABLATE_ROLE]"))
                elif field == "region":
                    replacements.append((persona["region"], "[ABLATE_LOCATION]"))
                elif field == "employer_type":
                    replacements.append((persona["employer_type"], "[ABLATE_EMPLOYER]"))
                    replacements.append((EMPLOYER_TYPES[persona["employer_type"]], "[ABLATE_EMPLOYER]"))
                else:
                    replacements.append((persona[field], f"[ABLATE_{field.upper()}]"))
                    try:
                        replacements.append((field_generalization(persona, field), f"[ABLATE_{field.upper()}]"))
                    except KeyError:
                        pass
            ablated.append({**doc, "text": replace_many(doc["text"], replacements)})
        aux, _ = aux_match_metrics(ablated, personas, candidates, split["test"])
        rows.append({"ablation": name, **aux})
    pd.DataFrame(rows).to_csv(paths.results / "ablation.csv", index=False)


def write_qualitative_examples(paths: Paths) -> None:
    personas = read_jsonl(paths.data / "personas.jsonl")
    chosen = next(p for p in personas if p["risk_tier"] == "T3")
    doc_id = f"{chosen['persona_id']}_D01"
    conditions = [
        ("original", "C0 original"),
        ("c1_direct_redaction", "C1 direct redaction"),
        ("c1b_presidio_redaction", "C1b Presidio redaction"),
        ("c4_doc_local_anon", "C4 document-local anonymization proxy"),
        ("c5_linkguard", "C5 LinkGuard"),
        ("c6_aggressive_redaction", "C6 aggressive redaction"),
    ]
    lines = [
        "# Qualitative Example",
        "",
        f"Synthetic persona: `{chosen['persona_id']}` ({chosen['risk_tier']}).",
        f"Document: `{doc_id}`.",
        "",
        "This example is synthetic and is intended for defensive privacy evaluation only.",
        "",
    ]
    for condition, label in conditions:
        rows = read_jsonl(paths.transformed / f"{condition}.jsonl")
        doc = next(row for row in rows if row["doc_id"] == doc_id)
        lines.extend([f"## {label}", "", "```text", doc["text"], "```", ""])
    (paths.results / "qualitative_examples.md").write_text("\n".join(lines), encoding="utf-8")


def write_research_notes(results: pd.DataFrame, paths: Paths) -> None:
    by_condition = {row["condition"]: row for _, row in results.iterrows()}
    linkguard = by_condition.get("c5_linkguard")
    doc_local = by_condition.get("c4_doc_local_anon")
    direct = by_condition.get("c1_direct_redaction")
    presidio = by_condition.get("c1b_presidio_redaction")
    aggressive = by_condition.get("c6_aggressive_redaction")
    consistent = by_condition.get("c2_consistent_pseudonym")
    lines = [
        "# Sprint Research Notes",
        "",
        "These notes summarize the deterministic no-API local benchmark. "
        "Cached GPT-5.5 stress-audit results and API provenance are tracked separately in "
        "`results/paper_ready_summary.md`, `REPRODUCE_RESULTS.md`, and the run-specific OpenAI audit artifacts.",
        "",
        "## Main Observations",
        "",
    ]
    if direct is not None:
        lines.append(
            f"- Direct redaction leaves auxiliary matching top-1 at {direct['aux_top1']:.3f} "
            f"and pairwise linkage F1 at {direct['pair_f1']:.3f}, so span-level PII removal is not enough in this generated setting."
        )
    if presidio is not None:
        lines.append(
            f"- Presidio-style direct PII detection leaves auxiliary matching top-1 at {presidio['aux_top1']:.3f}; "
            "off-the-shelf document PII removal does not address cross-document quasi-identifiers."
        )
    if consistent is not None:
        lines.append(
            f"- Consistent pseudonyms produce pairwise linkage F1 {consistent['pair_f1']:.3f}; stable handles are visibly risky."
        )
    if linkguard is not None and doc_local is not None:
        lines.append(
            f"- LinkGuard changes auxiliary top-1 from {doc_local['aux_top1']:.3f} under local anonymization "
            f"to {linkguard['aux_top1']:.3f}, with issue accuracy {linkguard['issue_acc']:.3f}."
        )
    if aggressive is not None:
        lines.append(
            f"- Aggressive redaction gives auxiliary top-1 {aggressive['aux_top1']:.3f} but issue accuracy {aggressive['issue_acc']:.3f}, "
            "which anchors the utility-loss side of the frontier."
        )
    lines.extend(
        [
            "",
            "## Next Experiments",
            "",
            "1. Keep the validated claim surface stable unless a new result passes the claim verifier.",
            "2. Run the remaining GPT-5.5 RAG-generation calls only after explicit approval, then promote them only if parse success and claim checks pass.",
            "3. If time allows after submission, expand the synthetic style stress test to more domains while keeping the no-real-data ethics boundary.",
            "4. Re-run the no-API reproduction dry-run, submission package build, supplement generation, and claim verifier before final upload.",
        ]
    )
    (paths.results / "research_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_all(cfg: dict[str, Any], paths: Paths) -> None:
    personas = generate_personas(cfg, paths)
    docs = render_documents(cfg, paths, personas)
    make_aux_profiles(cfg, paths, personas)
    transform_docs(cfg, paths, personas, docs)


def validate_outputs(cfg: dict[str, Any], paths: Paths) -> None:
    personas = read_jsonl(paths.data / "personas.jsonl")
    docs = read_jsonl(paths.data / "original_docs.jsonl")
    expected_docs = int(cfg["num_personas"]) * int(cfg["docs_per_persona"])
    assert len(personas) == int(cfg["num_personas"]), len(personas)
    assert len(docs) == expected_docs, len(docs)
    counts = Counter(d["persona_id"] for d in docs)
    assert set(counts.values()) == {int(cfg["docs_per_persona"])}, counts.most_common(3)
    for condition in cfg["conditions"]:
        path = paths.transformed / f"{condition}.jsonl"
        assert path.exists(), path
        assert len(read_jsonl(path)) == expected_docs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument(
        "command",
        choices=["generate", "transform", "evaluate", "all", "validate"],
        help="Pipeline stage to run.",
    )
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)

    if args.command == "generate":
        generate_all(cfg, paths)
        validate_outputs(cfg, paths)
    elif args.command == "transform":
        personas = read_jsonl(paths.data / "personas.jsonl")
        docs = read_jsonl(paths.data / "original_docs.jsonl")
        transform_docs(cfg, paths, personas, docs)
        validate_outputs(cfg, paths)
    elif args.command == "evaluate":
        validate_outputs(cfg, paths)
        evaluate_all(cfg, paths)
    elif args.command == "validate":
        validate_outputs(cfg, paths)
    elif args.command == "all":
        generate_all(cfg, paths)
        validate_outputs(cfg, paths)
        evaluate_all(cfg, paths)
    else:
        raise ValueError(args.command)


if __name__ == "__main__":
    main()
