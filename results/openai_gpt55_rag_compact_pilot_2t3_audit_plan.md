# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_compact_pilot_2t3`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Git commit: `e928b1f`
Personas planned: P0002, P0008
Total planned calls: 10
Cached calls: 10
Missing calls: 0

| condition               | n | cached | mean_input_chars |
| ----------------------- | - | ------ | ---------------- |
| c1_direct_redaction     | 2 | 2      | 4232.0           |
| c1b_presidio_redaction  | 2 | 2      | 4577.5           |
| c4_doc_local_anon       | 2 | 2      | 4233.5           |
| c5_linkguard            | 2 | 2      | 4014.5           |
| c6_aggressive_redaction | 2 | 2      | 3883.0           |
