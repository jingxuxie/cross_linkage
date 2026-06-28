# Venue Upload Checklist

Verified against the official workshop page on 2026-06-27.

## Venue Facts

- Venue: Workshop on Responsibly Enabling Data for Foundation Models at COLM 2026.
- Official workshop page: `https://re-data-colm2026.github.io/`.
- Submission system: OpenReview, linked from the workshop page.
- Template: COLM 2026 template, linked from the workshop page.
- Paper type: short paper.
- Page limit: up to 4 pages for short papers.
- Deadline: June 28, 2026 at 23:59 AoE.
- Accepted papers are non-archival.
- Concurrent submissions are allowed.

## Upload Targets

Primary paper PDF:

- `submission/colm2026_submission.pdf`

Source package:

- `submission/colm2026_submission_source.zip`

Optional reviewer-facing supplement:

- `supplement/SUPPLEMENT_INDEX.md`
- `supplement/benchmark_card.md`
- `supplement/noisy_style_examples.md`
- `supplement/reproducibility_checklist.md`
- `supplement/claim_trace.md`
- `supplement/supplement_manifest.json`

## Pre-Upload Commands

Run from the repository root:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py --dry-run
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error short_paper.tex)
(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex)
conda run -n cross_linkage python src/build_submission_package.py
conda run -n cross_linkage python src/make_supplement.py --config configs/sprint.yaml
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Required status:

- Claim verifier reports zero failures.
- `paper/short_paper.pdf` has 4 pages.
- `paper/colm2026_submission.pdf` has 4 pages.
- `submission/colm2026_submission.pdf` has 4 pages.
- `submission/submission_manifest.json` records `checks_passed: true`.
- `supplement/supplement_manifest.json` lists all supplement file hashes.
- LaTeX logs have no unresolved references, rerun warnings, undefined citations, or overfull boxes.
- No local filesystem paths appear in the submission package or supplement.

## Anonymity And Content Checks

- The COLM PDF is built with `\usepackage[submission]{colm2026_conference}`.
- `pdfinfo submission/colm2026_submission.pdf` has blank author metadata.
- `pdftotext -layout submission/colm2026_submission.pdf -` contains the anonymous submission header.
- The paper contains no author names, acknowledgments, repository URLs, local filesystem paths, API keys, or institution-specific self-identifying text.
- The project uses synthetic personas only; do not upload real data.
- The OpenAI audit is cached and should be described as small corroborating evidence, not the main quantitative result.

## Final Manual Upload Steps

1. Log in to the OpenReview page linked from the official workshop site.
2. Upload `submission/colm2026_submission.pdf` as the paper PDF.
3. If the form permits source or supplementary material, upload `submission/colm2026_submission_source.zip` and the `supplement/` files according to the form fields.
4. Use the title from `paper/colm2026_submission.tex`.
5. Use the abstract from `paper/colm2026_submission.tex`.
6. Before submitting, preview the PDF in OpenReview and confirm the rendered first page is anonymous and 4 pages total.
