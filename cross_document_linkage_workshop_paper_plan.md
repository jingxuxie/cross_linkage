# Concrete Paper Plan: Cross-Document Linkage Attacks on Pseudonymized Corpora

**Working title:** *Pseudonymized but Linkable: Cross-Document Re-identification Risks in LLM-Ready Sensitive Text Corpora*  
**Target venue:** Workshop on Responsibly Enabling Data for Foundation Models @ COLM 2026  
**Recommended submission type:** 4-page short paper if submitting near the June 28, 2026 AoE deadline; 8-page long paper if you have time to expand experiments.  
**Compute assumption:** no local LLMs; one consumer GPU available but not required; about $100 API budget; local CPU Python for data generation, baselines, clustering, and metrics.  
**Data stance:** synthetic-only benchmark; no real sensitive data; no real-person re-identification.

---

## 1. One-paragraph paper pitch

Sensitive corpora are often de-identified one document at a time before being used for RAG, fine-tuning, or data sharing. However, document-local pseudonymization may leave enough repeated quasi-identifiers—occupation, region, family structure, dates, institutional context, rare life events, writing style, and domain-specific details—to link multiple records belonging to the same person. This paper introduces a synthetic cross-document linkage benchmark and shows that common document-local transformations reduce obvious PII while still allowing an LLM-assisted attacker to cluster records, reconstruct profiles, and match pseudonymous clusters to auxiliary profiles. The paper then proposes a simple corpus-aware defense, **LinkGuard**, that generalizes high-linkage quasi-identifiers across a whole corpus while preserving task-relevant utility better than blanket redaction.

**Reviewer-facing claim:** responsible data transformation for foundation-model corpora must be **corpus-aware**, not only document-local.

---

## 2. Why this is a strong workshop paper

The workshop explicitly lists data transformation, de-identification, anonymization, pseudonymization, privacy attack benchmarks, and utility–privacy tradeoffs as topics of interest. It also invites 4-page short papers for preliminary studies or negative results, which makes a carefully scoped benchmark-and-audit paper realistic even with limited compute.[^workshop]

The idea is timely because recent work already shows three relevant facts:

1. **PII removal is not enough.** RAT-Bench argues that text anonymization should be evaluated by residual re-identification risk, including direct and indirect identifiers, not only by span-level recall.[^ratbench]
2. **LLMs can infer private attributes.** Beyond Memorization showed that LLMs can infer personal attributes such as location, income, and sex from text, with high top-k accuracy in their setting.[^beyondmem]
3. **RAG systems raise corpus-level leakage issues.** Recent RAG privacy work emphasizes dataset leakage and mitigation placement in RAG pipelines.[^ragsok][^guardrag]

Your paper’s differentiator is **cross-document linkage**. Most text anonymization benchmarks evaluate whether one anonymized document still reveals one person. Real corpora for RAG, support systems, patient portals, legal files, HR records, and financial systems often contain many documents per person. Your paper asks whether pseudonymized documents remain linkable across the corpus.

---

## 3. Main contribution package

Aim for four concrete contributions:

1. **A synthetic cross-document benchmark** for privacy evaluation of de-identified text corpora.  
   Working name: **CrossDoc-PrivacyBench** or **LinkBench-Text**.

2. **A reproducible LLM-assisted linkage attack protocol** with three tasks:
   - document clustering,
   - profile reconstruction,
   - auxiliary-profile matching.

3. **An audit of common document-local transformations**, including redaction, consistent pseudonymization, per-document pseudonymization, and LLM-based document-local anonymization.

4. **A simple corpus-aware defense**, LinkGuard, which generalizes high-linkage quasi-identifiers and reports a privacy–utility frontier.

This is enough for a strong workshop paper without training any models.

---

## 4. Core research questions and hypotheses

### RQ1: Are pseudonymized corpora still linkable across documents?

**Hypothesis:** Yes. Even if names, emails, phone numbers, addresses, and IDs are removed, repeated quasi-identifiers allow both local algorithms and LLM attackers to cluster documents belonging to the same synthetic person.

### RQ2: Does consistent pseudonymization make the problem worse?

**Hypothesis:** Consistent pseudonyms preserve longitudinal utility, but they create stable handles that make cross-document linkage nearly trivial. Per-document pseudonyms reduce direct handles but do not eliminate linkage from quasi-identifiers.

### RQ3: Which quasi-identifiers drive linkage?

**Hypothesis:** Rare combinations matter more than individual attributes. Examples: `mid-40s + rural Idaho + neonatal nurse + twins + rare autoimmune condition`, or `patent attorney + German language school + Saturday dialysis + robotics startup`.

### RQ4: Can corpus-aware generalization reduce linkage while preserving utility?

**Hypothesis:** A corpus-aware method that generalizes only high-linkage quasi-identifiers preserves more utility than full redaction and provides better privacy than document-local pseudonymization.

---

## 5. Threat model

### Data holder

A data holder wants to make a sensitive multi-document text corpus usable for foundation-model workflows such as RAG, evaluation, fine-tuning, or internal analytics. They apply de-identification before release or indexing.

### Attacker

The attacker has access to the transformed corpus. They may also have access to a synthetic auxiliary profile database, meant to simulate public or internal background knowledge. In this benchmark, the auxiliary profiles are fully synthetic and generated by the experimenter.

### Attacker goals

The attacker tries to:

1. **Cluster documents** that belong to the same synthetic person.
2. **Reconstruct a structured profile** from a cluster of anonymized documents.
3. **Match the cluster** to one profile in a candidate set of synthetic auxiliary profiles.
4. **Infer sensitive attributes**, such as city, occupation, institution type, condition category, family structure, or financial/legal context.

### Ethical boundary

Do **not** use real people, real public profiles, real social-media posts, real patient records, real legal client documents, or web-search agents. The attack is a controlled benchmark over synthetic personas only.

---

## 6. Minimal viable experiment design

### Sprint version for a short workshop paper

Use this if you need results very quickly.

| Component | Sprint setting |
|---|---:|
| Personas | 120 synthetic personas |
| Documents per persona | 4 |
| Total documents | 480 |
| Domains | 4: healthcare portal, legal intake, financial support, workplace/HR |
| Transformation conditions | 5 |
| Attack tasks | clustering + auxiliary matching + attribute inference |
| Utility tasks | domain classification + key-fact preservation |
| API models | cheap model for extraction/transformation; stronger model for final attacker on a subset |
| Manual audit | 40 personas / 160 documents |
| Main paper type | 4-page short paper |

### Full version for a stronger 8-page paper

| Component | Full setting |
|---|---:|
| Personas | 300–500 synthetic personas |
| Documents per persona | 4–6 |
| Total documents | 1,200–3,000 |
| Domains | 6: healthcare, legal, financial, HR, education, customer support |
| Transformation conditions | 6–8 |
| Attack tasks | clustering + auxiliary matching + attribute inference + RAG query leakage |
| Utility tasks | classification + QA + retrieval + fact preservation |
| API models | cheap model for most calls; stronger model for attack audit and adjudication |
| Manual audit | 80–100 personas |
| Main paper type | 8-page long paper |

---

## 7. Synthetic corpus design

### 7.1 Persona schema

Each persona should have stable attributes, quasi-identifiers, and utility labels.

```json
{
  "persona_id": "P00073",
  "synthetic_name": "Mira Calder",
  "age_band": "40-49",
  "gender_marker": "woman",
  "region": "Pacific Northwest",
  "city": "Boise",
  "occupation": "neonatal nurse",
  "employer_type": "regional hospital",
  "education": "community college nursing program",
  "family_structure": "parent of twins",
  "medical_context": "autoimmune condition",
  "financial_context": "mortgage hardship",
  "legal_context": "workplace accommodation dispute",
  "schedule_pattern": "night shifts",
  "hobby_or_affiliation": "local ceramics co-op",
  "rare_event": "testified at a county hearing about hospital staffing",
  "sensitive_attributes_to_score": [
    "city",
    "occupation",
    "family_structure",
    "medical_context",
    "legal_context"
  ],
  "utility_labels": {
    "healthcare_issue": "medication refill",
    "legal_issue": "employment accommodation",
    "financial_issue": "payment deferral",
    "hr_issue": "schedule adjustment"
  }
}
```

Use randomly generated names only as synthetic placeholders. Do not claim that they are fictional famous people; they are just synthetic row identifiers.

### 7.2 Document types

Generate 4–6 documents per persona. Each document should reveal a different slice of the same underlying profile.

Recommended sprint set:

1. **Healthcare portal message**  
   Example utility label: appointment request, refill, symptom follow-up, insurance issue.

2. **Legal intake note**  
   Example utility label: employment, housing, consumer dispute, immigration-style administrative issue. Keep it generic and synthetic.

3. **Financial support ticket**  
   Example utility label: payment extension, fraud inquiry, account correction, hardship request.

4. **Workplace/HR note**  
   Example utility label: leave request, accommodation, schedule change, benefits question.

Optional expansion:

5. **Education/advising message**
6. **Customer support ticket**

### 7.3 Risk tiers

Create three risk tiers. This makes the results interpretable.

| Tier | Description | Example |
|---|---|---|
| T1: direct PII only | Direct identifiers appear, but quasi-identifiers are generic | name, email, phone number |
| T2: moderate quasi-identifiers | Several common indirect attributes appear | job type + region + age band |
| T3: high-linkage combinations | Rare or highly specific combinations across documents | rare job + city + family event + schedule + institution |

Each persona should be assigned a risk tier. Ensure that T3 personas have realistic decoys so the attack is not artificially easy.

### 7.4 Decoy persona design

For every target persona, generate 3–9 decoy profiles that share some attributes but differ in others. This makes auxiliary matching meaningful.

Example decoy logic:

- Same region, different city.
- Same occupation, different family structure.
- Same medical context, different occupation.
- Same schedule pattern, different employer type.
- Same legal context, different age band.

---

## 8. Corpus generation workflow

### Step 1: Generate structured personas locally

Use Python with deterministic seeds.

Recommended libraries:

```text
faker
pandas
numpy
pydantic
scikit-learn
tqdm
```

### Step 2: Render templated documents locally

Use templates first, not LLMs. This keeps the ground truth controlled.

Example template fragment:

```text
Subject: Question about schedule and medication refill

Hi, I am trying to schedule a follow-up before my next week of night shifts.
The refill I discussed after the county hearing is almost out, and my twins'
school pickup schedule makes mornings difficult. I can come in after 3pm.
```

This document has no direct name, but it contains linkable context: night shifts, county hearing, twins, medication refill.

### Step 3: Optional API paraphrasing

Use a cheap model to paraphrase templated documents so they look less synthetic. The prompt must preserve the structured facts exactly.

```text
You are rewriting a synthetic benchmark document. Do not add new facts.
Do not remove any bracketed facts. Preserve the domain, issue type, and all factual details.
Make the text natural, concise, and realistic. Output only the rewritten document.

DOCUMENT:
{templated_document}
```

### Step 4: Validate generated documents

Run local checks:

- Does each doc contain its required utility label signal?
- Does each doc contain the intended quasi-identifiers?
- Does the corpus have the expected number of docs per persona?
- Are direct identifiers present only in the original condition?
- Are there enough decoys per persona?

### Step 5: Save everything in JSONL

Use separate files:

```text
data/personas.jsonl
data/original_docs.jsonl
data/auxiliary_profiles.jsonl
data/transformed/{condition}.jsonl
```

Recommended document record:

```json
{
  "doc_id": "P00073_D03",
  "persona_id": "P00073",
  "domain": "financial_support",
  "risk_tier": "T3",
  "text": "...",
  "intended_quasi_ids": ["night shifts", "twins", "county hearing", "Boise"],
  "utility_labels": {
    "domain": "financial_support",
    "issue": "payment_deferral"
  }
}
```

---

## 9. Transformation conditions

Use at least five conditions. These become your main table columns.

### C0: Original synthetic documents

This is the upper-bound reference and is not counted as anonymized.

### C1: Direct redaction

Remove direct PII spans only.

Examples:

```text
Mira Calder -> [NAME]
mira.calder@example.com -> [EMAIL]
(208) 555-0194 -> [PHONE]
1124 Grove Street -> [ADDRESS]
```

Implementation:

- local regex for email, phone, street-like addresses;
- optional Microsoft Presidio for names, dates, locations, phones, emails, and IDs.

Presidio is a good baseline because it is a widely used open-source de-identification SDK with analyzer and anonymizer modules for private entities in text.[^presidio]

### C2: Consistent pseudonymization

Replace direct identifiers with stable pseudonyms across the whole corpus.

```text
Mira Calder -> PERSON_073
Boise -> CITY_012
regional hospital -> ORG_044
```

This tests whether stable pseudonyms preserve linkability.

### C3: Per-document pseudonymization

Replace direct identifiers independently per document.

```text
P00073_D01: Mira Calder -> PERSON_A
P00073_D02: Mira Calder -> PERSON_Q
P00073_D03: Mira Calder -> PERSON_K
```

This removes the stable pseudonym handle but leaves quasi-identifiers.

### C4: Document-local LLM anonymization

Ask an API model to anonymize one document at a time. Do not provide neighboring documents.

Prompt:

```text
You are anonymizing a synthetic benchmark document. Remove or generalize direct personal identifiers.
Also remove obvious PII such as names, emails, phone numbers, exact street addresses, account numbers, and exact dates.
Do not invent new events. Preserve task-relevant content for classification and support triage.
Output only the anonymized document.

DOCUMENT:
{document}
```

This is an important baseline because many real workflows treat documents independently.

### C5: LinkGuard, the proposed corpus-aware generalization method

LinkGuard has access to the whole corpus and, ideally, the data holder’s internal grouping metadata. This is realistic for many organizations: they often know which records belong to the same patient, customer, employee, or case even after transformation.

LinkGuard extracts quasi-identifiers, estimates linkage risk, and rewrites high-risk combinations using semantic generalization ladders.

### C6: Full aggressive redaction

Remove nearly all attributes that could be identifying.

This is a privacy upper bound and utility lower bound.

---

## 10. Proposed method: LinkGuard

### 10.1 Intuition

Document-local anonymizers answer: “Is this span PII in this document?”  
LinkGuard answers: “Does this detail, repeated across the corpus, make a person linkable?”

### 10.2 Algorithm overview

```text
Input: multi-document corpus D, optional person/case grouping G, utility labels U
Output: transformed corpus D'

1. Extract candidate quasi-identifiers from every document.
2. Normalize extracted values into attribute types.
3. Estimate linkage risk for each attribute and attribute combination.
4. Select high-risk attributes to generalize or suppress.
5. Rewrite documents with constrained edits.
6. Verify that direct PII is removed and task utility is preserved.
```

### 10.3 Candidate quasi-identifier types

Use a fixed taxonomy so your experiments are reproducible.

| Type | Examples | Generalization ladder |
|---|---|---|
| age | 43, born in 1982 | exact age → age band → adult/senior |
| date | March 12, 2024 | exact date → month/year → year → relative period |
| location | Boise, Ada County | city → county/state → region → country |
| occupation | neonatal nurse | specific role → job family → sector |
| employer/institution | St. Luke's hospital | org → org type → industry |
| education | Boise State nursing program | school → institution type → region |
| family | twins, spouse deployed | specific relation/event → family obligation |
| medical | lupus, dialysis | diagnosis → condition category → health issue |
| financial | mortgage hardship | specific product/event → financial issue category |
| legal | county hearing, EEOC complaint | exact proceeding → legal issue category |
| schedule | night shift, Saturdays | exact schedule → time window → availability constraint |
| hobby/affiliation | ceramics co-op | specific group → hobby category |

### 10.4 Risk score

A simple heuristic is enough for a workshop paper if it is transparent and ablated.

For each persona cluster `g` and candidate attribute `a = (type, value)`:

```text
risk(a, g) = rarity(a) + stability(a, g) + specificity(a) + cross_domain_presence(a, g)
```

Where:

```text
rarity(a) = -log((count_personas_with_a + alpha) / (num_personas + alpha * V_type))
stability(a, g) = number of documents in g where a appears / number of documents in g
specificity(a) = manually assigned type prior from 0 to 2
cross_domain_presence(a, g) = number of distinct domains in g where a appears / number of domains
```

Start with these priors:

| Attribute type | Specificity prior |
|---|---:|
| exact date | 2.0 |
| city/small location | 2.0 |
| rare occupation | 2.0 |
| institution/employer | 2.0 |
| family event | 1.5 |
| medical condition | 1.5 |
| legal proceeding | 1.5 |
| schedule pattern | 1.0 |
| broad region | 0.5 |
| broad domain label | 0.2 |

A high-risk combination can be approximated as:

```text
combo_risk(g) = sum(top_m risk(a, g))
```

Set `m = 5` for the sprint paper.

### 10.5 Generalization rule

Generalize the minimum set of attributes until the estimated group uniqueness is reduced.

Pseudo-rule:

```text
For each persona group g:
    Extract attributes A_g.
    While estimated_k(A_g) < target_k:
        Choose attribute a with highest risk(a, g) / utility_cost(a).
        Replace a with its next coarser generalization.
        Recompute A_g and estimated_k(A_g).
```

For the sprint paper, set `target_k = 5` and estimate `k` inside your synthetic corpus:

```text
estimated_k(A_g) = number of personas whose generalized attribute set matches A_g on selected fields
```

This borrows the spirit of k-anonymity—generalization and suppression to make released records less distinguishable—without claiming a formal privacy guarantee.[^kanon]

### 10.6 Utility cost

Assign lower utility cost to details that are rarely needed for downstream tasks.

| Attribute | Example utility cost |
|---|---:|
| exact name | 0.0 |
| exact phone/email/address | 0.0 |
| exact date | 0.2 |
| exact city | 0.3 |
| employer name | 0.4 |
| rare hobby | 0.4 |
| broad medical category | 0.8 |
| legal issue category | 0.8 |
| support issue type | 1.0 |

This makes the method preserve task-relevant information.

### 10.7 Rewrite prompt

Use this as a constrained editing prompt.

```text
You are editing a synthetic benchmark document for privacy research.
Apply only the requested replacements. Do not add new facts. Do not change the domain or issue type.
Preserve information needed for the utility labels.

REPLACEMENTS:
{replacement_table}

DOCUMENT:
{document}

Return JSON with:
{
  "rewritten_text": "...",
  "changes_made": [
    {"original": "...", "replacement": "...", "reason": "..."}
  ],
  "utility_risk_notes": "..."
}
```

Example replacements:

```json
[
  {"original": "Boise", "replacement": "a city in the western United States"},
  {"original": "neonatal nurse", "replacement": "healthcare worker"},
  {"original": "twins' school pickup", "replacement": "childcare responsibilities"},
  {"original": "county hearing about hospital staffing", "replacement": "a local civic meeting"}
]
```

---

## 11. Attacks

Use three attacks. They are all benchmark attacks over synthetic data.

### Attack A: document clustering

**Goal:** group documents belonging to the same synthetic persona.

Pipeline:

1. Extract a structured profile signature from each anonymized document.
2. Generate candidate pairs using local lexical similarity or embedding similarity.
3. Score candidate pairs with an LLM or deterministic similarity function.
4. Cluster documents using thresholded graph components or agglomerative clustering.
5. Compare clusters against ground-truth `persona_id`.

#### A1. Attribute extraction prompt

```text
You are extracting non-identifying and quasi-identifying attributes from a synthetic anonymization benchmark document.
Do not identify real people. The text is synthetic.
Return only JSON.

Extract any evidence for these fields:
- age_band
- location
- occupation_or_role
- employer_or_institution_type
- family_structure
- medical_context
- financial_context
- legal_context
- education_context
- schedule_pattern
- hobby_or_affiliation
- rare_event
- domain
- issue_type

For each field, include:
- value: string or null
- confidence: low/medium/high
- evidence: short quote or paraphrase

DOCUMENT:
{document}
```

#### A2. Pairwise match prompt

Use only after local blocking has selected candidate pairs. Avoid all-pairs LLM scoring.

```text
You are evaluating whether two synthetic benchmark documents likely refer to the same synthetic person.
Do not identify real people. Use only the provided text.
Return only JSON.

DOC_A:
{doc_a}

DOC_B:
{doc_b}

Return:
{
  "same_person_probability": 0.0,
  "decision": "same" | "different" | "uncertain",
  "shared_signals": ["..."],
  "conflicting_signals": ["..."],
  "rationale": "one sentence"
}
```

#### A3. Clustering method

Local method:

```text
- Create a graph with documents as nodes.
- Add an edge if pair score >= threshold.
- Connected components are predicted persona clusters.
```

Tune threshold on a small validation split, then report test results.

### Attack B: profile reconstruction

**Goal:** reconstruct a structured profile from all documents in a predicted or true cluster.

Prompt:

```text
You are reconstructing a synthetic profile from anonymized benchmark documents.
The documents are synthetic and do not describe real people.
Do not guess names, phone numbers, emails, or exact addresses.
Return only JSON.

DOCUMENTS:
{cluster_docs}

Return fields:
{
  "age_band": null,
  "region_or_city": null,
  "occupation_or_role": null,
  "employer_or_institution_type": null,
  "family_structure": null,
  "medical_context": null,
  "financial_context": null,
  "legal_context": null,
  "schedule_pattern": null,
  "hobby_or_affiliation": null,
  "rare_event": null,
  "confidence_by_field": {}
}
```

Score reconstructed fields against ground truth using exact, coarse, and semantic match rules.

### Attack C: auxiliary-profile matching

**Goal:** match a pseudonymous cluster to one profile among synthetic candidates.

Candidate set: one true auxiliary profile + 4, 9, or 19 decoys.

Prompt:

```text
You are matching anonymized synthetic benchmark documents to one of several synthetic auxiliary profiles.
No real people are involved. Use only the provided synthetic candidates.
Return only JSON.

ANONYMIZED DOCUMENTS:
{cluster_docs}

CANDIDATE PROFILES:
{candidate_profiles}

Return:
{
  "top_1_candidate_id": "...",
  "ranked_candidates": [
    {"candidate_id": "...", "score": 0.0, "matching_evidence": ["..."]}
  ],
  "uncertain": true | false,
  "most_important_signals": ["..."]
}
```

Metrics:

- top-1 accuracy,
- top-3 accuracy,
- mean reciprocal rank,
- calibration of uncertainty,
- accuracy by risk tier.

---

## 12. Utility evaluation

You need utility metrics because a privacy-only paper is less compelling for this workshop.

### Utility Task 1: domain and issue classification

Each document has a known domain and issue label.

Examples:

```text
healthcare: refill_request, appointment_scheduling, symptom_followup, insurance_question
legal: employment_dispute, housing_issue, benefits_appeal, consumer_complaint
financial: payment_deferral, fraud_inquiry, account_correction, hardship_request
HR: leave_request, accommodation_request, benefits_question, schedule_change
```

Measure whether labels remain recoverable after transformation.

Use a cheap LLM or a simple local classifier over TF-IDF features. The local classifier is useful because it avoids extra API cost.

### Utility Task 2: key-fact preservation

For each document, create a small list of utility-critical facts.

```json
{
  "doc_id": "P00073_D03",
  "key_facts": [
    "the user asks for payment deferral",
    "the cause is schedule-related hardship",
    "the user wants a temporary arrangement"
  ]
}
```

After transformation, ask a cheap model to answer yes/no for each fact.

Prompt:

```text
You are evaluating whether an anonymized synthetic document preserves task-relevant facts.
Return only JSON.

FACTS:
{facts}

ANONYMIZED DOCUMENT:
{document}

Return:
{
  "facts": [
    {"fact": "...", "preserved": true, "evidence": "..."}
  ],
  "overall_preservation": 0.0
}
```

### Utility Task 3: retrieval utility, optional

Index anonymized documents with local TF-IDF. Query for domain tasks.

Example query:

```text
Find documents about payment deferral due to temporary hardship.
```

Metrics:

- Recall@5,
- MRR,
- nDCG@10.

This is optional for the sprint paper but useful for an 8-page version.

---

## 13. Privacy metrics

### 13.1 Pairwise linkage F1

For document pairs:

```text
positive = same persona_id
negative = different persona_id
```

Report precision, recall, F1, and threshold.

### 13.2 Clustering quality

Recommended metrics:

- Adjusted Rand Index,
- normalized mutual information,
- B-cubed precision/recall/F1,
- cluster purity.

### 13.3 Auxiliary matching accuracy

Report:

- top-1 accuracy,
- top-3 accuracy,
- MRR,
- accuracy by candidate-set size,
- accuracy by risk tier.

### 13.4 Attribute inference

For each sensitive attribute field:

- exact match,
- coarse match,
- macro-F1 across values,
- abstention rate.

### 13.5 Privacy–utility frontier

Create a summary table:

| Condition | Pair F1 ↓ | Cluster ARI ↓ | Aux top-1 ↓ | Attr F1 ↓ | Utility acc ↑ | Fact preservation ↑ | Edit ratio ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| C1 direct redaction | | | | | | | |
| C2 consistent pseudonym | | | | | | | |
| C3 per-doc pseudonym | | | | | | | |
| C4 doc-local LLM | | | | | | | |
| C5 LinkGuard | | | | | | | |
| C6 aggressive redaction | | | | | | | |

The arrows matter: lower privacy attack scores are better, higher utility scores are better.

---

## 14. Statistical analysis

Use simple, reviewer-friendly statistics.

1. **Bootstrap confidence intervals**  
   Bootstrap over personas, not documents, because documents from the same persona are correlated.

2. **Paired tests**  
   Compare C5 LinkGuard vs C4 document-local LLM anonymization on the same personas.

3. **Risk-tier stratification**  
   Report results separately for T1, T2, and T3. This will make your story much sharper.

4. **Ablation analysis**  
   Remove one quasi-identifier category at a time:
   - no location,
   - no occupation,
   - no family details,
   - no temporal details,
   - no institution details,
   - no rare-event details.

5. **Sensitivity analysis**  
   Vary:
   - number of documents per persona,
   - candidate-set size,
   - target `k` in LinkGuard,
   - pair-score threshold.

---

## 15. Baselines

### Required baselines

1. **Regex direct redaction**  
   Emails, phone numbers, account numbers, exact dates, obvious addresses.

2. **Presidio direct redaction**  
   Use Presidio analyzer + anonymizer for standard PII categories.

3. **Consistent pseudonymization**  
   Stable pseudonyms across the corpus.

4. **Per-document pseudonymization**  
   Pseudonym mappings reset per document.

5. **Document-local LLM anonymization**  
   One document at a time, no corpus context.

6. **Aggressive redaction**  
   Privacy upper bound, utility lower bound.

### Optional baselines

1. **OpenAI Privacy Filter**  
   Optional only. It is an open-weight PII detection/redaction model that can run locally, but it is not necessary if you do not want local model setup.[^opf]

2. **LLM corpus-aware prompt without explicit risk score**  
   Give the LLM all documents for one persona and ask it to anonymize. This is a useful comparison against LinkGuard’s more explicit risk scoring.

---

## 16. API-light budget plan

Use three model roles rather than hard-coding one provider:

| Role | Use | Quality need | Cost need |
|---|---|---|---|
| Cheap generator | paraphrasing synthetic documents, extraction, utility judging | moderate | very low |
| Cheap transformer | document-local anonymization and LinkGuard rewrites | moderate | low |
| Strong attacker | final auxiliary matching and profile reconstruction audit | high | controlled subset only |

### OpenAI pricing snapshot

As of the checked pricing page, OpenAI lists standard short-context prices per 1M tokens for flagship models such as `gpt-5.4-nano` at $0.20 input / $1.25 output, `gpt-5.4-mini` at $0.75 input / $4.50 output, and `gpt-5.5` at $5.00 input / $30.00 output.[^openai_pricing]

### Conservative token budget for sprint experiment

Assume 480 documents, average 350 input tokens and 250 output tokens per transformation/judging call.

| Step | Calls | Model role | Approx tokens | Expected cost band |
|---|---:|---|---:|---:|
| Optional paraphrase | 480 | cheap generator | 0.17M in / 0.12M out | <$1 |
| C4 doc-local anonymization | 480 | cheap transformer | 0.20M in / 0.14M out | <$2 |
| LinkGuard extraction | 480 | cheap generator | 0.20M in / 0.10M out | <$1 |
| LinkGuard rewrite | 480 | cheap transformer | 0.25M in / 0.15M out | <$2 |
| Utility fact judging | 2,400 facts | cheap generator | 0.80M in / 0.20M out | <$3 |
| Pairwise LLM scoring after blocking | 2,000 pairs | cheap generator | 1.80M in / 0.20M out | <$4 |
| Strong auxiliary attack | 120 personas × 5 conditions | strong attacker subset | 1.80M in / 0.18M out | about $15–$20 using a high-end model |
| Reruns / debugging reserve | — | mixed | — | $20–$40 |

A realistic sprint should fit comfortably inside $100 if you cache API responses, avoid all-pairs LLM scoring, and use the strong attacker only for the final attack subset.

### API privacy caution

Use only synthetic data. OpenAI’s API data controls state that API data is not used to train or improve models by default unless the customer opts in, but abuse-monitoring logs may contain customer content and are retained for up to 30 days by default unless modified controls apply.[^openai_data] Synthetic data avoids unnecessary privacy risk.

---

## 17. Local implementation plan

### Repository structure

```text
crossdoc-linkage/
  README.md
  configs/
    sprint.yaml
    full.yaml
  data/
    personas.jsonl
    original_docs.jsonl
    auxiliary_profiles.jsonl
    transformed/
      c1_direct_redaction.jsonl
      c2_consistent_pseudonym.jsonl
      c3_per_doc_pseudonym.jsonl
      c4_doc_local_llm.jsonl
      c5_linkguard.jsonl
      c6_aggressive_redaction.jsonl
  prompts/
    paraphrase.md
    doc_local_anonymize.md
    extract_attributes.md
    pairwise_match.md
    profile_reconstruct.md
    auxiliary_match.md
    utility_fact_judge.md
    linkguard_rewrite.md
  src/
    generate_personas.py
    render_documents.py
    make_aux_profiles.py
    transform_regex.py
    transform_presidio.py
    transform_pseudonym.py
    transform_llm.py
    linkguard_extract.py
    linkguard_generalize.py
    linkguard_rewrite.py
    attack_extract.py
    attack_pairwise.py
    attack_cluster.py
    attack_aux_match.py
    eval_privacy.py
    eval_utility.py
    bootstrap_ci.py
    make_tables.py
    make_plots.py
  cache/
    api_responses/
  paper/
    figures/
    tables/
```

### Minimal dependencies

```text
python>=3.11
pandas
numpy
scikit-learn
scipy
pydantic
faker
networkx
tqdm
openai
presidio-analyzer
presidio-anonymizer
matplotlib
```

### Key engineering choices

1. **Cache every API response** by hashing prompt + input + model.
2. **Store structured JSON outputs** and validate with Pydantic.
3. **Use local candidate blocking** before LLM pair scoring.
4. **Use deterministic random seeds** for personas, templates, decoys, and splits.
5. **Log prompt versions** so results are reproducible.
6. **Separate validation and test personas** to avoid threshold overfitting.

---

## 18. Candidate blocking to avoid API blowup

All-pairs scoring for 480 documents is 114,960 pairs. Do not do that.

Use local blocking:

1. Extract lightweight local features:
   - domain,
   - issue label,
   - TF-IDF unigrams/bigrams,
   - normalized quasi-id tokens from cheap extraction.

2. For each document, keep only top `b` candidate neighbors.
   - Sprint: `b = 10`.
   - Full: `b = 20`.

3. Score only those pairs with LLM or deterministic similarity.

4. Add a small sample of random negative pairs for threshold calibration.

This lets you get strong attack results without expensive all-pairs inference.

---

## 19. Expected result patterns to look for

Do not invent results in the paper. But these are the patterns you should test for.

### Pattern 1: direct redaction removes visible PII but not linkage

Expected: C1 lowers direct identifier leakage but still has high clustering and auxiliary matching in T2/T3 personas.

### Pattern 2: consistent pseudonyms preserve utility but make linkage easier

Expected: C2 may be almost as linkable as original data because stable handles act like record IDs.

### Pattern 3: per-document pseudonymization is not enough

Expected: C3 reduces trivial links but high-risk combinations still link across domains.

### Pattern 4: document-local LLM anonymization misses corpus-level uniqueness

Expected: C4 removes many sensitive spans but leaves repeated details that only become risky when viewed across documents.

### Pattern 5: LinkGuard improves the privacy–utility frontier

Expected: C5 should reduce cluster ARI/top-1 matching more than C4 while preserving more utility than C6 aggressive redaction.

---

## 20. Tables and figures for the paper

### Figure 1: motivating example

A three-panel figure:

1. Four documents about the same synthetic person after direct redaction.
2. Highlighted quasi-identifiers that repeat across documents.
3. Attacker links them and matches to an auxiliary profile.

### Figure 2: attack pipeline

Corpus → transformation → attribute extraction → pair scoring → clustering → profile matching.

### Figure 3: privacy–utility frontier

X-axis: auxiliary matching top-1 accuracy, lower is better.  
Y-axis: utility accuracy or fact preservation, higher is better.  
Plot one point per transformation.

### Table 1: benchmark composition

Personas, documents, domains, risk tiers, quasi-identifier types.

### Table 2: main results

Privacy and utility metrics by transformation.

### Table 3: ablation

Remove one quasi-identifier family at a time and show attack degradation.

### Table 4: failure cases

Qualitative examples with synthetic snippets.

---

## 21. Reviewer-facing novelty matrix

| Prior area | What it usually evaluates | Your paper’s added angle |
|---|---|---|
| PII detection | Span recall/precision | Linkability after transformation |
| Text anonymization benchmarks | Single-document re-identification | Multi-document corpus linkage |
| RAG privacy | Leakage through retrieval/generation | Data transformation before corpus indexing |
| k-anonymity-style methods | Structured tables | Textual quasi-identifier generalization |
| LLM privacy inference | Attribute inference from text | Cluster-level inference across pseudonymized documents |

This matrix should appear in your introduction or related work section.

---

## 22. Paper outline

### Title

*Pseudonymized but Linkable: Cross-Document Re-identification Risks in LLM-Ready Sensitive Text Corpora*

### Abstract draft

> Sensitive text corpora are commonly transformed through document-level redaction or pseudonymization before use in retrieval-augmented generation, evaluation, or model adaptation. We show that such transformations can leave documents linkable across a corpus: repeated quasi-identifiers such as occupation, region, family structure, institutional context, schedule, and rare life events allow an LLM-assisted attacker to cluster documents and match pseudonymous clusters to auxiliary profiles. We introduce CrossDoc-PrivacyBench, a synthetic multi-document benchmark with controlled ground truth, decoy profiles, and privacy–utility labels. We evaluate common transformations including direct redaction, consistent pseudonymization, per-document pseudonymization, and document-local LLM anonymization. We then propose LinkGuard, a lightweight corpus-aware generalization method that identifies high-linkage quasi-identifiers and rewrites them to coarser semantic categories. Our study suggests that responsible data transformation for foundation-model corpora should be evaluated at the corpus level, not only at the span or single-document level.

### 1. Introduction

Key points:

- Sensitive data sources are valuable for foundation models but restricted.
- De-identification is often applied document by document.
- Multi-document corpora create linkage risk.
- Pseudonyms can preserve longitudinal utility while increasing linkability.
- Contributions: benchmark, attack protocol, audit, LinkGuard.

### 2. Related work

Cover:

- k-anonymity and classic linkage attacks,
- text anonymization benchmarks such as TAB and RAT-Bench,
- LLM inference privacy,
- RAG privacy and data-leakage risks,
- PII tools such as Presidio and optional Privacy Filter.

### 3. Threat model and benchmark

Define:

- synthetic-only data,
- attacker access,
- tasks,
- corpus schema,
- risk tiers,
- utility labels.

### 4. Transformations and LinkGuard

Describe baselines and your method.

### 5. Experiments

Describe:

- attacks,
- metrics,
- API budget,
- validation/test split,
- confidence intervals.

### 6. Results

Main findings. Use cautious language:

- “We find that…” only after experiments.
- “This suggests…” for interpretation.

### 7. Limitations and ethics

Mention:

- synthetic data may not capture every real-world distribution,
- no formal privacy guarantee,
- attacker prompts are simplified,
- no real-person re-identification,
- benchmark should be used for defensive auditing.

### 8. Conclusion

Close with the core claim:

> For LLM-ready sensitive corpora, privacy evaluation must move from document-local PII removal to corpus-level linkage resistance.

---

## 23. Concrete week-by-week execution plan

### Phase 1: benchmark skeleton

Deliverables:

- `personas.jsonl`,
- `original_docs.jsonl`,
- `auxiliary_profiles.jsonl`,
- risk tiers,
- utility labels,
- 20 manually inspected examples.

Acceptance criterion:

- Each persona has at least 4 documents.
- Each document has a domain and issue label.
- Each persona has 5–10 auxiliary candidates.
- T1/T2/T3 tiers are balanced.

### Phase 2: transformations

Deliverables:

- C1–C6 transformed datasets,
- transformation logs,
- edit ratio per condition.

Acceptance criterion:

- Direct identifiers are removed in all anonymized conditions.
- Pseudonymization conditions are deterministic and auditable.
- LinkGuard produces a replacement table for each high-risk persona.

### Phase 3: attacks

Deliverables:

- extracted attribute signatures,
- pairwise linkage predictions,
- predicted clusters,
- auxiliary matching predictions,
- attack metrics by condition and risk tier.

Acceptance criterion:

- All metrics are computed over held-out personas.
- API calls are cached.
- Results can be regenerated from scripts.

### Phase 4: utility evaluation

Deliverables:

- domain/issue classification results,
- fact preservation scores,
- optional retrieval scores.

Acceptance criterion:

- Utility metrics are reported side by side with privacy metrics.
- Aggressive redaction shows the expected utility cost.

### Phase 5: analysis and writing

Deliverables:

- main results table,
- privacy–utility plot,
- ablation table,
- 3 qualitative examples,
- 4-page or 8-page draft.

Acceptance criterion:

- Paper has one clear claim.
- Every claim is supported by a table, figure, or example.
- Limitations are explicit.

---

## 24. Short-paper version: what to cut

For a 4-page submission, keep only:

1. Motivation and threat model.
2. 120-persona synthetic benchmark.
3. Four transformations: direct redaction, consistent pseudonymization, document-local LLM anonymization, LinkGuard.
4. Two attacks: clustering and auxiliary matching.
5. One utility metric: issue classification or fact preservation.
6. One ablation: remove location/occupation/family/rare events.
7. One qualitative example.

Do **not** include optional RAG experiments in the short version unless they are already done.

---

## 25. Long-paper version: what to add

For an 8-page submission, add:

1. More personas and domains.
2. RAG retrieval leakage experiment.
3. Stronger attacker comparison:
   - local lexical attacker,
   - cheap LLM attacker,
   - strong LLM attacker.
4. Multi-document vs single-document comparison.
5. Human audit of 100 transformed examples.
6. More robust statistics and sensitivity analysis.
7. Release-ready benchmark documentation.

---

## 26. Example result claims that would be high-impact

Use only if your results support them.

### Strong claim A

> Document-local pseudonymization reduces direct PII exposure but leaves cross-document linkability largely intact for high-risk personas.

### Strong claim B

> Consistent pseudonyms can function as stable record identifiers, improving utility but making linkage attacks substantially easier.

### Strong claim C

> Document-local LLM anonymization misses quasi-identifiers that are harmless in isolation but identifying in combination across a corpus.

### Strong claim D

> A simple corpus-aware generalization policy can reduce auxiliary matching accuracy while preserving more task utility than aggressive redaction.

### Strong claim E

> Evaluating anonymization at the span level systematically underestimates privacy risk for LLM-ready multi-document corpora.

---

## 27. Risks and fallback plans

### Risk: synthetic data looks too artificial

Fallback:

- Add paraphrasing.
- Use multiple templates per domain.
- Include manual qualitative examples.
- Release the templates and state the limitation clearly.

### Risk: attacks are too easy

Fallback:

- Increase decoy similarity.
- Increase candidate set size.
- Reduce number of documents per persona.
- Add risk-tier stratification.

### Risk: attacks are too hard

Fallback:

- Start with T3 high-linkage personas.
- Increase documents per persona.
- Use true clusters for auxiliary matching to isolate matching risk from clustering error.

### Risk: LinkGuard reduces utility too much

Fallback:

- Show a privacy–utility tradeoff curve over different target `k` values.
- Position LinkGuard as a controllable risk-budgeting method rather than a universally optimal anonymizer.

### Risk: reviewers say this is “just synthetic”

Fallback:

- Emphasize controlled ground truth and ethical reproducibility.
- Add a small TAB-inspired legal slice if time permits.
- Discuss why real re-identification benchmarks are hard to release responsibly.

### Risk: reviewers ask why not use real auxiliary web data

Fallback:

- State that the paper intentionally avoids real-person linkage to prevent harm.
- The benchmark simulates auxiliary knowledge with synthetic decoys and controlled ground truth.

---

## 28. Ethics and responsible release statement

Suggested paper language:

> This work studies re-identification risk using synthetic personas only. We do not collect, process, or attempt to re-identify real people. Auxiliary profiles are generated from the same synthetic schema and are used solely to evaluate defensive anonymization methods. We will release generation scripts, prompts, synthetic data, and evaluation code, but not any tool or dataset intended to identify real individuals. The attack prompts are framed as benchmark tasks and should not be applied to real corpora without authorization and ethical review.

---

## 29. Reproducibility checklist

Include this in the appendix or repository.

- [ ] Fixed random seeds.
- [ ] Versioned prompt files.
- [ ] API responses cached with prompt/model hash.
- [ ] No real personal data.
- [ ] Synthetic corpus generation script released.
- [ ] Transformation scripts released.
- [ ] Evaluation scripts released.
- [ ] Config files for sprint and full runs.
- [ ] Tables generated from raw results.
- [ ] Human audit protocol included.
- [ ] Known limitations documented.

---

## 30. Recommended first implementation order

Build in this order:

1. `generate_personas.py`
2. `render_documents.py`
3. `make_aux_profiles.py`
4. `transform_regex.py`
5. `transform_pseudonym.py`
6. `transform_llm.py`
7. `linkguard_extract.py`
8. `linkguard_generalize.py`
9. `linkguard_rewrite.py`
10. `attack_extract.py`
11. `attack_cluster.py`
12. `attack_aux_match.py`
13. `eval_privacy.py`
14. `eval_utility.py`
15. `make_tables.py`
16. `make_plots.py`

Do not spend time on a polished UI. A clean CLI and cached JSONL outputs are enough for a workshop paper.

---

## 31. Minimal CLI design

```bash
python src/generate_personas.py --config configs/sprint.yaml
python src/render_documents.py --config configs/sprint.yaml
python src/make_aux_profiles.py --config configs/sprint.yaml

python src/transform_regex.py --condition c1_direct_redaction
python src/transform_pseudonym.py --condition c2_consistent_pseudonym
python src/transform_pseudonym.py --condition c3_per_doc_pseudonym
python src/transform_llm.py --condition c4_doc_local_llm --model cheap
python src/linkguard_extract.py --model cheap
python src/linkguard_generalize.py --target-k 5
python src/linkguard_rewrite.py --condition c5_linkguard --model cheap

python src/attack_extract.py --all-conditions --model cheap
python src/attack_cluster.py --all-conditions --blocking-neighbors 10
python src/attack_aux_match.py --all-conditions --model strong --candidate-set-size 10

python src/eval_privacy.py --all-conditions
python src/eval_utility.py --all-conditions
python src/make_tables.py
python src/make_plots.py
```

---

## 32. What to put in the abstract and introduction if results are preliminary

Use cautious workshop language:

- “We introduce a benchmark and protocol…”
- “We conduct an initial audit…”
- “Our preliminary results suggest…”
- “We identify a failure mode…”
- “We release code and synthetic data to support follow-up work…”

Avoid overclaiming:

- Do not say “solves anonymization.”
- Do not claim formal anonymity.
- Do not claim real-world rates from synthetic data.
- Do not claim legal compliance.

---

## 33. Final paper positioning

The most compelling positioning is:

> Existing anonymization tools often operate at the level of spans or individual documents. But foundation-model data workflows operate at corpus scale. In that setting, privacy failures can emerge from repeated weak signals rather than from one obvious identifier. Cross-document linkage should therefore become a standard part of privacy evaluation for transformed sensitive corpora.

That is a clean, high-impact workshop message.

---

## References and useful sources

[^workshop]: Workshop on Responsibly Enabling Data for Foundation Models @ COLM 2026. The page lists data transformation, anonymization, pseudonymization, privacy attack benchmarks, and utility–privacy tradeoffs as topics; it also lists short and long paper formats and key dates. https://re-data-colm2026.github.io/

[^ratbench]: N. Krčo, Z. Yao, M. Meeus, and Y.-A. de Montjoye. *RAT-Bench: A Comprehensive Benchmark for Text Anonymization*. arXiv, 2026. https://arxiv.org/html/2602.12806v1

[^beyondmem]: R. Staab, M. Vero, M. Balunović, and M. Vechev. *Beyond Memorization: Violating Privacy Via Inference with Large Language Models*. ICLR 2024 / arXiv 2023. https://arxiv.org/abs/2310.07298

[^ragsok]: A. Bodea, S. Meisenbacher, A. Klymenko, and F. Matthes. *SoK: Privacy Risks and Mitigations in Retrieval-Augmented Generation Systems*. arXiv, 2026. https://arxiv.org/html/2601.03979v1

[^guardrag]: A. Bodea, S. Meisenbacher, A. Klymenko, and F. Matthes. *A Case Study on the Impact of Anonymization Along the RAG Pipeline*. arXiv, 2026. https://arxiv.org/html/2604.15958v1

[^tab]: I. Pilán, P. Lison, L. Øvrelid, A. Papadopoulou, D. Sánchez, and M. Batet. *The Text Anonymization Benchmark (TAB): A Dedicated Corpus and Evaluation Framework for Text Anonymization*. Computational Linguistics, 2022. https://aclanthology.org/2022.cl-4.19/

[^kanon]: L. Sweeney. *Achieving k-anonymity privacy protection using generalization and suppression*. International Journal on Uncertainty, Fuzziness and Knowledge-Based Systems, 2002. Summary page: https://dataprivacylab.org/people/sweeney/kanonymity2.html

[^netflix]: A. Narayanan and V. Shmatikov. *Robust De-anonymization of Large Sparse Datasets*. IEEE Symposium on Security and Privacy, 2008. https://www.cs.cornell.edu/~shmat/shmat_oak08netflix.pdf

[^presidio]: Microsoft Presidio documentation. https://microsoft.github.io/presidio/

[^opf]: OpenAI. *Introducing OpenAI Privacy Filter*. https://openai.com/index/introducing-openai-privacy-filter/

[^openai_pricing]: OpenAI API pricing page, prices per 1M tokens. https://developers.openai.com/api/docs/pricing

[^openai_data]: OpenAI API data controls. https://developers.openai.com/api/docs/guides/your-data
