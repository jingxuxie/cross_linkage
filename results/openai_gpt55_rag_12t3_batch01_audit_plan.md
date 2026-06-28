# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_12t3_batch01`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `250`
Text format: `json_object`
Text verbosity: `low`
Git commit: `ccd0129`
Personas planned: P0011, P0014
Total planned calls: 10
Cached calls: 10
Missing calls: 0

| condition               | n | cached | mean_input_chars |
| ----------------------- | - | ------ | ---------------- |
| c1_direct_redaction     | 2 | 2      | 4213.5           |
| c1b_presidio_redaction  | 2 | 2      | 4512.0           |
| c4_doc_local_anon       | 2 | 2      | 4234.5           |
| c5_linkguard            | 2 | 2      | 4013.5           |
| c6_aggressive_redaction | 2 | 2      | 3853.0           |
