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
