# GPT-5.5 RAG Generation Audit Notes

Run name: `gpt55_rag_12t3`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Started at UTC: `2026-06-28T21:56:13+00:00`
Git commit: `110d6ca`
Persona count: 12
New API calls this run: 0
Cached calls served this run: 60
Token usage: 53121 input, 8529 output, 61650 total.
Usage CSV: `results/openai_gpt55_rag_12t3_audit_usage.csv`

All records sent to the API are synthetic transformed benchmark records.
All OpenAI response calls in this script pass `store=False` through `CachedOpenAI`.
Cached response files are under `cache/api_responses/`.
If this notes file was regenerated from cache, `New API calls this run` may be zero even though the cached responses originated from an earlier capped live run.

## RAG Generation Summary

# GPT-5.5 RAG Generation Exposure Audit

Local profile-query retrieval supplies the top-5 transformed documents; GPT-5.5 then reports what the retrieved documents expose.
Generation metrics are averaged over parsed JSON responses; parse success is reported separately.

| condition_label | n  | n_parsed | parse_success_rate | retrieval_hit_at_5 | likely_same_person_rate | sensitive_contexts_mean | exact_field_match_rate | uncertain_rate |
| --------------- | -- | -------- | ------------------ | ------------------ | ----------------------- | ----------------------- | ---------------------- | -------------- |
| C1 Redact       | 12 | 12       | 1.000              | 1.000              | 1.000                   | 3.000                   | 0.233                  | 0.083          |
| C1b Presidio    | 12 | 12       | 1.000              | 1.000              | 1.000                   | 3.000                   | 0.258                  | 0.083          |
| C4 Local        | 12 | 12       | 1.000              | 1.000              | 1.000                   | 3.000                   | 0.217                  | 0.167          |
| C5 LG           | 12 | 12       | 1.000              | 0.500              | 0.417                   | 3.000                   | 0.000                  | 1.000          |
| C6 Agg          | 12 | 12       | 1.000              | 0.083              | 0.000                   | 2.917                   | 0.000                  | 1.000          |
