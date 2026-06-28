# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_12t3`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `550`
Git commit: `1761b8e`
Personas planned: P0002, P0008, P0011, P0014, P0017, P0023, P0026, P0029, P0032, P0038, P0041, P0044
Total planned calls: 60
Cached calls: 0
Missing calls: 60

| condition               | n  | cached | mean_input_chars |
| ----------------------- | -- | ------ | ---------------- |
| c1_direct_redaction     | 12 | 0      | 3943.5           |
| c1b_presidio_redaction  | 12 | 0      | 4280.6           |
| c4_doc_local_anon       | 12 | 0      | 3958.8           |
| c5_linkguard            | 12 | 0      | 3803.0           |
| c6_aggressive_redaction | 12 | 0      | 3600.5           |
