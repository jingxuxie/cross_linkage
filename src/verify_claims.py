#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from crossdoc_pipeline import dataframe_to_markdown, load_config, read_jsonl, split_personas


LOCAL_PATH_MARKERS = ("/home/" + "eston", "colm_" + "workshop")
EXPECTED_SHORT_PAGES = 4
EXPECTED_COLM_PAGES = 8


@dataclass
class Check:
    check_id: str
    status: str
    detail: str
    source: str
    expected: str = ""
    observed: str = ""


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def add_check(
    checks: list[Check],
    check_id: str,
    ok: bool,
    detail: str,
    source: str,
    expected: str = "",
    observed: str = "",
) -> None:
    checks.append(
        Check(
            check_id=check_id,
            status="PASS" if ok else "FAIL",
            detail=detail,
            source=source,
            expected=expected,
            observed=observed,
        )
    )


def contains(text: str, fragment: str) -> bool:
    return fragment in text


def has_local_path_marker(text: str) -> bool:
    return any(marker in text for marker in LOCAL_PATH_MARKERS)


def row(df: pd.DataFrame, condition: str) -> pd.Series:
    match = df[df["condition"] == condition]
    if match.empty:
        raise KeyError(condition)
    return match.iloc[0]


def weighted_openai(summary: pd.DataFrame, condition: str) -> dict[str, float]:
    group = summary[summary["condition"] == condition]
    n = int(group["n"].sum())
    out = {
        "n": n,
        "top1": float((group["top1"] * group["n"]).sum() / n),
        "top3": float((group["top3"] * group["n"]).sum() / n),
    }
    if "uncertain_rate" in group.columns:
        out["uncertain_rate"] = float((group["uncertain_rate"] * group["n"]).sum() / n)
    return out


def command_text(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_member_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            hashes[name] = hashlib.sha256(archive.read(name)).hexdigest()
    return hashes


def pdf_pages(path: Path) -> int | None:
    try:
        info = command_text(["pdfinfo", str(path)], path.parent)
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
    return int(match.group(1)) if match else None


def pdf_info_field(path: Path, field: str) -> str:
    try:
        info = command_text(["pdfinfo", str(path)], path.parent)
    except (OSError, subprocess.CalledProcessError):
        return ""
    match = re.search(rf"^{re.escape(field)}:[ \t]*(.*)$", info, re.MULTILINE)
    return match.group(1).strip() if match else ""


def pdf_text(path: Path) -> str:
    try:
        return command_text(["pdftotext", "-layout", str(path), "-"], path.parent)
    except (OSError, subprocess.CalledProcessError):
        return ""


def log_problem_lines(path: Path) -> list[str]:
    if not path.exists():
        return ["missing log"]
    patterns = [
        "Undefined",
        "undefined references",
        "undefined citations",
        "Overfull",
        "LaTeX Warning",
        "Rerun to get",
        "Rerun to",
        "Citation `",
        "Reference `",
        "Package natbib Warning",
    ]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [
        line
        for line in lines
        if any(pattern in line for pattern in patterns)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--paper", default="paper/short_paper.tex")
    args = parser.parse_args()

    root = Path.cwd()
    cfg = load_config(Path(args.config))
    results_dir = root / cfg["results_dir"]
    paper_dir = root / "paper"
    paper_text = Path(args.paper).read_text(encoding="utf-8")

    checks: list[Check] = []
    required_artifacts = [
        "results/main_results.csv",
        "results/benchmark_validation.csv",
        "results/benchmark_validation.json",
        "results/benchmark_validation.md",
        "results/by_tier.csv",
        "results/aux_match_rows.csv",
        "results/attribute_leakage_rows.csv",
        "results/ablation.csv",
        "results/linkguard_sensitivity.csv",
        "results/linkguard_sensitivity_field_rows.csv",
        "results/corpus_awareness_ablation.csv",
        "results/corpus_awareness_ablation_by_tier.csv",
        "results/corpus_awareness_ablation_log.jsonl",
        "results/corpus_awareness_ablation.md",
        "results/multiseed/claim_summary.csv",
        "results/candidate_sensitivity.csv",
        "results/attack_sensitivity.csv",
        "results/linkguard_failure_analysis.csv",
        "results/utility_stress.csv",
        "results/rag_exposure.csv",
        "results/rag_exposure_rows.csv",
        "results/rag_exposure_by_tier.csv",
        "data/generated_profile_queries.jsonl",
        "results/rag_query_sensitivity.csv",
        "results/rag_query_sensitivity_rows.csv",
        "results/rag_query_sensitivity_by_tier.csv",
        "results/rag_query_sensitivity.md",
        "results/rag_context_recovery.csv",
        "results/rag_context_recovery_rows.csv",
        "results/rag_context_recovery_field_rows.csv",
        "results/rag_context_recovery_by_tier.csv",
        "results/rag_context_recovery.md",
        "results/noisy_style_stress/noisy_style_results.csv",
        "results/noisy_style_stress/noisy_style_compact_results.csv",
        "results/noisy_style_stress/noisy_style_diagnostic_summary.csv",
        "results/noisy_style_stress/noisy_style_stress.md",
        "results/noisy_style_stress/noisy_original_docs.jsonl",
        "results/noisy_style_stress/transformed/c1_direct_redaction.jsonl",
        "results/noisy_style_stress/transformed/c1b_presidio_redaction.jsonl",
        "results/noisy_style_stress/transformed/c4_doc_local_anon.jsonl",
        "results/noisy_style_stress/transformed/c5_linkguard.jsonl",
        "results/noisy_style_stress/transformed/c6_aggressive_redaction.jsonl",
        "data/transformed/c4_openai_doc_local_gpt55_24p.jsonl",
        "results/openai_aux_match_summary.csv",
        "results/openai_audit_plan.csv",
        "results/openai_gpt55_48p_aux_match_rows.csv",
        "results/openai_gpt55_48p_aux_match_summary.csv",
        "results/openai_gpt55_48p_audit_plan.csv",
        "results/openai_gpt55_48p_audit_notes.md",
        "results/openai_gpt55_48p_audit_usage.csv",
        "results/openai_gpt55_doclocal_24p_aux_match_rows.csv",
        "results/openai_gpt55_doclocal_24p_aux_match_summary.csv",
        "results/openai_gpt55_doclocal_24p_audit_plan.csv",
        "results/openai_gpt55_doclocal_24p_audit_notes.md",
        "results/openai_gpt55_doclocal_24p_audit_usage.csv",
        "results/openai_gpt55_evidence_24p_evidence_rows.csv",
        "results/openai_gpt55_evidence_24p_evidence_summary.csv",
        "results/openai_gpt55_evidence_24p_evidence_summary.md",
        "results/openai_gpt55_evidence_24p_evidence_signal_counts.csv",
        "results/openai_gpt55_evidence_24p_audit_plan.csv",
        "results/openai_gpt55_evidence_24p_audit_notes.md",
        "results/openai_gpt55_evidence_24p_audit_usage.csv",
        "results/openai_gpt55_rag_12t3_audit_plan.csv",
        "results/openai_gpt55_rag_12t3_audit_plan.md",
        "results/openai_gpt55_rag_12t3_audit_notes.md",
        "results/openai_gpt55_rag_12t3_audit_usage.csv",
        "results/openai_gpt55_rag_12t3_rag_generation_rows.csv",
        "results/openai_gpt55_rag_12t3_rag_generation_summary.csv",
        "results/openai_gpt55_rag_12t3_rag_generation_summary.md",
        "results/openai_gpt55_rag_compact_pilot_2t3_audit_notes.md",
        "results/openai_gpt55_rag_compact_pilot_2t3_audit_plan.csv",
        "results/openai_gpt55_rag_compact_pilot_2t3_audit_plan.md",
        "results/openai_gpt55_rag_compact_pilot_2t3_audit_usage.csv",
        "results/openai_gpt55_rag_compact_pilot_2t3_rag_generation_rows.csv",
        "results/openai_gpt55_rag_compact_pilot_2t3_rag_generation_summary.csv",
        "results/openai_gpt55_rag_compact_pilot_2t3_rag_generation_summary.md",
        "results/openai_gpt55_rag_12t3_budget.csv",
        "results/openai_gpt55_rag_12t3_budget.md",
        "results/api_audit_provenance.csv",
        "results/api_audit_provenance.md",
        "results/paper_ready_summary.md",
        "SUBMISSION_UPLOAD_CHECKLIST.md",
        "paper/tables/paper_main_results.tex",
        "paper/tables/linkguard_sensitivity.tex",
        "paper/tables/corpus_awareness_ablation.csv",
        "paper/tables/corpus_awareness_ablation.tex",
        "paper/tables/tier_aux_results.tex",
        "paper/tables/openai_aux_audit.tex",
        "paper/tables/gpt55_aux_audit.tex",
        "paper/tables/gpt55_aux_bootstrap_ci.csv",
        "paper/tables/gpt55_doclocal_audit.tex",
        "paper/tables/gpt55_doclocal_bootstrap_ci.csv",
        "paper/tables/gpt55_evidence_signals.tex",
        "paper/tables/rag_exposure_t3.tex",
        "paper/tables/rag_query_sensitivity.csv",
        "paper/tables/rag_query_sensitivity.tex",
        "paper/tables/rag_context_recovery_t3.tex",
        "paper/tables/gpt55_rag_generation_audit.csv",
        "paper/tables/gpt55_rag_generation_audit.tex",
        "paper/tables/noisy_style_stress.tex",
        "paper/short_paper.pdf",
        "paper/colm2026_submission.tex",
        "paper/colm2026_submission.pdf",
        "paper/colm2026_conference.sty",
        "paper/colm2026_conference.bst",
        "paper/natbib.sty",
        "paper/fancyhdr.sty",
        "paper/math_commands.tex",
        "submission/colm2026_submission.pdf",
        "submission/colm2026_source/colm2026_submission.tex",
        "submission/colm2026_source/colm2026_conference.sty",
        "submission/colm2026_source/colm2026_conference.bst",
        "submission/colm2026_source/natbib.sty",
        "submission/colm2026_source/fancyhdr.sty",
        "submission/colm2026_source/math_commands.tex",
        "submission/colm2026_source/README_SUBMISSION_PACKAGE.md",
        "submission/colm2026_submission_source.zip",
        "submission/submission_manifest.json",
        "submission/submission_manifest.md",
        "supplement/SUPPLEMENT_INDEX.md",
        "supplement/benchmark_card.md",
        "supplement/noisy_style_examples.md",
        "supplement/reproducibility_checklist.md",
        "supplement/claim_trace.md",
        "supplement/supplement_manifest.json",
    ]
    rag_batch_run_names = []
    for plan_path in sorted(results_dir.glob("openai_gpt55_rag_12t3_batch*_audit_plan.csv")):
        match = re.search(r"openai_(gpt55_rag_12t3_batch\d+)_audit_plan\.csv$", plan_path.name)
        if not match:
            continue
        run_name = match.group(1)
        rag_batch_run_names.append(run_name)
        required_artifacts.extend(
            [
                f"results/openai_{run_name}_audit_notes.md",
                f"results/openai_{run_name}_audit_plan.csv",
                f"results/openai_{run_name}_audit_plan.md",
                f"results/openai_{run_name}_audit_usage.csv",
                f"results/openai_{run_name}_rag_generation_rows.csv",
                f"results/openai_{run_name}_rag_generation_summary.csv",
                f"results/openai_{run_name}_rag_generation_summary.md",
            ]
        )
    for rel in required_artifacts:
        path = root / rel
        add_check(
            checks,
            f"artifact:{rel}",
            path.exists() and path.stat().st_size > 0,
            "required artifact exists and is non-empty",
            rel,
            observed=str(path.stat().st_size if path.exists() else 0),
        )

    colm_text = (paper_dir / "colm2026_submission.tex").read_text(encoding="utf-8")
    upload_checklist = (root / "SUBMISSION_UPLOAD_CHECKLIST.md").read_text(encoding="utf-8")
    upload_required_fragments = [
        "Verified against the official workshop page on 2026-06-28",
        "Workshop on Responsibly Enabling Data for Foundation Models at COLM 2026",
        "https://re-data-colm2026.github.io/",
        "Submission system: OpenReview",
        "COLM 2026 template",
        "full paper",
        "up to 8 pages",
        "June 28, 2026 at 23:59 AoE",
        "Accepted papers are non-archival",
        "Concurrent submissions are allowed",
        "submission/colm2026_submission.pdf",
        "submission/colm2026_submission_source.zip",
        "supplement/SUPPLEMENT_INDEX.md",
        "src/reproduce_no_api.py --dry-run",
        "src/build_submission_package.py",
        "src/make_supplement.py",
        "src/verify_claims.py",
        "Claim verifier reports zero failures",
        "paper/short_paper.pdf` has 4 pages",
        "paper/colm2026_submission.pdf` has 8 pages",
        "submission/colm2026_submission.pdf` has 8 pages",
        "submission/submission_manifest.json` records `checks_passed: true`",
        "supplement/supplement_manifest.json` lists all supplement file hashes",
        "blank author metadata",
        "anonymous submission header",
        "no author names",
        "synthetic personas only",
        "Upload `submission/colm2026_submission.pdf`",
    ]
    for fragment in upload_required_fragments:
        add_check(
            checks,
            f"upload_checklist:{fragment[:36]}",
            contains(upload_checklist, fragment),
            f"upload checklist contains required fragment {fragment}",
            "SUBMISSION_UPLOAD_CHECKLIST.md",
            expected=fragment,
            observed=fragment if contains(upload_checklist, fragment) else "missing",
        )
    add_check(
        checks,
        "upload_checklist:no_local_paths",
        not has_local_path_marker(upload_checklist),
        "upload checklist does not expose local filesystem paths",
        "SUBMISSION_UPLOAD_CHECKLIST.md",
        expected="no local paths",
        observed="ok" if not has_local_path_marker(upload_checklist) else "local path found",
    )
    add_check(
        checks,
        "colm_template:submission_mode",
        "\\usepackage[submission]{colm2026_conference}" in colm_text,
        "COLM submission copy uses official submission style option",
        "paper/colm2026_submission.tex",
        expected="submission style",
        observed="present" if "\\usepackage[submission]{colm2026_conference}" in colm_text else "missing",
    )
    add_check(
        checks,
        "colm_template:no_custom_geometry",
        "\\usepackage{geometry}" not in colm_text and "{geometry}" not in colm_text,
        "COLM submission copy does not set custom page geometry in the preamble",
        "paper/colm2026_submission.tex",
        expected="no geometry override",
        observed="ok",
    )
    add_check(
        checks,
        "colm_template:inline_tables",
        "\\input{tables/" not in colm_text,
        "COLM submission copy uses inline compact tables to avoid float reordering",
        "paper/colm2026_submission.tex",
        expected="no generated table inputs",
        observed="ok" if "\\input{tables/" not in colm_text else "has table input",
    )

    for rel_pdf, expected_pages in [
        ("paper/short_paper.pdf", EXPECTED_SHORT_PAGES),
        ("paper/colm2026_submission.pdf", EXPECTED_COLM_PAGES),
    ]:
        pages = pdf_pages(root / rel_pdf)
        add_check(
            checks,
            f"pdf:{rel_pdf}:page_count",
            pages == expected_pages,
            "compiled PDF has expected page count",
            rel_pdf,
            expected=str(expected_pages),
            observed=str(pages) if pages is not None else "unreadable",
        )

    for rel_log in ["paper/short_paper.log", "paper/colm2026_submission.log"]:
        problems = log_problem_lines(root / rel_log)
        add_check(
            checks,
            f"log:{rel_log}:clean",
            not problems,
            "LaTeX log has no unresolved refs, rerun warnings, undefined citations, or overfull boxes",
            rel_log,
            expected="0 problem lines",
            observed="; ".join(problems[:3]) if problems else "0",
        )

    colm_pdf = paper_dir / "colm2026_submission.pdf"
    colm_pdf_text = pdf_text(colm_pdf)
    add_check(
        checks,
        "colm_pdf:anonymous_header",
        "Anonymous authors" in colm_pdf_text and "Paper under double-blind review" in colm_pdf_text,
        "COLM PDF text contains anonymous submission header",
        "paper/colm2026_submission.pdf",
        expected="anonymous header",
        observed="present"
        if "Anonymous authors" in colm_pdf_text and "Paper under double-blind review" in colm_pdf_text
        else "missing",
    )
    author_meta = pdf_info_field(colm_pdf, "Author")
    add_check(
        checks,
        "colm_pdf:author_metadata_blank",
        author_meta == "",
        "COLM PDF has no author metadata",
        "paper/colm2026_submission.pdf",
        expected="blank",
        observed=author_meta or "blank",
    )
    add_check(
        checks,
        "colm_pdf:no_local_paths",
        not has_local_path_marker(colm_pdf_text),
        "COLM PDF text does not expose local filesystem paths",
        "paper/colm2026_submission.pdf",
        expected="no local paths",
        observed="ok" if not has_local_path_marker(colm_pdf_text) else "local path found",
    )

    manifest_path = root / "submission" / "submission_manifest.json"
    manifest_raw = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    manifest = json.loads(manifest_raw) if manifest_raw else {}
    expected_source_members = [
        "colm2026_submission.tex",
        "colm2026_conference.sty",
        "colm2026_conference.bst",
        "natbib.sty",
        "fancyhdr.sty",
        "math_commands.tex",
        "README_SUBMISSION_PACKAGE.md",
    ]
    add_check(
        checks,
        "submission_manifest:checks_passed",
        manifest.get("checks_passed") is True,
        "submission package manifest records all package checks as passed",
        "submission/submission_manifest.json",
        expected="true",
        observed=str(manifest.get("checks_passed")),
    )
    add_check(
        checks,
        "submission_manifest:no_local_paths",
        not has_local_path_marker(manifest_raw),
        "submission manifest does not expose local filesystem paths",
        "submission/submission_manifest.json",
        expected="no local paths",
        observed="ok" if not has_local_path_marker(manifest_raw) else "local path found",
    )
    clean_compile = manifest.get("clean_compile", {})
    add_check(
        checks,
        "submission_manifest:clean_compile",
        clean_compile.get("status") is True,
        "submission source package compiles in a clean temporary directory",
        "submission/submission_manifest.json",
        expected="true",
        observed=str(clean_compile.get("status")),
    )
    add_check(
        checks,
        "submission_manifest:clean_compile_pdf_pages",
        clean_compile.get("pdf_pages") == EXPECTED_COLM_PAGES,
        "clean-room compiled submission PDF has expected page count",
        "submission/submission_manifest.json",
        expected=str(EXPECTED_COLM_PAGES),
        observed=str(clean_compile.get("pdf_pages")),
    )
    add_check(
        checks,
        "submission_manifest:clean_compile_log_clean",
        clean_compile.get("log_problem_count") == 0,
        "clean-room compile log has no unresolved refs, rerun warnings, undefined citations, or overfull boxes",
        "submission/submission_manifest.json",
        expected="0",
        observed=str(clean_compile.get("log_problem_count")),
    )
    add_check(
        checks,
        "submission_manifest:clean_compile_anonymous",
        clean_compile.get("anonymous_header") is True
        and clean_compile.get("author_metadata_blank") is True
        and clean_compile.get("no_local_paths") is True,
        "clean-room compiled PDF remains anonymous and does not expose local paths",
        "submission/submission_manifest.json",
        expected="anonymous, blank author metadata, no local paths",
        observed=(
            f"anonymous={clean_compile.get('anonymous_header')},"
            f"author_blank={clean_compile.get('author_metadata_blank')},"
            f"no_paths={clean_compile.get('no_local_paths')}"
        ),
    )
    source_zip = root / "submission" / "colm2026_submission_source.zip"
    zip_hashes = zip_member_hashes(source_zip) if source_zip.exists() else {}
    add_check(
        checks,
        "submission_zip:members",
        sorted(zip_hashes) == sorted(expected_source_members),
        "submission source zip contains exactly the expected source files",
        "submission/colm2026_submission_source.zip",
        expected=", ".join(sorted(expected_source_members)),
        observed=", ".join(sorted(zip_hashes)),
    )
    manifest_members = manifest.get("source_zip", {}).get("members", [])
    add_check(
        checks,
        "submission_manifest:zip_members",
        sorted(manifest_members) == sorted(expected_source_members),
        "manifest source-zip member list matches expected source files",
        "submission/submission_manifest.json",
        expected=", ".join(sorted(expected_source_members)),
        observed=", ".join(sorted(str(member) for member in manifest_members)),
    )
    manifest_zip_sha = manifest.get("source_zip", {}).get("sha256")
    add_check(
        checks,
        "submission_zip:sha256_matches_manifest",
        source_zip.exists() and sha256_file(source_zip) == manifest_zip_sha,
        "submission source zip SHA-256 matches manifest",
        "submission/colm2026_submission_source.zip",
        expected=str(manifest_zip_sha),
        observed=sha256_file(source_zip) if source_zip.exists() else "missing",
    )
    submission_pdf = root / "submission" / "colm2026_submission.pdf"
    add_check(
        checks,
        "submission_pdf:page_count",
        pdf_pages(submission_pdf) == EXPECTED_COLM_PAGES,
        "packaged submission PDF has expected page count",
        "submission/colm2026_submission.pdf",
        expected=str(EXPECTED_COLM_PAGES),
        observed=str(pdf_pages(submission_pdf)),
    )
    add_check(
        checks,
        "submission_pdf:matches_paper_pdf",
        submission_pdf.exists() and sha256_file(submission_pdf) == sha256_file(colm_pdf),
        "packaged submission PDF matches the compiled COLM PDF",
        "submission/colm2026_submission.pdf",
        expected=sha256_file(colm_pdf) if colm_pdf.exists() else "missing",
        observed=sha256_file(submission_pdf) if submission_pdf.exists() else "missing",
    )
    source_manifest_hashes = {
        item["path"].split("/", 1)[1]: item["sha256"]
        for item in manifest.get("source_files", [])
        if isinstance(item, dict) and item.get("path", "").startswith("colm2026_source/")
    }
    manifest_source_ok = all(
        source_manifest_hashes.get(member) == sha256_file(root / "submission" / "colm2026_source" / member)
        for member in expected_source_members
        if (root / "submission" / "colm2026_source" / member).exists()
    ) and set(source_manifest_hashes) == set(expected_source_members)
    add_check(
        checks,
        "submission_source:hashes_match_manifest",
        manifest_source_ok,
        "packaged source-file hashes match the manifest",
        "submission/submission_manifest.json",
        expected=str(len(expected_source_members)),
        observed=str(len(source_manifest_hashes)),
    )
    zip_source_ok = (
        set(zip_hashes) == set(expected_source_members)
        and all(zip_hashes[member] == source_manifest_hashes.get(member) for member in expected_source_members)
    )
    add_check(
        checks,
        "submission_zip:source_hashes_match_manifest",
        zip_source_ok,
        "source zip member hashes match the manifest source hashes",
        "submission/colm2026_submission_source.zip",
        expected="all source hashes match",
        observed="ok" if zip_source_ok else "hash mismatch",
    )
    paper_source_ok = all(
        sha256_file(root / "paper" / member)
        == sha256_file(root / "submission" / "colm2026_source" / member)
        for member in expected_source_members
        if member != "README_SUBMISSION_PACKAGE.md"
    )
    add_check(
        checks,
        "submission_source:matches_paper_sources",
        paper_source_ok,
        "packaged source files match the working COLM source and style files",
        "submission/colm2026_source",
        expected="paper source hashes",
        observed="ok" if paper_source_ok else "hash mismatch",
    )
    manifest_md = root / "submission" / "submission_manifest.md"
    manifest_md_text = manifest_md.read_text(encoding="utf-8") if manifest_md.exists() else ""
    add_check(
        checks,
        "submission_manifest_md:summary",
        "Clean-room compile: True" in manifest_md_text
        and "Checks passed: True" in manifest_md_text
        and f"PDF pages: {EXPECTED_COLM_PAGES}" in manifest_md_text,
        "human-readable manifest summarizes clean package status",
        "submission/submission_manifest.md",
        expected=f"clean compile true, checks passed true, {EXPECTED_COLM_PAGES} pages",
        observed="present" if "Checks passed: True" in manifest_md_text else "missing",
    )
    add_check(
        checks,
        "submission_manifest_md:no_local_paths",
        not has_local_path_marker(manifest_md_text),
        "human-readable manifest does not expose local filesystem paths",
        "submission/submission_manifest.md",
        expected="no local paths",
        observed="ok" if not has_local_path_marker(manifest_md_text) else "local path found",
    )

    supplement_dir = root / "supplement"
    supplement_manifest_path = supplement_dir / "supplement_manifest.json"
    supplement_manifest_raw = (
        supplement_manifest_path.read_text(encoding="utf-8")
        if supplement_manifest_path.exists()
        else ""
    )
    supplement_manifest = json.loads(supplement_manifest_raw) if supplement_manifest_raw else {}
    supplement_files = [
        "SUPPLEMENT_INDEX.md",
        "benchmark_card.md",
        "noisy_style_examples.md",
        "reproducibility_checklist.md",
        "claim_trace.md",
    ]
    manifest_supp_files = {
        Path(item.get("path", "")).name: item
        for item in supplement_manifest.get("files", [])
        if isinstance(item, dict)
    }
    add_check(
        checks,
        "supplement_manifest:files",
        sorted(manifest_supp_files) == sorted(supplement_files),
        "supplement manifest lists exactly the generated reviewer-facing files",
        "supplement/supplement_manifest.json",
        expected=", ".join(sorted(supplement_files)),
        observed=", ".join(sorted(manifest_supp_files)),
    )
    add_check(
        checks,
        "supplement_manifest:no_local_paths",
        not has_local_path_marker(supplement_manifest_raw),
        "supplement manifest does not expose local filesystem paths",
        "supplement/supplement_manifest.json",
        expected="no local paths",
        observed="ok" if not has_local_path_marker(supplement_manifest_raw) else "local path found",
    )
    for name in supplement_files:
        path = supplement_dir / name
        manifest_item = manifest_supp_files.get(name, {})
        actual_hash = sha256_file(path) if path.exists() else "missing"
        add_check(
            checks,
            f"supplement:{name}:sha256",
            path.exists()
            and manifest_item.get("sha256") == actual_hash
            and manifest_item.get("bytes") == path.stat().st_size,
            "supplement file hash and byte count match manifest",
            f"supplement/{name}",
            expected=str(manifest_item.get("sha256")),
            observed=actual_hash,
        )
    supplement_text = "\n".join(
        (supplement_dir / name).read_text(encoding="utf-8")
        for name in supplement_files
        if (supplement_dir / name).exists()
    )
    add_check(
        checks,
        "supplement:no_local_paths",
        not has_local_path_marker(supplement_text),
        "supplement markdown does not expose local filesystem paths",
        "supplement/*.md",
        expected="no local paths",
        observed="ok" if not has_local_path_marker(supplement_text) else "local path found",
    )
    benchmark_card = (supplement_dir / "benchmark_card.md").read_text(encoding="utf-8")
    benchmark_fragments = [
        "CrossDoc-PrivacyBench",
        "Synthetic-only benchmark",
        "No real people",
        "Personas: 120",
        "Documents: 480",
        "Held-out personas for main evaluation: 96",
        "Candidate set size: 10",
        "LinkGuard target k: 5",
        "Out-of-Scope Uses",
        "formal anonymity guarantees",
    ]
    for fragment in benchmark_fragments:
        add_check(
            checks,
            f"supplement:benchmark_card:{fragment[:24]}",
            contains(benchmark_card, fragment),
            f"benchmark card contains required fragment {fragment}",
            "supplement/benchmark_card.md",
            expected=fragment,
            observed=fragment if contains(benchmark_card, fragment) else "missing",
        )
    repro_checklist = (supplement_dir / "reproducibility_checklist.md").read_text(encoding="utf-8")
    for command_fragment in [
        "src/reproduce_no_api.py",
        "src/corpus_awareness_ablation.py",
        "src/rag_query_sensitivity.py",
        "src/noisy_style_stress.py",
        "src/make_supplement.py",
        "src/verify_claims.py",
        "planned_calls=120",
        "missing_or_dependent_calls=0",
    ]:
        add_check(
            checks,
            f"supplement:repro:{command_fragment}",
            contains(repro_checklist, command_fragment),
            f"reproducibility checklist contains {command_fragment}",
            "supplement/reproducibility_checklist.md",
            expected=command_fragment,
            observed=command_fragment if contains(repro_checklist, command_fragment) else "missing",
        )
    noisy_examples = (supplement_dir / "noisy_style_examples.md").read_text(encoding="utf-8")
    for fragment in [
        "P0002_D01",
        "N0 noisy original",
        "C1 direct redaction",
        "C5 LinkGuard",
        "C6 aggressive redaction",
        "This example is synthetic",
    ]:
        add_check(
            checks,
            f"supplement:noisy_example:{fragment}",
            contains(noisy_examples, fragment),
            f"noisy-style supplement example contains {fragment}",
            "supplement/noisy_style_examples.md",
            expected=fragment,
            observed=fragment if contains(noisy_examples, fragment) else "missing",
        )
    claim_trace = (supplement_dir / "claim_trace.md").read_text(encoding="utf-8")
    for fragment in [
        "Direct PII redaction leaves auxiliary matching risk",
        "Presidio-style PII redaction remains linkable",
        "Stable pseudonyms create linkage handles",
        "LinkGuard improves the privacy-utility frontier",
        "Corpus co-occurrence statistics matter for LinkGuard planning",
        "results/corpus_awareness_ablation.csv",
        "Generated profile-like queries preserve the RAG exposure ordering",
        "results/rag_query_sensitivity.csv",
        "GPT-5.5 RAG generation preserves the exposure ordering",
        "results/openai_gpt55_rag_12t3_rag_generation_summary.csv",
        "Noisy-style synthetic rerendering preserves the ordering",
        "results/noisy_style_stress/noisy_style_results.csv",
    ]:
        add_check(
            checks,
            f"supplement:claim_trace:{fragment[:24]}",
            contains(claim_trace, fragment),
            f"claim trace contains {fragment}",
            "supplement/claim_trace.md",
            expected=fragment,
            observed=fragment if contains(claim_trace, fragment) else "missing",
        )

    validation = pd.read_csv(results_dir / "benchmark_validation.csv")
    validation_failures = int((validation["status"] != "PASS").sum())
    add_check(
        checks,
        "benchmark_validation:all_pass",
        validation_failures == 0,
        "benchmark validation report has no failures",
        "results/benchmark_validation.csv",
        expected="0",
        observed=str(validation_failures),
    )
    direct_id_checks = validation[
        validation["check_id"].str.contains(":no_exact_direct_ids", regex=False)
    ]
    direct_id_failures = int((direct_id_checks["status"] != "PASS").sum())
    add_check(
        checks,
        "benchmark_validation:no_exact_direct_id_leaks",
        len(direct_id_checks) == len(cfg["conditions"]) - 1 and direct_id_failures == 0,
        "all transformed non-original conditions passed exact synthetic direct-ID leak checks",
        "results/benchmark_validation.csv",
        expected=f"{len(cfg['conditions']) - 1} checks, 0 failures",
        observed=f"{len(direct_id_checks)} checks, {direct_id_failures} failures",
    )
    utility_checks = validation[
        validation["check_id"].str.startswith("utility:")
        & validation["check_id"].str.endswith(":issue_phrase_retention")
    ]
    utility_failures = int((utility_checks["status"] != "PASS").sum())
    add_check(
        checks,
        "benchmark_validation:utility_retention_checks",
        len(utility_checks) == 7 and utility_failures == 0,
        "utility-preserving conditions passed issue-phrase retention validation",
        "results/benchmark_validation.csv",
        expected="7 checks, 0 failures",
        observed=f"{len(utility_checks)} checks, {utility_failures} failures",
    )

    personas = read_jsonl(root / cfg["data_dir"] / "personas.jsonl")
    docs = read_jsonl(root / cfg["data_dir"] / "original_docs.jsonl")
    split = split_personas(personas)
    gpt55_doclocal_docs = read_jsonl(
        root / cfg["data_dir"] / "transformed" / "c4_openai_doc_local_gpt55_24p.jsonl"
    )
    gpt55_doclocal_text_by_pid = {
        doc["persona_id"]: "\n".join(
            row["text"]
            for row in gpt55_doclocal_docs
            if row["persona_id"] == doc["persona_id"]
        ).lower()
        for doc in gpt55_doclocal_docs
    }
    persona_by_id = {persona["persona_id"]: persona for persona in personas}
    direct_id_fields = ["synthetic_name", "email", "phone", "address", "account_id"]
    exact_direct_leaks = []
    for pid, combined_text in gpt55_doclocal_text_by_pid.items():
        persona = persona_by_id[pid]
        for field in direct_id_fields:
            value = str(persona[field]).strip().lower()
            if value and value in combined_text:
                exact_direct_leaks.append(f"{pid}:{field}")
    add_check(
        checks,
        "gpt55_doclocal:no_exact_direct_id_leaks",
        len(gpt55_doclocal_docs) == 96
        and len(gpt55_doclocal_text_by_pid) == 24
        and not exact_direct_leaks,
        "GPT-5.5 document-local generated corpus removes exact synthetic direct identifiers",
        "data/transformed/c4_openai_doc_local_gpt55_24p.jsonl",
        expected="96 docs, 24 personas, 0 exact direct-ID leaks",
        observed=(
            f"{len(gpt55_doclocal_docs)} docs, "
            f"{len(gpt55_doclocal_text_by_pid)} personas, "
            f"{len(exact_direct_leaks)} leaks"
        ),
    )
    add_check(
        checks,
        "corpus:persona_count",
        len(personas) == int(cfg["num_personas"]) and contains(paper_text, str(len(personas))),
        "persona count matches config and is stated in paper",
        "data/personas.jsonl",
        expected=str(cfg["num_personas"]),
        observed=str(len(personas)),
    )
    add_check(
        checks,
        "corpus:document_count",
        len(docs) == int(cfg["num_personas"]) * int(cfg["docs_per_persona"])
        and contains(paper_text, str(len(docs))),
        "document count matches config and is stated in paper",
        "data/original_docs.jsonl",
        expected=str(int(cfg["num_personas"]) * int(cfg["docs_per_persona"])),
        observed=str(len(docs)),
    )
    add_check(
        checks,
        "corpus:test_persona_count",
        len(split["test"]) == 96 and contains(paper_text, "96 held-out personas"),
        "held-out test size is stated in paper",
        "crossdoc_pipeline.split_personas",
        expected="96",
        observed=str(len(split["test"])),
    )

    main = pd.read_csv(results_dir / "main_results.csv")
    direct = row(main, "c1_direct_redaction")
    presidio = row(main, "c1b_presidio_redaction")
    stable = row(main, "c2_consistent_pseudonym")
    local = row(main, "c4_doc_local_anon")
    lg = row(main, "c5_linkguard")
    aggressive = row(main, "c6_aggressive_redaction")
    main_claims = {
        "main:direct_aux": direct["aux_top1"],
        "main:presidio_aux": presidio["aux_top1"],
        "main:stable_pair": stable["pair_f1"],
        "main:lg_aux": lg["aux_top1"],
        "main:lg_issue": lg["issue_acc"],
        "main:lg_ret5": lg["retrieval_recall_at_5"],
        "main:agg_issue": aggressive["issue_acc"],
        "main:agg_ret5": aggressive["retrieval_recall_at_5"],
        "main:direct_exact": direct["attr_exact_recovery"],
        "main:presidio_exact": presidio["attr_exact_recovery"],
        "main:local_exact": local["attr_exact_recovery"],
    }
    for check_id, value in main_claims.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains(paper_text, fragment),
            f"paper contains value {fragment}",
            "results/main_results.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    sensitivity = pd.read_csv(results_dir / "linkguard_sensitivity.csv")
    k2 = sensitivity[sensitivity["target_k"] == 2].iloc[0]
    k5 = sensitivity[sensitivity["target_k"] == 5].iloc[0]
    k20 = sensitivity[sensitivity["target_k"] == 20].iloc[0]
    for check_id, value in {
        "sensitivity:k2_aux": k2["aux_top1"],
        "sensitivity:k2_exact": k2["attr_exact_recovery"],
        "sensitivity:k5_exact": k5["attr_exact_recovery"],
        "sensitivity:field_k1_aux": sensitivity.iloc[0]["field_aux_top1"],
        "sensitivity:field_k5_aux": k5["field_aux_top1"],
        "sensitivity:field_k20_aux": k20["field_aux_top1"],
    }.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains(paper_text, fragment),
            f"paper contains target-k sensitivity value {fragment}",
            "results/linkguard_sensitivity.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    corpus_awareness = pd.read_csv(results_dir / "corpus_awareness_ablation.csv")
    expected_ca_conditions = {
        "ca_true_corpus_linkguard",
        "ca_shuffled_corpus_stats",
        "ca_global_l1_generalization",
        "ca_direct_targetk_suppression",
    }
    add_check(
        checks,
        "corpus_awareness:variant_shape",
        len(corpus_awareness) == 4
        and set(corpus_awareness["condition"]) == expected_ca_conditions
        and set(corpus_awareness["target_k"].astype(int)) == {5},
        "corpus-awareness ablation contains the four planned target-k variants",
        "results/corpus_awareness_ablation.csv",
        expected="4 variants at target k=5",
        observed=f"{len(corpus_awareness)} variants, target_k={sorted(set(corpus_awareness['target_k'].astype(int)))}",
    )
    ca_true = row(corpus_awareness, "ca_true_corpus_linkguard")
    ca_shuffled = row(corpus_awareness, "ca_shuffled_corpus_stats")
    ca_global = row(corpus_awareness, "ca_global_l1_generalization")
    ca_suppression = row(corpus_awareness, "ca_direct_targetk_suppression")
    add_check(
        checks,
        "corpus_awareness:true_reaches_target",
        float(ca_true["min_true_estimated_k"]) >= 5.0
        and float(ca_true["target_k_coverage"]) == 1.0,
        "true corpus-aware LinkGuard reaches target k for every persona",
        "results/corpus_awareness_ablation.csv",
        expected="min_true_estimated_k >= 5 and target_k_coverage = 1",
        observed=f"min={fmt(ca_true['min_true_estimated_k'])}, coverage={fmt(ca_true['target_k_coverage'])}",
    )
    add_check(
        checks,
        "corpus_awareness:shuffled_breaks_certificate",
        float(ca_shuffled["target_k_coverage"]) < 1.0
        and float(ca_shuffled["min_true_estimated_k"]) < 5.0,
        "shuffled co-occurrence planning breaks the true target-k certificate for at least one persona",
        "results/corpus_awareness_ablation.csv",
        expected="target_k_coverage < 1 and min_true_estimated_k < 5",
        observed=f"min={fmt(ca_shuffled['min_true_estimated_k'])}, coverage={fmt(ca_shuffled['target_k_coverage'])}",
    )
    for check_id, value in {
        "corpus_awareness:true_aux": ca_true["aux_top1"],
        "corpus_awareness:shuffled_aux": ca_shuffled["aux_top1"],
        "corpus_awareness:global_aux": ca_global["aux_top1"],
        "corpus_awareness:suppression_aux": ca_suppression["aux_top1"],
    }.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains((results_dir / "paper_ready_summary.md").read_text(encoding="utf-8"), fragment),
            f"paper-ready result brief contains corpus-awareness value {fragment}",
            "results/corpus_awareness_ablation.csv",
            expected=fragment,
            observed=fragment
            if contains((results_dir / "paper_ready_summary.md").read_text(encoding="utf-8"), fragment)
            else "missing",
        )

    multiseed = pd.read_csv(results_dir / "multiseed" / "claim_summary.csv")
    for condition in ["c1_direct_redaction", "c1b_presidio_redaction", "c4_doc_local_anon", "c5_linkguard"]:
        value = float(row(multiseed, condition)["aux_top1_mean"])
        fragment = fmt(value)
        add_check(
            checks,
            f"multiseed:{condition}:aux_mean",
            contains(paper_text, fragment),
            f"paper contains three-seed mean Aux@1 {fragment}",
            "results/multiseed/claim_summary.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    ablation = pd.read_csv(results_dir / "ablation.csv")
    role = ablation[ablation["ablation"] == "remove_occupation"].iloc[0]["aux_top1"]
    location = ablation[ablation["ablation"] == "remove_location"].iloc[0]["aux_top1"]
    for check_id, value in {"ablation:role_org": role, "ablation:location": location}.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains(paper_text, fragment),
            f"paper contains ablation value {fragment}",
            "results/ablation.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    aux_ci = pd.read_csv(paper_dir / "tables" / "local_aux_bootstrap_ci.csv")
    for label, condition in [
        ("direct", "C1 direct redaction"),
        ("presidio", "C1b Presidio redaction"),
        ("lg", "C5 LinkGuard"),
    ]:
        match = aux_ci[aux_ci["condition"] == condition]
        if match.empty:
            raise KeyError(condition)
        values = [fmt(match.iloc[0][col]) for col in ["aux_top1", "ci_low", "ci_high"]]
        fragment = f"{values[0]} [{values[1]}, {values[2]}]"
        add_check(
            checks,
            f"ci:{label}:aux_top1",
            contains(paper_text, fragment),
            f"paper contains bootstrap CI {fragment}",
            "paper/tables/local_aux_bootstrap_ci.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    by_tier = pd.read_csv(results_dir / "by_tier.csv")

    def tier_metric(condition: str, risk_tier: str, metric: str = "aux_top1") -> float:
        match = by_tier[
            (by_tier["condition"] == condition)
            & (by_tier["risk_tier"] == risk_tier)
        ]
        if match.empty:
            raise KeyError(f"{condition}:{risk_tier}:{metric}")
        return float(match[metric].iloc[0])

    tier_claims = {
        "tier:direct_t1_aux": tier_metric("c1_direct_redaction", "T1"),
        "tier:direct_t2_aux": tier_metric("c1_direct_redaction", "T2"),
        "tier:direct_t3_aux": tier_metric("c1_direct_redaction", "T3"),
        "tier:lg_t1_aux": tier_metric("c5_linkguard", "T1"),
        "tier:lg_t2_aux": tier_metric("c5_linkguard", "T2"),
        "tier:lg_t3_aux": tier_metric("c5_linkguard", "T3"),
    }
    for check_id, value in tier_claims.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains(paper_text, fragment),
            f"paper contains risk-tier stratification value {fragment}",
            "results/by_tier.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    candidate = pd.read_csv(results_dir / "candidate_sensitivity.csv")
    candidate_checks = {
        "candidate:direct_50": candidate[
            (candidate["condition"] == "c1_direct_redaction")
            & (candidate["candidate_set_size"] == 50)
        ].iloc[0]["aux_top1"],
        "candidate:local_50": candidate[
            (candidate["condition"] == "c4_doc_local_anon")
            & (candidate["candidate_set_size"] == 50)
        ].iloc[0]["aux_top1"],
        "candidate:lg_50": candidate[
            (candidate["condition"] == "c5_linkguard")
            & (candidate["candidate_set_size"] == 50)
        ].iloc[0]["aux_top1"],
        "candidate:chance_50": candidate[candidate["candidate_set_size"] == 50].iloc[0]["chance_top1"],
    }
    for check_id, value in candidate_checks.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains(paper_text, fragment),
            f"paper contains candidate-pool sensitivity value {fragment}",
            "results/candidate_sensitivity.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    attack = pd.read_csv(results_dir / "attack_sensitivity.csv")
    for condition, label in [
        ("c1_direct_redaction", "direct"),
        ("c4_doc_local_anon", "local"),
        ("c5_linkguard", "lg"),
    ]:
        values = attack[attack["condition"] == condition]["aux_top1"]
        for suffix, value in [("min", values.min()), ("max", values.max())]:
            fragment = fmt(value)
            add_check(
                checks,
                f"attack:{label}:{suffix}",
                contains(paper_text, fragment),
                f"paper contains attack-family range value {fragment}",
                "results/attack_sensitivity.csv",
                expected=fragment,
                observed=fragment if contains(paper_text, fragment) else "missing",
            )

    utility = pd.read_csv(results_dir / "utility_stress.csv")
    for condition, metric in [
        ("c5_linkguard", "stress_utility_score"),
        ("c1_direct_redaction", "stress_utility_score"),
        ("c6_aggressive_redaction", "stress_utility_score"),
    ]:
        value = row(utility, condition)[metric]
        fragment = fmt(value)
        add_check(
            checks,
            f"utility:{condition}:{metric}",
            contains(paper_text, fragment),
            f"paper contains body-only utility value {fragment}",
            "results/utility_stress.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    noisy_dir = results_dir / "noisy_style_stress"
    noisy = pd.read_csv(noisy_dir / "noisy_style_results.csv")
    noisy_diag = pd.read_csv(noisy_dir / "noisy_style_diagnostic_summary.csv").iloc[0]
    noisy_direct = row(noisy, "c1_direct_redaction")
    noisy_presidio = row(noisy, "c1b_presidio_redaction")
    noisy_local = row(noisy, "c4_doc_local_anon")
    noisy_lg = row(noisy, "c5_linkguard")
    noisy_aggressive = row(noisy, "c6_aggressive_redaction")
    add_check(
        checks,
        "noisy_style:document_count",
        int(noisy_diag["n_docs"]) == len(docs),
        "noisy-style stress corpus has one rerendered document per original document",
        "results/noisy_style_stress/noisy_style_diagnostic_summary.csv",
        expected=str(len(docs)),
        observed=str(int(noisy_diag["n_docs"])),
    )
    add_check(
        checks,
        "noisy_style:template_similarity",
        float(noisy_diag["mean_template_similarity"]) < 0.35,
        "noisy-style stress corpus is substantially less aligned to canonical templates",
        "results/noisy_style_stress/noisy_style_diagnostic_summary.csv",
        expected="<0.35",
        observed=fmt(noisy_diag["mean_template_similarity"]),
    )
    add_check(
        checks,
        "noisy_style:ordering",
        noisy_direct["aux_top1"] > 0.5
        and noisy_presidio["aux_top1"] > 0.5
        and noisy_local["aux_top1"] > 0.5
        and noisy_lg["aux_top1"] <= 0.05
        and noisy_aggressive["aux_top1"] <= 0.05,
        "noisy-style stress test preserves the main privacy ordering",
        "results/noisy_style_stress/noisy_style_results.csv",
        expected="direct/presidio/local high, LinkGuard/aggressive low",
        observed=(
            f"{fmt(noisy_direct['aux_top1'])}/"
            f"{fmt(noisy_presidio['aux_top1'])}/"
            f"{fmt(noisy_local['aux_top1'])}/"
            f"{fmt(noisy_lg['aux_top1'])}/"
            f"{fmt(noisy_aggressive['aux_top1'])}"
        ),
    )
    add_check(
        checks,
        "noisy_style:utility_frontier",
        noisy_lg["issue_acc"] == 1.0
        and noisy_lg["retrieval_recall_at_5"] == 1.0
        and noisy_aggressive["issue_acc"] < 0.7
        and noisy_aggressive["retrieval_recall_at_5"] < 0.8,
        "noisy-style stress test preserves LinkGuard utility advantage over aggressive redaction",
        "results/noisy_style_stress/noisy_style_results.csv",
        expected="LinkGuard utility 1.000/1.000, aggressive lower",
        observed=(
            f"lg={fmt(noisy_lg['issue_acc'])}/{fmt(noisy_lg['retrieval_recall_at_5'])},"
            f"agg={fmt(noisy_aggressive['issue_acc'])}/{fmt(noisy_aggressive['retrieval_recall_at_5'])}"
        ),
    )
    noisy_source_fragments = {
        "template_similarity": fmt(noisy_diag["mean_template_similarity"]),
        "direct_presidio_local": (
            f"{fmt(noisy_direct['aux_top1'])}/"
            f"{fmt(noisy_presidio['aux_top1'])}/"
            f"{fmt(noisy_local['aux_top1'])}"
        ),
        "linkguard_aux_utility": (
            f"{fmt(noisy_lg['aux_top1'])} with issue/Ret@5 "
            f"{fmt(noisy_lg['issue_acc'])}"
        ),
        "aggressive_utility": (
            f"{fmt(noisy_aggressive['issue_acc'])}/"
            f"{fmt(noisy_aggressive['retrieval_recall_at_5'])}"
        ),
    }
    for name, fragment in noisy_source_fragments.items():
        add_check(
            checks,
            f"noisy_style:paper_fragment:{name}",
            contains(paper_text, fragment) and contains(colm_text, fragment),
            f"both paper drafts contain noisy-style stress claim fragment {fragment}",
            "results/noisy_style_stress/noisy_style_results.csv",
            expected=fragment,
            observed=fragment
            if contains(paper_text, fragment) and contains(colm_text, fragment)
            else "missing",
        )
    noisy_summary = (noisy_dir / "noisy_style_stress.md").read_text(encoding="utf-8")
    for fragment in [
        fmt(noisy_direct["aux_top1"]),
        fmt(noisy_presidio["aux_top1"]),
        fmt(noisy_local["aux_top1"]),
        fmt(noisy_lg["aux_top1"]),
        fmt(noisy_aggressive["issue_acc"]),
    ]:
        add_check(
            checks,
            f"noisy_style:summary_fragment:{fragment}",
            contains(noisy_summary, fragment),
            f"noisy-style markdown summary contains value {fragment}",
            "results/noisy_style_stress/noisy_style_stress.md",
            expected=fragment,
            observed=fragment if contains(noisy_summary, fragment) else "missing",
        )

    rag_tier = pd.read_csv(results_dir / "rag_exposure_by_tier.csv")

    def rag_t3_value(condition: str, metric: str) -> float:
        match = rag_tier[
            (rag_tier["condition"] == condition)
            & (rag_tier["risk_tier"] == "T3")
        ]
        if match.empty:
            raise KeyError(f"{condition}:T3:{metric}")
        return float(match[metric].iloc[0])

    rag_claims = {
        "rag:direct_t3_hit5": (
            rag_t3_value("c1_direct_redaction", "hit_at_5"),
            "Hit@5 1.000",
        ),
        "rag:direct_t3_multi10": (
            rag_t3_value("c1_direct_redaction", "multi_doc_at_10"),
            "Multi@10 1.000",
        ),
        "rag:lg_t3_hit5": (
            rag_t3_value("c5_linkguard", "hit_at_5"),
            "0.312",
        ),
        "rag:lg_t3_multi10": (
            rag_t3_value("c5_linkguard", "multi_doc_at_10"),
            "Multi@10 to 0.000",
        ),
    }
    for check_id, (value, fragment) in rag_claims.items():
        expected = fmt(value)
        add_check(
            checks,
            check_id,
            contains(paper_text, fragment),
            f"paper contains RAG exposure claim fragment {fragment}",
            "results/rag_exposure_by_tier.csv",
            expected=expected,
            observed=fragment if contains(paper_text, fragment) else "missing",
        )

    generated_queries = read_jsonl(root / cfg["data_dir"] / "generated_profile_queries.jsonl")
    query_types = {row_data["query_type"] for row_data in generated_queries}
    add_check(
        checks,
        "rag_query:generated_query_shape",
        len(generated_queries) == 288
        and query_types == {"short", "medium", "verbose"}
        and len({row_data["persona_id"] for row_data in generated_queries}) == 96,
        "generated profile-query file has three deterministic query types per held-out persona",
        "data/generated_profile_queries.jsonl",
        expected="96 personas x 3 query types",
        observed=f"{len(generated_queries)} rows, query_types={sorted(query_types)}",
    )
    rag_query = pd.read_csv(results_dir / "rag_query_sensitivity.csv")
    rag_query_rows = pd.read_csv(results_dir / "rag_query_sensitivity_rows.csv")
    add_check(
        checks,
        "rag_query:summary_shape",
        len(rag_query) == 15
        and len(rag_query_rows) == 1440
        and set(rag_query["query_type"]) == {"short", "medium", "verbose"},
        "generated-query RAG sensitivity covers five conditions and three query types",
        "results/rag_query_sensitivity.csv",
        expected="15 summary rows and 1440 per-query rows",
        observed=f"{len(rag_query)} summary rows, {len(rag_query_rows)} rows",
    )

    def rag_query_value(condition: str, query_type: str, metric: str = "hit_at_5") -> float:
        match = rag_query[
            (rag_query["condition"] == condition)
            & (rag_query["query_type"] == query_type)
        ]
        if match.empty:
            raise KeyError(f"{condition}:{query_type}:{metric}")
        return float(match[metric].iloc[0])

    result_brief_for_rag = (results_dir / "paper_ready_summary.md").read_text(encoding="utf-8")
    for check_id, value in {
        "rag_query:short_direct_hit5": rag_query_value("c1_direct_redaction", "short"),
        "rag_query:short_lg_hit5": rag_query_value("c5_linkguard", "short"),
        "rag_query:verbose_direct_hit5": rag_query_value("c1_direct_redaction", "verbose"),
        "rag_query:verbose_lg_hit5": rag_query_value("c5_linkguard", "verbose"),
    }.items():
        fragment = fmt(value)
        add_check(
            checks,
            check_id,
            contains(result_brief_for_rag, fragment),
            f"paper-ready result brief contains generated-query RAG value {fragment}",
            "results/rag_query_sensitivity.csv",
            expected=fragment,
            observed=fragment if contains(result_brief_for_rag, fragment) else "missing",
        )

    rag_context = pd.read_csv(results_dir / "rag_context_recovery_by_tier.csv")

    def rag_context_t3_value(condition: str, metric: str) -> float:
        match = rag_context[
            (rag_context["condition"] == condition)
            & (rag_context["risk_tier"] == "T3")
        ]
        if match.empty:
            raise KeyError(f"{condition}:T3:{metric}")
        return float(match[metric].iloc[0])

    rag_context_fragments = {
        "direct_exact_fields": fmt(
            rag_context_t3_value("c1_direct_redaction", "exact_fields_recovered")
        ),
        "doclocal_exact_fields": fmt(
            rag_context_t3_value("c4_doc_local_anon", "exact_fields_recovered")
        ),
        "doclocal_coarse_fields": fmt(
            rag_context_t3_value("c4_doc_local_anon", "coarse_fields_recovered")
        ),
        "lg_coarse_fields": fmt(
            rag_context_t3_value("c5_linkguard", "coarse_fields_recovered")
        ),
    }
    for name, fragment in rag_context_fragments.items():
        add_check(
            checks,
            f"rag_context:paper_fragment:{name}",
            contains(paper_text, fragment) and contains(colm_text, fragment),
            f"both paper drafts contain RAG context recovery value {fragment}",
            "results/rag_context_recovery_by_tier.csv",
            expected=fragment,
            observed=fragment
            if contains(paper_text, fragment) and contains(colm_text, fragment)
            else "missing",
        )

    openai = pd.read_csv(results_dir / "openai_aux_match_summary.csv")
    gpt55 = pd.read_csv(results_dir / "openai_gpt55_48p_aux_match_summary.csv")
    gpt55_doclocal = pd.read_csv(results_dir / "openai_gpt55_doclocal_24p_aux_match_summary.csv")
    gpt55_evidence = pd.read_csv(results_dir / "openai_gpt55_evidence_24p_evidence_summary.csv")
    gpt55_evidence_rows = pd.read_csv(results_dir / "openai_gpt55_evidence_24p_evidence_rows.csv")
    evidence_bucket_counts = gpt55_evidence_rows.groupby("bucket").size().to_dict()
    add_check(
        checks,
        "gpt55_evidence:row_count_and_parse",
        len(gpt55_evidence_rows) == 24
        and evidence_bucket_counts.get("direct_success") == 8
        and evidence_bucket_counts.get("linkguard_residual") == 8
        and evidence_bucket_counts.get("aggressive_failure") == 8
        and gpt55_evidence_rows["signal_labels"].notna().all()
        and gpt55_evidence_rows["residual_risk_category"].astype(str).str.len().gt(0).all(),
        "GPT-5.5 evidence extraction produced 24 parsed cases across the intended buckets",
        "results/openai_gpt55_evidence_24p_evidence_rows.csv",
        expected="24 rows, 8/8/8 buckets, parsed signals/categories",
        observed=f"{len(gpt55_evidence_rows)} rows, {evidence_bucket_counts}",
    )
    for condition in [
        "c1_direct_redaction",
        "c1b_presidio_redaction",
        "c4_doc_local_anon",
        "c5_linkguard",
        "c6_aggressive_redaction",
    ]:
        stats = weighted_openai(gpt55, condition)
        fragment = fmt(stats["top1"])
        add_check(
            checks,
            f"gpt55:{condition}:top1",
            stats["n"] == 48 and contains(paper_text, fragment),
            f"paper contains 48-person GPT-5.5 top-1 value {fragment}",
            "results/openai_gpt55_48p_aux_match_summary.csv",
            expected=f"n=48,{fragment}",
            observed=f"n={stats['n']},{fragment if contains(paper_text, fragment) else 'missing'}",
        )
    for condition in [
        "c4_openai_doc_local_gpt55_24p",
        "c5_linkguard",
    ]:
        stats = weighted_openai(gpt55_doclocal, condition)
        fragment = fmt(stats["top1"])
        add_check(
            checks,
            f"gpt55_doclocal:{condition}:top1",
            stats["n"] == 24 and contains(paper_text, fragment),
            f"paper contains 24-person GPT-5.5 doc-local top-1 value {fragment}",
            "results/openai_gpt55_doclocal_24p_aux_match_summary.csv",
            expected=f"n=24,{fragment}",
            observed=f"n={stats['n']},{fragment if contains(paper_text, fragment) else 'missing'}",
        )
    evidence_fragments = [
        "24-case GPT-5.5 evidence-extraction audit",
        "direct-redaction successful matches cite location in 1.000 and role in 0.750",
        "residual matches cite role, location, and institution at 0.000",
        "uncertain in 0.875",
    ]
    for fragment in evidence_fragments:
        add_check(
            checks,
            f"gpt55_evidence:paper_fragment:{fragment[:32]}",
            contains(paper_text, fragment) and contains(colm_text, fragment),
            f"both paper drafts contain GPT-5.5 evidence audit fragment {fragment}",
            "results/openai_gpt55_evidence_24p_evidence_summary.csv",
            expected=fragment,
            observed=fragment if contains(paper_text, fragment) and contains(colm_text, fragment) else "missing",
        )

    colm_core_claims = {
        "persona_count": str(len(personas)),
        "document_count": str(len(docs)),
        "test_persona_count": "96 held-out personas",
        "direct_aux": fmt(direct["aux_top1"]),
        "presidio_aux": fmt(presidio["aux_top1"]),
        "stable_pair": fmt(stable["pair_f1"]),
        "local_aux": fmt(local["aux_top1"]),
        "local_exact": fmt(local["attr_exact_recovery"]),
        "lg_aux": fmt(lg["aux_top1"]),
        "lg_issue": fmt(lg["issue_acc"]),
        "lg_ret5": fmt(lg["retrieval_recall_at_5"]),
        "aggressive_aux": fmt(aggressive["aux_top1"]),
        "aggressive_issue": fmt(aggressive["issue_acc"]),
        "aggressive_ret5": fmt(aggressive["retrieval_recall_at_5"]),
        "stress_lg": fmt(row(utility, "c5_linkguard")["stress_utility_score"]),
        "stress_direct": fmt(row(utility, "c1_direct_redaction")["stress_utility_score"]),
        "stress_aggressive": fmt(row(utility, "c6_aggressive_redaction")["stress_utility_score"]),
        "tier_direct_t1": fmt(tier_metric("c1_direct_redaction", "T1")),
        "tier_direct_t2": fmt(tier_metric("c1_direct_redaction", "T2")),
        "tier_direct_t3": fmt(tier_metric("c1_direct_redaction", "T3")),
        "tier_lg_t1": fmt(tier_metric("c5_linkguard", "T1")),
        "tier_lg_t2": fmt(tier_metric("c5_linkguard", "T2")),
        "tier_lg_t3": fmt(tier_metric("c5_linkguard", "T3")),
        "ci_direct": "0.708 [0.615, 0.802]",
        "ci_presidio": "0.594 [0.490, 0.698]",
        "ci_lg": "0.042 [0.010, 0.083]",
        "multiseed_direct": fmt(row(multiseed, "c1_direct_redaction")["aux_top1_mean"]),
        "multiseed_presidio": fmt(row(multiseed, "c1b_presidio_redaction")["aux_top1_mean"]),
        "multiseed_local": fmt(row(multiseed, "c4_doc_local_anon")["aux_top1_mean"]),
        "multiseed_lg": fmt(row(multiseed, "c5_linkguard")["aux_top1_mean"]),
        "attack_direct_min": fmt(
            attack[attack["condition"] == "c1_direct_redaction"]["aux_top1"].min()
        ),
        "attack_direct_max": fmt(
            attack[attack["condition"] == "c1_direct_redaction"]["aux_top1"].max()
        ),
        "attack_local_min": fmt(
            attack[attack["condition"] == "c4_doc_local_anon"]["aux_top1"].min()
        ),
        "attack_local_max": fmt(
            attack[attack["condition"] == "c4_doc_local_anon"]["aux_top1"].max()
        ),
        "attack_lg_min": fmt(
            attack[attack["condition"] == "c5_linkguard"]["aux_top1"].min()
        ),
        "attack_lg_max": fmt(
            attack[attack["condition"] == "c5_linkguard"]["aux_top1"].max()
        ),
        "field_k1": fmt(sensitivity.iloc[0]["field_aux_top1"]),
        "field_k5": fmt(k5["field_aux_top1"]),
        "field_k20": fmt(k20["field_aux_top1"]),
        "corpus_awareness_true_cover": fmt(ca_true["target_k_coverage"]),
        "corpus_awareness_shuffled_cover": fmt(ca_shuffled["target_k_coverage"]),
        "corpus_awareness_shuffled_min": fmt(ca_shuffled["min_true_estimated_k"]),
        "corpus_awareness_global_field": fmt(ca_global["field_aux_top1"]),
        "rag_lg_t3_hit5": fmt(rag_t3_value("c5_linkguard", "hit_at_5")),
        "rag_lg_t3_multi10": "Multi@10 to 0.000",
        "rag_query_verbose_direct": fmt(rag_query_value("c1_direct_redaction", "verbose")),
        "rag_query_verbose_lg": fmt(rag_query_value("c5_linkguard", "verbose")),
        "rag_query_verbose_aggressive": fmt(rag_query_value("c6_aggressive_redaction", "verbose")),
        "rag_query_short_direct": fmt(rag_query_value("c1_direct_redaction", "short")),
        "rag_query_short_lg": fmt(rag_query_value("c5_linkguard", "short")),
        "rag_context_direct_exact": fmt(
            rag_context_t3_value("c1_direct_redaction", "exact_fields_recovered")
        ),
        "rag_context_lg_coarse": fmt(
            rag_context_t3_value("c5_linkguard", "coarse_fields_recovered")
        ),
        "gpt55_direct": fmt(weighted_openai(gpt55, "c1_direct_redaction")["top1"]),
        "gpt55_presidio": fmt(weighted_openai(gpt55, "c1b_presidio_redaction")["top1"]),
        "gpt55_local": fmt(weighted_openai(gpt55, "c4_doc_local_anon")["top1"]),
        "gpt55_lg": fmt(weighted_openai(gpt55, "c5_linkguard")["top1"]),
        "gpt55_lg_top3": fmt(weighted_openai(gpt55, "c5_linkguard")["top3"]),
        "gpt55_lg_uncertainty": fmt(
            weighted_openai(gpt55, "c5_linkguard")["uncertain_rate"]
        ),
        "gpt55_aggressive": fmt(
            weighted_openai(gpt55, "c6_aggressive_redaction")["top1"]
        ),
        "gpt55_doclocal_top1": fmt(
            weighted_openai(gpt55_doclocal, "c4_openai_doc_local_gpt55_24p")["top1"]
        ),
        "gpt55_doclocal_lg_subset": fmt(
            weighted_openai(gpt55_doclocal, "c5_linkguard")["top1"]
        ),
        "gpt55_evidence_direct_location": fmt(
            gpt55_evidence[gpt55_evidence["bucket"] == "direct_success"][
                "location_signal_rate"
            ].iloc[0]
        ),
        "gpt55_evidence_direct_role": fmt(
            gpt55_evidence[gpt55_evidence["bucket"] == "direct_success"][
                "role_signal_rate"
            ].iloc[0]
        ),
        "gpt55_evidence_lg_uncertain": fmt(
            gpt55_evidence[gpt55_evidence["bucket"] == "linkguard_residual"][
                "uncertain_rate"
            ].iloc[0]
        ),
    }
    for name, fragment in colm_core_claims.items():
        add_check(
            checks,
            f"colm:{name}",
            contains(colm_text, fragment),
            f"COLM submission contains core claim fragment {fragment}",
            "paper/colm2026_submission.tex",
            expected=fragment,
            observed=fragment if contains(colm_text, fragment) else "missing",
        )
    plan = pd.read_csv(results_dir / "openai_audit_plan.csv")
    add_check(
        checks,
        "openai:plan_fully_cached",
        len(plan) == int(plan["cached"].sum()),
        "OpenAI audit plan has no missing calls",
        "results/openai_audit_plan.csv",
        expected=str(len(plan)),
        observed=str(int(plan["cached"].sum())),
    )
    gpt55_plan = pd.read_csv(results_dir / "openai_gpt55_48p_audit_plan.csv")
    add_check(
        checks,
        "gpt55:plan_fully_cached",
        len(gpt55_plan) == int(gpt55_plan["cached"].sum()),
        "GPT-5.5 audit plan has no missing calls",
        "results/openai_gpt55_48p_audit_plan.csv",
        expected=str(len(gpt55_plan)),
        observed=str(int(gpt55_plan["cached"].sum())),
    )
    gpt55_doclocal_plan = pd.read_csv(results_dir / "openai_gpt55_doclocal_24p_audit_plan.csv")
    add_check(
        checks,
        "gpt55_doclocal:plan_fully_cached",
        len(gpt55_doclocal_plan) == int(gpt55_doclocal_plan["cached"].sum()),
        "GPT-5.5 document-local audit plan has no missing calls",
        "results/openai_gpt55_doclocal_24p_audit_plan.csv",
        expected=str(len(gpt55_doclocal_plan)),
        observed=str(int(gpt55_doclocal_plan["cached"].sum())),
    )
    gpt55_evidence_plan = pd.read_csv(results_dir / "openai_gpt55_evidence_24p_audit_plan.csv")
    add_check(
        checks,
        "gpt55_evidence:plan_fully_cached",
        len(gpt55_evidence_plan) == int(gpt55_evidence_plan["cached"].sum()),
        "GPT-5.5 evidence audit plan has no missing calls",
        "results/openai_gpt55_evidence_24p_audit_plan.csv",
        expected=str(len(gpt55_evidence_plan)),
        observed=str(int(gpt55_evidence_plan["cached"].sum())),
    )
    gpt55_rag_plan = pd.read_csv(results_dir / "openai_gpt55_rag_12t3_audit_plan.csv")
    rag_conditions = set(gpt55_rag_plan["condition"])
    rag_personas = set(gpt55_rag_plan["persona_id"])
    rag_cached = int(gpt55_rag_plan["cached"].sum())
    expected_rag_cached = 10 + 10 * len(rag_batch_run_names)
    expected_rag_pending = 60 - expected_rag_cached
    add_check(
        checks,
        "gpt55_rag_generation:plan_shape",
        len(gpt55_rag_plan) == 60
        and len(rag_conditions) == 5
        and len(rag_personas) == 12
        and rag_cached == expected_rag_cached
        and "json_object" in set(gpt55_rag_plan.get("text_format", pd.Series(dtype=str)).astype(str))
        and set(gpt55_rag_plan.get("max_output_tokens", pd.Series(dtype=int)).astype(int)) == {250},
        "GPT-5.5 RAG generation audit plan is fully cached across compact pilot plus cache-fill batches",
        "results/openai_gpt55_rag_12t3_audit_plan.csv",
        expected=(
            "60 planned calls, 5 conditions, 12 personas, compact JSON, "
            f"{expected_rag_cached} cached and {expected_rag_pending} pending"
        ),
        observed=(
            f"{len(gpt55_rag_plan)} calls, {len(rag_conditions)} conditions, "
            f"{len(rag_personas)} personas, {rag_cached} cached, "
            f"{len(gpt55_rag_plan) - rag_cached} pending"
        ),
    )
    rag_pilot_rows = pd.read_csv(results_dir / "openai_gpt55_rag_compact_pilot_2t3_rag_generation_rows.csv")
    rag_pilot_summary = pd.read_csv(
        results_dir / "openai_gpt55_rag_compact_pilot_2t3_rag_generation_summary.csv"
    )
    add_check(
        checks,
        "gpt55_rag_compact_pilot:parse_success",
        len(rag_pilot_rows) == 10
        and len(set(rag_pilot_rows["condition"])) == 5
        and len(set(rag_pilot_rows["persona_id"])) == 2
        and bool(rag_pilot_rows["parse_success"].astype(bool).all())
        and float(rag_pilot_summary["parse_success_rate"].min()) == 1.0,
        "compact GPT-5.5 RAG pilot parsed all cached JSON responses but is not a full paper claim",
        "results/openai_gpt55_rag_compact_pilot_2t3_rag_generation_rows.csv",
        expected="10 rows, 5 conditions, 2 personas, parse_success_rate 1.000",
        observed=(
            f"{len(rag_pilot_rows)} rows, {len(set(rag_pilot_rows['condition']))} conditions, "
            f"{len(set(rag_pilot_rows['persona_id']))} personas, "
            f"min_parse={float(rag_pilot_summary['parse_success_rate'].min()):.3f}"
        ),
    )
    rag_full_rows = pd.read_csv(results_dir / "openai_gpt55_rag_12t3_rag_generation_rows.csv")
    rag_full_summary = pd.read_csv(results_dir / "openai_gpt55_rag_12t3_rag_generation_summary.csv")
    add_check(
        checks,
        "gpt55_rag_generation:full_parse_success",
        len(rag_full_rows) == 60
        and len(set(rag_full_rows["condition"])) == 5
        and len(set(rag_full_rows["persona_id"])) == 12
        and bool(rag_full_rows["parse_success"].astype(bool).all())
        and float(rag_full_summary["parse_success_rate"].min()) == 1.0
        and float(
            rag_full_summary[
                rag_full_summary["condition"] == "c1_direct_redaction"
            ]["likely_same_person_rate"].iloc[0]
        )
        == 1.0
        and float(
            rag_full_summary[
                rag_full_summary["condition"] == "c5_linkguard"
            ]["likely_same_person_rate"].iloc[0]
        )
        < 0.5
        and float(
            rag_full_summary[
                rag_full_summary["condition"] == "c6_aggressive_redaction"
            ]["likely_same_person_rate"].iloc[0]
        )
        == 0.0,
        "completed GPT-5.5 RAG-generation stress audit parsed all responses and preserves the expected ordering",
        "results/openai_gpt55_rag_12t3_rag_generation_summary.csv",
        expected="60 rows, 12 personas, parse_success_rate 1.000, direct same-person 1.000, LinkGuard <0.500, aggressive 0.000",
        observed=(
            f"{len(rag_full_rows)} rows, {len(set(rag_full_rows['persona_id']))} personas, "
            f"min_parse={float(rag_full_summary['parse_success_rate'].min()):.3f}"
        ),
    )
    for run_name in rag_batch_run_names:
        rag_batch_rows = pd.read_csv(results_dir / f"openai_{run_name}_rag_generation_rows.csv")
        rag_batch_summary = pd.read_csv(results_dir / f"openai_{run_name}_rag_generation_summary.csv")
        rag_batch_plan = pd.read_csv(results_dir / f"openai_{run_name}_audit_plan.csv")
        add_check(
            checks,
            f"{run_name}:parse_success",
            len(rag_batch_rows) == 10
            and len(set(rag_batch_rows["condition"])) == 5
            and len(set(rag_batch_rows["persona_id"])) == 2
            and bool(rag_batch_rows["parse_success"].astype(bool).all())
            and int(rag_batch_plan["cached"].sum()) == 10
            and float(rag_batch_summary["parse_success_rate"].min()) == 1.0,
            "10-call GPT-5.5 RAG cache-fill batch parsed cleanly but is not a full paper claim",
            f"results/openai_{run_name}_rag_generation_rows.csv",
            expected="10 rows, 5 conditions, 2 personas, 10 cached calls, parse_success_rate 1.000",
            observed=(
                f"{len(rag_batch_rows)} rows, {len(set(rag_batch_rows['condition']))} conditions, "
                f"{len(set(rag_batch_rows['persona_id']))} personas, "
                f"cached={int(rag_batch_plan['cached'].sum())}, "
                f"min_parse={float(rag_batch_summary['parse_success_rate'].min()):.3f}"
            ),
        )
    rag_budget = pd.read_csv(results_dir / "openai_gpt55_rag_12t3_budget.csv")
    rag_budget_md = (results_dir / "openai_gpt55_rag_12t3_budget.md").read_text(encoding="utf-8")
    expected_remaining_batches = expected_rag_pending // 10
    if expected_rag_pending == 0:
        budget_shape_ok = rag_budget.empty
        budget_observed = f"{len(rag_budget)} batches, 0 calls, tokens=0"
    else:
        budget_shape_ok = (
            len(rag_budget) == expected_remaining_batches
            and int(rag_budget["new_calls"].sum()) == expected_rag_pending
            and int(rag_budget["new_calls"].max()) == 10
            and int(rag_budget["conditions"].min()) == 5
            and int(rag_budget["estimated_total_tokens"].sum()) > 0
        )
        budget_observed = (
            f"{len(rag_budget)} batches, {int(rag_budget['new_calls'].sum())} calls, "
            f"max={int(rag_budget['new_calls'].max())}, "
            f"tokens={int(rag_budget['estimated_total_tokens'].sum())}"
        )
    add_check(
        checks,
        "gpt55_rag_budget:batch_shape",
        budget_shape_ok,
        "RAG-generation API budget reflects the remaining optional run state",
        "results/openai_gpt55_rag_12t3_budget.csv",
        expected=f"{expected_remaining_batches} batches, {expected_rag_pending} pending calls, max 10 calls per batch",
        observed=budget_observed,
    )
    if expected_rag_pending == 0:
        batch_commands_ok = rag_budget.empty and "_No pending calls._" in rag_budget_md
        batch_commands_observed = "no pending calls"
    else:
        batch_commands_ok = (
            rag_budget["command"].astype(str).str.contains("--persona-ids").all()
            and rag_budget["command"].astype(str).str.contains("--max-calls 10").all()
            and rag_budget["batch_run_name"].astype(str).str.startswith("gpt55_rag_12t3_batch").all()
            and set(rag_budget["batch_run_name"].astype(str)).isdisjoint(set(rag_batch_run_names))
            and not has_local_path_marker("\n".join(rag_budget["command"].astype(str).tolist()))
        )
        batch_commands_observed = "ok"
    add_check(
        checks,
        "gpt55_rag_budget:batch_commands",
        batch_commands_ok,
        "RAG-generation batch commands use explicit persona subsets while pending, or report no pending calls when complete",
        "results/openai_gpt55_rag_12t3_budget.csv",
        expected="remaining persona subset commands or no pending calls, no local key path marker",
        observed=batch_commands_observed,
    )
    add_check(
        checks,
        "gpt55_rag_budget:markdown_boundary",
        "This report makes no API calls" in rag_budget_md
        and "Use one command at a time only after explicit approval for paid API calls" in rag_budget_md
        and not has_local_path_marker(rag_budget_md),
        "RAG-generation budget markdown states no-call generation and paid-call approval boundary",
        "results/openai_gpt55_rag_12t3_budget.md",
        expected="no API calls, explicit approval language, no local path markers",
        observed="ok" if "This report makes no API calls" in rag_budget_md else "missing",
    )
    provenance = pd.read_csv(results_dir / "api_audit_provenance.csv")
    provenance_md = (results_dir / "api_audit_provenance.md").read_text(encoding="utf-8")
    expected_provenance_runs = {
        "legacy_openai_aux_doclocal",
        "gpt55_aux_48p",
        "gpt55_doclocal_24p",
        "gpt55_evidence_24p",
        "gpt55_rag_12t3",
        "gpt55_rag_compact_pilot_2t3",
    }
    expected_provenance_runs.update(rag_batch_run_names)
    provenance_runs = set(provenance["run_id"].astype(str))
    add_check(
        checks,
        "api_provenance:run_inventory",
        provenance_runs == expected_provenance_runs,
        "API provenance manifest covers all cached or planned OpenAI audit runs",
        "results/api_audit_provenance.csv",
        expected=";".join(sorted(expected_provenance_runs)),
        observed=";".join(sorted(provenance_runs)),
    )
    paper_api_runs = provenance[
        provenance["paper_claim_status"].astype(str).str.startswith("paper_facing")
    ]
    add_check(
        checks,
        "api_provenance:paper_facing_runs_cached",
        len(paper_api_runs) == 4
        and int(paper_api_runs["missing_calls"].sum()) == 0
        and set(paper_api_runs["run_id"])
        == {"gpt55_aux_48p", "gpt55_doclocal_24p", "gpt55_evidence_24p", "gpt55_rag_12t3"},
        "paper-facing GPT-5.5 API stress audits are complete cached runs",
        "results/api_audit_provenance.csv",
        expected="4 paper-facing GPT-5.5 rows, zero missing calls",
        observed=f"{len(paper_api_runs)} rows, {int(paper_api_runs['missing_calls'].sum())} missing",
    )
    rag_provenance = provenance[provenance["run_id"] == "gpt55_rag_12t3"].iloc[0]
    add_check(
        checks,
        "api_provenance:rag_generation_stress_audit",
        int(rag_provenance["planned_calls"]) == 60
        and int(rag_provenance["cached_calls"]) == expected_rag_cached
        and int(rag_provenance["missing_calls"]) == expected_rag_pending
        and int(rag_provenance["usage_total_tokens"]) > 0
        and str(rag_provenance["paper_claim_status"])
        == "paper_facing_cached_rag_generation_stress_audit",
        "API provenance records completed RAG generation as a cached synthetic stress audit",
        "results/api_audit_provenance.csv",
        expected=f"60 planned, {expected_rag_cached} cached, {expected_rag_pending} missing, paper-facing stress audit",
        observed=(
            f"{int(rag_provenance['planned_calls'])} planned, "
            f"{int(rag_provenance['cached_calls'])} cached, "
            f"{int(rag_provenance['missing_calls'])} missing, "
            f"{rag_provenance['paper_claim_status']}"
        ),
    )
    for run_name in rag_batch_run_names:
        rag_batch_provenance = provenance[provenance["run_id"] == run_name].iloc[0]
        add_check(
            checks,
            f"api_provenance:{run_name}_non_claim",
            int(rag_batch_provenance["planned_calls"]) == 10
            and int(rag_batch_provenance["cached_calls"]) == 10
            and int(rag_batch_provenance["missing_calls"]) == 0
            and int(rag_batch_provenance["usage_total_tokens"]) > 0
            and str(rag_batch_provenance["paper_claim_status"]) == "partial_cache_fill_not_paper_claim",
            "API provenance records completed RAG batch as a partial cache-fill run, not a paper claim",
            "results/api_audit_provenance.csv",
            expected="10 planned, 10 cached, partial cache-fill not paper claim",
            observed=(
                f"{int(rag_batch_provenance['planned_calls'])} planned, "
                f"{int(rag_batch_provenance['cached_calls'])} cached, "
                f"{rag_batch_provenance['paper_claim_status']}"
            ),
        )
    add_check(
        checks,
        "api_provenance:privacy_protocol",
        provenance["store_false_protocol"].astype(str).str.lower().eq("true").all()
        and provenance["data_scope"].astype(str).eq("synthetic transformed benchmark records only").all(),
        "API provenance records store=False and synthetic-data-only protocol",
        "results/api_audit_provenance.csv",
        expected="store_false_protocol true and synthetic transformed benchmark records only",
        observed="ok"
        if provenance["store_false_protocol"].astype(str).str.lower().eq("true").all()
        else "missing store_false",
    )
    add_check(
        checks,
        "api_provenance:markdown_boundary",
        "This command makes no API calls" in provenance_md
        and "Completed 12-person RAG-generation stress audit" in provenance_md,
        "API provenance markdown states the no-call generation path and completed RAG stress-audit boundary",
        "results/api_audit_provenance.md",
        expected="no API calls and completed RAG stress-audit language",
        observed="ok"
        if "This command makes no API calls" in provenance_md
        else "missing no-call language",
    )
    result_brief = (results_dir / "paper_ready_summary.md").read_text(encoding="utf-8")
    add_check(
        checks,
        "result_brief:rag_generation_boundary",
        "GPT-5.5 RAG Generation Stress Audit" in result_brief
        and f"fully cached at {expected_rag_cached}/60 calls" in result_brief
        and "Remaining RAG-generation calls: 0." in result_brief,
        "paper-ready result brief records the completed RAG-generation stress audit",
        "results/paper_ready_summary.md",
        expected=f"completed RAG stress audit documented with {expected_rag_cached}/60 cached calls",
        observed="ok" if "GPT-5.5 RAG Generation Stress Audit" in result_brief else "missing",
    )
    abstract_rag_fragment = "Cached GPT-5.5 auxiliary and RAG-generation stress audits preserve this ordering"
    add_check(
        checks,
        "paper:abstract_rag_generation_stress_audit",
        contains(paper_text, abstract_rag_fragment) and contains(colm_text, abstract_rag_fragment),
        "both paper drafts mention completed GPT-5.5 auxiliary and RAG-generation stress audits in the abstract",
        "paper/short_paper.tex;paper/colm2026_submission.tex",
        expected=abstract_rag_fragment,
        observed=abstract_rag_fragment
        if contains(paper_text, abstract_rag_fragment) and contains(colm_text, abstract_rag_fragment)
        else "missing",
    )
    add_check(
        checks,
        "result_brief:gpt55_caveat_current",
        "GPT-5.5 audits are cached, time-stamped synthetic subset stress audits" in result_brief
        and "The OpenAI audit is a small subset" not in result_brief,
        "paper-ready result brief has current GPT-5.5 audit caveat language",
        "results/paper_ready_summary.md",
        expected="current GPT-5.5 caveat and no stale small-audit caveat",
        observed="ok"
        if "GPT-5.5 audits are cached, time-stamped synthetic subset stress audits" in result_brief
        else "missing",
    )
    reproduce_text = (root / "REPRODUCE_RESULTS.md").read_text(encoding="utf-8")
    readiness_text = (root / "SUBMISSION_READINESS.md").read_text(encoding="utf-8")
    research_notes = (results_dir / "research_notes.md").read_text(encoding="utf-8")
    add_check(
        checks,
        "reproduce_results:claim_verifier_count",
        "Expected current result: `checks=486 failures=0`." in reproduce_text,
        "reproduction guide reports the current claim verifier count",
        "REPRODUCE_RESULTS.md",
        expected="Expected current result: `checks=486 failures=0`.",
        observed="ok"
        if "Expected current result: `checks=486 failures=0`." in reproduce_text
        else "missing",
    )
    add_check(
        checks,
        "submission_readiness:claim_verifier_count",
        "Main claim verifier: `checks=486 failures=0`." in readiness_text,
        "submission readiness audit reports the current claim verifier count",
        "SUBMISSION_READINESS.md",
        expected="Main claim verifier: `checks=486 failures=0`.",
        observed="ok"
        if "Main claim verifier: `checks=486 failures=0`." in readiness_text
        else "missing",
    )
    readiness_rag_claim = (
        "GPT-5.5 RAG generation over retrieved synthetic records preserves the exposure ordering."
    )
    add_check(
        checks,
        "submission_readiness:rag_generation_claim_ready",
        readiness_rag_claim in readiness_text,
        "submission readiness lists the completed GPT-5.5 RAG-generation claim",
        "SUBMISSION_READINESS.md",
        expected=readiness_rag_claim,
        observed=readiness_rag_claim if readiness_rag_claim in readiness_text else "missing",
    )
    add_check(
        checks,
        "research_notes:scope_current",
        "deterministic no-API local benchmark" in research_notes
        and "Cached GPT-5.5 stress-audit results" in research_notes
        and "API-free first pass" not in research_notes,
        "research notes distinguish local no-API benchmark notes from cached GPT-5.5 audit artifacts",
        "results/research_notes.md",
        expected="local notes plus cached GPT-5.5 provenance pointer",
        observed="ok"
        if "deterministic no-API local benchmark" in research_notes
        else "missing",
    )

    # Check that paper tables reflect the generated sources for core tables.
    table_checks = {
        "paper/tables/paper_main_results.tex": [fmt(lg["aux_top1"]), fmt(aggressive["issue_acc"])],
        "paper/tables/openai_aux_audit.tex": [fmt(weighted_openai(openai, "c5_linkguard")["top1"]), "12"],
        "paper/tables/gpt55_aux_audit.tex": [
            fmt(weighted_openai(gpt55, "c5_linkguard")["top1"]),
            fmt(weighted_openai(gpt55, "c5_linkguard")["uncertain_rate"]),
            "48",
        ],
        "paper/tables/gpt55_doclocal_audit.tex": [
            fmt(weighted_openai(gpt55_doclocal, "c4_openai_doc_local_gpt55_24p")["top1"]),
            fmt(weighted_openai(gpt55_doclocal, "c5_linkguard")["top1"]),
            "24",
        ],
        "paper/tables/gpt55_evidence_signals.tex": [
            "Direct success",
            fmt(
                gpt55_evidence[gpt55_evidence["bucket"] == "direct_success"][
                    "role_signal_rate"
                ].iloc[0]
            ),
            fmt(
                gpt55_evidence[gpt55_evidence["bucket"] == "linkguard_residual"][
                    "uncertain_rate"
                ].iloc[0]
            ),
        ],
        "paper/tables/linkguard_sensitivity.tex": [
            fmt(k2["aux_top1"]),
            fmt(k5["attr_exact_recovery"]),
            fmt(k20["field_aux_top1"]),
        ],
        "paper/tables/corpus_awareness_ablation.tex": [
            fmt(ca_true["aux_top1"]),
            fmt(ca_shuffled["aux_top1"]),
            fmt(ca_shuffled["target_k_coverage"]),
            fmt(ca_suppression["edit_ratio"]),
        ],
        "paper/tables/tier_aux_results.tex": [
            fmt(tier_metric("c1_direct_redaction", "T3")),
            fmt(tier_metric("c5_linkguard", "T3")),
        ],
        "paper/tables/rag_exposure_t3.tex": [
            fmt(rag_t3_value("c5_linkguard", "hit_at_5")),
            fmt(rag_t3_value("c1_direct_redaction", "multi_doc_at_10")),
        ],
        "paper/tables/rag_query_sensitivity.tex": [
            fmt(rag_query_value("c1_direct_redaction", "short")),
            fmt(rag_query_value("c5_linkguard", "short")),
            fmt(rag_query_value("c5_linkguard", "verbose")),
        ],
        "paper/tables/rag_context_recovery_t3.tex": [
            fmt(rag_context_t3_value("c1_direct_redaction", "exact_fields_recovered")),
            fmt(rag_context_t3_value("c4_doc_local_anon", "coarse_fields_recovered")),
            fmt(rag_context_t3_value("c5_linkguard", "coarse_fields_recovered")),
        ],
        "paper/tables/noisy_style_stress.tex": [
            fmt(noisy_direct["aux_top1"]),
            fmt(noisy_lg["aux_top1"]),
            fmt(noisy_aggressive["issue_acc"]),
        ],
    }
    for rel, fragments in table_checks.items():
        table_text = (root / rel).read_text(encoding="utf-8")
        for fragment in fragments:
            add_check(
                checks,
                f"table:{rel}:{fragment}",
                contains(table_text, fragment),
                f"generated table contains {fragment}",
                rel,
                expected=fragment,
                observed=fragment if contains(table_text, fragment) else "missing",
            )

    rows = [check.__dict__ for check in checks]
    df = pd.DataFrame(rows)
    out_json = results_dir / "claim_verification.json"
    out_md = results_dir / "claim_verification.md"
    out_json.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")

    summary = df.groupby("status").size().reset_index(name="n")
    failed = df[df["status"] != "PASS"]
    lines = [
        "# Claim Verification Report",
        "",
        "## Summary",
        "",
        dataframe_to_markdown(summary, floatfmt=".0f"),
        "",
        "## Checks",
        "",
        dataframe_to_markdown(df, floatfmt=".3f"),
    ]
    if not failed.empty:
        lines.extend(["", "## Failures", "", dataframe_to_markdown(failed, floatfmt=".3f")])
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    n_fail = int((df["status"] != "PASS").sum())
    print(out_md)
    print(f"checks={len(df)} failures={n_fail}")
    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
