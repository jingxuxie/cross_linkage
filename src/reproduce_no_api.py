#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path
    default: bool = True
    expensive: bool = False


def python_cmd(env: str, script: str, *args: str) -> list[str]:
    return ["conda", "run", "-n", env, "python", script, *args]


def build_steps(args: argparse.Namespace) -> list[Step]:
    root = Path.cwd()
    paper_dir = root / "paper"
    env = args.conda_env
    config = args.config
    steps = [
        Step(
            "local_benchmark",
            python_cmd(env, "src/crossdoc_pipeline.py", "--config", config, "all"),
            root,
        ),
        Step(
            "benchmark_validation",
            python_cmd(env, "src/validate_benchmark.py", "--config", config),
            root,
        ),
        Step(
            "linkguard_sensitivity",
            python_cmd(
                env,
                "src/linkguard_sensitivity.py",
                "--config",
                config,
                "--target-ks",
                "1,2,3,5,8,12,20",
            ),
            root,
        ),
        Step(
            "multiseed_sweep",
            python_cmd(
                env,
                "src/multiseed_sweep.py",
                "--config",
                config,
                "--seeds",
                "20260627,20260628,20260629",
                "--out-dir",
                "results/multiseed",
            ),
            root,
            expensive=True,
        ),
        Step(
            "candidate_sensitivity",
            python_cmd(
                env,
                "src/candidate_sensitivity.py",
                "--config",
                config,
                "--candidate-sizes",
                "10,20,50",
            ),
            root,
        ),
        Step(
            "attack_sensitivity",
            python_cmd(env, "src/attack_sensitivity.py", "--config", config),
            root,
        ),
        Step(
            "linkguard_failure_analysis",
            python_cmd(env, "src/linkguard_failure_analysis.py", "--config", config),
            root,
        ),
        Step(
            "utility_stress",
            python_cmd(env, "src/utility_stress.py", "--config", config),
            root,
        ),
        Step(
            "rag_exposure",
            python_cmd(env, "src/rag_exposure.py", "--config", config),
            root,
        ),
        Step(
            "rag_context_recovery",
            python_cmd(env, "src/rag_context_recovery.py", "--config", config),
            root,
        ),
        Step(
            "noisy_style_stress",
            python_cmd(env, "src/noisy_style_stress.py", "--config", config),
            root,
        ),
        Step(
            "openai_audit_plan_cached_only",
            python_cmd(
                env,
                "src/openai_audit.py",
                "--model",
                "gpt-5.4-nano",
                "--max-personas",
                "12",
                "--max-calls",
                "1",
                "--tasks",
                "doc-local,aux-match",
                "--conditions",
                "c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction",
                "--plan-only",
            ),
            root,
        ),
        Step(
            "openai_evidence_plan_cached_only",
            python_cmd(
                env,
                "src/openai_evidence_audit.py",
                "--model",
                "gpt-5.5",
                "--run-name",
                "gpt55_evidence_24p",
                "--cases-per-bucket",
                "8",
                "--max-calls",
                "24",
                "--reasoning-effort",
                "none",
                "--max-output-tokens",
                "650",
                "--plan-only",
            ),
            root,
        ),
        Step(
            "openai_rag_generation_plan_only",
            python_cmd(
                env,
                "src/openai_rag_audit.py",
                "--config",
                config,
                "--model",
                "gpt-5.5",
                "--run-name",
                "gpt55_rag_12t3",
                "--max-personas",
                "12",
                "--tier",
                "T3",
                "--max-calls",
                "60",
                "--reasoning-effort",
                "none",
                "--max-output-tokens",
                "550",
                "--plan-only",
            ),
            root,
        ),
        Step(
            "paper_assets",
            python_cmd(env, "src/make_paper_assets.py", "--config", config),
            root,
        ),
        Step(
            "pdf_compile",
            ["latexmk", "-g", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "short_paper.tex"],
            paper_dir,
        ),
        Step(
            "colm_pdf_compile",
            [
                "latexmk",
                "-g",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "colm2026_submission.tex",
            ],
            paper_dir,
        ),
        Step(
            "submission_package",
            python_cmd(env, "src/build_submission_package.py"),
            root,
        ),
        Step(
            "supplement",
            python_cmd(env, "src/make_supplement.py", "--config", config),
            root,
        ),
        Step(
            "claim_verification",
            python_cmd(env, "src/verify_claims.py", "--config", config),
            root,
        ),
        Step(
            "result_brief_final",
            python_cmd(env, "src/make_paper_assets.py", "--config", config),
            root,
        ),
    ]
    if args.skip_multiseed:
        steps = [step for step in steps if step.name != "multiseed_sweep"]
    if args.skip_pdf:
        steps = [
            step
            for step in steps
            if step.name
            not in {
                "pdf_compile",
                "colm_pdf_compile",
                "submission_package",
                "claim_verification",
                "result_brief_final",
            }
        ]
    if args.step:
        requested = set(args.step)
        known = {step.name for step in steps}
        unknown = sorted(requested - known)
        if unknown:
            raise SystemExit(f"Unknown step(s): {', '.join(unknown)}. Known: {', '.join(sorted(known))}")
        steps = [step for step in steps if step.name in requested]
    return steps


def run_step(step: Step, dry_run: bool) -> float:
    cmd_text = " ".join(step.cmd)
    print(f"==> {step.name}")
    print(f"cwd: {step.cwd}")
    print(cmd_text)
    if dry_run:
        return 0.0
    start = time.monotonic()
    subprocess.run(step.cmd, cwd=step.cwd, check=True)
    elapsed = time.monotonic() - start
    print(f"<== {step.name} completed in {elapsed:.1f}s")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reproduce the no-API CrossDoc-PrivacyBench result package."
    )
    parser.add_argument("--config", default="configs/sprint.yaml")
    parser.add_argument("--conda-env", default="cross_linkage")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-multiseed", action="store_true")
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument(
        "--step",
        action="append",
        help="Run only a named step. May be supplied multiple times.",
    )
    args = parser.parse_args()

    steps = build_steps(args)
    if not steps:
        raise SystemExit("No steps selected.")
    total_start = time.monotonic()
    total = 0.0
    try:
        for step in steps:
            total += run_step(step, args.dry_run)
    except subprocess.CalledProcessError as exc:
        print(f"FAILED step: {step.name}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    wall = time.monotonic() - total_start
    mode = "dry-run" if args.dry_run else "executed"
    print(f"Reproduction {mode}: {len(steps)} step(s), command time {total:.1f}s, wall time {wall:.1f}s")


if __name__ == "__main__":
    main()
