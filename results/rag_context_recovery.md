# RAG Context Recovery

Profile-query retrieval supplies the top 5 transformed documents. This deterministic audit scans those retrieved documents for exact and coarse quasi-identifier recovery for the target persona.

## Overall

| condition_label         | n_personas | retrieval_hit_at_k | exact_field_recovery | coarse_field_recovery | exact_fields_recovered | coarse_fields_recovered |
| ----------------------- | ---------- | ------------------ | -------------------- | --------------------- | ---------------------- | ----------------------- |
| C0 original             | 96         | 0.333              | 0.590                | 0.590                 | 6.490                  | 6.490                   |
| C1 direct redaction     | 96         | 0.333              | 0.595                | 0.595                 | 6.542                  | 6.542                   |
| C1b Presidio redaction  | 96         | 0.333              | 0.524                | 0.524                 | 5.760                  | 5.760                   |
| C2 consistent pseudonym | 96         | 0.333              | 0.488                | 0.488                 | 5.365                  | 5.365                   |
| C3 per-doc pseudonym    | 96         | 0.333              | 0.488                | 0.488                 | 5.365                  | 5.365                   |
| C4 doc-local proxy      | 96         | 0.333              | 0.509                | 0.572                 | 5.594                  | 6.292                   |
| C5 LinkGuard            | 96         | 0.208              | 0.000                | 0.048                 | 0.000                  | 0.531                   |
| C6 aggressive redaction | 96         | 0.021              | 0.000                | 0.000                 | 0.000                  | 0.000                   |

## T3 Focus

| condition_label         | n_personas | retrieval_hit_at_k | exact_field_recovery | coarse_field_recovery | exact_fields_recovered | coarse_fields_recovered |
| ----------------------- | ---------- | ------------------ | -------------------- | --------------------- | ---------------------- | ----------------------- |
| C0 original             | 32         | 1.000              | 0.872                | 0.872                 | 9.594                  | 9.594                   |
| C1 direct redaction     | 32         | 1.000              | 0.889                | 0.889                 | 9.781                  | 9.781                   |
| C1b Presidio redaction  | 32         | 1.000              | 0.784                | 0.784                 | 8.625                  | 8.625                   |
| C2 consistent pseudonym | 32         | 1.000              | 0.676                | 0.676                 | 7.438                  | 7.438                   |
| C3 per-doc pseudonym    | 32         | 1.000              | 0.676                | 0.676                 | 7.438                  | 7.438                   |
| C4 doc-local proxy      | 32         | 1.000              | 0.713                | 0.861                 | 7.844                  | 9.469                   |
| C5 LinkGuard            | 32         | 0.312              | 0.000                | 0.040                 | 0.000                  | 0.438                   |
| C6 aggressive redaction | 32         | 0.031              | 0.000                | 0.000                 | 0.000                  | 0.000                   |
