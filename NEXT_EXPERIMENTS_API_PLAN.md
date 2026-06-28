# Next Experiments Plan for the Cross-Document Linkage Paper

This plan assumes the current repository already contains the synthetic benchmark, deterministic local attacks, LinkGuard, Presidio-style redaction, noisy-style stress tests, RAG exposure diagnostics, and a small cached OpenAI audit. The goal is not to replace the current evidence, but to make the workshop paper more convincing by adding a stronger instruction-following attacker and clearer API-run provenance.

## 0. Current status to report honestly

The main pipeline is API-free by default. The repository README says the default pipeline uses deterministic synthetic personas, local transformations, TF-IDF and field-aware attacks, Presidio-based PII redaction, and local utility classifiers. It also says OpenAI calls are isolated in `src/openai_audit.py`, cached under `cache/api_responses/`, and guarded by `--max-calls`.

However, the current results already include a small OpenAI audit artifact:

- `results/openai_aux_match_summary.csv`
- `paper/tables/openai_aux_audit.tex`
- a paragraph in the paper reporting a 12-person OpenAI audit

So the precise wording should be:

> The main claims are based on deterministic no-API experiments. We additionally include a small cached OpenAI audit on synthetic data as preliminary corroborating evidence.

Avoid saying “we did not use any API” unless you remove the OpenAI audit results from the paper and artifact set.

## 1. Most valuable additional experiment: GPT-5.5 auxiliary-profile attacker

### Why this helps

The core paper claim is about corpus-level linkage after de-identification. A local TF-IDF attacker is useful because it is deterministic and cheap, but reviewers may ask whether the failure persists with a modern instruction-following model. A GPT-5.5 auxiliary-profile matcher is the cleanest API addition because it directly tests the paper’s threat model without changing the benchmark.

### Recommended scope

Run GPT-5.5 on 48 T2/T3 personas and 5 conditions:

- `c1_direct_redaction`
- `c1b_presidio_redaction`
- `c4_doc_local_anon`
- `c5_linkguard`
- `c6_aggressive_redaction`

This is 48 × 5 = 240 auxiliary-matching calls. It should fit comfortably under a $100 API budget if prompts stay close to the current script size.

### Command

First do a dry plan:

```bash
conda run -n cross_linkage python src/openai_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --max-personas 48 \
  --tiers T2,T3 \
  --max-calls 300 \
  --tasks aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c5_linkguard,c6_aggressive_redaction \
  --plan-only
```

Then run live:

```bash
OPENAI_API_KEY=... conda run -n cross_linkage python src/openai_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --max-personas 48 \
  --tiers T2,T3 \
  --max-calls 300 \
  --tasks aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c5_linkguard,c6_aggressive_redaction
```

### Important implementation fix before running

Right now `openai_audit.py` writes model-independent output names such as:

- `results/openai_aux_match_rows.csv`
- `results/openai_aux_match_summary.csv`
- `results/openai_audit_notes.md`

That is risky because a GPT-5.5 run can overwrite or be confused with an earlier nano/mini run. Add a `--run-name` argument and write outputs like:

- `results/openai_gpt55_48p_aux_match_rows.csv`
- `results/openai_gpt55_48p_aux_match_summary.csv`
- `results/openai_gpt55_48p_audit_usage.csv`
- `results/openai_gpt55_48p_audit_notes.md`

Also include the model name, date, git commit, number of personas, conditions, and token usage in the notes file.

### Metrics to report

For each condition:

- top-1 accuracy
- top-3 accuracy
- mean reciprocal rank
- T2 top-1
- T3 top-1
- bootstrap confidence intervals if using 48 personas
- median confidence/margin if the model returns scores
- qualitative signals used by the model

### Paper placement

Add a subsection under Results:

> GPT-5.5 instruction-following attacker audit.

Use careful phrasing:

> We use this as a stress audit rather than the main statistical evidence because API model behavior can change over time and the benchmark remains synthetic.

## 2. Second most valuable experiment: GPT-5.5 document-local anonymization baseline

### Why this helps

The current paper includes a document-local proxy and a small OpenAI document-local baseline. Expanding this baseline answers a likely reviewer question: “Maybe a stronger LLM anonymizer would remove the quasi-identifiers better than your local proxy.”

### Recommended scope

Run GPT-5.5 document-local anonymization on 24 T2/T3 personas first. That is 24 × 4 = 96 document-anonymization calls. Then run auxiliary matching on the generated condition plus the main baselines.

Use 24 personas if time is limited; use 48 only if the 24-person run is clean and inexpensive.

### Two-stage command

Stage 1: generate GPT-5.5 document-local anonymized docs.

```bash
OPENAI_API_KEY=... conda run -n cross_linkage python src/openai_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --max-personas 24 \
  --tiers T2,T3 \
  --max-calls 120 \
  --tasks doc-local \
  --conditions c4_openai_doc_local
```

Stage 2: match auxiliary profiles against those outputs.

```bash
OPENAI_API_KEY=... conda run -n cross_linkage python src/openai_audit.py \
  --config configs/sprint.yaml \
  --model gpt-5.5 \
  --max-personas 24 \
  --tiers T2,T3 \
  --max-calls 180 \
  --tasks aux-match \
  --conditions c1_direct_redaction,c1b_presidio_redaction,c4_doc_local_anon,c4_openai_doc_local,c5_linkguard,c6_aggressive_redaction
```

### Necessary fix

Do not reuse the same `c4_openai_doc_local_subset.jsonl` across models. Either:

1. include the model in the output condition, e.g. `c4_openai_doc_local_gpt55`, or
2. write the output under a run-specific directory, e.g. `results/api_runs/gpt55_24p/transformed/`.

The first option is easier for paper tables.

### What to report

Report whether GPT-5.5 document-local anonymization remains matchable. The strongest outcome for the paper is:

- GPT-5.5 document-local anonymization improves over regex/Presidio redaction,
- but remains substantially more matchable than LinkGuard,
- because it lacks corpus-level uniqueness accounting.

If GPT-5.5 performs extremely well, that is still publishable: it would show that strong document-local LLM anonymization is a serious baseline and that the paper’s benchmark can distinguish it from cheaper tools.

## 3. Third experiment: evidence extraction / quasi-identifier explanation

### Why this helps

Auxiliary matching gives a number, but reviewers will want to understand why matching succeeds. Ask GPT-5.5 to identify the signals it used without exposing direct identifiers.

### Prompt idea

For each matched persona, ask the model to return JSON:

```json
{
  "top_signals": [
    {"signal": "role", "evidence": "...", "specificity": "high|medium|low"},
    {"signal": "location", "evidence": "...", "specificity": "high|medium|low"}
  ],
  "would_match_without_role": true,
  "would_match_without_location": false,
  "residual_risk_summary": "..."
}
```

Run this only on a small subset:

- 8 personas where direct redaction succeeds as an attack
- 8 personas where LinkGuard still has residual match risk
- 8 personas where aggressive redaction breaks utility

### Paper use

Use this as qualitative analysis, not a main metric. Add a short table with failure categories:

- stable pseudonym handle
- repeated role/institution
- repeated city/region
- rare event
- schedule/family combination
- coarse residual context
- model over-inference

## 4. Fourth experiment: stronger RAG exposure audit

### Why this helps

The paper is aimed at LLM-ready corpora. The current RAG-style diagnostic uses local retrieval. Add a small generation step to show what an LLM can expose after retrieval.

### Design

For each condition, run local retrieval with profile-like queries. Feed the top-5 retrieved documents to GPT-5.5 and ask it to answer:

> Based only on these transformed documents, list what can be inferred about the person matching this profile. Return JSON with fields: likely_same_person, inferred_contexts, sensitive_contexts, uncertainty.

Use 12 T3 personas × 5 conditions = 60 calls.

### Metrics

- target document retrieved in top-5
- model says likely same person
- number of sensitive contexts recovered
- exact or coarse match to true quasi-identifiers
- refusal/uncertainty rate

### Paper use

This can become a paragraph plus one compact table:

> RAG exposure is not just retrieval: when the top retrieved transformed documents are passed to an instruction-following model, direct/document-local conditions allow profile reconstruction, whereas LinkGuard mostly leaves coarse context.

## 5. Optional small GPT-5.5-pro stress audit

### Should you use GPT-5.5-pro?

Only use GPT-5.5-pro for a tiny stress audit after the GPT-5.5 run is complete. It is much more expensive. A good scope is 12 T3 personas × 5 conditions = 60 calls.

### Why it may help

It gives the paper one sentence:

> A small GPT-5.5-pro stress audit on the hardest T3 tier preserved the same qualitative ordering.

### Why it may not be necessary

For a workshop paper, GPT-5.5 is already a strong enough instruction-following attacker. GPT-5.5-pro may look like a prestige addition, but it is less important than clean run provenance, confidence intervals, and qualitative analysis.

## 6. Estimated API cost

Use `--plan-only` first and estimate input characters/tokens before live calls. Approximate planning numbers:

- 1 auxiliary matching call: 4 transformed documents + 10 candidate profiles + instructions
- rough input: 4k–8k tokens
- rough output: 200–600 tokens

At GPT-5.5 standard short-context pricing, a 240-call auxiliary-matching run is likely well under $100. GPT-5.5-pro is much more expensive, so keep it to a tiny subset.

Use Batch or Flex pricing only if turnaround time is acceptable. Use Standard if the submission deadline is close.

## 7. Reporting rules for the paper

Add a small “API audit protocol” paragraph:

- synthetic data only
- no real sensitive data sent to APIs
- model name and date recorded
- `store=false`
- cached responses retained only for reproducibility
- max calls capped
- prompts and parsing scripts released
- API results are corroborating, not the sole basis for claims

Use this wording in the Results section:

> Because API models and prices can change, we treat the GPT-5.5 audit as a time-stamped stress test. The deterministic local sweeps remain the main reproducible evidence.

## 8. Minimum set to finish before submission

If time is limited, do only these:

1. Add `--run-name` to `src/openai_audit.py` so API artifacts cannot overwrite each other.
2. Run GPT-5.5 auxiliary matching on 48 T2/T3 personas and 5 conditions.
3. Add one table to the paper with GPT-5.5 Aux@1/Aux@3/T2/T3.
4. Add one paragraph comparing GPT-5.5 results to the local attacker.
5. Keep the GPT-5.5-pro and RAG generation audits as future work unless the GPT-5.5 run is clean.

## 9. Success criteria

The extra API experiments are worth including if they show one of these:

- Direct redaction, Presidio, or document-local anonymization remain substantially more matchable than LinkGuard under GPT-5.5.
- GPT-5.5 identifies the same signal families as the local ablations: role/institution, location, rare event, and combinations.
- GPT-5.5 document-local anonymization helps but still misses corpus-level uniqueness.
- LinkGuard’s residual matches are mostly low-confidence or based on coarse context.

If GPT-5.5 results are noisy, still report them honestly as a small stress audit and keep the main paper centered on deterministic reproducible evidence.
