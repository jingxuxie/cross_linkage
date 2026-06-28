# OpenAI Audit Plan

Run name: `gpt55_doclocal_24p`
Model: `gpt-5.5`
Reasoning effort: `none`
Aux compact output: `True`
Aux max output tokens: `400`
Git commit: `6b1880a`
Conditions: c1_direct_redaction, c1b_presidio_redaction, c4_doc_local_anon, c4_openai_doc_local_gpt55_24p, c5_linkguard, c6_aggressive_redaction
Personas planned: P0001, P0002, P0004, P0005, P0007, P0008, P0010, P0011, P0013, P0014, P0016, P0017, P0019, P0020, P0022, P0023, P0025, P0026, P0028, P0029, P0031, P0032, P0034, P0035
Total planned calls: 240
Cached calls: 240
Missing or dependent calls: 0

## Summary

| task                                     | condition                     | cached | note | n  | input_chars |
| ---------------------------------------- | ----------------------------- | ------ | ---- | -- | ----------- |
| aux_match::c1_direct_redaction           | c1_direct_redaction           | 1      |      | 24 | 160880      |
| aux_match::c1b_presidio_redaction        | c1b_presidio_redaction        | 1      |      | 24 | 166996      |
| aux_match::c4_doc_local_anon             | c4_doc_local_anon             | 1      |      | 24 | 161675      |
| aux_match::c4_openai_doc_local_gpt55_24p | c4_openai_doc_local_gpt55_24p | 1      |      | 24 | 163696      |
| aux_match::c5_linkguard                  | c5_linkguard                  | 1      |      | 24 | 159292      |
| aux_match::c6_aggressive_redaction       | c6_aggressive_redaction       | 1      |      | 24 | 154762      |
| doc_local_anonymize                      | c4_openai_doc_local_gpt55_24p | 1      |      | 96 | 78816       |

Notes:
- `requires doc-local output before prompt can be hashed` means the final auxiliary-matching prompt depends on a generated document-local anonymization output.
- This plan does not call the OpenAI API and does not modify audit result summaries.
