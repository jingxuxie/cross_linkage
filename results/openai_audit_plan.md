# OpenAI Audit Plan

Run name: `legacy`
Model: `gpt-5.4-nano`
Reasoning effort: `default`
Aux compact output: `False`
Aux max output tokens: `800`
Git commit: `6b1880a`
Conditions: c1_direct_redaction, c1b_presidio_redaction, c4_doc_local_anon, c4_openai_doc_local, c5_linkguard, c6_aggressive_redaction
Personas planned: P0001, P0002, P0004, P0005, P0007, P0008, P0010, P0011, P0013, P0014, P0016, P0017
Total planned calls: 120
Cached calls: 120
Missing or dependent calls: 0

## Summary

| task                               | condition               | cached | note | n  | input_chars |
| ---------------------------------- | ----------------------- | ------ | ---- | -- | ----------- |
| aux_match::c1_direct_redaction     | c1_direct_redaction     | 1      |      | 12 | 76559       |
| aux_match::c1b_presidio_redaction  | c1b_presidio_redaction  | 1      |      | 12 | 79592       |
| aux_match::c4_doc_local_anon       | c4_doc_local_anon       | 1      |      | 12 | 76946       |
| aux_match::c4_openai_doc_local     | c4_openai_doc_local     | 1      |      | 12 | 76253       |
| aux_match::c5_linkguard            | c5_linkguard            | 1      |      | 12 | 75676       |
| aux_match::c6_aggressive_redaction | c6_aggressive_redaction | 1      |      | 12 | 73427       |
| doc_local_anonymize                | c4_openai_doc_local     | 1      |      | 48 | 39489       |

Notes:
- `requires doc-local output before prompt can be hashed` means the final auxiliary-matching prompt depends on a generated document-local anonymization output.
- This plan does not call the OpenAI API and does not modify audit result summaries.
