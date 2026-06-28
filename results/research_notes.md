# Sprint Research Notes

This is an API-free first pass over the synthetic sprint benchmark.

## Main Observations

- Direct redaction leaves auxiliary matching top-1 at 0.708 and pairwise linkage F1 at 0.214, so span-level PII removal is not enough in this generated setting.
- Presidio-style direct PII detection leaves auxiliary matching top-1 at 0.594; off-the-shelf document PII removal does not address cross-document quasi-identifiers.
- Consistent pseudonyms produce pairwise linkage F1 0.979; stable handles are visibly risky.
- LinkGuard changes auxiliary top-1 from 0.604 under local anonymization to 0.042, with issue accuracy 1.000.
- Aggressive redaction gives auxiliary top-1 0.052 but issue accuracy 0.350, which anchors the utility-loss side of the frontier.

## Next Experiments

1. Do final title/abstract polish without changing the validated claim surface.
2. Expand the cached OpenAI audit only if budget allows, keeping neutral document labels and the same candidate-set protocol.
3. If time allows after submission, expand the synthetic style stress test to more domains while keeping the no-real-data ethics boundary.
4. Verify the official anonymity and artifact policies before final upload.
