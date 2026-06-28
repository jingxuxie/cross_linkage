# RAG Exposure Diagnostic

Exact synthetic auxiliary-profile queries are issued against each transformed corpus.
`Hit@5` asks whether any target document appears in the top 5.
`Multi@10` asks whether at least two documents from the target persona appear in the top 10.

| condition_label         | top1_doc_hit | hit_at_5 | multi_doc_at_10 | target_doc_recall_at_10 | mrr   |
| ----------------------- | ------------ | -------- | --------------- | ----------------------- | ----- |
| C0 original             | 0.333        | 0.333    | 0.333           | 0.318                   | 0.353 |
| C1 direct redaction     | 0.333        | 0.333    | 0.333           | 0.320                   | 0.354 |
| C1b Presidio redaction  | 0.333        | 0.333    | 0.333           | 0.318                   | 0.354 |
| C2 consistent pseudonym | 0.333        | 0.333    | 0.333           | 0.302                   | 0.347 |
| C3 per-doc pseudonym    | 0.333        | 0.333    | 0.333           | 0.302                   | 0.347 |
| C4 doc-local proxy      | 0.333        | 0.333    | 0.333           | 0.323                   | 0.354 |
| C5 LinkGuard            | 0.062        | 0.208    | 0.010           | 0.107                   | 0.161 |
| C6 aggressive redaction | 0.000        | 0.021    | 0.000           | 0.026                   | 0.036 |

## By Risk Tier

| condition_label         | risk_tier | top1_doc_hit | hit_at_5 | multi_doc_at_10 | target_doc_recall_at_10 | mrr   |
| ----------------------- | --------- | ------------ | -------- | --------------- | ----------------------- | ----- |
| C0 original             | T2        | 0.000        | 0.000    | 0.000           | 0.008                   | 0.043 |
| C0 original             | T3        | 1.000        | 1.000    | 1.000           | 0.945                   | 1.000 |
| C0 original             | T1        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.016 |
| C1 direct redaction     | T2        | 0.000        | 0.000    | 0.000           | 0.008                   | 0.045 |
| C1 direct redaction     | T3        | 1.000        | 1.000    | 1.000           | 0.953                   | 1.000 |
| C1 direct redaction     | T1        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.018 |
| C1b Presidio redaction  | T2        | 0.000        | 0.000    | 0.000           | 0.008                   | 0.044 |
| C1b Presidio redaction  | T3        | 1.000        | 1.000    | 1.000           | 0.945                   | 1.000 |
| C1b Presidio redaction  | T1        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.016 |
| C2 consistent pseudonym | T2        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.021 |
| C2 consistent pseudonym | T3        | 1.000        | 1.000    | 1.000           | 0.906                   | 1.000 |
| C2 consistent pseudonym | T1        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.019 |
| C3 per-doc pseudonym    | T2        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.021 |
| C3 per-doc pseudonym    | T3        | 1.000        | 1.000    | 1.000           | 0.906                   | 1.000 |
| C3 per-doc pseudonym    | T1        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.019 |
| C4 doc-local proxy      | T2        | 0.000        | 0.000    | 0.000           | 0.008                   | 0.043 |
| C4 doc-local proxy      | T3        | 1.000        | 1.000    | 1.000           | 0.961                   | 1.000 |
| C4 doc-local proxy      | T1        | 0.000        | 0.000    | 0.000           | 0.000                   | 0.018 |
| C5 LinkGuard            | T2        | 0.062        | 0.281    | 0.031           | 0.133                   | 0.172 |
| C5 LinkGuard            | T3        | 0.125        | 0.312    | 0.000           | 0.180                   | 0.259 |
| C5 LinkGuard            | T1        | 0.000        | 0.031    | 0.000           | 0.008                   | 0.052 |
| C6 aggressive redaction | T2        | 0.000        | 0.031    | 0.000           | 0.031                   | 0.033 |
| C6 aggressive redaction | T3        | 0.000        | 0.031    | 0.000           | 0.031                   | 0.041 |
| C6 aggressive redaction | T1        | 0.000        | 0.000    | 0.000           | 0.016                   | 0.034 |
