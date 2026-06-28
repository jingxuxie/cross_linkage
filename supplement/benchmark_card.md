# Benchmark Card

## Name

CrossDoc-PrivacyBench.

## Purpose

Evaluate whether document-level de-identification leaves synthetic multi-document corpora linkable through repeated quasi-identifiers.

## Data Stance

- Synthetic-only benchmark.
- No real people, public profiles, social-media posts, patient records, legal records, customer records, or web-searched records.
- Direct identifiers are generated placeholders used only to test transformations.
- Auxiliary profiles and decoys are generated from the same synthetic schema.

## Corpus

- Personas: 120.
- Documents: 480.
- Documents per persona: 4.
- Held-out personas for main evaluation: 96.
- Domains: healthcare, legal, financial, hr.
- Candidate set size: 10.
- LinkGuard target k: 5.

### Risk Tiers

| risk_tier | n_personas |
| --------- | ---------- |
| T1        | 40         |
| T2        | 40         |
| T3        | 40         |

### Domains

| domain     | n_documents |
| ---------- | ----------- |
| financial  | 120         |
| healthcare | 120         |
| hr         | 120         |
| legal      | 120         |

## Transformations

- C1 direct redaction: masks synthetic direct identifiers.
- C1b Presidio redaction: off-the-shelf PII detection plus direct synthetic ID masking.
- C2 consistent pseudonymization: stable per-person handles.
- C3 per-document pseudonymization: unstable document-local handles.
- C4 document-local proxy: local quasi-identifier generalization.
- C5 LinkGuard: corpus-aware quasi-identifier generalization.
- C6 aggressive redaction: broad direct and quasi-identifier suppression.

## Metrics

- Privacy: pairwise linkage F1, fixed-K clustering, auxiliary top-1/top-3/MRR, exact quasi-identifier recovery, profile-query RAG exposure.
- Utility: domain/issue classification, retrieval Recall@5, fact preservation, body-only utility stress score.
- Robustness: multi-seed sweep, candidate-pool sensitivity, attacker-family sensitivity, target-k sensitivity, noisy-style synthetic rerendering.

## Main Result Snapshot

| condition               | pair_f1 | aux_top1 | aux_top3 | attr_exact_recovery | issue_acc | retrieval_recall_at_5 | edit_ratio |
| ----------------------- | ------- | -------- | -------- | ------------------- | --------- | --------------------- | ---------- |
| original                | 0.963   | 0.708    | 0.844    | 0.395               | 1.000     | 1.000                 | 0.000      |
| c1_direct_redaction     | 0.214   | 0.708    | 0.844    | 0.395               | 1.000     | 1.000                 | 0.246      |
| c1b_presidio_redaction  | 0.142   | 0.594    | 0.802    | 0.332               | 1.000     | 1.000                 | 0.348      |
| c2_consistent_pseudonym | 0.979   | 0.427    | 0.677    | 0.273               | 1.000     | 1.000                 | 0.299      |
| c3_per_doc_pseudonym    | 0.148   | 0.427    | 0.677    | 0.273               | 1.000     | 1.000                 | 0.315      |
| c4_doc_local_anon       | 0.155   | 0.604    | 0.844    | 0.304               | 1.000     | 1.000                 | 0.288      |
| c5_linkguard            | 0.019   | 0.042    | 0.260    | 0.000               | 1.000     | 1.000                 | 0.535      |
| c6_aggressive_redaction | 0.016   | 0.052    | 0.312    | 0.000               | 0.350     | 0.312                 | 0.681      |

## Noisy-Style Stress Metadata

- Rerendered documents: 480.
- Mean template similarity: 0.306.
- Mean type-token ratio: 0.791.
- Unique first lines: 16.

## Intended Use

Defensive auditing, method comparison, and paper reproduction for corpus-level text privacy evaluation.

## Out-of-Scope Uses

Do not use this benchmark to make claims about real-person re-identification rates, deployment safety, legal compliance, or formal anonymity guarantees.

## Limitations

- Synthetic and schema-controlled.
- Noisy-style stress improves style variation but does not substitute for authorized real-data validation.
- LinkGuard is heuristic and has no formal privacy proof.
- Utility metrics are lightweight proxies rather than downstream product evaluations.
