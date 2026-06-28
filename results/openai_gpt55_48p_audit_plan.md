# OpenAI Audit Plan

Run name: `gpt55_48p`
Model: `gpt-5.5`
Reasoning effort: `none`
Aux compact output: `True`
Aux max output tokens: `400`
Git commit: `6839b4f`
Conditions: c1_direct_redaction, c1b_presidio_redaction, c4_doc_local_anon, c5_linkguard, c6_aggressive_redaction
Personas planned: P0001, P0002, P0004, P0005, P0007, P0008, P0010, P0011, P0013, P0014, P0016, P0017, P0019, P0020, P0022, P0023, P0025, P0026, P0028, P0029, P0031, P0032, P0034, P0035, P0037, P0038, P0040, P0041, P0043, P0044, P0046, P0047, P0049, P0050, P0052, P0053, P0055, P0056, P0058, P0059, P0061, P0062, P0064, P0065, P0067, P0068, P0070, P0071
Total planned calls: 240
Cached calls: 240
Missing or dependent calls: 0

## Summary

| task                               | condition               | cached | note | n  | input_chars |
| ---------------------------------- | ----------------------- | ------ | ---- | -- | ----------- |
| aux_match::c1_direct_redaction     | c1_direct_redaction     | 1      |      | 48 | 321338      |
| aux_match::c1b_presidio_redaction  | c1b_presidio_redaction  | 1      |      | 48 | 333720      |
| aux_match::c4_doc_local_anon       | c4_doc_local_anon       | 1      |      | 48 | 322934      |
| aux_match::c5_linkguard            | c5_linkguard            | 1      |      | 48 | 318267      |
| aux_match::c6_aggressive_redaction | c6_aggressive_redaction | 1      |      | 48 | 309161      |

Notes:
- `requires doc-local output before prompt can be hashed` means the final auxiliary-matching prompt depends on a generated document-local anonymization output.
- This plan does not call the OpenAI API and does not modify audit result summaries.
