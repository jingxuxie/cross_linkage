#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from crossdoc_pipeline import dataframe_to_markdown, load_config, make_paths, read_jsonl


SUPPLEMENT_FILES = [
    "SUPPLEMENT_INDEX.md",
    "benchmark_card.md",
    "noisy_style_examples.md",
    "reproducibility_checklist.md",
    "claim_trace.md",
    "supplement_manifest.json",
]


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row(df: pd.DataFrame, condition: str) -> pd.Series:
    match = df[df["condition"] == condition]
    if match.empty:
        raise KeyError(condition)
    return match.iloc[0]


def compact_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition",
        "pair_f1",
        "aux_top1",
        "aux_top3",
        "attr_exact_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
        "edit_ratio",
    ]
    return df[cols].copy()


def risk_tier_counts(personas: list[dict[str, Any]]) -> pd.DataFrame:
    rows = (
        pd.DataFrame(personas)
        .groupby("risk_tier", sort=True)
        .size()
        .reset_index(name="n_personas")
    )
    return rows


def write_index(out_dir: Path) -> None:
    lines = [
        "# CrossDoc-PrivacyBench Supplement",
        "",
        "This supplement is generated from the current result artifacts. It contains no real-person data.",
        "",
        "## Files",
        "",
        "- `benchmark_card.md`: dataset, threat-model, ethics, metrics, and intended-use card.",
        "- `noisy_style_examples.md`: side-by-side synthetic noisy-style examples.",
        "- `reproducibility_checklist.md`: command checklist and expected artifact gates.",
        "- `claim_trace.md`: paper claims mapped to result artifacts.",
        "- `supplement_manifest.json`: file sizes and SHA-256 hashes.",
        "",
    ]
    (out_dir / "SUPPLEMENT_INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def write_benchmark_card(
    out_dir: Path,
    cfg: dict[str, Any],
    personas: list[dict[str, Any]],
    docs: list[dict[str, Any]],
    main: pd.DataFrame,
    noisy_diag: pd.Series,
) -> None:
    tier_counts = risk_tier_counts(personas)
    domain_counts = (
        pd.DataFrame(docs)
        .groupby("domain", sort=True)
        .size()
        .reset_index(name="n_documents")
    )
    lines = [
        "# Benchmark Card",
        "",
        "## Name",
        "",
        "CrossDoc-PrivacyBench.",
        "",
        "## Purpose",
        "",
        "Evaluate whether document-level de-identification leaves synthetic multi-document corpora linkable through repeated quasi-identifiers.",
        "",
        "## Data Stance",
        "",
        "- Synthetic-only benchmark.",
        "- No real people, public profiles, social-media posts, patient records, legal records, customer records, or web-searched records.",
        "- Direct identifiers are generated placeholders used only to test transformations.",
        "- Auxiliary profiles and decoys are generated from the same synthetic schema.",
        "",
        "## Corpus",
        "",
        f"- Personas: {len(personas)}.",
        f"- Documents: {len(docs)}.",
        f"- Documents per persona: {cfg['docs_per_persona']}.",
        f"- Held-out personas for main evaluation: 96.",
        f"- Domains: {', '.join(cfg['domains'])}.",
        f"- Candidate set size: {cfg['candidate_set_size']}.",
        f"- LinkGuard target k: {cfg['target_k']}.",
        "",
        "### Risk Tiers",
        "",
        dataframe_to_markdown(tier_counts, floatfmt=".0f"),
        "",
        "### Domains",
        "",
        dataframe_to_markdown(domain_counts, floatfmt=".0f"),
        "",
        "## Transformations",
        "",
        "- C1 direct redaction: masks synthetic direct identifiers.",
        "- C1b Presidio redaction: off-the-shelf PII detection plus direct synthetic ID masking.",
        "- C2 consistent pseudonymization: stable per-person handles.",
        "- C3 per-document pseudonymization: unstable document-local handles.",
        "- C4 document-local proxy: local quasi-identifier generalization.",
        "- C5 LinkGuard: corpus-aware quasi-identifier generalization.",
        "- C6 aggressive redaction: broad direct and quasi-identifier suppression.",
        "",
        "## Metrics",
        "",
        "- Privacy: pairwise linkage F1, fixed-K clustering, auxiliary top-1/top-3/MRR, exact quasi-identifier recovery, profile-query RAG exposure.",
        "- Utility: domain/issue classification, retrieval Recall@5, fact preservation, body-only utility stress score.",
        "- Robustness: multi-seed sweep, candidate-pool sensitivity, attacker-family sensitivity, target-k sensitivity, noisy-style synthetic rerendering.",
        "",
        "## Main Result Snapshot",
        "",
        dataframe_to_markdown(compact_metric_table(main), floatfmt=".3f"),
        "",
        "## Noisy-Style Stress Metadata",
        "",
        f"- Rerendered documents: {int(noisy_diag['n_docs'])}.",
        f"- Mean template similarity: {fmt(noisy_diag['mean_template_similarity'])}.",
        f"- Mean type-token ratio: {fmt(noisy_diag['mean_type_token_ratio'])}.",
        f"- Unique first lines: {int(noisy_diag['unique_first_lines'])}.",
        "",
        "## Intended Use",
        "",
        "Defensive auditing, method comparison, and paper reproduction for corpus-level text privacy evaluation.",
        "",
        "## Out-of-Scope Uses",
        "",
        "Do not use this benchmark to make claims about real-person re-identification rates, deployment safety, legal compliance, or formal anonymity guarantees.",
        "",
        "## Limitations",
        "",
        "- Synthetic and schema-controlled.",
        "- Noisy-style stress improves style variation but does not substitute for authorized real-data validation.",
        "- LinkGuard is heuristic and has no formal privacy proof.",
        "- Utility metrics are lightweight proxies rather than downstream product evaluations.",
        "",
    ]
    (out_dir / "benchmark_card.md").write_text("\n".join(lines), encoding="utf-8")


def doc_by_id(rows: list[dict[str, Any]], doc_id: str) -> dict[str, Any]:
    for row_data in rows:
        if row_data["doc_id"] == doc_id:
            return row_data
    raise KeyError(doc_id)


def write_noisy_examples(out_dir: Path, root: Path) -> None:
    doc_id = "P0002_D01"
    noisy_dir = root / "results" / "noisy_style_stress"
    sources = [
        ("N0 noisy original", noisy_dir / "transformed" / "noisy_original.jsonl"),
        ("C1 direct redaction", noisy_dir / "transformed" / "c1_direct_redaction.jsonl"),
        ("C1b Presidio redaction", noisy_dir / "transformed" / "c1b_presidio_redaction.jsonl"),
        ("C4 doc-local proxy", noisy_dir / "transformed" / "c4_doc_local_anon.jsonl"),
        ("C5 LinkGuard", noisy_dir / "transformed" / "c5_linkguard.jsonl"),
        ("C6 aggressive redaction", noisy_dir / "transformed" / "c6_aggressive_redaction.jsonl"),
    ]
    lines = [
        "# Noisy-Style Synthetic Example",
        "",
        f"Synthetic document: `{doc_id}`.",
        "",
        "This example is synthetic and intended only for defensive privacy evaluation.",
        "",
    ]
    for label, path in sources:
        doc = doc_by_id(read_jsonl(path), doc_id)
        lines.extend([f"## {label}", "", "```text", doc["text"], "```", ""])
    (out_dir / "noisy_style_examples.md").write_text("\n".join(lines), encoding="utf-8")


def write_repro_checklist(out_dir: Path) -> None:
    lines = [
        "# Reproducibility Checklist",
        "",
        "Run from the repository root.",
        "",
        "## Full No-API Path",
        "",
        "```bash",
        "conda run -n cross_linkage python src/reproduce_no_api.py",
        "```",
        "",
        "This runs the synthetic benchmark, validation, robustness checks, RAG exposure and context-recovery scans, noisy-style stress test, cached-only OpenAI plan checks, an optional RAG-generation plan check, RAG API budget reporting, API provenance reporting, table generation, PDF compilation, submission packaging, supplement generation, and claim verification.",
        "",
        "## Fast Preview",
        "",
        "```bash",
        "conda run -n cross_linkage python src/reproduce_no_api.py --dry-run",
        "```",
        "",
        "## Core Gates",
        "",
        "```bash",
        "conda run -n cross_linkage python src/validate_benchmark.py --config configs/sprint.yaml",
        "conda run -n cross_linkage python src/corpus_awareness_ablation.py --config configs/sprint.yaml --target-k 5",
        "conda run -n cross_linkage python src/rag_query_sensitivity.py --config configs/sprint.yaml",
        "conda run -n cross_linkage python src/noisy_style_stress.py --config configs/sprint.yaml",
        "conda run -n cross_linkage python src/make_paper_assets.py --config configs/sprint.yaml",
        "(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error short_paper.tex)",
        "(cd paper && latexmk -g -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex)",
        "conda run -n cross_linkage python src/build_submission_package.py",
        "conda run -n cross_linkage python src/make_supplement.py --config configs/sprint.yaml",
        "conda run -n cross_linkage python src/verify_claims.py --config configs/sprint.yaml",
        "```",
        "",
        "Expected gate status: zero benchmark-validation failures, a 4-page short PDF, an 8-page COLM PDF, clean submission-package compile, and zero claim-verifier failures.",
        "",
        "## API Boundary",
        "",
        "The default path is API-free. The legacy OpenAI audit is cached and can be checked without making calls:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/openai_audit.py --config configs/sprint.yaml --model gpt-5.4-nano --max-personas 12 --max-calls 1 --tasks doc-local,aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction --plan-only",
        "```",
        "",
        "Expected legacy cached audit status: `planned_calls=120`, `cached_calls=120`, `missing_or_dependent_calls=0`.",
        "",
        "The paper-facing GPT-5.5 auxiliary-matching audit is cached and can be checked without calls:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/openai_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_48p --max-personas 48 --tiers T2,T3 --max-calls 300 --tasks aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c5_linkguard,c6_aggressive_redaction --reasoning-effort none --aux-compact-output --aux-max-output-tokens 400 --plan-only",
        "```",
        "",
        "Expected GPT-5.5 auxiliary status: `planned_calls=240`, `cached_calls=240`, `missing_or_dependent_calls=0`.",
        "",
        "The GPT-5.5 document-local anonymization baseline and auxiliary-matching evaluation are cached:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/openai_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_doclocal_24p --doc-local-condition c4_openai_doc_local_gpt55_24p --max-personas 24 --tiers T2,T3 --max-calls 300 --tasks doc-local,aux-match --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local_gpt55_24p,c5_linkguard,c6_aggressive_redaction --reasoning-effort none --aux-compact-output --aux-max-output-tokens 400 --plan-only",
        "```",
        "",
        "Expected GPT-5.5 document-local status: `planned_calls=240`, `cached_calls=240`, `missing_or_dependent_calls=0`.",
        "",
        "The GPT-5.5 qualitative evidence-extraction audit is cached:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/openai_evidence_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_evidence_24p --cases-per-bucket 8 --max-calls 24 --reasoning-effort none --max-output-tokens 650 --plan-only",
        "```",
        "",
        "Expected GPT-5.5 evidence status: `planned_calls=24`, `cached_calls=24`, `missing_calls=0`.",
        "",
        "The optional GPT-5.5 RAG-generation audit has a compact 2-person pilot cached, but the full 12-person run is not part of the default paper claims until the remaining calls are explicitly approved:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/openai_rag_audit.py --config configs/sprint.yaml --model gpt-5.5 --run-name gpt55_rag_12t3 --max-personas 12 --tier T3 --max-calls 60 --reasoning-effort none --max-output-tokens 250 --plan-only",
        "```",
        "",
        "Expected pre-approval status after the compact pilot plus first cache-fill batch: `planned_calls=60`, `cached_calls=20`, `missing_calls=40`.",
        "",
        "The RAG API budget report splits the remaining optional RAG-generation calls into small approval units without making API calls:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/rag_api_budget.py --config configs/sprint.yaml",
        "```",
        "",
        "Expected budget boundary: 4 remaining batches, 10 calls per batch, using batch-specific run names that fill the shared response cache.",
        "",
        "The API provenance manifest summarizes run names, cache completeness, token usage, claim status, and the `store=False` protocol without making API calls:",
        "",
        "```bash",
        "conda run -n cross_linkage python src/api_provenance_report.py --config configs/sprint.yaml",
        "```",
        "",
        "Expected manifest boundary: paper-facing GPT-5.5 auxiliary, document-local, and evidence audits are fully cached; the optional 12-person RAG-generation plan remains `20/60` cached and is not a paper claim.",
        "",
    ]
    (out_dir / "reproducibility_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def write_claim_trace(
    out_dir: Path,
    main: pd.DataFrame,
    noisy: pd.DataFrame,
    rag_tier: pd.DataFrame,
    rag_query: pd.DataFrame,
    rag_context_tier: pd.DataFrame,
    sensitivity: pd.DataFrame,
    corpus_awareness: pd.DataFrame,
) -> None:
    direct = row(main, "c1_direct_redaction")
    presidio = row(main, "c1b_presidio_redaction")
    local = row(main, "c4_doc_local_anon")
    linkguard = row(main, "c5_linkguard")
    aggressive = row(main, "c6_aggressive_redaction")
    stable = row(main, "c2_consistent_pseudonym")
    noisy_direct = row(noisy, "c1_direct_redaction")
    noisy_lg = row(noisy, "c5_linkguard")
    noisy_aggressive = row(noisy, "c6_aggressive_redaction")
    field_k5 = sensitivity[sensitivity["target_k"] == 5].iloc[0]
    field_k20 = sensitivity[sensitivity["target_k"] == 20].iloc[0]
    ca_true = corpus_awareness[
        corpus_awareness["condition"] == "ca_true_corpus_linkguard"
    ].iloc[0]
    ca_shuffled = corpus_awareness[
        corpus_awareness["condition"] == "ca_shuffled_corpus_stats"
    ].iloc[0]
    rag_lg = rag_tier[
        (rag_tier["condition"] == "c5_linkguard") & (rag_tier["risk_tier"] == "T3")
    ].iloc[0]
    rag_direct = rag_tier[
        (rag_tier["condition"] == "c1_direct_redaction") & (rag_tier["risk_tier"] == "T3")
    ].iloc[0]
    rag_query_direct_verbose = rag_query[
        (rag_query["condition"] == "c1_direct_redaction")
        & (rag_query["query_type"] == "verbose")
    ].iloc[0]
    rag_query_lg_verbose = rag_query[
        (rag_query["condition"] == "c5_linkguard")
        & (rag_query["query_type"] == "verbose")
    ].iloc[0]
    rag_context_direct = rag_context_tier[
        (rag_context_tier["condition"] == "c1_direct_redaction")
        & (rag_context_tier["risk_tier"] == "T3")
    ].iloc[0]
    rag_context_lg = rag_context_tier[
        (rag_context_tier["condition"] == "c5_linkguard")
        & (rag_context_tier["risk_tier"] == "T3")
    ].iloc[0]
    rows = pd.DataFrame(
        [
            {
                "claim": "Direct PII redaction leaves auxiliary matching risk.",
                "evidence": f"direct Aux@1 {fmt(direct['aux_top1'])}",
                "artifact": "results/main_results.csv",
            },
            {
                "claim": "Presidio-style PII redaction remains linkable.",
                "evidence": f"Presidio Aux@1 {fmt(presidio['aux_top1'])}",
                "artifact": "results/main_results.csv",
            },
            {
                "claim": "Stable pseudonyms create linkage handles.",
                "evidence": f"stable pair F1 {fmt(stable['pair_f1'])}",
                "artifact": "results/main_results.csv",
            },
            {
                "claim": "Document-local anonymization misses corpus-level risk.",
                "evidence": f"doc-local Aux@1 {fmt(local['aux_top1'])}",
                "artifact": "results/main_results.csv",
            },
            {
                "claim": "LinkGuard improves the privacy-utility frontier.",
                "evidence": f"LinkGuard Aux@1 {fmt(linkguard['aux_top1'])}, Issue {fmt(linkguard['issue_acc'])}, Ret@5 {fmt(linkguard['retrieval_recall_at_5'])}; aggressive Issue {fmt(aggressive['issue_acc'])}, Ret@5 {fmt(aggressive['retrieval_recall_at_5'])}",
                "artifact": "results/main_results.csv",
            },
            {
                "claim": "Field-aware stress risk is controllable by target k.",
                "evidence": f"field Aux@1 k=5 {fmt(field_k5['field_aux_top1'])}, k=20 {fmt(field_k20['field_aux_top1'])}",
                "artifact": "results/linkguard_sensitivity.csv",
            },
            {
                "claim": "Corpus co-occurrence statistics matter for LinkGuard planning.",
                "evidence": f"true-corpus k-cover {fmt(ca_true['target_k_coverage'])}, shuffled-stats k-cover {fmt(ca_shuffled['target_k_coverage'])}",
                "artifact": "results/corpus_awareness_ablation.csv",
            },
            {
                "claim": "Profile-query RAG retrieval exposes high-linkage direct-redacted records.",
                "evidence": f"T3 direct Hit@5 {fmt(rag_direct['hit_at_5'])}, LinkGuard Hit@5 {fmt(rag_lg['hit_at_5'])}",
                "artifact": "results/rag_exposure_by_tier.csv",
            },
            {
                "claim": "Generated profile-like queries preserve the RAG exposure ordering.",
                "evidence": f"verbose direct Hit@5 {fmt(rag_query_direct_verbose['hit_at_5'])}, LinkGuard Hit@5 {fmt(rag_query_lg_verbose['hit_at_5'])}",
                "artifact": "results/rag_query_sensitivity.csv",
            },
            {
                "claim": "Retrieved profile-query contexts expose quasi-identifiers under direct baselines.",
                "evidence": f"T3 direct exact fields {fmt(rag_context_direct['exact_fields_recovered'])}, LinkGuard exact/coarse {fmt(rag_context_lg['exact_fields_recovered'])}/{fmt(rag_context_lg['coarse_fields_recovered'])}",
                "artifact": "results/rag_context_recovery_by_tier.csv",
            },
            {
                "claim": "Noisy-style synthetic rerendering preserves the ordering.",
                "evidence": f"noisy direct Aux@1 {fmt(noisy_direct['aux_top1'])}, LinkGuard Aux@1 {fmt(noisy_lg['aux_top1'])}, aggressive Issue/Ret@5 {fmt(noisy_aggressive['issue_acc'])}/{fmt(noisy_aggressive['retrieval_recall_at_5'])}",
                "artifact": "results/noisy_style_stress/noisy_style_results.csv",
            },
        ]
    )
    lines = [
        "# Claim Trace",
        "",
        "Each row maps a paper-facing claim to the artifact that supports it.",
        "",
        dataframe_to_markdown(rows, floatfmt=".3f"),
        "",
    ]
    (out_dir / "claim_trace.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(out_dir: Path) -> None:
    manifest: dict[str, Any] = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [],
    }
    for name in SUPPLEMENT_FILES:
        if name == "supplement_manifest.json":
            continue
        path = out_dir / name
        manifest["files"].append(
            {
                "path": f"supplement/{name}",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest_path = out_dir / "supplement_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--out-dir", default="supplement")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    out_dir = paths.root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    personas = read_jsonl(paths.data / "personas.jsonl")
    docs = read_jsonl(paths.data / "original_docs.jsonl")
    main_results = pd.read_csv(paths.results / "main_results.csv")
    noisy = pd.read_csv(paths.results / "noisy_style_stress" / "noisy_style_results.csv")
    noisy_diag = pd.read_csv(paths.results / "noisy_style_stress" / "noisy_style_diagnostic_summary.csv").iloc[0]
    rag_tier = pd.read_csv(paths.results / "rag_exposure_by_tier.csv")
    rag_query = pd.read_csv(paths.results / "rag_query_sensitivity.csv")
    rag_context_tier = pd.read_csv(paths.results / "rag_context_recovery_by_tier.csv")
    sensitivity = pd.read_csv(paths.results / "linkguard_sensitivity.csv")
    corpus_awareness = pd.read_csv(paths.results / "corpus_awareness_ablation.csv")

    write_index(out_dir)
    write_benchmark_card(out_dir, cfg, personas, docs, main_results, noisy_diag)
    write_noisy_examples(out_dir, paths.root)
    write_repro_checklist(out_dir)
    write_claim_trace(
        out_dir,
        main_results,
        noisy,
        rag_tier,
        rag_query,
        rag_context_tier,
        sensitivity,
        corpus_awareness,
    )
    write_manifest(out_dir)
    print(out_dir / "SUPPLEMENT_INDEX.md")


if __name__ == "__main__":
    main()
