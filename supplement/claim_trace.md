# Claim Trace

Each row maps a paper-facing claim to the artifact that supports it.

| claim                                                                             | evidence                                                                             | artifact                                                 |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| Direct PII redaction leaves auxiliary matching risk.                              | direct Aux@1 0.708                                                                   | results/main_results.csv                                 |
| Presidio-style PII redaction remains linkable.                                    | Presidio Aux@1 0.594                                                                 | results/main_results.csv                                 |
| Stable pseudonyms create linkage handles.                                         | stable pair F1 0.979                                                                 | results/main_results.csv                                 |
| Document-local anonymization misses corpus-level risk.                            | doc-local Aux@1 0.604                                                                | results/main_results.csv                                 |
| LinkGuard improves the privacy-utility frontier.                                  | LinkGuard Aux@1 0.042, Issue 1.000, Ret@5 1.000; aggressive Issue 0.350, Ret@5 0.312 | results/main_results.csv                                 |
| Field-aware stress risk is controllable by target k.                              | field Aux@1 k=5 0.240, k=20 0.104                                                    | results/linkguard_sensitivity.csv                        |
| Corpus co-occurrence statistics matter for LinkGuard planning.                    | true-corpus k-cover 1.000, shuffled-stats k-cover 0.917                              | results/corpus_awareness_ablation.csv                    |
| Profile-query RAG retrieval exposes high-linkage direct-redacted records.         | T3 direct Hit@5 1.000, LinkGuard Hit@5 0.312                                         | results/rag_exposure_by_tier.csv                         |
| Generated profile-like queries preserve the RAG exposure ordering.                | verbose direct Hit@5 0.375, LinkGuard Hit@5 0.260                                    | results/rag_query_sensitivity.csv                        |
| Retrieved profile-query contexts expose quasi-identifiers under direct baselines. | T3 direct exact fields 9.781, LinkGuard exact/coarse 0.000/0.438                     | results/rag_context_recovery_by_tier.csv                 |
| GPT-5.5 RAG generation preserves the exposure ordering.                           | direct Same 1.000, LinkGuard Same/Unc. 0.417/1.000, aggressive Same 0.000            | results/openai_gpt55_rag_12t3_rag_generation_summary.csv |
| Noisy-style synthetic rerendering preserves the ordering.                         | noisy direct Aux@1 0.656, LinkGuard Aux@1 0.042, aggressive Issue/Ret@5 0.473/0.635  | results/noisy_style_stress/noisy_style_results.csv       |
