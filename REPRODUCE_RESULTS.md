# Reproducing the Result Package

This project has two reproducibility paths:

1. A no-API path that regenerates the synthetic corpus, deterministic attacks,
   robustness checks, paper tables, figures, PDFs, submission bundle, reviewer supplement, and claim verifier.
2. Cached OpenAI audit checks that verify the legacy 12-person audit plus the
   paper-facing GPT-5.5 stress-audit, document-local baseline, and evidence-extraction
   artifacts without making new API calls.

## No-API End-to-End Run

Run:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py
```

This executes:

- local benchmark generation and evaluation;
- benchmark artifact validation;
- LinkGuard target-k sensitivity;
- three-seed robustness sweep;
- candidate-pool sensitivity;
- local attacker-family sensitivity, including a field-aware stress attacker;
- LinkGuard residual failure analysis;
- body-only utility stress test;
- profile-query RAG exposure diagnostic;
- noisy synthetic style stress test;
- cached-only OpenAI audit plan check;
- paper table and figure generation;
- generic PDF compilation;
- official COLM-template PDF compilation;
- clean COLM source/PDF submission packaging;
- reviewer-facing supplement generation;
- claim verification;
- final result-brief refresh.

For a quick command preview:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --dry-run
```

For a faster local smoke that skips the multi-seed sweep, PDF compile,
submission packaging, and PDF-dependent claim verification:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --skip-multiseed --skip-pdf
```

Run a single named step:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --step claim_verification
```

## OpenAI Audit Boundary

The main pipeline is API-free. The current 12-person OpenAI audit is cached under
`cache/api_responses/`. To verify that no audit calls are missing:

```bash
conda run -n cross_linkage python src/openai_audit.py \
  --model gpt-5.4-nano \
  --max-personas 12 \
  --max-calls 1 \
  --tasks doc-local,aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction \
  --plan-only
```

Expected current result: `planned_calls=120`, `cached_calls=120`, and
`missing_or_dependent_calls=0`.

The paper-facing GPT-5.5 auxiliary-matching audit is also cached:

```bash
conda run -n cross_linkage python src/openai_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --run-name gpt55_48p \
  --max-personas 48 \
  --tiers T2,T3 \
  --max-calls 300 \
  --tasks aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c5_linkguard,c6_aggressive_redaction \
  --reasoning-effort none \
  --aux-compact-output \
  --aux-max-output-tokens 400 \
  --plan-only
```

Expected current result: `planned_calls=240`, `cached_calls=240`, and
`missing_or_dependent_calls=0`.

The GPT-5.5 document-local anonymization baseline and auxiliary-matching evaluation
are cached:

```bash
conda run -n cross_linkage python src/openai_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --run-name gpt55_doclocal_24p \
  --doc-local-condition c4_openai_doc_local_gpt55_24p \
  --max-personas 24 \
  --tiers T2,T3 \
  --max-calls 300 \
  --tasks doc-local,aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local_gpt55_24p,c5_linkguard,c6_aggressive_redaction \
  --reasoning-effort none \
  --aux-compact-output \
  --aux-max-output-tokens 400 \
  --plan-only
```

Expected current result: `planned_calls=240`, `cached_calls=240`, and
`missing_or_dependent_calls=0`.

The GPT-5.5 qualitative evidence-extraction audit is cached:

```bash
conda run -n cross_linkage python src/openai_evidence_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --run-name gpt55_evidence_24p \
  --cases-per-bucket 8 \
  --max-calls 24 \
  --reasoning-effort none \
  --max-output-tokens 650 \
  --plan-only
```

Expected current result: `planned_calls=24`, `cached_calls=24`, and
`missing_calls=0`.

The optional GPT-5.5 RAG-generation audit has a compact 2-person pilot cached,
but the full 12-person run is not part of the paper claims unless the remaining
calls are explicitly approved:

```bash
conda run -n cross_linkage python src/openai_rag_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --run-name gpt55_rag_12t3 \
  --max-personas 12 \
  --tier T3 \
  --max-calls 60 \
  --reasoning-effort none \
  --max-output-tokens 250 \
  --plan-only
```

Expected pre-approval result after the compact pilot: `planned_calls=60`,
`cached_calls=10`, and `missing_calls=50`.

## Verification Gate

The claim verifier checks that manuscript numbers, generated tables, PDFs, the
clean submission bundle, reviewer-facing supplement, and venue upload checklist
match the source artifacts:

```bash
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Expected current result: `checks=356 failures=0`.

The verifier writes:

- `results/claim_verification.md`
- `results/claim_verification.json`

The compiled manuscript should be:

- `paper/short_paper.pdf`
- 4 pages
- `paper/colm2026_submission.pdf`
- 8 pages in the official COLM 2026 submission template
- `submission/colm2026_submission.pdf`
- `submission/colm2026_submission_source.zip`
- `submission/submission_manifest.json`
- `supplement/SUPPLEMENT_INDEX.md`
- `supplement/benchmark_card.md`
- `supplement/noisy_style_examples.md`
- `supplement/reproducibility_checklist.md`
- `supplement/claim_trace.md`
- `SUBMISSION_UPLOAD_CHECKLIST.md`
- clean-room source compile recorded as passed in `submission/submission_manifest.json`
- no unresolved references, rerun warnings, undefined references, or overfull boxes
  in `paper/short_paper.log` or `paper/colm2026_submission.log`.
