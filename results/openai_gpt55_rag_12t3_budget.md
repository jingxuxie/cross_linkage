# GPT-5.5 RAG Generation Budget Plan

This report makes no API calls. It uses the full RAG-generation plan and the cached compact pilot usage to estimate the remaining cache-fill batches.

Full run: `gpt55_rag_12t3`.
Pilot usage source: `results/openai_gpt55_rag_compact_pilot_2t3_audit_usage.csv`.
Cached calls in full plan: 60/60.
Remaining calls: 0.
Recommended batches: 0 batches of at most 0 new calls.
Estimated remaining total tokens: 0.

_No pending calls._

## Batch Commands

Use one command at a time only after explicit approval for paid API calls. Each batch uses a batch-specific run name while filling the shared response cache; after all batches are cached, rerun the full `gpt55_rag_12t3` command to produce the paper-facing 60-call summary from cache.
