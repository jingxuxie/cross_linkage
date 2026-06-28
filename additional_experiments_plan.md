# Additional Experiment Plan for the Cross-Document Linkage Paper

This plan is written for the current `cross_linkage` repo state after the first synthetic sprint. The main paper should continue to emphasize that the core results are deterministic, local, and reproducible; API-based experiments should be used as corroborating stress tests rather than the foundation of the paper.

## 1. Current status: what is already strong

The paper already has a coherent workshop contribution:

- A synthetic, controlled benchmark with 120 personas and 480 documents.
- Multiple transformation baselines: direct redaction, Presidio-style redaction, stable pseudonyms, per-document pseudonyms, document-local anonymization proxy, LinkGuard, and aggressive redaction.
- Multiple privacy views: pairwise linkage, fixed-K clustering, auxiliary-profile matching, exact quasi-identifier recovery, RAG-style exposure, tier analysis, candidate-size sensitivity, and attacker-family sensitivity.
- Multiple utility views: issue classification, retrieval Recall@5, lightweight fact preservation, and body-only utility stress testing.
- A strong central finding: document-local de-identification leaves cross-document linkage risk, while corpus-aware generalization gives a better privacy–utility point than blanket redaction.

The current main quantitative story should remain:

| Claim | Strongest current evidence |
|---|---|
| Direct PII removal is insufficient | Direct redaction leaves Aux@1 at 0.708, unchanged from original. |
| Presidio-style PII redaction is not enough | Presidio-style redaction leaves Aux@1 at 0.594. |
| Stable pseudonyms are dangerous linkage handles | Stable pseudonyms give pairwise linkage F1 0.979. |
| Corpus-aware generalization helps | LinkGuard at target k=5 reduces Aux@1 to 0.042 and exact quasi-ID recovery to 0.000. |
| Blanket redaction is not the right default | Aggressive redaction has similar Aux@1, but issue accuracy falls to 0.350 and Recall@5 to 0.312. |
| The result is not just a template artifact | Noisy-style stress test preserves the ordering. |
| The result is not just one attacker | Word, char, hybrid, and field-weighted attackers preserve the privacy ordering. |

## 2. Did the paper use API yet?

The honest wording is:

> The main benchmark pipeline is API-free by default. The main quantitative results are deterministic local experiments. The repo also contains a small cached OpenAI audit, which should be reported as preliminary corroboration rather than the primary evidence.

Do **not** write “we did not use any API” in the paper, because the repo already contains cached OpenAI audit results. Instead write:

> We report local deterministic sweeps as the main results and include a small cached OpenAI audit over 12 T2/T3 personas as a preliminary robustness check.

## 3. Highest-value additional experiment

### Experiment A: frontier-model auxiliary-profile attacker audit

**Goal:** Check whether a stronger instruction-following model sees the same privacy ordering as the local TF-IDF attackers.

**Recommended model:** `gpt-5.5` as the main frontier attacker; optionally add `gpt-5.4-mini` as a cheaper secondary attacker.

**Why it helps reviewers:**  
Reviewers may worry that TF-IDF attackers are too weak or too synthetic. A frontier-model attacker directly addresses this by asking whether the transformed documents still let a capable LLM match the correct auxiliary profile among decoys.

**Scope options:**

| Scope | Personas | Conditions | Repeats | Calls | Expected cost |
|---|---:|---|---:|---:|---:|
| Minimal | 24 T2/T3 | C1, C1b, C4, C5, C6 | 1 | 120 | <$10 |
| Good | 48 balanced T1/T2/T3 | C1, C1b, C4, C4-OpenAI, C5, C6 | 1 | 288 | ~$10–$20 |
| Strong | 96 held-out | C1, C1b, C4, C4-OpenAI, C5, C6 | 1 | 576 | ~$20–$40 |
| Strong + uncertainty | 96 held-out | same six | 3 shuffled repeats | 1,728 | ~$60–$100 |

These are rough estimates. The true cost depends on prompt length, document length, candidate profile length, output length, and whether you use Batch/Flex.

### Prompt: LLM auxiliary attacker

Use neutral labels only. Do not expose `persona_id`, `doc_id`, or true candidate IDs.

```text
You are conducting a defensive privacy audit on synthetic data.

Task:
Given several transformed documents that may refer to the same synthetic person,
rank which auxiliary profile is most likely to match the documents.

Important:
- All data is synthetic.
- Do not try to identify any real person.
- Use only the text below.
- Candidate labels are arbitrary.
- Return JSON only.

Transformed documents:
[DOC_A]
...
[DOC_B]
...
[DOC_C]
...
[DOC_D]
...

Candidate auxiliary profiles:
[A] ...
[B] ...
[C] ...
...
[J] ...

Return JSON with this schema:
{
  "top1": "A-J",
  "top3": ["A-J", "A-J", "A-J"],
  "confidence": 0.0-1.0,
  "evidence_fields": ["location", "role", "employer", "family", "medical", "financial", "legal", "schedule", "affiliation", "rare_event", "other"],
  "brief_reason": "one sentence without chain-of-thought"
}
```

**Controls:**

- Shuffle candidate order independently per call.
- Use neutral candidate labels A–J.
- Remove `persona_id`, `doc_id`, and any synthetic labels that encode ground truth.
- Set temperature to 0.
- Ask for JSON only.
- Cache every request and response with a hash of prompt content, model, and parameters.
- Run a parser that rejects malformed JSON and retries once.
- Report malformed rate.

**Metrics:**

- Aux@1, Aux@3, MRR by condition.
- Tiered Aux@1 for T1/T2/T3.
- Bootstrap 95% CIs over personas.
- Evidence-field frequency: which signals does the LLM cite?
- Compare against local word, hybrid, and field-weighted attackers.

**Success criterion for the paper:**

A high-impact result would look like:

> A GPT-5.5 attacker preserves the same ordering as local attackers: direct/document-local transformations remain highly matchable, while LinkGuard substantially reduces matching but does not eliminate all risk.

Even if GPT-5.5 finds higher residual risk under LinkGuard, that is still useful: it strengthens the paper by exposing a remaining failure mode and justifies the limitations section.

## 4. Second-highest-value experiment

### Experiment B: LLM document-local anonymizer baseline

**Goal:** Compare LinkGuard to a stronger document-local baseline that uses an LLM to anonymize each document independently.

**Why it helps:**  
A reviewer may argue that your C4 document-local proxy is too weak. An LLM anonymizer baseline makes the comparison more credible.

**Conditions to add:**

- `c4_openai_doc_local_gpt55`: GPT-5.5 anonymizes each document independently.
- Optional cheaper baseline: `c4_openai_doc_local_mini`: GPT-5.4-mini anonymizes each document independently.
- Keep your existing `c4_openai_doc_local` if already cached, but clearly specify which model generated it.

### Prompt: document-local anonymizer

```text
You are anonymizing one synthetic support document for a privacy-preserving benchmark.

Goal:
Remove or generalize direct identifiers and details that could identify a person.
Preserve the service issue and task-relevant facts as much as possible.

Rules:
- Remove names, emails, phone numbers, addresses, account IDs.
- Generalize exact locations, rare events, institutions, schedules, family details, and health/legal/financial details when they could identify a person.
- Do not add new facts.
- Do not mention that the text is synthetic.
- Return only the anonymized document text.

Document:
...
```

**Evaluation:**

Run the same local attackers and the GPT-5.5 auxiliary attacker on this condition. This lets you answer:

- Does a stronger document-local LLM anonymizer beat C4?
- Does it still leave corpus-level linkage risk?
- Does LinkGuard still offer a better privacy–utility point?

**Expected paper framing:**

> Even a capable document-local anonymizer can miss corpus-level combinations because it does not know how rare repeated fields are across the corpus.

## 5. Third-highest-value experiment

### Experiment C: harder RAG exposure using generated auxiliary queries

The current RAG diagnostic uses exact synthetic profile queries. That is a good first stress test, but reviewers may see it as too direct. Add a harder but more realistic query set:

1. For each target persona, generate 3 profile-like queries:
   - A short query: one sentence with role + location.
   - A medium query: role + location + one sensitive context.
   - A verbose query: a noisy paraphrase of the auxiliary profile.
2. Generate paraphrases using a cheap model or deterministic templates.
3. Run retrieval against each transformed corpus.
4. Report Hit@5, Multi@10, DocRecall@10, and MRR by query type and risk tier.

**Expected result:**

LinkGuard should reduce exposure most on verbose/profile-like queries, while aggressive redaction may reduce exposure more but at higher utility cost.

**Paper placement:**

A small table in Results or an appendix:

| Query type | Direct Hit@5 | Presidio Hit@5 | Local Hit@5 | LinkGuard Hit@5 | Aggressive Hit@5 |
|---|---:|---:|---:|---:|---:|
| Short | ... | ... | ... | ... | ... |
| Medium | ... | ... | ... | ... | ... |
| Verbose | ... | ... | ... | ... | ... |

## 6. Fourth-highest-value experiment

### Experiment D: external benchmark bridge

A full real-data experiment is not necessary for this workshop and may create ethics/review complexity. But adding a small external benchmark bridge would improve credibility.

Options:

1. **RAT-Bench bridge:** Run available anonymization examples through your auxiliary-risk evaluator where possible. If the data is not naturally multi-document, report this as a document-level indirect-identifier stress bridge rather than cross-document linkage.
2. **TAB bridge:** Use legal-text anonymization examples to test whether direct span masking preserves indirect legal/person context. Again, do not force a cross-document claim if the data does not support it.
3. **Synthetic-to-public style bridge:** Re-render your synthetic documents in legal/clinical/support styles and show the privacy ordering holds across style.

**Recommendation:**  
Do not attempt a large external benchmark before submission unless you already have the data pipeline. The noisy-style synthetic stress test already helps. A small “external bridge” paragraph is optional.

## 7. Fifth-highest-value experiment

### Experiment E: LLM utility judge or QA utility

The current utility metrics are local and lightweight. That is acceptable for a workshop paper, but a small LLM utility audit could make the privacy–utility claim more persuasive.

**Design:**

For 48 personas × 4 domains × selected conditions, ask a model to answer task-relevant questions from the transformed document:

- What is the service issue?
- What domain is this document from?
- What constraints matter for scheduling or support?
- What action should the service provider take next?

Compare answers to gold labels/facts.

**Use model choice carefully:**

- Use a cheaper model for utility judging if cost matters.
- Use GPT-5.5 only if you need a strong judge for ambiguous cases.
- Keep deterministic local utility as the main metric.

**Output metrics:**

- Issue preservation.
- Domain preservation.
- Constraint preservation.
- Hallucination or unsupported-detail rate.
- Over-redaction failure rate.

## 8. Ablations that are cheap and worthwhile

These do not require API calls and would make the method section stronger.

### A. Corpus-awareness ablation

Compare:

- LinkGuard with true corpus statistics.
- LinkGuard with shuffled corpus statistics.
- LinkGuard with global field generalization but no per-person uniqueness estimate.
- LinkGuard with only direct redaction plus target-k field suppression.

This isolates whether the gain comes from corpus-aware uniqueness or just heavier editing.

### B. Larger synthetic corpus

Try 240 personas and 960 documents. The goal is not scale; it tests whether target-k behavior changes with a larger population.

Report only one compact table:

| n personas | Direct Aux@1 | LinkGuard Aux@1 | LinkGuard edit | Issue acc | Ret@5 |
|---:|---:|---:|---:|---:|---:|

### C. Documents-per-person sensitivity

Try 2, 4, and 8 documents per persona. This directly tests the cross-document thesis.

Expected pattern:

- More documents per persona should increase linkage risk under document-local transformations.
- LinkGuard should be less sensitive because it generalizes stable quasi-identifiers.

### D. Auxiliary candidate hardness

You already have 10/20/50 candidate sizes. Add a sentence explaining why top-1 can go down with larger candidate pools but the ordering remains meaningful.

## 9. Recommended final experiment package

For the strongest workshop paper with limited API budget, run this exact package:

1. **GPT-5.5 auxiliary attacker audit**
   - 48 held-out personas, stratified across T1/T2/T3.
   - Conditions: C1, C1b, C4, C4-OpenAI, C5, C6.
   - One repeat initially; add two more shuffled repeats only if results are noisy.
2. **GPT-5.5 or GPT-5.4-mini document-local anonymizer**
   - 48 personas × 4 documents.
   - Reuse in the attacker audit as C4-OpenAI.
3. **Generated-query RAG exposure**
   - No GPT-5.5 required if you use deterministic paraphrase templates.
   - Evaluate short, medium, and verbose queries.
4. **Corpus-awareness ablation**
   - No API required.
   - Adds method credibility.

This package is likely enough to upgrade the paper from “nice synthetic result” to “credible workshop audit framework.”

## 10. Suggested paper edits after additional experiments

Add one paragraph to the Results section:

> To test whether the local attackers understate risk, we ran a GPT-5.5 auxiliary-profile audit on a stratified subset of held-out personas. The frontier-model attacker preserved the same qualitative ordering as the local attackers: direct and document-local transformations remained highly matchable, while LinkGuard reduced but did not eliminate auxiliary matching. This supports our main claim that corpus-level quasi-identifier risk is not an artifact of TF-IDF matching.

Add one compact table:

| Condition | Local Aux@1 | Field Aux@1 | GPT-5.5 Aux@1 | GPT-5.5 Aux@3 | Issue acc | Ret@5 |
|---|---:|---:|---:|---:|---:|---:|
| Direct redaction | ... | ... | ... | ... | ... | ... |
| Presidio-style | ... | ... | ... | ... | ... | ... |
| Document-local proxy | ... | ... | ... | ... | ... | ... |
| GPT document-local | ... | ... | ... | ... | ... | ... |
| LinkGuard | ... | ... | ... | ... | ... | ... |
| Aggressive | ... | ... | ... | ... | ... | ... |

Add one limitations sentence:

> The GPT-5.5 audit is subset-based and should be interpreted as a stress test rather than a population estimate; nevertheless, it is useful because it checks whether the privacy ordering persists under a stronger instruction-following attacker.

## 11. API budget management

Use the current OpenAI model/pricing page before running the experiment, because prices can change. As of the current docs checked for this plan:

- `gpt-5.5` is listed as the flagship model for complex reasoning and coding.
- Standard short-context pricing is listed as $5 per 1M input tokens and $30 per 1M output tokens.
- Batch and Flex short-context pricing are listed as $2.50 per 1M input tokens and $15 per 1M output tokens.

Practical budget tips:

- Use Batch or Flex if latency does not matter.
- Use short prompts and compact candidate profiles.
- Cap output to 200–300 tokens.
- Use structured JSON output.
- Cache all calls.
- Start with 24 personas before scaling to 48 or 96.
- Do not use `gpt-5.5-pro`; it is too expensive for this paper.

## 12. Data handling and ethics

Use synthetic data only for API calls.

OpenAI’s API data controls page says API data is not used to train or improve models unless you explicitly opt in, but abuse-monitoring logs may contain prompts/responses and are retained up to 30 days by default. This is acceptable for synthetic benchmark text, but it is not a reason to send real sensitive data.

In the paper, write:

> All API audits use synthetic benchmark documents only. We do not send real sensitive data, public profiles, patient records, legal records, or customer records to external APIs.

## 13. Implementation checklist

Create or update these scripts:

- `src/openai_aux_attacker.py`
  - inputs: transformed docs, auxiliary profiles, candidate sets, conditions, model, max personas
  - outputs: `results/openai_aux_attacker_rows.csv`, `results/openai_aux_attacker_summary.csv`
- `src/openai_doc_local_anonymizer.py`
  - inputs: original docs, model, max docs
  - outputs: `data/transformed/c4_openai_doc_local_gpt55.jsonl`
- `src/generated_rag_queries.py`
  - outputs: `data/generated_profile_queries.jsonl`, `results/rag_generated_query_exposure.csv`
- `src/corpus_awareness_ablation.py`
  - outputs: `results/corpus_awareness_ablation.csv`

Add claim checks to `src/verify_claims.py`:

- Assert no raw `persona_id` appears in OpenAI attacker prompts.
- Assert candidate labels are neutral.
- Assert all OpenAI results have parseable JSON.
- Assert cached calls include model, prompt hash, and timestamp.
- Assert any new paper table values match CSV outputs.

## 14. Go/no-go criteria

Use the GPT-5.5 results in the main paper if:

- At least 48 personas are evaluated, or
- 24 personas are evaluated and the effect size is very clear with CIs or per-tier consistency.

Keep it in appendix or limitations if:

- Only 12 personas are evaluated.
- There are parsing failures.
- Results are unstable across shuffled candidate order.
- The model frequently refuses or gives non-JSON outputs.

Do not overclaim. The strongest framing is:

> The frontier-model audit corroborates the local privacy ordering, while the deterministic synthetic benchmark remains the main reproducible evidence.
