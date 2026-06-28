# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_12t3`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Git commit: `e928b1f`
Personas planned: P0002, P0008, P0011, P0014, P0017, P0023, P0026, P0029, P0032, P0038, P0041, P0044
Total planned calls: 60
Cached calls: 10
Missing calls: 50

| condition               | n  | cached | mean_input_chars |
| ----------------------- | -- | ------ | ---------------- |
| c1_direct_redaction     | 12 | 2      | 4216.5           |
| c1b_presidio_redaction  | 12 | 2      | 4553.6           |
| c4_doc_local_anon       | 12 | 2      | 4231.8           |
| c5_linkguard            | 12 | 2      | 4076.0           |
| c6_aggressive_redaction | 12 | 2      | 3873.5           |
