# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_12t3_batch05`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Git commit: `110d6ca`
Personas planned: P0041, P0044
Total planned calls: 10
Cached calls: 10
Missing calls: 0

| condition               | n | cached | mean_input_chars |
| ----------------------- | - | ------ | ---------------- |
| c1_direct_redaction     | 2 | 2      | 4200.0           |
| c1b_presidio_redaction  | 2 | 2      | 4547.5           |
| c4_doc_local_anon       | 2 | 2      | 4203.0           |
| c5_linkguard            | 2 | 2      | 4096.0           |
| c6_aggressive_redaction | 2 | 2      | 3854.5           |
