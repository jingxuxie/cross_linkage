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
    return {
        "n": n,
        "top1": float((group["top1"] * group["n"]).sum() / n),
        "top3": float((group["top3"] * group["n"]).sum() / n),
    }


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
        "results/multiseed/claim_summary.csv",
        "results/candidate_sensitivity.csv",
        "results/attack_sensitivity.csv",
        "results/linkguard_failure_analysis.csv",
        "results/utility_stress.csv",
        "results/rag_exposure.csv",
        "results/rag_exposure_rows.csv",
        "results/rag_exposure_by_tier.csv",
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
        "results/openai_aux_match_summary.csv",
        "results/openai_audit_plan.csv",
        "results/paper_ready_summary.md",
        "SUBMISSION_UPLOAD_CHECKLIST.md",
        "paper/tables/paper_main_results.tex",
        "paper/tables/linkguard_sensitivity.tex",
        "paper/tables/tier_aux_results.tex",
        "paper/tables/openai_aux_audit.tex",
        "paper/tables/rag_exposure_t3.tex",
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
        "Verified against the official workshop page on 2026-06-27",
        "Workshop on Responsibly Enabling Data for Foundation Models at COLM 2026",
        "https://re-data-colm2026.github.io/",
        "Submission system: OpenReview",
        "COLM 2026 template",
        "short paper",
        "up to 4 pages",
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
        ("paper/short_paper.pdf", 4),
        ("paper/colm2026_submission.pdf", 4),
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
        clean_compile.get("pdf_pages") == 4,
        "clean-room compiled submission PDF has four pages",
        "submission/submission_manifest.json",
        expected="4",
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
        pdf_pages(submission_pdf) == 4,
        "packaged submission PDF has expected page count",
        "submission/colm2026_submission.pdf",
        expected="4",
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
        and "PDF pages: 4" in manifest_md_text,
        "human-readable manifest summarizes clean package status",
        "submission/submission_manifest.md",
        expected="clean compile true, checks passed true, 4 pages",
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

    openai = pd.read_csv(results_dir / "openai_aux_match_summary.csv")
    for condition in [
        "c1_direct_redaction",
        "c4_doc_local_anon",
        "c4_openai_doc_local",
        "c5_linkguard",
    ]:
        stats = weighted_openai(openai, condition)
        fragment = fmt(stats["top1"])
        add_check(
            checks,
            f"openai:{condition}:top1",
            stats["n"] == 12 and contains(paper_text, fragment),
            f"paper contains 12-person OpenAI top-1 value {fragment}",
            "results/openai_aux_match_summary.csv",
            expected=f"n=12,{fragment}",
            observed=f"n={stats['n']},{fragment if contains(paper_text, fragment) else 'missing'}",
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
        "rag_lg_t3_hit5": fmt(rag_t3_value("c5_linkguard", "hit_at_5")),
        "rag_lg_t3_multi10": "Multi@10 to 0.000",
        "openai_direct": fmt(weighted_openai(openai, "c1_direct_redaction")["top1"]),
        "openai_doc_local": fmt(weighted_openai(openai, "c4_openai_doc_local")["top1"]),
        "openai_lg": fmt(weighted_openai(openai, "c5_linkguard")["top1"]),
        "openai_aggressive": fmt(weighted_openai(openai, "c6_aggressive_redaction")["top1"]),
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

    # Check that paper tables reflect the generated sources for core tables.
    table_checks = {
        "paper/tables/paper_main_results.tex": [fmt(lg["aux_top1"]), fmt(aggressive["issue_acc"])],
        "paper/tables/openai_aux_audit.tex": [fmt(weighted_openai(openai, "c5_linkguard")["top1"]), "12"],
        "paper/tables/linkguard_sensitivity.tex": [
            fmt(k2["aux_top1"]),
            fmt(k5["attr_exact_recovery"]),
            fmt(k20["field_aux_top1"]),
        ],
        "paper/tables/tier_aux_results.tex": [
            fmt(tier_metric("c1_direct_redaction", "T3")),
            fmt(tier_metric("c5_linkguard", "T3")),
        ],
        "paper/tables/rag_exposure_t3.tex": [
            fmt(rag_t3_value("c5_linkguard", "hit_at_5")),
            fmt(rag_t3_value("c1_direct_redaction", "multi_doc_at_10")),
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
