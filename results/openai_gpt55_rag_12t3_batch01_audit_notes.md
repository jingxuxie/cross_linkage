# GPT-5.5 RAG Generation Audit Notes

Run name: `gpt55_rag_12t3_batch01`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Started at UTC: `2026-06-28T21:23:13+00:00`
Git commit: `ccd0129`
Persona count: 2
New API calls this run: 10
Cached calls served this run: 0
Token usage: 8802 input, 1457 output, 10259 total.
Usage CSV: `results/openai_gpt55_rag_12t3_batch01_audit_usage.csv`

All records sent to the API are synthetic transformed benchmark records.
All OpenAI response calls in this script pass `store=False` through `CachedOpenAI`.
Cached response files are under `cache/api_responses/`.
If this notes file was regenerated from cache, `New API calls this run` may be zero even though the cached responses originated from an earlier capped live run.

## RAG Generation Summary

# GPT-5.5 RAG Generation Exposure Audit

Local profile-query retrieval supplies the top-5 transformed documents; GPT-5.5 then reports what the retrieved documents expose.
Generation metrics are averaged over parsed JSON responses; parse success is reported separately.

| condition_label | n | n_parsed | parse_success_rate | retrieval_hit_at_5 | likely_same_person_rate | sensitive_contexts_mean | exact_field_match_rate | uncertain_rate |
| --------------- | - | -------- | ------------------ | ------------------ | ----------------------- | ----------------------- | ---------------------- | -------------- |
| C1 Redact       | 2 | 2        | 1.000              | 1.000              | 1.000                   | 3.000                   | 0.250                  | 0.000          |
| C1b Presidio    | 2 | 2        | 1.000              | 1.000              | 1.000                   | 3.000                   | 0.250                  | 0.000          |
| C4 Local        | 2 | 2        | 1.000              | 1.000              | 1.000                   | 3.000                   | 0.200                  | 0.500          |
| C5 LG           | 2 | 2        | 1.000              | 0.500              | 0.500                   | 3.000                   | 0.000                  | 1.000          |
| C6 Agg          | 2 | 2        | 1.000              | 0.500              | 0.000                   | 3.000                   | 0.000                  | 1.000          |
