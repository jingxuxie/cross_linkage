# GPT-5.5 RAG Generation Audit Notes

Run name: `gpt55_rag_pilot_3t3`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `450`
Started at UTC: `2026-06-28T11:15:58+00:00`
Git commit: `7ec5e26`
Persona count: 3
New API calls this run: 15
Cached calls served this run: 0
Token usage: 12314 input, 6283 output, 18597 total.
Usage CSV: `results/openai_gpt55_rag_pilot_3t3_audit_usage.csv`

All records sent to the API are synthetic transformed benchmark records.
All OpenAI response calls in this script pass `store=False` through `CachedOpenAI`.
Cached response files are under `cache/api_responses/`.

Warning: this pilot exposed an output-truncation issue. Several responses did not parse
as complete JSON, so this run is a debug artifact and should not be reported as
paper-ready RAG-generation evidence.

## RAG Generation Summary

# GPT-5.5 RAG Generation Exposure Audit

Local profile-query retrieval supplies the top-5 transformed documents; GPT-5.5 then reports what the retrieved documents expose.
Generation metrics are averaged over parsed JSON responses; parse success is reported separately.

| condition_label | n | n_parsed | parse_success_rate | retrieval_hit_at_5 | likely_same_person_rate | sensitive_contexts_mean | exact_field_match_rate | uncertain_rate |
| --------------- | - | -------- | ------------------ | ------------------ | ----------------------- | ----------------------- | ---------------------- | -------------- |
| C1 Redact       | 3 | 0        | 0.000              | 1.000              | NA                      | NA                      | NA                     | NA             |
| C1b Presidio    | 3 | 0        | 0.000              | 1.000              | NA                      | NA                      | NA                     | NA             |
| C4 Local        | 3 | 0        | 0.000              | 1.000              | NA                      | NA                      | NA                     | NA             |
| C5 LG           | 3 | 2        | 0.667              | 1.000              | 0.500                   | 5.500                   | 0.000                  | 1.000          |
| C6 Agg          | 3 | 3        | 1.000              | 0.333              | 0.000                   | 5.667                   | 0.000                  | 1.000          |
