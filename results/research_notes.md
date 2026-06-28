# Sprint Research Notes

These notes summarize the deterministic no-API local benchmark. Cached GPT-5.5 stress-audit results and API provenance are tracked separately in `results/paper_ready_summary.md`, `REPRODUCE_RESULTS.md`, and the run-specific OpenAI audit artifacts.

## Main Observations

- Direct redaction leaves auxiliary matching top-1 at 0.708 and pairwise linkage F1 at 0.214, so span-level PII removal is not enough in this generated setting.
- Presidio-style direct PII detection leaves auxiliary matching top-1 at 0.594; off-the-shelf document PII removal does not address cross-document quasi-identifiers.
- Consistent pseudonyms produce pairwise linkage F1 0.979; stable handles are visibly risky.
- LinkGuard changes auxiliary top-1 from 0.604 under local anonymization to 0.042, with issue accuracy 1.000.
- Aggressive redaction gives auxiliary top-1 0.052 but issue accuracy 0.350, which anchors the utility-loss side of the frontier.

## Next Experiments

1. Keep the validated claim surface stable unless a new result passes the claim verifier.
2. Run the remaining GPT-5.5 RAG-generation calls only after explicit approval, then promote them only if parse success and claim checks pass.
3. If time allows after submission, expand the synthetic style stress test to more domains while keeping the no-real-data ethics boundary.
4. Re-run the no-API reproduction dry-run, submission package build, supplement generation, and claim verifier before final upload.
