# Noisy Synthetic Style Stress Test

This is a synthetic-only external-validity stress test. It re-renders the same 120 personas and 480 documents as less template-aligned support notes, while preserving persona IDs, candidate sets, direct identifiers, quasi-identifiers, utility labels, and ground truth.

## Style Diagnostics

| n_docs  | mean_chars | mean_type_token_ratio | mean_template_similarity | unique_first_lines |
| ------- | ---------- | --------------------- | ------------------------ | ------------------ |
| 480.000 | 602.144    | 0.791                 | 0.306                    | 16.000             |

## Main Result

- Direct redaction remains highly matchable at Aux@1 0.656; Presidio-style redaction is 0.562; the document-local proxy is 0.594.
- LinkGuard reduces noisy-style Aux@1 to 0.042 with issue accuracy 1.000 and retrieval Recall@5 1.000.
- Aggressive redaction has Aux@1 0.042, but issue accuracy 0.473 and retrieval Recall@5 0.635.

| condition               | pair_f1 | aux_top1 | aux_top3 | exact | issue | ret5  | facts | edit  |
| ----------------------- | ------- | -------- | -------- | ----- | ----- | ----- | ----- | ----- |
| N0 noisy original       | 0.961   | 0.656    | 0.844    | 0.395 | 1.000 | 1.000 | 1.000 | nan   |
| C1 direct redaction     | 0.187   | 0.656    | 0.844    | 0.395 | 1.000 | 1.000 | 1.000 | 0.243 |
| C1b Presidio redaction  | 0.143   | 0.562    | 0.802    | 0.327 | 1.000 | 1.000 | 1.000 | 0.345 |
| C4 doc-local proxy      | 0.161   | 0.594    | 0.844    | 0.304 | 1.000 | 1.000 | 1.000 | 0.295 |
| C5 LinkGuard            | 0.019   | 0.042    | 0.219    | 0.000 | 1.000 | 1.000 | 1.000 | 0.465 |
| C6 aggressive redaction | 0.012   | 0.042    | 0.292    | 0.000 | 0.473 | 0.635 | 0.667 | 0.627 |
