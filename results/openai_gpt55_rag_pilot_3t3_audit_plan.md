# GPT-5.5 RAG Generation Audit Plan

Run name: `gpt55_rag_pilot_3t3`
Model: `gpt-5.5`
Reasoning effort: `none`
Top retrieved documents: `5`
Max output tokens: `450`
Git commit: `7ec5e26`
Personas planned: P0002, P0008, P0011
Total planned calls: 15
Cached calls: 0
Missing calls: 15

| condition               | n | cached | mean_input_chars |
| ----------------------- | - | ------ | ---------------- |
| c1_direct_redaction     | 3 | 0      | 3970.0           |
| c1b_presidio_redaction  | 3 | 0      | 4290.3           |
| c4_doc_local_anon       | 3 | 0      | 3979.7           |
| c5_linkguard            | 3 | 0      | 3746.0           |
| c6_aggressive_redaction | 3 | 0      | 3591.7           |
