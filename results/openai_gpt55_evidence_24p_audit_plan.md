# GPT-5.5 Evidence Extraction Audit Plan

Run name: `gpt55_evidence_24p`
Model: `gpt-5.5`
Reasoning effort: `none`
Max output tokens: `650`
Git commit: `6b1880a`
Total planned calls: 24
Cached calls: 24
Missing calls: 0

## Selection

- `direct_success`: GPT-5.5 top-1 matches under direct redaction.
- `linkguard_residual`: GPT-5.5 top-1 residual matches under LinkGuard.
- `aggressive_failure`: aggressive-redaction cases where GPT-5.5 misses the target in top-3.

| bucket             | condition               | n | cached | mean_input_chars |
| ------------------ | ----------------------- | - | ------ | ---------------- |
| direct_success     | c1_direct_redaction     | 8 | 8      | 3644.5           |
| linkguard_residual | c5_linkguard            | 8 | 8      | 3556.1           |
| aggressive_failure | c6_aggressive_redaction | 8 | 8      | 3389.4           |

## Personas

direct_success:P0002, direct_success:P0005, direct_success:P0008, direct_success:P0011, direct_success:P0001, direct_success:P0004, direct_success:P0007, direct_success:P0010, linkguard_residual:P0002, linkguard_residual:P0005, linkguard_residual:P0011, linkguard_residual:P0014, linkguard_residual:P0007, linkguard_residual:P0019, linkguard_residual:P0025, linkguard_residual:P0037, aggressive_failure:P0002, aggressive_failure:P0008, aggressive_failure:P0017, aggressive_failure:P0020, aggressive_failure:P0001, aggressive_failure:P0016, aggressive_failure:P0028, aggressive_failure:P0034
