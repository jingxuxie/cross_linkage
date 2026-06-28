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
