# Paper-Ready Result Brief

## Validated Local Sprint Results

- Direct redaction leaves auxiliary matching top-1 at 0.708 while preserving issue utility at 1.000 and retrieval Recall@5 at 1.000.
- Presidio-style PII redaction leaves auxiliary matching top-1 at 0.594, showing that an off-the-shelf document PII baseline does not remove corpus-level quasi-identifier risk.
- Exact quasi-identifier recovery remains 0.395 after direct redaction and 0.332 after Presidio, but drops to 0.000 under LinkGuard.
- Consistent pseudonymization makes document linkage nearly trivial in this benchmark: pair F1 0.979 and fixed-K cluster ARI 1.000.
- The document-local anonymization proxy leaves auxiliary top-1 at 0.604.
- LinkGuard reduces auxiliary top-1 to 0.042 with issue accuracy 1.000 and retrieval Recall@5 1.000.
- Aggressive redaction lowers auxiliary top-1 to 0.052, but issue accuracy falls to 0.350 and retrieval Recall@5 to 0.312.

## Local Main Table

| condition               | pair_f1 | fixedk_ari | aux_top1 | aux_top3 | attr_exact_recovery | attr_coarse_recovery | issue_acc | retrieval_recall_at_5 | fact_preservation | edit_ratio |
| ----------------------- | ------- | ---------- | -------- | -------- | ------------------- | -------------------- | --------- | --------------------- | ----------------- | ---------- |
| C0 original             | 0.963   | 1.000      | 0.708    | 0.844    | 0.395               | 0.788                | 1.000     | 1.000                 | 0.682             | 0.000      |
| C1 direct redaction     | 0.214   | 0.113      | 0.708    | 0.844    | 0.395               | 0.788                | 1.000     | 1.000                 | 0.682             | 0.246      |
| C1b Presidio redaction  | 0.142   | 0.073      | 0.594    | 0.802    | 0.332               | 0.705                | 1.000     | 1.000                 | 0.682             | 0.348      |
| C2 consistent pseudonym | 0.979   | 1.000      | 0.427    | 0.677    | 0.273               | 0.696                | 1.000     | 1.000                 | 0.679             | 0.299      |
| C3 per-doc pseudonym    | 0.148   | 0.072      | 0.427    | 0.677    | 0.273               | 0.696                | 1.000     | 1.000                 | 0.679             | 0.315      |
| C4 doc-local proxy      | 0.155   | 0.089      | 0.604    | 0.844    | 0.304               | 0.788                | 1.000     | 1.000                 | 0.682             | 0.288      |
| C5 LinkGuard            | 0.019   | -0.010     | 0.042    | 0.260    | 0.000               | 0.112                | 1.000     | 1.000                 | 0.695             | 0.535      |
| C6 aggressive redaction | 0.016   | -0.012     | 0.052    | 0.312    | 0.000               | 0.000                | 0.350     | 0.312                 | 0.389             | 0.681      |

## Local Auxiliary Bootstrap CIs

| condition               | n_personas | aux_top1 | ci_low | ci_high |
| ----------------------- | ---------- | -------- | ------ | ------- |
| C0 original             | 96         | 0.708    | 0.615  | 0.802   |
| C1 direct redaction     | 96         | 0.708    | 0.615  | 0.802   |
| C1b Presidio redaction  | 96         | 0.594    | 0.490  | 0.698   |
| C2 consistent pseudonym | 96         | 0.427    | 0.333  | 0.521   |
| C3 per-doc pseudonym    | 96         | 0.427    | 0.323  | 0.531   |
| C4 doc-local proxy      | 96         | 0.604    | 0.500  | 0.698   |
| C5 LinkGuard            | 96         | 0.042    | 0.010  | 0.083   |
| C6 aggressive redaction | 96         | 0.052    | 0.010  | 0.104   |

## Benchmark Validation

- Benchmark validation checks: 30; failures: 0.
- Exact synthetic direct-identifier leak checks across transformed conditions: 7; failures: 0.
- Full report: `results/benchmark_validation.md`.

## Quasi-Identifier Ablation

- Removing Role+org gives the largest direct-redaction Aux@1 drop (0.708 to 0.500), followed by Location (0.521).

| Signal removed | Aux@1 | Drop  | Aux@3 | MRR   |
| -------------- | ----- | ----- | ----- | ----- |
| Role+org       | 0.500 | 0.208 | 0.760 | 0.662 |
| Location       | 0.521 | 0.188 | 0.781 | 0.673 |
| Family         | 0.708 | 0.000 | 0.844 | 0.793 |
| Health         | 0.708 | 0.000 | 0.844 | 0.793 |
| Rare event     | 0.708 | 0.000 | 0.844 | 0.793 |
| Schedule       | 0.708 | 0.000 | 0.844 | 0.793 |

## GPT-5.5 API Stress Audit

- GPT-5.5 auxiliary matching on 48 T2/T3 personas finds direct redaction top-1 1.000, Presidio 0.979, document-local proxy 1.000, LinkGuard 0.438, and aggressive redaction 0.333.
- LinkGuard has lower confidence and higher uncertainty in this audit: top-3 0.708, T2 top-1 0.417, and T3 top-1 0.458.
- Treat this as a time-stamped stress audit; deterministic local sweeps remain the main reproducible evidence.

| condition               | n  | top1  | top3  | T2_top1 | T3_top1 |
| ----------------------- | -- | ----- | ----- | ------- | ------- |
| C1 direct redaction     | 48 | 1.000 | 1.000 | 1.000   | 1.000   |
| C1b Presidio redaction  | 48 | 0.979 | 1.000 | 0.958   | 1.000   |
| C4 doc-local proxy      | 48 | 1.000 | 1.000 | 1.000   | 1.000   |
| C5 LinkGuard            | 48 | 0.438 | 0.708 | 0.417   | 0.458   |
| C6 aggressive redaction | 48 | 0.333 | 0.667 | 0.417   | 0.250   |

## GPT-5.5 Document-Local Baseline

- GPT-5.5 document-local anonymization on 24 T2/T3 personas removes exact direct identifiers but remains matchable: Aux@1 1.000, Aux@3 1.000.
- On the same persona subset, the local document-local proxy is 1.000, LinkGuard is 0.333, and aggressive redaction is 0.292.
- This supports the corpus-level argument: a strong document-local anonymizer can still preserve repeated quasi-identifier combinations.

| condition               | n  | top1  | top3  | T2_top1 | T3_top1 |
| ----------------------- | -- | ----- | ----- | ------- | ------- |
| C1 direct redaction     | 24 | 1.000 | 1.000 | 1.000   | 1.000   |
| C1b Presidio redaction  | 24 | 0.958 | 1.000 | 0.917   | 1.000   |
| C4 doc-local proxy      | 24 | 1.000 | 1.000 | 1.000   | 1.000   |
| C4 GPT-5.5 doc-local    | 24 | 1.000 | 1.000 | 1.000   | 1.000   |
| C5 LinkGuard            | 24 | 0.333 | 0.625 | 0.250   | 0.417   |
| C6 aggressive redaction | 24 | 0.292 | 0.583 | 0.417   | 0.167   |

## GPT-5.5 Evidence Extraction

- On 8 direct-redaction successful matches, GPT-5.5 cites location in 1.000 of explanations and role in 0.750.
- On 8 LinkGuard residual matches, it cites role, location, and institution at 0.000 and marks 0.875 of explanations uncertain.
- On 8 aggressive-redaction top-3 failures, explanations are mostly information-removed or coarse-context contrasts with uncertainty 0.750.

| Case           | n | Role  | Loc.  | Inst. | High-spec. | Unc.  |
| -------------- | - | ----- | ----- | ----- | ---------- | ----- |
| Direct success | 8 | 0.750 | 1.000 | 0.500 | 0.475      | 0.000 |
| LG residual    | 8 | 0.000 | 0.000 | 0.000 | 0.075      | 0.875 |
| Agg failure    | 8 | 0.000 | 0.000 | 0.000 | 0.179      | 0.750 |

## Small OpenAI Audit

- Corrected 12-person audit: direct redaction top-1 0.750; Presidio top-1 0.500; OpenAI document-local top-1 0.667; LinkGuard top-1 0.250.
- This audit is intentionally small and should be reported as preliminary corroboration, not the main quantitative result.

| condition               | n  | top1  | top3  | T2_top1 | T3_top1 |
| ----------------------- | -- | ----- | ----- | ------- | ------- |
| C1 direct redaction     | 12 | 0.750 | 0.917 | 0.500   | 1.000   |
| C1b Presidio redaction  | 12 | 0.500 | 1.000 | 0.333   | 0.667   |
| C4 doc-local proxy      | 12 | 0.750 | 0.833 | 0.500   | 1.000   |
| C4 OpenAI doc-local     | 12 | 0.667 | 1.000 | 0.333   | 1.000   |
| C5 LinkGuard            | 12 | 0.250 | 0.500 | 0.167   | 0.333   |
| C6 aggressive redaction | 12 | 0.167 | 0.667 | 0.167   | 0.167   |

## Risk-Tier Stratification

- Direct-redacted Aux@1 rises from 0.156 on T1 to 0.969 on T2 and 1.000 on T3, confirming that the synthetic tiers encode increasing linkage risk.
- LinkGuard reduces tiered Aux@1 to 0.031, 0.000, and 0.094 for T1/T2/T3, with T3 exact recovery 0.000.

| Cond.        | T1 Aux@1 | T2 Aux@1 | T3 Aux@1 | T3 Exact |
| ------------ | -------- | -------- | -------- | -------- |
| C1 Redact    | 0.156    | 0.969    | 1.000    | 1.000    |
| C1b Presidio | 0.094    | 0.688    | 1.000    | 0.875    |
| C4 Local     | 0.156    | 0.656    | 1.000    | 0.818    |
| C5 LG        | 0.031    | 0.000    | 0.094    | 0.000    |
| C6 Agg       | 0.062    | 0.000    | 0.094    | 0.000    |

## LinkGuard Sensitivity

- Increasing target k from 1 to 2 drops auxiliary top-1 from 0.708 to 0.062; target k=5 gives 0.042.
- The edit ratio rises from 0.246 at k=1 to 0.521 at k=2 and 0.535 at k=5.
- Under the field-weighted stress attacker, top-1 falls from 0.979 at k=1 to 0.240 at k=5 and 0.104 at k=20.

| target_k | min_estimated_k | median_estimated_k | edit_ratio | pair_f1 | aux_top1 | aux_top3 | field_aux_top1 | field_aux_top3 | attr_exact_recovery | attr_coarse_recovery | issue_acc | retrieval_recall_at_5 | fact_preservation |
| -------- | --------------- | ------------------ | ---------- | ------- | -------- | -------- | -------------- | -------------- | ------------------- | -------------------- | --------- | --------------------- | ----------------- |
| 1.000    | 1.000           | 1.000              | 0.246      | 0.214   | 0.708    | 0.844    | 0.979          | 1.000          | 0.395               | 0.788                | 1.000     | 1.000                 | 0.682             |
| 2.000    | 2.000           | 3.000              | 0.521      | 0.036   | 0.062    | 0.281    | 0.354          | 0.729          | 0.007               | 0.189                | 1.000     | 1.000                 | 0.692             |
| 3.000    | 3.000           | 4.000              | 0.528      | 0.029   | 0.052    | 0.271    | 0.333          | 0.729          | 0.004               | 0.160                | 1.000     | 1.000                 | 0.694             |
| 5.000    | 5.000           | 8.000              | 0.535      | 0.019   | 0.042    | 0.260    | 0.240          | 0.667          | 0.000               | 0.112                | 1.000     | 1.000                 | 0.695             |
| 8.000    | 8.000           | 16.000             | 0.538      | 0.017   | 0.042    | 0.260    | 0.167          | 0.615          | 0.000               | 0.092                | 1.000     | 1.000                 | 0.695             |
| 12.000   | 12.000          | 17.000             | 0.539      | 0.017   | 0.042    | 0.260    | 0.125          | 0.604          | 0.000               | 0.083                | 1.000     | 1.000                 | 0.695             |
| 20.000   | 20.000          | 27.000             | 0.544      | 0.017   | 0.042    | 0.260    | 0.104          | 0.469          | 0.000               | 0.046                | 1.000     | 1.000                 | 0.718             |

## Multi-Seed Robustness

- Three no-API corpus seeds preserve the same qualitative ordering: direct/document-local redaction remain highly matchable, while LinkGuard approaches aggressive-redaction privacy with much higher utility.

| condition               | aux_top1_mean | aux_top1_std | attr_exact_recovery_mean | attr_exact_recovery_std | issue_acc_mean | retrieval_recall_at_5_mean | edit_ratio_mean |
| ----------------------- | ------------- | ------------ | ------------------------ | ----------------------- | -------------- | -------------------------- | --------------- |
| c1_direct_redaction     | 0.719         | 0.038        | 0.395                    | 0.002                   | 0.999          | 1.000                      | 0.247           |
| c1b_presidio_redaction  | 0.628         | 0.043        | 0.331                    | 0.002                   | 0.999          | 1.000                      | 0.353           |
| c4_doc_local_anon       | 0.663         | 0.063        | 0.304                    | 0.002                   | 0.999          | 1.000                      | 0.282           |
| c5_linkguard            | 0.045         | 0.006        | 0.000                    | 0.001                   | 0.999          | 1.000                      | 0.538           |
| c6_aggressive_redaction | 0.056         | 0.016        | 0.000                    | 0.000                   | 0.338          | 0.294                      | 0.682           |

## Candidate-Set Hardness Sensitivity

- Expanding candidate sets from 10 to 50 preserves the ordering: direct redaction changes from 0.708 to 0.635, the document-local proxy from 0.604 to 0.500, LinkGuard from 0.042 to 0.000, and aggressive redaction from 0.052 to 0.000.

| Cond.        | Aux@10 | Aux@20 | Aux@50 |
| ------------ | ------ | ------ | ------ |
| C1 Redact    | 0.708  | 0.646  | 0.635  |
| C1b Presidio | 0.594  | 0.573  | 0.479  |
| C4 Local     | 0.604  | 0.552  | 0.500  |
| C5 LG        | 0.042  | 0.000  | 0.000  |
| C6 Agg       | 0.052  | 0.000  | 0.000  |
| Chance       | 0.100  | 0.050  | 0.020  |

## Attack-Model Sensitivity

- Word, character, hybrid TF-IDF, and field-weighted auxiliary matchers preserve the privacy ordering: direct redaction Aux@1 ranges from 0.510 to 0.979, the document-local proxy ranges from 0.479 to 0.979, and LinkGuard ranges from 0.031 to 0.240.
- The field-weighted attacker is the strongest local stress test because it explicitly scans exact and generalized quasi-identifier fields; it exposes residual LinkGuard risk while preserving a large gap from document-local baselines.

| Cond.        | Word  | Char  | Hybrid | Field |
| ------------ | ----- | ----- | ------ | ----- |
| C1 Redact    | 0.708 | 0.510 | 0.573  | 0.979 |
| C1b Presidio | 0.594 | 0.479 | 0.510  | 0.958 |
| C4 Local     | 0.604 | 0.479 | 0.521  | 0.979 |
| C5 LG        | 0.042 | 0.031 | 0.031  | 0.240 |
| C6 Agg       | 0.052 | 0.021 | 0.021  | 0.115 |

## Profile-Query RAG Exposure

- Across all held-out personas, exact synthetic profile queries retrieve a target document in the top five at 0.333 under direct redaction and 0.208 under LinkGuard.
- For high-linkage T3 personas, direct redaction, Presidio, and the document-local proxy all have Hit@5 1.000 and Multi@10 1.000; LinkGuard reduces T3 Hit@5 to 0.312 and Multi@10 to 0.000.

| Cond.        | Hit@5 | Multi@10 | DocRec@10 | MRR   |
| ------------ | ----- | -------- | --------- | ----- |
| C1 Redact    | 1.000 | 1.000    | 0.953     | 1.000 |
| C1b Presidio | 1.000 | 1.000    | 0.945     | 1.000 |
| C4 Local     | 1.000 | 1.000    | 0.961     | 1.000 |
| C5 LG        | 0.312 | 0.000    | 0.180     | 0.259 |
| C6 Agg       | 0.031 | 0.000    | 0.031     | 0.041 |

## RAG Context Recovery

- In T3 top-5 retrieval results, direct redaction exposes 9.781 exact quasi-identifier fields on average, Presidio exposes 8.625, and the document-local proxy exposes 7.844 exact / 9.469 coarse fields.
- LinkGuard reduces the same T3 context recovery to 0.000 exact and 0.438 coarse fields; aggressive redaction is 0.000/0.000.

| Cond.        | Hit@5 | ExactRate | CoarseRate | Exact# | Coarse# |
| ------------ | ----- | --------- | ---------- | ------ | ------- |
| C1 Redact    | 1.000 | 0.889     | 0.889      | 9.781  | 9.781   |
| C1b Presidio | 1.000 | 0.784     | 0.784      | 8.625  | 8.625   |
| C4 Local     | 1.000 | 0.713     | 0.861      | 7.844  | 9.469   |
| C5 LG        | 0.312 | 0.000     | 0.040      | 0.000  | 0.438   |
| C6 Agg       | 0.031 | 0.000     | 0.000      | 0.000  | 0.000   |

## GPT-5.5 RAG Generation Pilot (Not Paper Claim)

- A compact 2-person T3 pilot parsed all generated JSON responses (minimum parse-success rate 1.000) and used 10 cached calls.
- In the pilot, direct redaction and the document-local proxy have likely-same-person rate 1.000 and 1.000; LinkGuard and aggressive redaction are 0.000 and 0.000.
- This validates the compact RAG-generation protocol only; the 12-person audit still has 50 pending calls and is not a paper claim.

| Cond.        | n | parsed | Parse | Hit@5 | Same  | Exact | Unc.  |
| ------------ | - | ------ | ----- | ----- | ----- | ----- | ----- |
| C1 Redact    | 2 | 2      | 1.000 | 1.000 | 1.000 | 0.250 | 0.000 |
| C1b Presidio | 2 | 2      | 1.000 | 1.000 | 1.000 | 0.200 | 0.500 |
| C4 Local     | 2 | 2      | 1.000 | 1.000 | 1.000 | 0.250 | 0.000 |
| C5 LG        | 2 | 2      | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| C6 Agg       | 2 | 2      | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 |

## LinkGuard Residual Failure Analysis

- LinkGuard has 4 top-1 residual matches and 21 additional top-3 residual matches under the main word TF-IDF attacker.
- Among top-1 residuals, 0 retain exact quasi-identifier fields; median score margin is 0.0036.

| persona_id | risk_tier | score_true | score_margin | estimated_k | residual_exact_fields | residual_coarse_fields            |
| ---------- | --------- | ---------- | ------------ | ----------- | --------------------- | --------------------------------- |
| P0011      | T3        | 0.021      | 0.008        | 12          | none                  | medical_context,financial_context |
| P0032      | T3        | 0.016      | 0.003        | 5           | none                  | financial_context,legal_context   |
| P0101      | T3        | 0.015      | 0.000        | 27          | none                  | financial_context                 |
| P0117      | T1        | 0.014      | 0.004        | 5           | none                  | none                              |

## Body-Only Utility Stress Test

- Removing subject/contact scaffolding, LinkGuard keeps stress utility at 0.880, close to direct redaction at 0.870, while aggressive redaction falls to 0.438.
- LinkGuard preserves body issue phrases at 1.000 with placeholder rate 0.000; aggressive redaction has issue phrase rate 0.000 and placeholder rate 0.160.

| Cond.        | Issue Phrase | Slots | Body Ret@5 | Placeholder | Stress Utility |
| ------------ | ------------ | ----- | ---------- | ----------- | -------------- |
| C0 Orig      | 1.000        | 0.904 | 1.000      | 0.000       | 0.870          |
| C1 Redact    | 1.000        | 0.904 | 1.000      | 0.000       | 0.870          |
| C1b Presidio | 1.000        | 0.904 | 1.000      | 0.019       | 0.871          |
| C2 Stable    | 1.000        | 0.904 | 1.000      | 0.000       | 0.870          |
| C3 PerDoc    | 1.000        | 0.904 | 1.000      | 0.000       | 0.870          |
| C4 Local     | 1.000        | 0.904 | 1.000      | 0.000       | 0.869          |
| C5 LG        | 1.000        | 0.905 | 1.000      | 0.000       | 0.880          |
| C6 Agg       | 0.000        | 0.646 | 0.286      | 0.160       | 0.438          |

## Noisy Synthetic Style Stress Test

- A deterministic noisy-style corpus re-renders the same 480 synthetic documents with mean template similarity 0.306 to the original templates.
- The privacy ordering is stable: direct redaction Aux@1 0.656, Presidio 0.562, document-local proxy 0.594, and LinkGuard 0.042.
- LinkGuard keeps issue accuracy 1.000 and retrieval Recall@5 1.000; aggressive redaction drops to issue accuracy 0.473 and Recall@5 0.635.

| Cond.        | Aux@1 | Aux@3 | Exact | Issue | Ret@5 | Edit  |
| ------------ | ----- | ----- | ----- | ----- | ----- | ----- |
| C1 Redact    | 0.656 | 0.844 | 0.395 | 1.000 | 1.000 | 0.243 |
| C1b Presidio | 0.562 | 0.802 | 0.327 | 1.000 | 1.000 | 0.345 |
| C4 Local     | 0.594 | 0.844 | 0.304 | 1.000 | 1.000 | 0.295 |
| C5 LG        | 0.042 | 0.219 | 0.000 | 1.000 | 1.000 | 0.465 |
| C6 Agg       | 0.042 | 0.292 | 0.000 | 0.473 | 0.635 | 0.627 |

## Claim Verification

- Claim verifier checks: 369.
- Claim verifier failures: 0.
- Full report: `results/claim_verification.md`.

## API Accounting

- Cached API responses: 625.
- Total cached token usage: 575034 input, 117651 output, 692685 total.
- The cache total includes legacy, exploratory, and compact RAG-pilot calls; paper-facing GPT-5.5 claims use the run-specific auxiliary, document-local, and evidence artifacts.
- The full GPT-5.5 RAG-generation audit remains outside paper claims until the pending calls are explicitly approved and verified.

## Claims Supported Now

1. Span-level direct redaction can leave strong cross-document auxiliary matching risk.
2. Consistent pseudonyms act like stable linkage handles.
3. Document-local anonymization can miss combinations that are risky at corpus scale.
4. Exact quasi-identifier recovery provides a structured profile-reconstruction signal in addition to auxiliary matching.
5. Profile-query RAG retrieval can expose high-linkage transformed records even when direct PII is removed.
6. GPT-5.5 auxiliary, document-local, and evidence stress audits corroborate the corpus-level linkage story on synthetic subsets.
7. A noisy-style synthetic rerendering preserves the main privacy-utility ordering.
8. Corpus-aware generalization gives a better privacy-utility point than blanket aggressive redaction in this synthetic sprint.

## Caveats To Keep In The Paper

- The benchmark is synthetic and uses controlled template families; this is a feature for controlled ground truth, but limits external validity.
- The threshold graph clustering attack is brittle outside the stable-pseudonym condition, so clustering claims should emphasize consistent pseudonymization and fixed-K/auxiliary-matching results.
- GPT-5.5 audits are cached, time-stamped synthetic subset stress audits; deterministic local sweeps remain the main reproducible evidence.
- The compact RAG-generation pilot validates the protocol but is not a paper result until the full 12-person run is approved and verified.
- LinkGuard is a heuristic generalization method, not a formal privacy guarantee.
