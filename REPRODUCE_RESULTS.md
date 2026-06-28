# Reproducing the Result Package

This project has two reproducibility paths:

1. A no-API path that regenerates the synthetic corpus, deterministic attacks,
   robustness checks, paper tables, figures, PDFs, submission bundle, reviewer supplement, and claim verifier.
2. A cached OpenAI audit path that verifies the 12-person audit plan is fully
   cached without making new API calls.

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

## Verification Gate

The claim verifier checks that manuscript numbers, generated tables, PDFs, the
clean submission bundle, reviewer-facing supplement, and venue upload checklist
match the source artifacts:

```bash
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Expected current result: `checks=318 failures=0`.

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
