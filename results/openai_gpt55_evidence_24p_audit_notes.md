# GPT-5.5 Evidence Extraction Audit Notes

Run name: `gpt55_evidence_24p`
Model: `gpt-5.5`
Reasoning effort: `none`
Max output tokens: `650`
Started at UTC: `2026-06-28T10:45:56+00:00`
Git commit: `1761b8e`
Case count: 24
New API calls this run: 24
Cached calls served this run: 0
Token usage: 18248 input, 6259 output, 24507 total.
Usage CSV: `results/openai_gpt55_evidence_24p_audit_usage.csv`

All records sent to the API are synthetic transformed benchmark records.
All OpenAI response calls in this script pass `store=False` through `CachedOpenAI`.
Cached response files are under `cache/api_responses/`.

## Evidence Summary

# GPT-5.5 Evidence Extraction Audit

Qualitative signal audit over selected synthetic cases.

## Bucket Summary

| bucket_label                      | condition_label         | n | role_signal_rate | location_signal_rate | institution_signal_rate | role_critical_rate | location_critical_rate | high_specificity_signal_rate | uncertain_rate |
| --------------------------------- | ----------------------- | - | ---------------- | -------------------- | ----------------------- | ------------------ | ---------------------- | ---------------------------- | -------------- |
| Direct-redaction successful match | C1 direct redaction     | 8 | 0.750            | 1.000                | 0.500                   | 0.000              | 0.000                  | 0.475                        | 0.000          |
| LinkGuard residual match          | C5 LinkGuard            | 8 | 0.000            | 0.000                | 0.000                   | 0.000              | 0.000                  | 0.075                        | 0.875          |
| Aggressive low-signal contrast    | C6 aggressive redaction | 8 | 0.000            | 0.000                | 0.000                   | 0.000              | 0.000                  | 0.179                        | 0.750          |

## Signal Counts

| bucket             | bucket_label                      | condition               | condition_label         | signal               | count | case_rate |
| ------------------ | --------------------------------- | ----------------------- | ----------------------- | -------------------- | ----- | --------- |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | affiliation          | 1     | 0.125     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | family               | 7     | 0.875     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | institution          | 4     | 0.500     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | location             | 8     | 1.000     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | medical              | 4     | 0.500     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | rare_event           | 3     | 0.375     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | role                 | 6     | 0.750     |
| direct_success     | Direct-redaction successful match | c1_direct_redaction     | C1 direct redaction     | schedule             | 7     | 0.875     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | coarse_context       | 1     | 0.125     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | family               | 8     | 1.000     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | financial            | 4     | 0.500     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | information_removed  | 8     | 1.000     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | legal                | 3     | 0.375     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | medical              | 8     | 1.000     |
| linkguard_residual | LinkGuard residual match          | c5_linkguard            | C5 LinkGuard            | schedule             | 8     | 1.000     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | coarse_context       | 8     | 1.000     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | family               | 6     | 0.750     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | information_removed  | 8     | 1.000     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | legal                | 3     | 0.375     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | medical              | 5     | 0.625     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | model_over_inference | 1     | 0.125     |
| aggressive_failure | Aggressive low-signal contrast    | c6_aggressive_redaction | C6 aggressive redaction | schedule             | 8     | 1.000     |
