# OpenAI Audit Notes

Run name: `gpt55_doclocal_24p`
Model: `gpt-5.5`
Reasoning effort: `none`
Aux compact output: `True`
Aux max output tokens: `400`
Started at UTC: `2026-06-28T10:32:05+00:00`
Git commit: `6839b4f`
Tasks: aux-match
Conditions: c1_direct_redaction, c1b_presidio_redaction, c4_doc_local_anon, c4_openai_doc_local_gpt55_24p, c5_linkguard, c6_aggressive_redaction
Persona count: 24
Personas audited: P0001, P0002, P0004, P0005, P0007, P0008, P0010, P0011, P0013, P0014, P0016, P0017, P0019, P0020, P0022, P0023, P0025, P0026, P0028, P0029, P0031, P0032, P0034, P0035
New API calls this run: 24
Cached calls served this run: 120
Token usage: 180965 input, 10395 output, 191360 total.
Usage CSV: `results/openai_gpt55_doclocal_24p_audit_usage.csv`

Cached response files are under `cache/api_responses/`.
All OpenAI response calls in this script pass `store=False`.

## Auxiliary Matching Summary

| condition                     | risk_tier | n  | top1  | top3  | mrr   | mean_rank | median_top_1_score | median_top_score_margin | uncertain_rate |
| ----------------------------- | --------- | -- | ----- | ----- | ----- | --------- | ------------------ | ----------------------- | -------------- |
| c1_direct_redaction           | T2        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.875              | nan                     | 0.083          |
| c1_direct_redaction           | T3        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c1b_presidio_redaction        | T2        | 12 | 0.917 | 1.000 | 0.958 | 1.083     | 0.860              | nan                     | 0.167          |
| c1b_presidio_redaction        | T3        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c4_doc_local_anon             | T2        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.820              | nan                     | 0.167          |
| c4_doc_local_anon             | T3        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c4_openai_doc_local_gpt55_24p | T2        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.860              | nan                     | 0.083          |
| c4_openai_doc_local_gpt55_24p | T3        | 12 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c5_linkguard                  | T2        | 12 | 0.250 | 0.500 | 0.454 | 3.333     | 0.380              | nan                     | 0.667          |
| c5_linkguard                  | T3        | 12 | 0.417 | 0.750 | 0.607 | 2.500     | 0.450              | nan                     | 1.000          |
| c6_aggressive_redaction       | T2        | 12 | 0.417 | 0.667 | 0.593 | 2.500     | 0.620              | nan                     | 0.833          |
| c6_aggressive_redaction       | T3        | 12 | 0.167 | 0.500 | 0.404 | 3.333     | 0.550              | nan                     | 0.917          |
