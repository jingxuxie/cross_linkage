# OpenAI Audit Notes

Run name: `gpt55_48p`
Model: `gpt-5.5`
Reasoning effort: `none`
Aux compact output: `True`
Aux max output tokens: `400`
Started at UTC: `2026-06-28T10:22:13+00:00`
Git commit: `6839b4f`
Tasks: aux-match
Conditions: c1_direct_redaction, c1b_presidio_redaction, c4_doc_local_anon, c5_linkguard, c6_aggressive_redaction
Persona count: 48
Personas audited: P0001, P0002, P0004, P0005, P0007, P0008, P0010, P0011, P0013, P0014, P0016, P0017, P0019, P0020, P0022, P0023, P0025, P0026, P0028, P0029, P0031, P0032, P0034, P0035, P0037, P0038, P0040, P0041, P0043, P0044, P0046, P0047, P0049, P0050, P0052, P0053, P0055, P0056, P0058, P0059, P0061, P0062, P0064, P0065, P0067, P0068, P0070, P0071
New API calls this run: 0
Cached calls served this run: 240
Token usage: 301358 input, 17310 output, 318668 total.
Usage CSV: `results/openai_gpt55_48p_audit_usage.csv`

Cached response files are under `cache/api_responses/`.
All OpenAI response calls in this script pass `store=False`.

## Auxiliary Matching Summary

| condition               | risk_tier | n  | top1  | top3  | mrr   | mean_rank | median_top_1_score | median_top_score_margin | uncertain_rate |
| ----------------------- | --------- | -- | ----- | ----- | ----- | --------- | ------------------ | ----------------------- | -------------- |
| c1_direct_redaction     | T2        | 24 | 1.000 | 1.000 | 1.000 | 1.000     | 0.920              | nan                     | 0.042          |
| c1_direct_redaction     | T3        | 24 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c1b_presidio_redaction  | T2        | 24 | 0.958 | 1.000 | 0.979 | 1.042     | 0.845              | nan                     | 0.250          |
| c1b_presidio_redaction  | T3        | 24 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c4_doc_local_anon       | T2        | 24 | 1.000 | 1.000 | 1.000 | 1.000     | 0.860              | nan                     | 0.167          |
| c4_doc_local_anon       | T3        | 24 | 1.000 | 1.000 | 1.000 | 1.000     | 0.990              | nan                     | 0.000          |
| c5_linkguard            | T2        | 24 | 0.417 | 0.625 | 0.581 | 2.750     | 0.390              | nan                     | 0.833          |
| c5_linkguard            | T3        | 24 | 0.458 | 0.792 | 0.630 | 2.458     | 0.430              | nan                     | 1.000          |
| c6_aggressive_redaction | T2        | 24 | 0.417 | 0.708 | 0.613 | 2.417     | 0.625              | nan                     | 0.750          |
| c6_aggressive_redaction | T3        | 24 | 0.250 | 0.625 | 0.485 | 2.958     | 0.650              | nan                     | 0.833          |
