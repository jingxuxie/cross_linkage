# Reproducibility Checklist

Run from the repository root.

## Full No-API Path

```bash
conda run -n cross_linkage python src/reproduce_no_api.py
```

This runs the synthetic benchmark, validation, robustness checks, RAG exposure and context-recovery scans, noisy-style stress test, cached-only OpenAI plan checks, an optional RAG-generation plan check, RAG API budget reporting, API provenance reporting, table generation, PDF compilation, submission packaging, supplement generation, and claim verification.

## Fast Preview

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --dry-run
```

## Core Gates

```bash
conda run -n cross_linkage python src/validate_benchmark.py --config configs/sprint.yaml
conda run -n cross_linkage python src/corpus_awareness_ablation.py --config configs/sprint.yaml --target-k 5
conda run -n cross_linkage python src/rag_query_sensitivity.py --config configs/sprint.yaml
conda run -n cross_linkage python src/noisy_style_stress.py --config configs/sprint.yaml
conda run -n cross_linkage python src/make_paper_assets.py --config configs/sprint.yaml
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error short_paper.tex)
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex)
conda run -n cross_linkage python src/build_submission_package.py
conda run -n cross_linkage python src/make_supplement.py --config configs/sprint.yaml
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Expected gate status: zero benchmark-validation failures, a 4-page short PDF, an 8-page COLM PDF, clean submission-package compile, and zero claim-verifier failures.

## API Boundary

The default path is API-free. The legacy OpenAI audit is cached and can be checked without making calls:

```bash
conda run -n cross_linkage python src/openai_audit.py --config configs/sprint.yaml --model gpt-5.4-nano --max-personas 12 --max-calls 1 --tasks doc-local,aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction --plan-only
```

Expected legacy cached audit status: `planned_calls=120`, `cached_calls=120`, `missing_or_dependent_calls=0`.

The paper-facing GPT-5.5 auxiliary-matching audit is cached and can be checked without calls:

```bash
conda run -n cross_linkage python src/openai_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_48p --max-personas 48 --tiers T2,T3 --max-calls 300 --tasks aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c5_linkguard,c6_aggressive_redaction --reasoning-effort none --aux-compact-output --aux-max-output-tokens 400 --plan-only
```

Expected GPT-5.5 auxiliary status: `planned_calls=240`, `cached_calls=240`, `missing_or_dependent_calls=0`.

The GPT-5.5 document-local anonymization baseline and auxiliary-matching evaluation are cached:

```bash
conda run -n cross_linkage python src/openai_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_doclocal_24p --doc-local-condition c4_openai_doc_local_gpt55_24p --max-personas 24 --tiers T2,T3 --max-calls 300 --tasks doc-local,aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local_gpt55_24p,c5_linkguard,c6_aggressive_redaction --reasoning-effort none --aux-compact-output --aux-max-output-tokens 400 --plan-only
```

Expected GPT-5.5 document-local status: `planned_calls=240`, `cached_calls=240`, `missing_or_dependent_calls=0`.

The GPT-5.5 qualitative evidence-extraction audit is cached:

```bash
conda run -n cross_linkage python src/openai_evidence_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_evidence_24p --cases-per-bucket 8 --max-calls 24 --reasoning-effort none --max-output-tokens 650 --plan-only
```

Expected GPT-5.5 evidence status: `planned_calls=24`, `cached_calls=24`, `missing_calls=0`.

The optional GPT-5.5 RAG-generation audit has a compact 2-person pilot cached, but the full 12-person run is not part of the default paper claims until the remaining calls are explicitly approved:

```bash
conda run -n cross_linkage python src/openai_rag_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_rag_12t3 --max-personas 12 --tier T3 --max-calls 60 --reasoning-effort none --max-output-tokens 250 --plan-only
```

Expected pre-approval status after the compact pilot: `planned_calls=60`, `cached_calls=10`, `missing_calls=50`.

The RAG API budget report splits the remaining optional RAG-generation calls into small approval units without making API calls:

```bash
conda run -n cross_linkage python src/rag_api_budget.py --config configs/sprint.yaml
```

Expected budget boundary: 5 batches, 10 calls per batch, using batch-specific run names that fill the shared response cache.

The API provenance manifest summarizes run names, cache completeness, token usage, claim status, and the `store=False` protocol without making API calls:

```bash
conda run -n cross_linkage python src/api_provenance_report.py --config configs/sprint.yaml
```

Expected manifest boundary: paper-facing GPT-5.5 auxiliary, document-local, and evidence audits are fully cached; the optional 12-person RAG-generation plan remains `10/60` cached and is not a paper claim.
