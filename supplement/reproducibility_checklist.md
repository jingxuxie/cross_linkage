# Reproducibility Checklist

Run from the repository root.

## Full No-API Path

```bash
conda run -n cross_linkage python src/reproduce_no_api.py
```

This runs the synthetic benchmark, validation, robustness checks, noisy-style stress test, cached-only OpenAI plan check, table generation, PDF compilation, submission packaging, supplement generation, and claim verification.

## Fast Preview

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --dry-run
```

## Core Gates

```bash
conda run -n cross_linkage python src/validate_benchmark.py --config configs/sprint.yaml
conda run -n cross_linkage python src/noisy_style_stress.py --config configs/sprint.yaml
conda run -n cross_linkage python src/make_paper_assets.py --config configs/sprint.yaml
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error short_paper.tex)
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex)
conda run -n cross_linkage python src/build_submission_package.py
conda run -n cross_linkage python src/make_supplement.py --config configs/sprint.yaml
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Expected gate status: zero benchmark-validation failures, four-page PDFs, clean submission-package compile, and zero claim-verifier failures.

## API Boundary

The default path is API-free. The OpenAI audit is cached and can be checked without making calls:

```bash
conda run -n cross_linkage python src/openai_audit.py --model gpt-5.4-nano --max-personas 12 --max-calls 1 --tasks doc-local,aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction --plan-only
```

Expected cached audit status: `planned_calls=120`, `cached_calls=120`, `missing_or_dependent_calls=0`.
