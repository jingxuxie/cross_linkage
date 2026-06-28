# Submission Readiness Audit

This file tracks the current paper package for the cross-document linkage project.

## Current Package Status

- Full working draft: `paper/short_paper.tex`
- Full working-draft PDF: `paper/short_paper.pdf`
- Official COLM-template submission draft: `paper/colm2026_submission.tex`
- Official COLM-template submission PDF: `paper/colm2026_submission.pdf`
- Clean submission PDF: `submission/colm2026_submission.pdf`
- Clean submission source zip: `submission/colm2026_submission_source.zip`
- Submission package manifest: `submission/submission_manifest.json`
- Reviewer supplement index: `supplement/SUPPLEMENT_INDEX.md`
- Benchmark card: `supplement/benchmark_card.md`
- Claim trace: `supplement/claim_trace.md`
- Venue upload checklist: `SUBMISSION_UPLOAD_CHECKLIST.md`
- Result brief: `results/paper_ready_summary.md`
- Noisy synthetic style stress test: `results/noisy_style_stress/noisy_style_stress.md`
- Claim verifier: `results/claim_verification.md`
- API provenance manifest: `results/api_audit_provenance.md`
- Optional RAG-generation budget: `results/openai_gpt55_rag_12t3_budget.md`
- Reproduction guide: `REPRODUCE_RESULTS.md`
- Qualitative example: `results/qualitative_examples.md`
- Official COLM style files: `paper/colm2026_conference.sty`, `paper/colm2026_conference.bst`

Current verified state:

- 120 synthetic personas and 480 synthetic documents.
- 96 held-out personas for the main local evaluation.
- No real people, public profiles, social-media posts, patient records, legal records, or customer records.
- Main claim verifier: `checks=429 failures=0`.
- Current generic PDF length: 4 pages.
- Current official COLM-template PDF length: 8 pages.
- Noisy-style stress corpus: 480 synthetic rerendered documents, mean template similarity 0.306.
- Reviewer-facing supplement: generated and hash-manifested.
- Venue-specific upload checklist: generated and verifier-covered.
- Submission source package clean-room compile: passed.
- GPT-5.5 audit is cached; the default reproduction path remains API-free.
- API provenance manifest records run names, cache completeness, token usage, claim boundaries, and `store=False`.
- Optional RAG-generation completion is budgeted as five 10-call batches and remains outside paper claims until approved and cached.

Venue facts verified from the workshop site on 2026-06-28:

- Short papers are up to 4 pages.
- Full papers are up to 8 pages.
- Papers should follow the COLM 2026 template.
- Submissions are through OpenReview with a June 28, 2026 AoE deadline.
- Accepted papers are non-archival, and concurrent submissions are allowed.

## Claims Ready To Use

1. Direct PII redaction leaves strong cross-document auxiliary matching risk.
2. Presidio-style document PII redaction still leaves corpus-level quasi-identifier risk.
3. Consistent pseudonyms act as stable cross-document linkage handles.
4. Document-local anonymization misses combinations that are risky at corpus scale.
5. LinkGuard improves the synthetic privacy-utility frontier over blanket aggressive redaction.
6. Field-aware stress testing exposes residual LinkGuard risk, but the risk is controllable by increasing target `k`.
7. Profile-query retrieval can expose high-linkage transformed records even after direct PII is removed.
8. A noisy-style synthetic rerendering preserves the main privacy-utility ordering.

## Caveats To Keep Explicit

- The benchmark is synthetic, so external validity remains limited even with the noisy-style stress test.
- LinkGuard is a heuristic corpus-aware generalization method, not a formal privacy guarantee.
- Utility is measured with issue labels, task retrieval, and lightweight fact checks, not full downstream deployment utility.
- The GPT-5.5 audit is a time-stamped stress audit and should be described as corroborating evidence, not the main quantitative result.
- The GPT-5.5 RAG-generation audit has only a compact 2-person pilot; do not report generation metrics unless the full live run is explicitly approved and verified.
- The field-weighted attacker shows residual structured-context risk at `k=5`; the paper should not claim complete anonymization.

## Pre-Submission Checklist

Run these from the repository root before final upload:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --dry-run
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error short_paper.tex)
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex)
conda run -n cross_linkage python src/build_submission_package.py
conda run -n cross_linkage python src/make_supplement.py --config configs/sprint.yaml
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Then check:

- `results/claim_verification.md` reports zero failures.
- `paper/colm2026_submission.pdf` is the intended 8-page target-venue PDF.
- `submission/colm2026_submission.pdf` and `submission/colm2026_submission_source.zip` are present.
- `submission/submission_manifest.json` records `checks_passed: true`.
- `supplement/supplement_manifest.json` records the generated supplement file hashes.
- `SUBMISSION_UPLOAD_CHECKLIST.md` matches the current upload artifacts and verified venue facts.
- `paper/short_paper.log` and `paper/colm2026_submission.log` have no unresolved references, rerun warnings, undefined references, or overfull boxes.
- The official anonymity policy and artifact policy have been verified against the venue website.
- Author names, acknowledgments, and repository links are handled according to the venue anonymity policy.

## High-Value Follow-Ups

If there is time for one more bounded improvement, prioritize final title/abstract polish. If there is limited time, keep the current package stable and avoid broad experiment changes.
