# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_12t3_batch04`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Git commit: `5185065`
Personas planned: P0032, P0038
Total planned calls: 10
Cached calls: 10
Missing calls: 0

| condition               | n | cached | mean_input_chars |
| ----------------------- | - | ------ | ---------------- |
| c1_direct_redaction     | 2 | 2      | 4239.5           |
| c1b_presidio_redaction  | 2 | 2      | 4563.0           |
| c4_doc_local_anon       | 2 | 2      | 4252.5           |
| c5_linkguard            | 2 | 2      | 4181.0           |
| c6_aggressive_redaction | 2 | 2      | 3854.0           |
