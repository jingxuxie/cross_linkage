# Generated-Query RAG Sensitivity

Deterministic short, medium, and verbose profile-like queries are issued against each transformed corpus.
`Hit@5` asks whether any target document appears in the top 5.
`Multi@10` asks whether at least two target-persona documents appear in the top 10.

| condition_label         | query_label | n_personas | hit_at_5 | multi_doc_at_10 | target_doc_recall_at_10 | mrr   |
| ----------------------- | ----------- | ---------- | -------- | --------------- | ----------------------- | ----- |
| C1 direct redaction     | Short       | 96         | 0.354    | 0.198           | 0.185                   | 0.257 |
| C1 direct redaction     | Medium      | 96         | 0.365    | 0.333           | 0.227                   | 0.358 |
| C1 direct redaction     | Verbose     | 96         | 0.375    | 0.354           | 0.336                   | 0.384 |
| C1b Presidio redaction  | Short       | 96         | 0.323    | 0.281           | 0.172                   | 0.221 |
| C1b Presidio redaction  | Medium      | 96         | 0.354    | 0.312           | 0.193                   | 0.347 |
| C1b Presidio redaction  | Verbose     | 96         | 0.375    | 0.333           | 0.302                   | 0.383 |
| C4 doc-local proxy      | Short       | 96         | 0.438    | 0.208           | 0.206                   | 0.372 |
| C4 doc-local proxy      | Medium      | 96         | 0.333    | 0.312           | 0.180                   | 0.334 |
| C4 doc-local proxy      | Verbose     | 96         | 0.375    | 0.333           | 0.305                   | 0.381 |
| C5 LinkGuard            | Short       | 96         | 0.021    | 0.000           | 0.010                   | 0.028 |
| C5 LinkGuard            | Medium      | 96         | 0.083    | 0.000           | 0.031                   | 0.064 |
| C5 LinkGuard            | Verbose     | 96         | 0.260    | 0.031           | 0.107                   | 0.178 |
| C6 aggressive redaction | Short       | 96         | 0.042    | 0.000           | 0.021                   | 0.042 |
| C6 aggressive redaction | Medium      | 96         | 0.042    | 0.000           | 0.023                   | 0.042 |
| C6 aggressive redaction | Verbose     | 96         | 0.031    | 0.000           | 0.018                   | 0.039 |

## T3 Focus

| condition_label         | query_label | risk_tier | n_personas | hit_at_5 | multi_doc_at_10 | target_doc_recall_at_10 | mrr   |
| ----------------------- | ----------- | --------- | ---------- | -------- | --------------- | ----------------------- | ----- |
| C1 direct redaction     | Short       | T3        | 32         | 0.844    | 0.500           | 0.359                   | 0.591 |
| C1 direct redaction     | Medium      | T3        | 32         | 1.000    | 1.000           | 0.641                   | 1.000 |
| C1 direct redaction     | Verbose     | T3        | 32         | 1.000    | 1.000           | 0.805                   | 1.000 |
| C1b Presidio redaction  | Short       | T3        | 32         | 0.906    | 0.844           | 0.461                   | 0.587 |
| C1b Presidio redaction  | Medium      | T3        | 32         | 1.000    | 0.938           | 0.547                   | 0.984 |
| C1b Presidio redaction  | Verbose     | T3        | 32         | 1.000    | 1.000           | 0.750                   | 1.000 |
| C4 doc-local proxy      | Short       | T3        | 32         | 1.000    | 0.500           | 0.383                   | 0.932 |
| C4 doc-local proxy      | Medium      | T3        | 32         | 1.000    | 0.938           | 0.539                   | 0.984 |
| C4 doc-local proxy      | Verbose     | T3        | 32         | 1.000    | 1.000           | 0.766                   | 1.000 |
| C5 LinkGuard            | Short       | T3        | 32         | 0.000    | 0.000           | 0.000                   | 0.015 |
| C5 LinkGuard            | Medium      | T3        | 32         | 0.031    | 0.000           | 0.023                   | 0.038 |
| C5 LinkGuard            | Verbose     | T3        | 32         | 0.219    | 0.031           | 0.086                   | 0.189 |
| C6 aggressive redaction | Short       | T3        | 32         | 0.000    | 0.000           | 0.000                   | 0.009 |
| C6 aggressive redaction | Medium      | T3        | 32         | 0.000    | 0.000           | 0.016                   | 0.029 |
| C6 aggressive redaction | Verbose     | T3        | 32         | 0.000    | 0.000           | 0.000                   | 0.014 |
