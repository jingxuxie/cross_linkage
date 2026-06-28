# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_12t3_batch03`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Git commit: `9a4b664`
Personas planned: P0026, P0029
Total planned calls: 10
Cached calls: 10
Missing calls: 0

| condition               | n | cached | mean_input_chars |
| ----------------------- | - | ------ | ---------------- |
| c1_direct_redaction     | 2 | 2      | 4183.5           |
| c1b_presidio_redaction  | 2 | 2      | 4537.5           |
| c4_doc_local_anon       | 2 | 2      | 4214.0           |
| c5_linkguard            | 2 | 2      | 4027.0           |
| c6_aggressive_redaction | 2 | 2      | 3946.5           |
