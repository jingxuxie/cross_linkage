# OpenAI Audit Notes

Model: `gpt-5.4-nano`
Personas audited: P0001, P0002, P0004, P0005, P0007, P0008, P0010, P0011, P0013, P0014, P0016, P0017
New API calls this run: 2
Token usage: 2587 input, 785 output, 3372 total.

Cached response files are under `cache/api_responses/`.

## Auxiliary Matching Summary

| condition               | risk_tier | n | top1  | top3  | mean_rank |
| ----------------------- | --------- | - | ----- | ----- | --------- |
| c1_direct_redaction     | T2        | 6 | 0.500 | 0.833 | 2.000     |
| c1_direct_redaction     | T3        | 6 | 1.000 | 1.000 | 1.000     |
| c1b_presidio_redaction  | T2        | 6 | 0.333 | 1.000 | 1.833     |
| c1b_presidio_redaction  | T3        | 6 | 0.667 | 1.000 | 1.333     |
| c4_doc_local_anon       | T2        | 6 | 0.500 | 0.667 | 2.500     |
| c4_doc_local_anon       | T3        | 6 | 1.000 | 1.000 | 1.000     |
| c4_openai_doc_local     | T2        | 6 | 0.333 | 1.000 | 1.833     |
| c4_openai_doc_local     | T3        | 6 | 1.000 | 1.000 | 1.000     |
| c5_linkguard            | T2        | 6 | 0.167 | 0.167 | 5.167     |
| c5_linkguard            | T3        | 6 | 0.333 | 0.833 | 2.500     |
| c6_aggressive_redaction | T2        | 6 | 0.167 | 0.833 | 2.667     |
| c6_aggressive_redaction | T3        | 6 | 0.167 | 0.500 | 3.667     |
