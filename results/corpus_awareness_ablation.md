# Corpus-Awareness Ablation

| label                    | min_true_estimated_k | median_true_estimated_k | target_k_coverage | mean_l1_fields | mean_l2_fields | edit_ratio | aux_top1 | field_aux_top1 | attr_exact_recovery | attr_coarse_recovery | issue_acc | retrieval_recall_at_5 |
| ------------------------ | -------------------- | ----------------------- | ----------------- | -------------- | -------------- | ---------- | -------- | -------------- | ------------------- | -------------------- | --------- | --------------------- |
| True corpus LinkGuard    | 5.000                | 8.000                   | 1.000             | 1.750          | 9.250          | 0.535      | 0.042    | 0.240          | 0.000               | 0.112                | 1.000     | 1.000                 |
| Shuffled corpus stats    | 1.000                | 13.000                  | 0.917             | 1.608          | 9.392          | 0.536      | 0.042    | 0.198          | 0.000               | 0.111                | 1.000     | 1.000                 |
| Global L1 generalization | 1.000                | 1.000                   | 0.000             | 11.000         | 0.000          | 0.381      | 0.198    | 0.979          | 0.000               | 0.787                | 1.000     | 1.000                 |
| Target-k suppression     | 5.000                | 8.000                   | 1.000             | 0.000          | 9.417          | 0.526      | 0.115    | 0.271          | 0.045               | 0.100                | 1.000     | 1.000                 |
