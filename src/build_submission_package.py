#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_FILES = [
    "colm2026_submission.tex",
    "colm2026_conference.sty",
    "colm2026_conference.bst",
    "natbib.sty",
    "fancyhdr.sty",
    "math_commands.tex",
]
README_NAME = "README_SUBMISSION_PACKAGE.md"
PDF_NAME = "colm2026_submission.pdf"
ZIP_NAME = "colm2026_submission_source.zip"
MANIFEST_JSON = "submission_manifest.json"
MANIFEST_MD = "submission_manifest.md"
EXPECTED_SUBMISSION_PAGES = 8
LATEXMK_CMD = [
    "latexmk",
    "-g",
    "-pdf",
    "-interaction=nonstopmode",
    "-halt-on-error",
    "colm2026_submission.tex",
]
LOG_PROBLEM_PATTERNS = [
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
LOCAL_PATH_MARKERS = ("/home/" + "eston", "colm_" + "workshop")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_text(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def pdf_pages(path: Path) -> int | None:
    try:
        info = run_text(["pdfinfo", str(path)], path.parent)
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in info.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return None


def pdf_info_field(path: Path, field: str) -> str:
    try:
        info = run_text(["pdfinfo", str(path)], path.parent)
    except (OSError, subprocess.CalledProcessError):
        return ""
    prefix = f"{field}:"
    for line in info.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def pdf_text(path: Path) -> str:
    try:
        return run_text(["pdftotext", "-layout", str(path), "-"], path.parent)
    except (OSError, subprocess.CalledProcessError):
        return ""


def has_local_path_marker(text: str) -> bool:
    return any(marker in text for marker in LOCAL_PATH_MARKERS)


def log_problem_lines(path: Path) -> list[str]:
    if not path.exists():
        return ["missing log"]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line for line in lines if any(pattern in line for pattern in LOG_PROBLEM_PATTERNS)]


def readme_text() -> str:
    return "\n".join(
        [
            "# COLM 2026 Submission Source",
            "",
            "Compile from this directory with:",
            "",
            "```bash",
            "latexmk -pdf -interaction=nonstopmode -halt-on-error colm2026_submission.tex",
            "```",
            "",
            "The PDF upload target is `colm2026_submission.pdf` in the parent submission package.",
            "",
        ]
    )


def copy_sources(paper_dir: Path, source_dir: Path) -> list[Path]:
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)
    copied = []
    for name in SOURCE_FILES:
        src = paper_dir / name
        dst = source_dir / name
        if not src.exists() or src.stat().st_size == 0:
            raise FileNotFoundError(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    readme = source_dir / README_NAME
    readme.write_text(readme_text(), encoding="utf-8")
    copied.append(readme)
    return copied


def make_source_zip(source_dir: Path, out_path: Path) -> list[str]:
    members = SOURCE_FILES + [README_NAME]
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            archive.write(source_dir / member, arcname=member)
    return members


def clean_compile_check(source_dir: Path, keep_temp: bool = False) -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="crosslinkage-colm-source-"))
    work_dir = temp_root / "source"
    shutil.copytree(source_dir, work_dir)
    env = os.environ.copy()
    env.setdefault("SOURCE_DATE_EPOCH", "1782518400")
    try:
        result = subprocess.run(
            LATEXMK_CMD,
            cwd=work_dir,
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        compiled_pdf = work_dir / PDF_NAME
        compiled_log = work_dir / "colm2026_submission.log"
        text = pdf_text(compiled_pdf) if compiled_pdf.exists() else ""
        problems = log_problem_lines(compiled_log)
        status = (
            result.returncode == 0
            and compiled_pdf.exists()
            and pdf_pages(compiled_pdf) == EXPECTED_SUBMISSION_PAGES
            and not problems
            and "Anonymous authors" in text
            and "Paper under double-blind review" in text
            and pdf_info_field(compiled_pdf, "Author") == ""
            and not has_local_path_marker(text)
        )
        return {
            "status": bool(status),
            "command": LATEXMK_CMD,
            "returncode": int(result.returncode),
            "temp_dir": str(work_dir) if keep_temp else "",
            "pdf_pages": pdf_pages(compiled_pdf) if compiled_pdf.exists() else None,
            "log_problem_count": len(problems),
            "log_problems": problems[:10],
            "anonymous_header": "Anonymous authors" in text
            and "Paper under double-blind review" in text,
            "author_metadata_blank": pdf_info_field(compiled_pdf, "Author") == ""
            if compiled_pdf.exists()
            else False,
            "no_local_paths": not has_local_path_marker(text),
        }
    finally:
        if not keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)


def build_manifest(
    root: Path,
    paper_dir: Path,
    package_dir: Path,
    source_dir: Path,
    source_members: list[str],
    clean_compile: dict[str, Any],
) -> dict[str, Any]:
    pdf_path = package_dir / PDF_NAME
    zip_path = package_dir / ZIP_NAME
    source_hashes = [
        {
            "path": f"colm2026_source/{member}",
            "bytes": (source_dir / member).stat().st_size,
            "sha256": sha256_file(source_dir / member),
        }
        for member in source_members
    ]
    paper_hashes = [
        {
            "path": f"paper/{member}",
            "bytes": (paper_dir / member).stat().st_size,
            "sha256": sha256_file(paper_dir / member),
        }
        for member in SOURCE_FILES
    ]
    checks_passed = (
        bool(clean_compile.get("status"))
        and pdf_pages(pdf_path) == EXPECTED_SUBMISSION_PAGES
    )
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package_dir": "submission",
        "source_dir": "submission/colm2026_source",
        "source_zip": {
            "path": f"submission/{ZIP_NAME}",
            "bytes": zip_path.stat().st_size,
            "sha256": sha256_file(zip_path),
            "members": source_members,
        },
        "submission_pdf": {
            "path": f"submission/{PDF_NAME}",
            "bytes": pdf_path.stat().st_size,
            "sha256": sha256_file(pdf_path),
            "pages": pdf_pages(pdf_path),
        },
        "paper_pdf": {
            "path": f"paper/{PDF_NAME}",
            "bytes": (paper_dir / PDF_NAME).stat().st_size,
            "sha256": sha256_file(paper_dir / PDF_NAME),
            "pages": pdf_pages(paper_dir / PDF_NAME),
        },
        "source_files": source_hashes,
        "paper_source_files": paper_hashes,
        "clean_compile": clean_compile,
        "checks_passed": checks_passed,
    }


def write_manifest_markdown(path: Path, manifest: dict[str, Any]) -> None:
    source_rows = [
        f"| `{item['path']}` | {item['bytes']} | `{item['sha256'][:12]}` |"
        for item in manifest["source_files"]
    ]
    lines = [
        "# Submission Package Manifest",
        "",
        f"- Created UTC: `{manifest['created_utc']}`",
        f"- Source zip: `{manifest['source_zip']['path']}`",
        f"- PDF: `{manifest['submission_pdf']['path']}`",
        f"- PDF pages: {manifest['submission_pdf']['pages']}",
        f"- Clean-room compile: {manifest['clean_compile']['status']}",
        f"- Clean-room log problem count: {manifest['clean_compile']['log_problem_count']}",
        f"- Checks passed: {manifest['checks_passed']}",
        "",
        "## Source Files",
        "",
        "| path | bytes | sha256 prefix |",
        "| --- | ---: | --- |",
        *source_rows,
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    paper_dir = root / "paper"
    package_dir = root / "submission"
    source_dir = package_dir / "colm2026_source"
    package_dir.mkdir(parents=True, exist_ok=True)

    copied_sources = copy_sources(paper_dir, source_dir)
    submission_pdf = paper_dir / PDF_NAME
    if not submission_pdf.exists() or submission_pdf.stat().st_size == 0:
        raise FileNotFoundError(submission_pdf)
    shutil.copy2(submission_pdf, package_dir / PDF_NAME)

    source_members = make_source_zip(source_dir, package_dir / ZIP_NAME)
    clean_compile = clean_compile_check(source_dir, keep_temp=args.keep_temp)
    manifest = build_manifest(
        root=root,
        paper_dir=paper_dir,
        package_dir=package_dir,
        source_dir=source_dir,
        source_members=source_members,
        clean_compile=clean_compile,
    )
    (package_dir / MANIFEST_JSON).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_manifest_markdown(package_dir / MANIFEST_MD, manifest)

    print(package_dir / MANIFEST_JSON)
    print(f"sources={len(copied_sources)} zip_members={len(source_members)} checks_passed={manifest['checks_passed']}")
    if not manifest["checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
