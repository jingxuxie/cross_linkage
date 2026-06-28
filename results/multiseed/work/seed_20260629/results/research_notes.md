# Sprint Research Notes

This is an API-free first pass over the synthetic sprint benchmark.

## Main Observations

- Direct redaction leaves auxiliary matching top-1 at 0.760 and pairwise linkage F1 at 0.222, so span-level PII removal is not enough in this generated setting.
- Presidio-style direct PII detection leaves auxiliary matching top-1 at 0.677; off-the-shelf document PII removal does not address cross-document quasi-identifiers.
- Consistent pseudonyms produce pairwise linkage F1 0.986; stable handles are visibly risky.
- LinkGuard changes auxiliary top-1 from 0.729 under local anonymization to 0.042, with issue accuracy 1.000.
- Aggressive redaction gives auxiliary top-1 0.042 but issue accuracy 0.319, which anchors the utility-loss side of the frontier.

## Next Experiments

1. Add a small cached OpenAI document-local anonymization audit on 40 personas to check whether the local proxy is too weak or too strong.
2. Add a strong auxiliary matcher on the same subset, using candidate sets only and capped token spend.
3. Manually inspect 12 T3 examples where LinkGuard still matches top-1 to identify missing generalization ladders.
4. Increase decoy hardness for any risk tier with near-perfect auxiliary matching after LinkGuard.
