# API Audit Provenance

Generated from existing local plan, usage, and note artifacts. This command makes no API calls.

All listed API scripts route live calls through `CachedOpenAI` with `store=False`; cached artifacts are synthetic transformed benchmark records only.

## Summary

| run_id                      | model        | paper_claim_status                           | planned_calls | cached_calls | missing_calls | usage_total_tokens | persona_count | condition_count | store_false_protocol | boundary_note                                                                                    |
| --------------------------- | ------------ | -------------------------------------------- | ------------- | ------------ | ------------- | ------------------ | ------------- | --------------- | -------------------- | ------------------------------------------------------------------------------------------------ |
| legacy_openai_aux_doclocal  | gpt-5.4-nano | legacy_small_cached_audit_not_main_claim     | 120           | 120          | 0             | 3372               | 12            | 6               | true                 | Historical cached 12-person audit; retained as a small sanity check.                             |
| gpt55_aux_48p               | gpt-5.5      | paper_facing_cached_stress_audit             | 240           | 240          | 0             | 318668             | 48            | 5               | true                 | Corroborating time-stamped stress audit, not the main statistical evidence.                      |
| gpt55_doclocal_24p          | gpt-5.5      | paper_facing_cached_stress_audit             | 240           | 240          | 0             | 191360             | 24            | 6               | true                 | Corroborating document-local LLM baseline on a synthetic subset.                                 |
| gpt55_evidence_24p          | gpt-5.5      | paper_facing_cached_qualitative_stress_audit | 24            | 24           | 0             | 24507              | 17            | 3               | true                 | Qualitative signal audit over selected synthetic cases.                                          |
| gpt55_rag_12t3_plan         | gpt-5.5      | planned_not_paper_claim_pending_calls        | 60            | 50           | 10            | 0                  | 12            | 5               | true                 | Full 12-person RAG-generation audit has pending calls and is not claimed.                        |
| gpt55_rag_compact_pilot_2t3 | gpt-5.5      | compact_pilot_not_paper_claim                | 10            | 10           | 0             | 10313              | 2             | 5               | true                 | Cached 2-person parsing pilot only; not a paper generation result.                               |
| gpt55_rag_12t3_batch01      | gpt-5.5      | partial_cache_fill_not_paper_claim           | 10            | 10           | 0             | 10259              | 2             | 5               | true                 | Completed 10-call batch that fills the shared 12-person RAG cache; not a standalone paper claim. |
| gpt55_rag_12t3_batch02      | gpt-5.5      | partial_cache_fill_not_paper_claim           | 10            | 10           | 0             | 10320              | 2             | 5               | true                 | Completed 10-call batch that fills the shared 12-person RAG cache; not a standalone paper claim. |
| gpt55_rag_12t3_batch03      | gpt-5.5      | partial_cache_fill_not_paper_claim           | 10            | 10           | 0             | 10245              | 2             | 5               | true                 | Completed 10-call batch that fills the shared 12-person RAG cache; not a standalone paper claim. |
| gpt55_rag_12t3_batch04      | gpt-5.5      | partial_cache_fill_not_paper_claim           | 10            | 10           | 0             | 10275              | 2             | 5               | true                 | Completed 10-call batch that fills the shared 12-person RAG cache; not a standalone paper claim. |

## Artifact Columns

The CSV adds run labels, task family, note timestamps, artifact git commits, token usage totals, source scripts, and primary output paths.

CSV artifact: `results/api_audit_provenance.csv`.
