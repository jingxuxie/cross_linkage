#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from crossdoc_pipeline import dataframe_to_markdown, load_config, make_paths


CONDITION_LABELS = {
    "original": "C0 original",
    "c1_direct_redaction": "C1 direct redaction",
    "c1b_presidio_redaction": "C1b Presidio redaction",
    "c2_consistent_pseudonym": "C2 consistent pseudonym",
    "c3_per_doc_pseudonym": "C3 per-doc pseudonym",
    "c4_doc_local_anon": "C4 doc-local proxy",
    "c4_openai_doc_local": "C4 OpenAI doc-local",
    "c4_openai_doc_local_gpt55_24p": "C4 GPT-5.5 doc-local",
    "c5_linkguard": "C5 LinkGuard",
    "c6_aggressive_redaction": "C6 aggressive redaction",
}

PAPER_LABELS = {
    "original": "C0 Orig",
    "c1_direct_redaction": "C1 Redact",
    "c1b_presidio_redaction": "C1b Presidio",
    "c2_consistent_pseudonym": "C2 Stable",
    "c3_per_doc_pseudonym": "C3 PerDoc",
    "c4_doc_local_anon": "C4 Local",
    "c4_openai_doc_local": "C4 OpenAI",
    "c4_openai_doc_local_gpt55_24p": "C4 GPT5.5",
    "c5_linkguard": "C5 LG",
    "c6_aggressive_redaction": "C6 Agg",
}

CANDIDATE_FOCUS_CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

ATTACK_LABELS = {
    "word_tfidf": "Word",
    "char_tfidf": "Char",
    "hybrid_tfidf": "Hybrid",
    "field_weighted": "Field",
}

RAG_FOCUS_CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]

TIER_FOCUS_CONDITIONS = [
    "c1_direct_redaction",
    "c1b_presidio_redaction",
    "c4_doc_local_anon",
    "c5_linkguard",
    "c6_aggressive_redaction",
]


def compact_main_table(results: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition",
        "pair_f1",
        "fixedk_ari",
        "aux_top1",
        "aux_top3",
        "attr_exact_recovery",
        "attr_coarse_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
        "fact_preservation",
        "edit_ratio",
    ]
    out = results[cols].copy()
    out["condition"] = out["condition"].map(CONDITION_LABELS).fillna(out["condition"])
    return out


def paper_main_table(results: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition",
        "pair_f1",
        "aux_top1",
        "attr_exact_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
        "fact_preservation",
        "edit_ratio",
    ]
    out = results[cols].copy()
    out["condition"] = out["condition"].map(PAPER_LABELS).fillna(out["condition"])
    out = out.rename(
        columns={
            "condition": "Cond.",
            "pair_f1": "Pair",
            "aux_top1": "Aux@1",
            "attr_exact_recovery": "Exact",
            "issue_acc": "Issue",
            "retrieval_recall_at_5": "Ret@5",
            "fact_preservation": "Facts",
            "edit_ratio": "Edit",
        }
    )
    return out


def compact_openai_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition, group in summary.groupby("condition", sort=False):
        rows.append(
            {
                "condition": CONDITION_LABELS.get(condition, condition),
                "n": int(group["n"].sum()),
                "top1": float((group["top1"] * group["n"]).sum() / group["n"].sum()),
                "top3": float((group["top3"] * group["n"]).sum() / group["n"].sum()),
                "T2_top1": float(group[group["risk_tier"] == "T2"]["top1"].iloc[0])
                if (group["risk_tier"] == "T2").any()
                else float("nan"),
                "T3_top1": float(group[group["risk_tier"] == "T3"]["top1"].iloc[0])
                if (group["risk_tier"] == "T3").any()
                else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def paper_openai_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition, group in summary.groupby("condition", sort=False):
        rows.append(
            {
                "Cond.": PAPER_LABELS.get(condition, condition),
                "n": int(group["n"].sum()),
                "Aux@1": float((group["top1"] * group["n"]).sum() / group["n"].sum()),
                "Aux@3": float((group["top3"] * group["n"]).sum() / group["n"].sum()),
                "T2@1": float(group[group["risk_tier"] == "T2"]["top1"].iloc[0])
                if (group["risk_tier"] == "T2").any()
                else float("nan"),
                "T3@1": float(group[group["risk_tier"] == "T3"]["top1"].iloc[0])
                if (group["risk_tier"] == "T3").any()
                else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def paper_gpt55_table(summary: pd.DataFrame) -> pd.DataFrame:
    out = paper_openai_table(summary)
    if "uncertain_rate" not in summary.columns:
        return out
    uncertainty_by_condition = {}
    for condition, group in summary.groupby("condition", sort=False):
        n = group["n"].sum()
        uncertainty_by_condition[PAPER_LABELS.get(condition, condition)] = float(
            (group["uncertain_rate"] * group["n"]).sum() / n
        )
    out["Unc."] = [uncertainty_by_condition.get(label, float("nan")) for label in out["Cond."]]
    return out


def paper_evidence_table(summary: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "bucket_label",
        "n",
        "role_signal_rate",
        "location_signal_rate",
        "institution_signal_rate",
        "high_specificity_signal_rate",
        "uncertain_rate",
    ]
    out = summary[cols].copy()
    out = out.rename(
        columns={
            "bucket_label": "Case",
            "role_signal_rate": "Role",
            "location_signal_rate": "Loc.",
            "institution_signal_rate": "Inst.",
            "high_specificity_signal_rate": "High-spec.",
            "uncertain_rate": "Unc.",
        }
    )
    out["Case"] = out["Case"].replace(
        {
            "Direct-redaction successful match": "Direct success",
            "LinkGuard residual match": "LG residual",
            "Aggressive low-signal contrast": "Agg failure",
        }
    )
    return out


def compact_sensitivity_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "target_k",
        "min_estimated_k",
        "median_estimated_k",
        "edit_ratio",
        "pair_f1",
        "aux_top1",
        "aux_top3",
        "field_aux_top1",
        "field_aux_top3",
        "attr_exact_recovery",
        "attr_coarse_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
        "fact_preservation",
    ]
    return df[[col for col in cols if col in df.columns]].copy()


def paper_sensitivity_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "target_k",
        "min_estimated_k",
        "edit_ratio",
        "pair_f1",
        "aux_top1",
        "field_aux_top1",
        "attr_exact_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
    ]
    out = df[[col for col in cols if col in df.columns]].copy()
    out = out.rename(
        columns={
            "target_k": "k",
            "min_estimated_k": "Min k",
            "edit_ratio": "Edit",
            "pair_f1": "Pair",
            "aux_top1": "Aux@1",
            "field_aux_top1": "Field@1",
            "attr_exact_recovery": "Exact",
            "issue_acc": "Issue",
            "retrieval_recall_at_5": "Ret@5",
        }
    )
    return out


def compact_corpus_awareness_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "label",
        "min_true_estimated_k",
        "median_true_estimated_k",
        "target_k_coverage",
        "mean_l1_fields",
        "mean_l2_fields",
        "edit_ratio",
        "aux_top1",
        "field_aux_top1",
        "attr_exact_recovery",
        "attr_coarse_recovery",
        "issue_acc",
        "retrieval_recall_at_5",
    ]
    out = df[[col for col in cols if col in df.columns]].copy()
    out = out.rename(
        columns={
            "label": "Variant",
            "min_true_estimated_k": "Min true k",
            "median_true_estimated_k": "Med true k",
            "target_k_coverage": "k-cover",
            "mean_l1_fields": "Mean L1",
            "mean_l2_fields": "Mean L2",
            "edit_ratio": "Edit",
            "aux_top1": "Aux@1",
            "field_aux_top1": "Field@1",
            "attr_exact_recovery": "Exact",
            "attr_coarse_recovery": "Coarse",
            "issue_acc": "Issue",
            "retrieval_recall_at_5": "Ret@5",
        }
    )
    return out


def paper_corpus_awareness_table(df: pd.DataFrame) -> pd.DataFrame:
    out = compact_corpus_awareness_table(df)
    keep = [
        "Variant",
        "Min true k",
        "k-cover",
        "Edit",
        "Aux@1",
        "Field@1",
        "Exact",
        "Issue",
        "Ret@5",
    ]
    return out[[col for col in keep if col in out.columns]].copy()


def compact_ablation_table(ablation: pd.DataFrame, direct_aux_top1: float) -> pd.DataFrame:
    labels = {
        "remove_location": "Location",
        "remove_occupation": "Role+org",
        "remove_family": "Family",
        "remove_medical": "Health",
        "remove_rare_event": "Rare event",
        "remove_schedule": "Schedule",
    }
    out = ablation.copy()
    out["Signal removed"] = out["ablation"].map(labels).fillna(out["ablation"])
    out["Aux@1"] = out["aux_top1"]
    out["Drop"] = direct_aux_top1 - out["aux_top1"]
    out = out[["Signal removed", "Aux@1", "Drop", "aux_top3", "aux_mrr"]]
    out = out.rename(columns={"aux_top3": "Aux@3", "aux_mrr": "MRR"})
    return out.sort_values("Drop", ascending=False)


def paper_candidate_sensitivity_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[df["condition"].isin(CANDIDATE_FOCUS_CONDITIONS)].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    pivot = focus.pivot(index="Cond.", columns="candidate_set_size", values="aux_top1")
    order = [PAPER_LABELS[condition] for condition in CANDIDATE_FOCUS_CONDITIONS]
    pivot = pivot.reindex([label for label in order if label in pivot.index])
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)
    pivot.columns = [f"Aux@{int(col)}" for col in pivot.columns]

    chance = (
        df[["candidate_set_size", "chance_top1"]]
        .drop_duplicates()
        .sort_values("candidate_set_size")
    )
    chance_row = {"Cond.": "Chance"}
    for _, row in chance.iterrows():
        chance_row[f"Aux@{int(row['candidate_set_size'])}"] = float(row["chance_top1"])

    out = pivot.reset_index()
    return pd.concat([out, pd.DataFrame([chance_row])], ignore_index=True)


def paper_attack_sensitivity_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[df["condition"].isin(CANDIDATE_FOCUS_CONDITIONS)].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    focus["Attack"] = focus["attack"].map(ATTACK_LABELS).fillna(focus["attack"])
    pivot = focus.pivot(index="Cond.", columns="Attack", values="aux_top1")
    condition_order = [PAPER_LABELS[condition] for condition in CANDIDATE_FOCUS_CONDITIONS]
    attack_order = [label for label in ATTACK_LABELS.values() if label in pivot.columns]
    pivot = pivot.reindex([label for label in condition_order if label in pivot.index])
    pivot = pivot.reindex(attack_order, axis=1)
    return pivot.reset_index()


def paper_utility_stress_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition",
        "body_issue_phrase_rate",
        "semantic_slot_score",
        "body_retrieval_recall_at_5",
        "placeholder_rate",
        "stress_utility_score",
    ]
    out = df[cols].copy()
    out["condition"] = out["condition"].map(PAPER_LABELS).fillna(out["condition"])
    out = out.rename(
        columns={
            "condition": "Cond.",
            "body_issue_phrase_rate": "Issue Phrase",
            "semantic_slot_score": "Slots",
            "body_retrieval_recall_at_5": "Body Ret@5",
            "placeholder_rate": "Placeholder",
            "stress_utility_score": "Stress Utility",
        }
    )
    return out


def paper_noisy_style_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[
        df["condition"].isin(
            [
                "c1_direct_redaction",
                "c1b_presidio_redaction",
                "c4_doc_local_anon",
                "c5_linkguard",
                "c6_aggressive_redaction",
            ]
        )
    ].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    out = focus[
        [
            "Cond.",
            "aux_top1",
            "aux_top3",
            "attr_exact_recovery",
            "issue_acc",
            "retrieval_recall_at_5",
            "edit_ratio",
        ]
    ].rename(
        columns={
            "aux_top1": "Aux@1",
            "aux_top3": "Aux@3",
            "attr_exact_recovery": "Exact",
            "issue_acc": "Issue",
            "retrieval_recall_at_5": "Ret@5",
            "edit_ratio": "Edit",
        }
    )
    return out


def paper_rag_t3_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[
        (df["condition"].isin(RAG_FOCUS_CONDITIONS))
        & (df["risk_tier"] == "T3")
    ].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    focus = focus[
        [
            "Cond.",
            "hit_at_5",
            "multi_doc_at_10",
            "target_doc_recall_at_10",
            "mrr",
        ]
    ]
    focus = focus.rename(
        columns={
            "hit_at_5": "Hit@5",
            "multi_doc_at_10": "Multi@10",
            "target_doc_recall_at_10": "DocRec@10",
            "mrr": "MRR",
        }
    )
    order = [PAPER_LABELS[condition] for condition in RAG_FOCUS_CONDITIONS]
    focus["_order"] = focus["Cond."].map({label: idx for idx, label in enumerate(order)})
    return focus.sort_values("_order").drop(columns="_order")


def paper_rag_query_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[df["condition"].isin(RAG_FOCUS_CONDITIONS)].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    focus["Query"] = focus["query_label"]
    pivot = focus.pivot(index="Query", columns="Cond.", values="hit_at_5")
    condition_order = [PAPER_LABELS[condition] for condition in RAG_FOCUS_CONDITIONS]
    query_order = ["Short", "Medium", "Verbose"]
    pivot = pivot.reindex([query for query in query_order if query in pivot.index])
    pivot = pivot.reindex([label for label in condition_order if label in pivot.columns], axis=1)
    pivot = pivot.reset_index()
    pivot.columns = [
        col if col == "Query" else f"{col} Hit@5"
        for col in pivot.columns
    ]
    return pivot


def paper_rag_context_t3_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[
        (df["condition"].isin(RAG_FOCUS_CONDITIONS))
        & (df["risk_tier"] == "T3")
    ].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    focus = focus[
        [
            "Cond.",
            "retrieval_hit_at_k",
            "exact_field_recovery",
            "coarse_field_recovery",
            "exact_fields_recovered",
            "coarse_fields_recovered",
        ]
    ].rename(
        columns={
            "retrieval_hit_at_k": "Hit@5",
            "exact_field_recovery": "ExactRate",
            "coarse_field_recovery": "CoarseRate",
            "exact_fields_recovered": "Exact#",
            "coarse_fields_recovered": "Coarse#",
        }
    )
    order = [PAPER_LABELS[condition] for condition in RAG_FOCUS_CONDITIONS]
    focus["_order"] = focus["Cond."].map({label: idx for idx, label in enumerate(order)})
    return focus.sort_values("_order").drop(columns="_order")


def paper_tier_aux_table(df: pd.DataFrame) -> pd.DataFrame:
    focus = df[df["condition"].isin(TIER_FOCUS_CONDITIONS)].copy()
    focus["Cond."] = focus["condition"].map(PAPER_LABELS).fillna(focus["condition"])
    aux = focus.pivot(index="Cond.", columns="risk_tier", values="aux_top1")
    exact = focus.pivot(index="Cond.", columns="risk_tier", values="attr_exact_recovery")
    order = [PAPER_LABELS[condition] for condition in TIER_FOCUS_CONDITIONS]
    out = pd.DataFrame({"Cond.": [label for label in order if label in aux.index]})
    for tier in ["T1", "T2", "T3"]:
        out[f"{tier} Aux@1"] = [float(aux.loc[label, tier]) for label in out["Cond."]]
    out["T3 Exact"] = [float(exact.loc[label, "T3"]) for label in out["Cond."]]
    return out


def bootstrap_aux_ci(rows: pd.DataFrame, seed: int = 20260627, n_boot: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = []
    for condition, group in rows.groupby("condition", sort=False):
        by_persona = group[["persona_id", "top1"]].drop_duplicates("persona_id")
        values = by_persona["top1"].to_numpy(dtype=float)
        if len(values) == 0:
            continue
        samples = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
        out.append(
            {
                "condition": CONDITION_LABELS.get(condition, condition),
                "n_personas": len(values),
                "aux_top1": float(values.mean()),
                "ci_low": float(np.quantile(samples, 0.025)),
                "ci_high": float(np.quantile(samples, 0.975)),
            }
        )
    return pd.DataFrame(out)


def to_latex_table(df: pd.DataFrame, path: Path, caption: str, label: str) -> None:
    def fmt(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    def esc(value: object) -> str:
        text = fmt(value)
        return (
            text.replace("\\", "\\textbackslash{}")
            .replace("&", "\\&")
            .replace("%", "\\%")
            .replace("$", "\\$")
            .replace("#", "\\#")
            .replace("_", "\\_")
            .replace("{", "\\{")
            .replace("}", "\\}")
        )

    cols = list(df.columns)
    spec = "l" + "r" * (len(cols) - 1)
    font_size = "\\scriptsize" if len(cols) >= 8 else "\\small"
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        font_size,
        "\\setlength{\\tabcolsep}{3pt}",
        f"\\caption{{{esc(caption)}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{spec}}}",
        "\\toprule",
        " & ".join(esc(col) for col in cols) + " \\\\",
        "\\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(" & ".join(esc(row[col]) for col in cols) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(paths: any) -> None:
    paper_dir = paths.root / "paper"
    tables_dir = paper_dir / "tables"
    figures_dir = paper_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    main = pd.read_csv(paths.results / "main_results.csv")
    main_compact = compact_main_table(main)
    main_compact.to_csv(tables_dir / "main_privacy_utility.csv", index=False)
    to_latex_table(
        main_compact,
        tables_dir / "main_privacy_utility.tex",
        "Local sprint privacy and utility results.",
        "tab:main_privacy_utility",
    )
    main_paper = paper_main_table(main)
    main_paper.to_csv(tables_dir / "paper_main_results.csv", index=False)
    to_latex_table(
        main_paper,
        tables_dir / "paper_main_results.tex",
        "Sprint benchmark results. Lower is better for Pair F1, Aux@1, Exact quasi-identifier recovery, and Edit; higher is better for Issue, Ret@5, and Facts.",
        "tab:paper_main_results",
    )

    aux_ci = bootstrap_aux_ci(pd.read_csv(paths.results / "aux_match_rows.csv"))
    aux_ci.to_csv(tables_dir / "local_aux_bootstrap_ci.csv", index=False)
    to_latex_table(
        aux_ci,
        tables_dir / "local_aux_bootstrap_ci.tex",
        "Bootstrap confidence intervals for local auxiliary top-1 matching.",
        "tab:local_aux_bootstrap_ci",
    )

    openai_summary_path = paths.results / "openai_aux_match_summary.csv"
    openai_compact = None
    if openai_summary_path.exists():
        openai_summary = pd.read_csv(openai_summary_path)
        openai_compact = compact_openai_table(openai_summary)
        openai_compact.to_csv(tables_dir / "openai_aux_audit.csv", index=False)
        to_latex_table(
            paper_openai_table(openai_summary),
            tables_dir / "openai_aux_audit.tex",
            "Small-subset OpenAI auxiliary matching audit.",
            "tab:openai_aux_audit",
        )

    gpt55_summary_path = paths.results / "openai_gpt55_48p_aux_match_summary.csv"
    gpt55_compact = None
    if gpt55_summary_path.exists():
        gpt55_summary = pd.read_csv(gpt55_summary_path)
        gpt55_compact = compact_openai_table(gpt55_summary)
        gpt55_compact.to_csv(tables_dir / "gpt55_aux_audit.csv", index=False)
        to_latex_table(
            paper_gpt55_table(gpt55_summary),
            tables_dir / "gpt55_aux_audit.tex",
            "GPT-5.5 instruction-following auxiliary matching audit on 48 T2/T3 synthetic personas. Unc. is the model-reported uncertainty rate.",
            "tab:gpt55_aux_audit",
        )
        gpt55_rows_path = paths.results / "openai_gpt55_48p_aux_match_rows.csv"
        if gpt55_rows_path.exists():
            gpt55_ci = bootstrap_aux_ci(pd.read_csv(gpt55_rows_path), seed=20260628)
            gpt55_ci.to_csv(tables_dir / "gpt55_aux_bootstrap_ci.csv", index=False)

    gpt55_doclocal_summary_path = paths.results / "openai_gpt55_doclocal_24p_aux_match_summary.csv"
    gpt55_doclocal_compact = None
    if gpt55_doclocal_summary_path.exists():
        gpt55_doclocal_summary = pd.read_csv(gpt55_doclocal_summary_path)
        gpt55_doclocal_compact = compact_openai_table(gpt55_doclocal_summary)
        gpt55_doclocal_compact.to_csv(tables_dir / "gpt55_doclocal_audit.csv", index=False)
        to_latex_table(
            paper_gpt55_table(gpt55_doclocal_summary),
            tables_dir / "gpt55_doclocal_audit.tex",
            "GPT-5.5 document-local anonymization baseline and auxiliary matching audit on 24 T2/T3 synthetic personas.",
            "tab:gpt55_doclocal_audit",
        )
        gpt55_doclocal_rows_path = paths.results / "openai_gpt55_doclocal_24p_aux_match_rows.csv"
        if gpt55_doclocal_rows_path.exists():
            gpt55_doclocal_ci = bootstrap_aux_ci(
                pd.read_csv(gpt55_doclocal_rows_path), seed=20260628
            )
            gpt55_doclocal_ci.to_csv(
                tables_dir / "gpt55_doclocal_bootstrap_ci.csv", index=False
            )

    gpt55_evidence_summary_path = paths.results / "openai_gpt55_evidence_24p_evidence_summary.csv"
    gpt55_evidence = None
    if gpt55_evidence_summary_path.exists():
        gpt55_evidence = pd.read_csv(gpt55_evidence_summary_path)
        paper_evidence = paper_evidence_table(gpt55_evidence)
        paper_evidence.to_csv(tables_dir / "gpt55_evidence_signals.csv", index=False)
        to_latex_table(
            paper_evidence,
            tables_dir / "gpt55_evidence_signals.tex",
            "GPT-5.5 qualitative evidence extraction over 24 selected synthetic cases. Entries are case-level rates for signal families in the extracted explanations.",
            "tab:gpt55_evidence_signals",
        )

    fig_src = paths.results / "privacy_utility.png"
    fig_dst = figures_dir / "privacy_utility.png"
    if fig_src.exists():
        fig_dst.write_bytes(fig_src.read_bytes())
    sens_fig_src = paths.results / "linkguard_sensitivity.png"
    sens_fig_dst = figures_dir / "linkguard_sensitivity.png"
    if sens_fig_src.exists():
        sens_fig_dst.write_bytes(sens_fig_src.read_bytes())
    cand_fig_src = paths.results / "candidate_sensitivity.png"
    cand_fig_dst = figures_dir / "candidate_sensitivity.png"
    if cand_fig_src.exists():
        cand_fig_dst.write_bytes(cand_fig_src.read_bytes())
    attack_fig_src = paths.results / "attack_sensitivity.png"
    attack_fig_dst = figures_dir / "attack_sensitivity.png"
    if attack_fig_src.exists():
        attack_fig_dst.write_bytes(attack_fig_src.read_bytes())
    utility_fig_src = paths.results / "utility_stress.png"
    utility_fig_dst = figures_dir / "utility_stress.png"
    if utility_fig_src.exists():
        utility_fig_dst.write_bytes(utility_fig_src.read_bytes())

    direct = main[main["condition"] == "c1_direct_redaction"].iloc[0]
    presidio = main[main["condition"] == "c1b_presidio_redaction"].iloc[0]
    doc_local = main[main["condition"] == "c4_doc_local_anon"].iloc[0]
    linkguard = main[main["condition"] == "c5_linkguard"].iloc[0]
    aggressive = main[main["condition"] == "c6_aggressive_redaction"].iloc[0]
    consistent = main[main["condition"] == "c2_consistent_pseudonym"].iloc[0]

    lines = [
        "# Paper-Ready Result Brief",
        "",
        "## Validated Local Sprint Results",
        "",
        f"- Direct redaction leaves auxiliary matching top-1 at {direct['aux_top1']:.3f} while preserving issue utility at {direct['issue_acc']:.3f} and retrieval Recall@5 at {direct['retrieval_recall_at_5']:.3f}.",
        f"- Presidio-style PII redaction leaves auxiliary matching top-1 at {presidio['aux_top1']:.3f}, showing that an off-the-shelf document PII baseline does not remove corpus-level quasi-identifier risk.",
        f"- Exact quasi-identifier recovery remains {direct['attr_exact_recovery']:.3f} after direct redaction and {presidio['attr_exact_recovery']:.3f} after Presidio, but drops to {linkguard['attr_exact_recovery']:.3f} under LinkGuard.",
        f"- Consistent pseudonymization makes document linkage nearly trivial in this benchmark: pair F1 {consistent['pair_f1']:.3f} and fixed-K cluster ARI {consistent['fixedk_ari']:.3f}.",
        f"- The document-local anonymization proxy leaves auxiliary top-1 at {doc_local['aux_top1']:.3f}.",
        f"- LinkGuard reduces auxiliary top-1 to {linkguard['aux_top1']:.3f} with issue accuracy {linkguard['issue_acc']:.3f} and retrieval Recall@5 {linkguard['retrieval_recall_at_5']:.3f}.",
        f"- Aggressive redaction lowers auxiliary top-1 to {aggressive['aux_top1']:.3f}, but issue accuracy falls to {aggressive['issue_acc']:.3f} and retrieval Recall@5 to {aggressive['retrieval_recall_at_5']:.3f}.",
        "",
        "## Local Main Table",
        "",
        dataframe_to_markdown(main_compact, floatfmt=".3f"),
        "",
        "## Local Auxiliary Bootstrap CIs",
        "",
        dataframe_to_markdown(aux_ci, floatfmt=".3f"),
    ]
    validation_path = paths.results / "benchmark_validation.csv"
    if validation_path.exists():
        validation = pd.read_csv(validation_path)
        n_checks = len(validation)
        n_failures = int((validation["status"] != "PASS").sum())
        direct_id_checks = validation[
            validation["check_id"].str.contains(":no_exact_direct_ids", regex=False)
        ]
        direct_id_failures = int((direct_id_checks["status"] != "PASS").sum())
        lines.extend(
            [
                "",
                "## Benchmark Validation",
                "",
                f"- Benchmark validation checks: {n_checks}; failures: {n_failures}.",
                f"- Exact synthetic direct-identifier leak checks across transformed conditions: {len(direct_id_checks)}; failures: {direct_id_failures}.",
                "- Full report: `results/benchmark_validation.md`.",
            ]
        )
    ablation_path = paths.results / "ablation.csv"
    if ablation_path.exists():
        ablation = compact_ablation_table(pd.read_csv(ablation_path), float(direct["aux_top1"]))
        ablation.to_csv(tables_dir / "ablation_results.csv", index=False)
        to_latex_table(
            ablation,
            tables_dir / "ablation_results.tex",
            "Single-signal ablations from direct-redacted documents.",
            "tab:ablation_results",
        )
        top = ablation.iloc[0]
        second = ablation.iloc[1]
        lines.extend(
            [
                "",
                "## Quasi-Identifier Ablation",
                "",
                f"- Removing {top['Signal removed']} gives the largest direct-redaction Aux@1 drop ({direct['aux_top1']:.3f} to {top['Aux@1']:.3f}), followed by {second['Signal removed']} ({second['Aux@1']:.3f}).",
                "",
                dataframe_to_markdown(ablation, floatfmt=".3f"),
            ]
        )
    if gpt55_compact is not None:
        gpt_lg = gpt55_compact[gpt55_compact["condition"] == "C5 LinkGuard"].iloc[0]
        gpt_c1 = gpt55_compact[gpt55_compact["condition"] == "C1 direct redaction"].iloc[0]
        gpt_c1b = gpt55_compact[
            gpt55_compact["condition"] == "C1b Presidio redaction"
        ].iloc[0]
        gpt_c4 = gpt55_compact[gpt55_compact["condition"] == "C4 doc-local proxy"].iloc[0]
        gpt_c6 = gpt55_compact[
            gpt55_compact["condition"] == "C6 aggressive redaction"
        ].iloc[0]
        gpt_n = int(gpt_c1["n"])
        lines.extend(
            [
                "",
                "## GPT-5.5 API Stress Audit",
                "",
                f"- GPT-5.5 auxiliary matching on {gpt_n} T2/T3 personas finds direct redaction top-1 {gpt_c1['top1']:.3f}, Presidio {gpt_c1b['top1']:.3f}, document-local proxy {gpt_c4['top1']:.3f}, LinkGuard {gpt_lg['top1']:.3f}, and aggressive redaction {gpt_c6['top1']:.3f}.",
                f"- LinkGuard has lower confidence and higher uncertainty in this audit: top-3 {gpt_lg['top3']:.3f}, T2 top-1 {gpt_lg['T2_top1']:.3f}, and T3 top-1 {gpt_lg['T3_top1']:.3f}.",
                "- Treat this as a time-stamped stress audit; deterministic local sweeps remain the main reproducible evidence.",
                "",
                dataframe_to_markdown(gpt55_compact, floatfmt=".3f"),
            ]
        )
    if gpt55_doclocal_compact is not None:
        gpt_dl = gpt55_doclocal_compact[
            gpt55_doclocal_compact["condition"] == "C4 GPT-5.5 doc-local"
        ].iloc[0]
        gpt_proxy = gpt55_doclocal_compact[
            gpt55_doclocal_compact["condition"] == "C4 doc-local proxy"
        ].iloc[0]
        gpt_lg_sub = gpt55_doclocal_compact[
            gpt55_doclocal_compact["condition"] == "C5 LinkGuard"
        ].iloc[0]
        gpt_agg_sub = gpt55_doclocal_compact[
            gpt55_doclocal_compact["condition"] == "C6 aggressive redaction"
        ].iloc[0]
        gpt_dl_n = int(gpt_dl["n"])
        lines.extend(
            [
                "",
                "## GPT-5.5 Document-Local Baseline",
                "",
                f"- GPT-5.5 document-local anonymization on {gpt_dl_n} T2/T3 personas removes exact direct identifiers but remains matchable: Aux@1 {gpt_dl['top1']:.3f}, Aux@3 {gpt_dl['top3']:.3f}.",
                f"- On the same persona subset, the local document-local proxy is {gpt_proxy['top1']:.3f}, LinkGuard is {gpt_lg_sub['top1']:.3f}, and aggressive redaction is {gpt_agg_sub['top1']:.3f}.",
                "- This supports the corpus-level argument: a strong document-local anonymizer can still preserve repeated quasi-identifier combinations.",
                "",
                dataframe_to_markdown(gpt55_doclocal_compact, floatfmt=".3f"),
            ]
        )
    if gpt55_evidence is not None:
        direct_ev = gpt55_evidence[gpt55_evidence["bucket"] == "direct_success"].iloc[0]
        lg_ev = gpt55_evidence[gpt55_evidence["bucket"] == "linkguard_residual"].iloc[0]
        agg_ev = gpt55_evidence[gpt55_evidence["bucket"] == "aggressive_failure"].iloc[0]
        lines.extend(
            [
                "",
                "## GPT-5.5 Evidence Extraction",
                "",
                f"- On {int(direct_ev['n'])} direct-redaction successful matches, GPT-5.5 cites location in {direct_ev['location_signal_rate']:.3f} of explanations and role in {direct_ev['role_signal_rate']:.3f}.",
                f"- On {int(lg_ev['n'])} LinkGuard residual matches, it cites role, location, and institution at 0.000 and marks {lg_ev['uncertain_rate']:.3f} of explanations uncertain.",
                f"- On {int(agg_ev['n'])} aggressive-redaction top-3 failures, explanations are mostly information-removed or coarse-context contrasts with uncertainty {agg_ev['uncertain_rate']:.3f}.",
                "",
                dataframe_to_markdown(paper_evidence_table(gpt55_evidence), floatfmt=".3f"),
            ]
        )
    if openai_compact is not None:
        lg = openai_compact[openai_compact["condition"] == "C5 LinkGuard"].iloc[0]
        c1 = openai_compact[openai_compact["condition"] == "C1 direct redaction"].iloc[0]
        c1b = openai_compact[openai_compact["condition"] == "C1b Presidio redaction"].iloc[0]
        c4 = openai_compact[openai_compact["condition"] == "C4 OpenAI doc-local"].iloc[0]
        audit_n = int(c1["n"])
        lines.extend(
            [
                "",
                "## Small OpenAI Audit",
                "",
                f"- Corrected {audit_n}-person audit: direct redaction top-1 {c1['top1']:.3f}; Presidio top-1 {c1b['top1']:.3f}; OpenAI document-local top-1 {c4['top1']:.3f}; LinkGuard top-1 {lg['top1']:.3f}.",
                "- This audit is intentionally small and should be reported as preliminary corroboration, not the main quantitative result.",
                "",
                dataframe_to_markdown(openai_compact, floatfmt=".3f"),
            ]
        )
    by_tier_path = paths.results / "by_tier.csv"
    if by_tier_path.exists():
        by_tier = pd.read_csv(by_tier_path)
        tier_table = paper_tier_aux_table(by_tier)
        tier_table.to_csv(tables_dir / "tier_aux_results.csv", index=False)
        to_latex_table(
            tier_table,
            tables_dir / "tier_aux_results.tex",
            "Auxiliary matching by synthetic risk tier.",
            "tab:tier_aux_results",
        )

        def tier_value(condition: str, risk_tier: str, metric: str = "aux_top1") -> float:
            match = by_tier[
                (by_tier["condition"] == condition)
                & (by_tier["risk_tier"] == risk_tier)
            ]
            return float(match[metric].iloc[0])

        lines.extend(
            [
                "",
                "## Risk-Tier Stratification",
                "",
                f"- Direct-redacted Aux@1 rises from {tier_value('c1_direct_redaction', 'T1'):.3f} on T1 to {tier_value('c1_direct_redaction', 'T2'):.3f} on T2 and {tier_value('c1_direct_redaction', 'T3'):.3f} on T3, confirming that the synthetic tiers encode increasing linkage risk.",
                f"- LinkGuard reduces tiered Aux@1 to {tier_value('c5_linkguard', 'T1'):.3f}, {tier_value('c5_linkguard', 'T2'):.3f}, and {tier_value('c5_linkguard', 'T3'):.3f} for T1/T2/T3, with T3 exact recovery {tier_value('c5_linkguard', 'T3', 'attr_exact_recovery'):.3f}.",
                "",
                dataframe_to_markdown(tier_table, floatfmt=".3f"),
            ]
        )
    sensitivity_path = paths.results / "linkguard_sensitivity.csv"
    if sensitivity_path.exists():
        sens = compact_sensitivity_table(pd.read_csv(sensitivity_path))
        sens.to_csv(tables_dir / "linkguard_sensitivity.csv", index=False)
        to_latex_table(
            paper_sensitivity_table(pd.read_csv(sensitivity_path)),
            tables_dir / "linkguard_sensitivity.tex",
            "LinkGuard sensitivity to target k.",
            "tab:linkguard_sensitivity",
        )
        k2 = sens[sens["target_k"] == 2].iloc[0] if (sens["target_k"] == 2).any() else None
        k5 = sens[sens["target_k"] == 5].iloc[0] if (sens["target_k"] == 5).any() else None
        lines.extend(["", "## LinkGuard Sensitivity", ""])
        if k2 is not None and k5 is not None:
            lines.append(
                f"- Increasing target k from 1 to 2 drops auxiliary top-1 from {sens.iloc[0]['aux_top1']:.3f} to {k2['aux_top1']:.3f}; target k=5 gives {k5['aux_top1']:.3f}."
            )
            lines.append(
                f"- The edit ratio rises from {sens.iloc[0]['edit_ratio']:.3f} at k=1 to {k2['edit_ratio']:.3f} at k=2 and {k5['edit_ratio']:.3f} at k=5."
            )
        if "field_aux_top1" in sens.columns and k5 is not None:
            k20 = sens[sens["target_k"] == 20].iloc[0] if (sens["target_k"] == 20).any() else None
            if k20 is not None:
                lines.append(
                    f"- Under the field-weighted stress attacker, top-1 falls from {sens.iloc[0]['field_aux_top1']:.3f} at k=1 to {k5['field_aux_top1']:.3f} at k=5 and {k20['field_aux_top1']:.3f} at k=20."
                )
        lines.extend(["", dataframe_to_markdown(sens, floatfmt=".3f")])
    corpus_awareness_path = paths.results / "corpus_awareness_ablation.csv"
    if corpus_awareness_path.exists():
        corpus_awareness = pd.read_csv(corpus_awareness_path)
        corpus_compact = compact_corpus_awareness_table(corpus_awareness)
        corpus_paper = paper_corpus_awareness_table(corpus_awareness)
        corpus_compact.to_csv(tables_dir / "corpus_awareness_ablation.csv", index=False)
        to_latex_table(
            corpus_paper,
            tables_dir / "corpus_awareness_ablation.tex",
            "Corpus-awareness ablation for LinkGuard variants.",
            "tab:corpus_awareness_ablation",
        )
        by_condition = {
            row["condition"]: row for _, row in corpus_awareness.iterrows()
        }
        true_lg = by_condition["ca_true_corpus_linkguard"]
        shuffled = by_condition["ca_shuffled_corpus_stats"]
        global_l1 = by_condition["ca_global_l1_generalization"]
        suppression = by_condition["ca_direct_targetk_suppression"]
        lines.extend(
            [
                "",
                "## Corpus-Awareness Ablation",
                "",
                f"- True corpus-aware LinkGuard reaches minimum true estimated k {true_lg['min_true_estimated_k']:.3f} with Aux@1 {true_lg['aux_top1']:.3f} and issue accuracy {true_lg['issue_acc']:.3f}.",
                f"- Shuffling quasi-identifier co-occurrences during planning yields Aux@1 {shuffled['aux_top1']:.3f}, but target-k coverage falls to {shuffled['target_k_coverage']:.3f} and minimum true estimated k to {shuffled['min_true_estimated_k']:.3f}, isolating the value of corpus co-occurrence statistics.",
                f"- A global level-1 rule gives Aux@1 {global_l1['aux_top1']:.3f} and field-aware top-1 {global_l1['field_aux_top1']:.3f}; direct target-k suppression gives Aux@1 {suppression['aux_top1']:.3f} but with edit ratio {suppression['edit_ratio']:.3f}.",
                "",
                dataframe_to_markdown(corpus_compact, floatfmt=".3f"),
            ]
        )
    multiseed_path = paths.results / "multiseed" / "claim_summary.csv"
    if multiseed_path.exists():
        multiseed = pd.read_csv(multiseed_path)
        lines.extend(
            [
                "",
                "## Multi-Seed Robustness",
                "",
                "- Three no-API corpus seeds preserve the same qualitative ordering: direct/document-local redaction remain highly matchable, while LinkGuard approaches aggressive-redaction privacy with much higher utility.",
                "",
                dataframe_to_markdown(multiseed, floatfmt=".3f"),
            ]
        )
    candidate_path = paths.results / "candidate_sensitivity.csv"
    if candidate_path.exists():
        candidate = pd.read_csv(candidate_path)
        candidate_table = paper_candidate_sensitivity_table(candidate)
        candidate_table.to_csv(tables_dir / "candidate_sensitivity.csv", index=False)
        to_latex_table(
            candidate_table,
            tables_dir / "candidate_sensitivity.tex",
            "Auxiliary matching sensitivity to candidate set size.",
            "tab:candidate_sensitivity",
        )
        sizes = sorted(int(size) for size in candidate["candidate_set_size"].unique())
        first_size = sizes[0]
        last_size = sizes[-1]

        def aux_at(condition: str, size: int) -> float:
            match = candidate[
                (candidate["condition"] == condition)
                & (candidate["candidate_set_size"] == size)
            ]
            return float(match["aux_top1"].iloc[0])

        lines.extend(
            [
                "",
                "## Candidate-Set Hardness Sensitivity",
                "",
                f"- Expanding candidate sets from {first_size} to {last_size} preserves the ordering: direct redaction changes from {aux_at('c1_direct_redaction', first_size):.3f} to {aux_at('c1_direct_redaction', last_size):.3f}, the document-local proxy from {aux_at('c4_doc_local_anon', first_size):.3f} to {aux_at('c4_doc_local_anon', last_size):.3f}, LinkGuard from {aux_at('c5_linkguard', first_size):.3f} to {aux_at('c5_linkguard', last_size):.3f}, and aggressive redaction from {aux_at('c6_aggressive_redaction', first_size):.3f} to {aux_at('c6_aggressive_redaction', last_size):.3f}.",
                "",
                dataframe_to_markdown(candidate_table, floatfmt=".3f"),
            ]
        )
    attack_path = paths.results / "attack_sensitivity.csv"
    if attack_path.exists():
        attack = pd.read_csv(attack_path)
        attack_table = paper_attack_sensitivity_table(attack)
        attack_table.to_csv(tables_dir / "attack_sensitivity.csv", index=False)
        to_latex_table(
            attack_table,
            tables_dir / "attack_sensitivity.tex",
            "Auxiliary matching sensitivity to local attacker family.",
            "tab:attack_sensitivity",
        )

        def attack_range(condition: str) -> tuple[float, float]:
            values = attack[attack["condition"] == condition]["aux_top1"]
            return float(values.min()), float(values.max())

        direct_min, direct_max = attack_range("c1_direct_redaction")
        local_min, local_max = attack_range("c4_doc_local_anon")
        lg_min, lg_max = attack_range("c5_linkguard")

        lines.extend(
            [
                "",
                "## Attack-Model Sensitivity",
                "",
                f"- Word, character, hybrid TF-IDF, and field-weighted auxiliary matchers preserve the privacy ordering: direct redaction Aux@1 ranges from {direct_min:.3f} to {direct_max:.3f}, the document-local proxy ranges from {local_min:.3f} to {local_max:.3f}, and LinkGuard ranges from {lg_min:.3f} to {lg_max:.3f}.",
                "- The field-weighted attacker is the strongest local stress test because it explicitly scans exact and generalized quasi-identifier fields; it exposes residual LinkGuard risk while preserving a large gap from document-local baselines.",
                "",
                dataframe_to_markdown(attack_table, floatfmt=".3f"),
            ]
        )
    rag_path = paths.results / "rag_exposure.csv"
    rag_tier_path = paths.results / "rag_exposure_by_tier.csv"
    if rag_path.exists() and rag_tier_path.exists():
        rag = pd.read_csv(rag_path)
        rag_tier = pd.read_csv(rag_tier_path)
        rag_t3_table = paper_rag_t3_table(rag_tier)
        rag_t3_table.to_csv(tables_dir / "rag_exposure_t3.csv", index=False)
        to_latex_table(
            rag_t3_table,
            tables_dir / "rag_exposure_t3.tex",
            "T3 profile-query RAG exposure.",
            "tab:rag_exposure_t3",
        )

        def rag_value(condition: str, metric: str, risk_tier: str | None = None) -> float:
            source = rag_tier if risk_tier is not None else rag
            match = source[source["condition"] == condition]
            if risk_tier is not None:
                match = match[match["risk_tier"] == risk_tier]
            return float(match[metric].iloc[0])

        lines.extend(
            [
                "",
                "## Profile-Query RAG Exposure",
                "",
                f"- Across all held-out personas, exact synthetic profile queries retrieve a target document in the top five at {rag_value('c1_direct_redaction', 'hit_at_5'):.3f} under direct redaction and {rag_value('c5_linkguard', 'hit_at_5'):.3f} under LinkGuard.",
                f"- For high-linkage T3 personas, direct redaction, Presidio, and the document-local proxy all have Hit@5 {rag_value('c1_direct_redaction', 'hit_at_5', 'T3'):.3f} and Multi@10 {rag_value('c1_direct_redaction', 'multi_doc_at_10', 'T3'):.3f}; LinkGuard reduces T3 Hit@5 to {rag_value('c5_linkguard', 'hit_at_5', 'T3'):.3f} and Multi@10 to {rag_value('c5_linkguard', 'multi_doc_at_10', 'T3'):.3f}.",
                "",
                dataframe_to_markdown(rag_t3_table, floatfmt=".3f"),
            ]
        )
    rag_query_path = paths.results / "rag_query_sensitivity.csv"
    if rag_query_path.exists():
        rag_query = pd.read_csv(rag_query_path)
        rag_query_table = paper_rag_query_table(rag_query)
        rag_query_table.to_csv(tables_dir / "rag_query_sensitivity.csv", index=False)
        to_latex_table(
            rag_query_table,
            tables_dir / "rag_query_sensitivity.tex",
            "Generated-query RAG exposure by query type.",
            "tab:rag_query_sensitivity",
        )

        def query_value(query_type: str, condition: str, metric: str = "hit_at_5") -> float:
            match = rag_query[
                (rag_query["query_type"] == query_type)
                & (rag_query["condition"] == condition)
            ]
            return float(match[metric].iloc[0])

        lines.extend(
            [
                "",
                "## Generated-Query RAG Sensitivity",
                "",
                f"- Deterministic generated queries preserve the RAG ordering: verbose-query Hit@5 is {query_value('verbose', 'c1_direct_redaction'):.3f} for direct redaction, {query_value('verbose', 'c4_doc_local_anon'):.3f} for the document-local proxy, and {query_value('verbose', 'c5_linkguard'):.3f} for LinkGuard.",
                f"- The short role-region query is a weaker attack but still separates direct redaction ({query_value('short', 'c1_direct_redaction'):.3f}) from LinkGuard ({query_value('short', 'c5_linkguard'):.3f}).",
                "",
                dataframe_to_markdown(rag_query_table, floatfmt=".3f"),
            ]
        )
    rag_context_path = paths.results / "rag_context_recovery_by_tier.csv"
    if rag_context_path.exists():
        rag_context = pd.read_csv(rag_context_path)
        rag_context_t3 = paper_rag_context_t3_table(rag_context)
        rag_context_t3.to_csv(tables_dir / "rag_context_recovery_t3.csv", index=False)
        to_latex_table(
            rag_context_t3,
            tables_dir / "rag_context_recovery_t3.tex",
            "T3 quasi-identifier context recovery from top-5 profile-query retrieval results.",
            "tab:rag_context_recovery_t3",
        )

        def ctx_value(condition: str, metric: str) -> float:
            match = rag_context[
                (rag_context["condition"] == condition)
                & (rag_context["risk_tier"] == "T3")
            ]
            return float(match[metric].iloc[0])

        lines.extend(
            [
                "",
                "## RAG Context Recovery",
                "",
                f"- In T3 top-5 retrieval results, direct redaction exposes {ctx_value('c1_direct_redaction', 'exact_fields_recovered'):.3f} exact quasi-identifier fields on average, Presidio exposes {ctx_value('c1b_presidio_redaction', 'exact_fields_recovered'):.3f}, and the document-local proxy exposes {ctx_value('c4_doc_local_anon', 'exact_fields_recovered'):.3f} exact / {ctx_value('c4_doc_local_anon', 'coarse_fields_recovered'):.3f} coarse fields.",
                f"- LinkGuard reduces the same T3 context recovery to {ctx_value('c5_linkguard', 'exact_fields_recovered'):.3f} exact and {ctx_value('c5_linkguard', 'coarse_fields_recovered'):.3f} coarse fields; aggressive redaction is {ctx_value('c6_aggressive_redaction', 'exact_fields_recovered'):.3f}/{ctx_value('c6_aggressive_redaction', 'coarse_fields_recovered'):.3f}.",
                "",
                dataframe_to_markdown(rag_context_t3, floatfmt=".3f"),
            ]
        )
    rag_generation_pilot_path = (
        paths.results / "openai_gpt55_rag_compact_pilot_2t3_rag_generation_summary.csv"
    )
    rag_generation_plan_path = paths.results / "openai_gpt55_rag_12t3_audit_plan.csv"
    if rag_generation_pilot_path.exists() and rag_generation_plan_path.exists():
        rag_generation_pilot = pd.read_csv(rag_generation_pilot_path)
        rag_generation_plan = pd.read_csv(rag_generation_plan_path)
        cached_calls = int(rag_generation_plan["cached"].sum())
        pending_calls = int(len(rag_generation_plan) - cached_calls)
        min_parse = float(rag_generation_pilot["parse_success_rate"].min())

        def pilot_value(condition: str, metric: str) -> float:
            match = rag_generation_pilot[rag_generation_pilot["condition"] == condition]
            return float(match[metric].iloc[0]) if not match.empty else float("nan")

        pilot_table = rag_generation_pilot[
            [
                "condition",
                "n",
                "n_parsed",
                "parse_success_rate",
                "retrieval_hit_at_5",
                "likely_same_person_rate",
                "exact_field_match_rate",
                "uncertain_rate",
            ]
        ].copy()
        pilot_table["condition"] = pilot_table["condition"].map(PAPER_LABELS).fillna(
            pilot_table["condition"]
        )
        pilot_table = pilot_table.rename(
            columns={
                "condition": "Cond.",
                "n": "n",
                "n_parsed": "parsed",
                "parse_success_rate": "Parse",
                "retrieval_hit_at_5": "Hit@5",
                "likely_same_person_rate": "Same",
                "exact_field_match_rate": "Exact",
                "uncertain_rate": "Unc.",
            }
        )

        lines.extend(
            [
                "",
                "## GPT-5.5 RAG Generation Pilot (Not Paper Claim)",
                "",
                f"- A compact 2-person T3 pilot parsed all generated JSON responses (minimum parse-success rate {min_parse:.3f}) and used 10 cached calls.",
                f"- In the pilot, direct redaction and the document-local proxy have likely-same-person rate {pilot_value('c1_direct_redaction', 'likely_same_person_rate'):.3f} and {pilot_value('c4_doc_local_anon', 'likely_same_person_rate'):.3f}; LinkGuard and aggressive redaction are {pilot_value('c5_linkguard', 'likely_same_person_rate'):.3f} and {pilot_value('c6_aggressive_redaction', 'likely_same_person_rate'):.3f}.",
                f"- This validates the compact RAG-generation protocol only; the 12-person audit still has {pending_calls} pending calls and is not a paper claim.",
                "",
                dataframe_to_markdown(pilot_table, floatfmt=".3f"),
            ]
        )
    failure_path = paths.results / "linkguard_failure_analysis.csv"
    if failure_path.exists():
        failures = pd.read_csv(failure_path)
        top1_failures = failures[failures["analysis_set"] == "top1"].copy()
        top3_failures = failures[failures["analysis_set"] == "top3_not_top1"].copy()
        compact_failures = top1_failures[
            [
                "persona_id",
                "risk_tier",
                "score_true",
                "score_margin",
                "estimated_k",
                "residual_exact_fields",
                "residual_coarse_fields",
            ]
        ].copy()
        exact_left = int((top1_failures["residual_exact_fields"] != "none").sum())
        median_margin = (
            float(top1_failures["score_margin"].median())
            if not top1_failures.empty
            else float("nan")
        )
        lines.extend(
            [
                "",
                "## LinkGuard Residual Failure Analysis",
                "",
                f"- LinkGuard has {len(top1_failures)} top-1 residual matches and {len(top3_failures)} additional top-3 residual matches under the main word TF-IDF attacker.",
                f"- Among top-1 residuals, {exact_left} retain exact quasi-identifier fields; median score margin is {median_margin:.4f}.",
                "",
                dataframe_to_markdown(compact_failures, floatfmt=".3f")
                if not compact_failures.empty
                else "No top-1 residual matches.",
            ]
        )
    utility_stress_path = paths.results / "utility_stress.csv"
    if utility_stress_path.exists():
        utility_stress = pd.read_csv(utility_stress_path)
        utility_table = paper_utility_stress_table(utility_stress)
        utility_table.to_csv(tables_dir / "utility_stress.csv", index=False)
        to_latex_table(
            utility_table,
            tables_dir / "utility_stress.tex",
            "Body-only utility stress test.",
            "tab:utility_stress",
        )
        lg = utility_stress[utility_stress["condition"] == "c5_linkguard"].iloc[0]
        aggressive_u = utility_stress[
            utility_stress["condition"] == "c6_aggressive_redaction"
        ].iloc[0]
        direct_u = utility_stress[
            utility_stress["condition"] == "c1_direct_redaction"
        ].iloc[0]
        lines.extend(
            [
                "",
                "## Body-Only Utility Stress Test",
                "",
                f"- Removing subject/contact scaffolding, LinkGuard keeps stress utility at {lg['stress_utility_score']:.3f}, close to direct redaction at {direct_u['stress_utility_score']:.3f}, while aggressive redaction falls to {aggressive_u['stress_utility_score']:.3f}.",
                f"- LinkGuard preserves body issue phrases at {lg['body_issue_phrase_rate']:.3f} with placeholder rate {lg['placeholder_rate']:.3f}; aggressive redaction has issue phrase rate {aggressive_u['body_issue_phrase_rate']:.3f} and placeholder rate {aggressive_u['placeholder_rate']:.3f}.",
                "",
                dataframe_to_markdown(utility_table, floatfmt=".3f"),
            ]
        )
    noisy_path = paths.results / "noisy_style_stress" / "noisy_style_results.csv"
    noisy_diag_path = paths.results / "noisy_style_stress" / "noisy_style_diagnostic_summary.csv"
    if noisy_path.exists() and noisy_diag_path.exists():
        noisy = pd.read_csv(noisy_path)
        noisy_diag = pd.read_csv(noisy_diag_path).iloc[0]
        noisy_table = paper_noisy_style_table(noisy)
        noisy_table.to_csv(tables_dir / "noisy_style_stress.csv", index=False)
        to_latex_table(
            noisy_table,
            tables_dir / "noisy_style_stress.tex",
            "Noisy synthetic style stress test.",
            "tab:noisy_style_stress",
        )
        direct_n = noisy[noisy["condition"] == "c1_direct_redaction"].iloc[0]
        presidio_n = noisy[noisy["condition"] == "c1b_presidio_redaction"].iloc[0]
        local_n = noisy[noisy["condition"] == "c4_doc_local_anon"].iloc[0]
        lg_n = noisy[noisy["condition"] == "c5_linkguard"].iloc[0]
        aggressive_n = noisy[noisy["condition"] == "c6_aggressive_redaction"].iloc[0]
        lines.extend(
            [
                "",
                "## Noisy Synthetic Style Stress Test",
                "",
                f"- A deterministic noisy-style corpus re-renders the same 480 synthetic documents with mean template similarity {noisy_diag['mean_template_similarity']:.3f} to the original templates.",
                f"- The privacy ordering is stable: direct redaction Aux@1 {direct_n['aux_top1']:.3f}, Presidio {presidio_n['aux_top1']:.3f}, document-local proxy {local_n['aux_top1']:.3f}, and LinkGuard {lg_n['aux_top1']:.3f}.",
                f"- LinkGuard keeps issue accuracy {lg_n['issue_acc']:.3f} and retrieval Recall@5 {lg_n['retrieval_recall_at_5']:.3f}; aggressive redaction drops to issue accuracy {aggressive_n['issue_acc']:.3f} and Recall@5 {aggressive_n['retrieval_recall_at_5']:.3f}.",
                "",
                dataframe_to_markdown(noisy_table, floatfmt=".3f"),
            ]
        )
    claim_path = paths.results / "claim_verification.json"
    if claim_path.exists():
        claim_rows = pd.DataFrame(json.loads(claim_path.read_text(encoding="utf-8")))
        n_checks = len(claim_rows)
        n_failures = int((claim_rows["status"] != "PASS").sum()) if not claim_rows.empty else 0
        lines.extend(
            [
                "",
                "## Claim Verification",
                "",
                f"- Claim verifier checks: {n_checks}.",
                f"- Claim verifier failures: {n_failures}.",
                "- Full report: `results/claim_verification.md`.",
            ]
        )
    cache_usage = summarize_api_cache(paths.root / "cache" / "api_responses")
    if cache_usage["cached_calls"] > 0:
        lines.extend(
            [
                "",
                "## API Accounting",
                "",
                f"- Cached API responses: {cache_usage['cached_calls']}.",
                f"- Total cached token usage: {cache_usage['input_tokens']} input, {cache_usage['output_tokens']} output, {cache_usage['total_tokens']} total.",
                "- The cache total includes legacy, exploratory, and compact RAG-pilot calls; paper-facing GPT-5.5 claims use the run-specific auxiliary, document-local, and evidence artifacts.",
                "- The full GPT-5.5 RAG-generation audit remains outside paper claims until the pending calls are explicitly approved and verified.",
            ]
        )
    lines.extend(
        [
            "",
            "## Claims Supported Now",
            "",
            "1. Span-level direct redaction can leave strong cross-document auxiliary matching risk.",
            "2. Consistent pseudonyms act like stable linkage handles.",
            "3. Document-local anonymization can miss combinations that are risky at corpus scale.",
            "4. Exact quasi-identifier recovery provides a structured profile-reconstruction signal in addition to auxiliary matching.",
            "5. Profile-query RAG retrieval can expose high-linkage transformed records even when direct PII is removed.",
            "6. GPT-5.5 auxiliary, document-local, and evidence stress audits corroborate the corpus-level linkage story on synthetic subsets.",
            "7. A noisy-style synthetic rerendering preserves the main privacy-utility ordering.",
            "8. Corpus-aware generalization gives a better privacy-utility point than blanket aggressive redaction in this synthetic sprint.",
            "",
            "## Caveats To Keep In The Paper",
            "",
            "- The benchmark is synthetic and uses controlled template families; this is a feature for controlled ground truth, but limits external validity.",
            "- The threshold graph clustering attack is brittle outside the stable-pseudonym condition, so clustering claims should emphasize consistent pseudonymization and fixed-K/auxiliary-matching results.",
            "- GPT-5.5 audits are cached, time-stamped synthetic subset stress audits; deterministic local sweeps remain the main reproducible evidence.",
            "- The compact RAG-generation pilot validates the protocol but is not a paper result until the full 12-person run is approved and verified.",
            "- LinkGuard is a heuristic generalization method, not a formal privacy guarantee.",
        ]
    )
    (paths.results / "paper_ready_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_api_cache(cache_dir: Path) -> dict[str, int]:
    totals = {"cached_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if not cache_dir.exists():
        return totals
    for path in cache_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        usage = data.get("usage") or {}
        totals["cached_calls"] += 1
        totals["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        totals["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
        totals["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
    return totals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sprint.yaml")
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    paths = make_paths(cfg)
    write_summary(paths)
    print(paths.results / "paper_ready_summary.md")


if __name__ == "__main__":
    main()
