# GPT-5.5 RAG Generation Budget Plan

This report makes no API calls. It uses the full RAG-generation plan and the cached compact pilot usage to estimate the remaining cache-fill batches.

Full run: `gpt55_rag_12t3`.
Pilot usage source: `results/openai_gpt55_rag_compact_pilot_2t3_audit_usage.csv`.
Cached calls in full plan: 30/60.
Remaining calls: 30.
Recommended batches: 3 batches of at most 10 new calls.
Estimated remaining total tokens: 30969.

| batch_id | batch_run_name         | persona_ids | new_calls | selected_calls | conditions | estimated_input_tokens | estimated_output_tokens | estimated_total_tokens | mean_input_chars |
| -------- | ---------------------- | ----------- | --------- | -------------- | ---------- | ---------------------- | ----------------------- | ---------------------- | ---------------- |
| batch03  | gpt55_rag_12t3_batch03 | P0026,P0029 | 10        | 10             | 5          | 8888                   | 1416                    | 10303                  | 4181.7           |
| batch04  | gpt55_rag_12t3_batch04 | P0032,P0038 | 10        | 10             | 5          | 8957                   | 1416                    | 10371                  | 4218.0           |
| batch05  | gpt55_rag_12t3_batch05 | P0041,P0044 | 10        | 10             | 5          | 8880                   | 1416                    | 10295                  | 4180.2           |

## Batch Commands

Use one command at a time only after explicit approval for paid API calls. Each batch uses a batch-specific run name while filling the shared response cache; after all batches are cached, rerun the full `gpt55_rag_12t3` command to produce the paper-facing 60-call summary from cache.

### batch03

```bash
conda run -n cross_linkage python src/openai_rag_audit.py --config configs/sprint.yaml --api-key-file /path/to/apikey.txt --model gpt-5.5 --run-name gpt55_rag_12t3_batch03 --persona-ids P0026,P0029 --tier T3 --max-calls 10 --reasoning-effort none --max-output-tokens 250
```

### batch04

```bash
conda run -n cross_linkage python src/openai_rag_audit.py --config configs/sprint.yaml --api-key-file /path/to/apikey.txt --model gpt-5.5 --run-name gpt55_rag_12t3_batch04 --persona-ids P0032,P0038 --tier T3 --max-calls 10 --reasoning-effort none --max-output-tokens 250
```

### batch05

```bash
conda run -n cross_linkage python src/openai_rag_audit.py --config configs/sprint.yaml --api-key-file /path/to/apikey.txt --model gpt-5.5 --run-name gpt55_rag_12t3_batch05 --persona-ids P0041,P0044 --tier T3 --max-calls 10 --reasoning-effort none --max-output-tokens 250
```
