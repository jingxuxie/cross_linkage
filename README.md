# Cross-Document Linkage Sprint

This repository contains a first-pass implementation of the sprint experiment in
`cross_document_linkage_workshop_paper_plan.md`.

Install dependencies in the existing environment:

```bash
conda run -n cross_linkage python -m pip install -r requirements.txt
conda run -n cross_linkage python -m spacy download en_core_web_sm
```

Run the local benchmark:

```bash
conda run -n cross_linkage python src/crossdoc_pipeline.py --config configs/sprint.yaml all
```

Validate generated benchmark artifacts:

```bash
conda run -n cross_linkage python src/validate_benchmark.py --config configs/sprint.yaml
```

Reproduce the no-API result package end to end:

```bash
conda run -n cross_linkage python src/reproduce_no_api.py
```

See `REPRODUCE_RESULTS.md` for faster smoke commands, the cached OpenAI audit
boundary, and the claim-verification gate. See `SUBMISSION_READINESS.md` for the
current claim/caveat checklist before upload, and `SUBMISSION_UPLOAD_CHECKLIST.md`
for the venue-specific upload steps.

Run the LinkGuard target-k sensitivity experiment:

```bash
conda run -n cross_linkage python src/linkguard_sensitivity.py --config configs/sprint.yaml --target-ks 1,2,3,5,8,12,20
```

Run the no-API multi-seed robustness sweep:

```bash
conda run -n cross_linkage python src/multiseed_sweep.py \
  --config configs/sprint.yaml \
  --seeds 20260627,20260628,20260629 \
  --out-dir results/multiseed
```

Run the no-API auxiliary candidate-pool sensitivity sweep:

```bash
conda run -n cross_linkage python src/candidate_sensitivity.py \
  --config configs/sprint.yaml \
  --candidate-sizes 10,20,50
```

Run the no-API local attacker-family sensitivity sweep:

```bash
conda run -n cross_linkage python src/attack_sensitivity.py --config configs/sprint.yaml
```

Generate a no-API residual-match analysis for LinkGuard:

```bash
conda run -n cross_linkage python src/linkguard_failure_analysis.py --config configs/sprint.yaml
```

Run the no-API body-only utility stress test:

```bash
conda run -n cross_linkage python src/utility_stress.py --config configs/sprint.yaml
```

Run the no-API profile-query RAG exposure diagnostic:

```bash
conda run -n cross_linkage python src/rag_exposure.py --config configs/sprint.yaml
```

Run the no-API noisy synthetic style stress test:

```bash
conda run -n cross_linkage python src/noisy_style_stress.py --config configs/sprint.yaml
```

Run the small cached OpenAI audit. This uses synthetic data only and should stay
capped. For live calls, set `OPENAI_API_KEY` or pass `--api-key-file`:

```bash
conda run -n cross_linkage python src/openai_audit.py \
  --model auto \
  --max-personas 12 \
  --max-calls 70 \
  --tasks doc-local,aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction
```

Regenerate paper-facing tables, figures, and the result brief:

```bash
conda run -n cross_linkage python src/make_paper_assets.py --config configs/sprint.yaml
```

Compile the current short-paper draft:

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error short_paper.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex
```

Build the clean COLM submission bundle:

```bash
conda run -n cross_linkage python src/build_submission_package.py
```

Build the reviewer-facing supplement:

```bash
conda run -n cross_linkage python src/make_supplement.py --config configs/sprint.yaml
```

Verify that paper claims, PDFs, and the submission bundle match generated artifacts:

```bash
conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml
```

Main outputs:

- `data/personas.jsonl`
- `data/original_docs.jsonl`
- `data/auxiliary_profiles.jsonl`
- `data/transformed/*.jsonl`
- `results/main_results.csv`
- `results/main_results.md`
- `results/benchmark_validation.md`
- `results/attribute_leakage_rows.csv`
- `results/by_tier.csv`
- `results/ablation.csv`
- `results/linkguard_sensitivity.csv`
- `results/linkguard_sensitivity_field_rows.csv`
- `results/candidate_sensitivity.csv`
- `results/attack_sensitivity.csv`
- `results/linkguard_failure_analysis.md`
- `results/utility_stress.csv`
- `results/rag_exposure.csv`
- `results/rag_exposure_by_tier.csv`
- `results/noisy_style_stress/noisy_style_stress.md`
- `results/noisy_style_stress/noisy_style_results.csv`
- `results/claim_verification.md`
- `results/multiseed/multiseed_summary.md`
- `results/openai_aux_match_summary.csv`
- `results/paper_ready_summary.md`
- `results/privacy_utility.png`
- `results/research_notes.md`
- `paper/tables/*.tex`
- `paper/figures/*.png`
- `paper/short_paper.tex`
- `paper/short_paper.pdf`
- `paper/colm2026_submission.tex`
- `paper/colm2026_submission.pdf`
- `paper/colm2026_conference.sty`
- `paper/colm2026_conference.bst`
- `submission/colm2026_submission.pdf`
- `submission/colm2026_submission_source.zip`
- `submission/submission_manifest.json`
- `submission/submission_manifest.md`
- `supplement/SUPPLEMENT_INDEX.md`
- `supplement/benchmark_card.md`
- `supplement/noisy_style_examples.md`
- `supplement/reproducibility_checklist.md`
- `supplement/claim_trace.md`
- `supplement/supplement_manifest.json`
- `SUBMISSION_UPLOAD_CHECKLIST.md`
- `REPRODUCE_RESULTS.md`
- `SUBMISSION_READINESS.md`

The current pipeline is API-free by default. It uses deterministic synthetic
personas, varied-template and noisy-style synthetic documents, local transformations, TF-IDF and
field-aware linkage attacks, auxiliary-profile matching, Presidio-based PII redaction, and local utility
classifiers. This keeps the first iteration fast and cheap. OpenAI calls are
isolated in `src/openai_audit.py`, cached under `cache/api_responses/`, and
guarded by `--max-calls`.
