# LinkGuard Residual Match Analysis

Top-1 residual matches: 4.
Additional top-3 residual matches: 21.
Median top-1 score margin: 0.0036.
Median estimated k among top-1 residuals: 8.5.

## Top-1 Residual Matches

| persona_id | risk_tier | rank | score_true | score_margin | estimated_k | residual_exact_fields | residual_coarse_fields            | shared_fields_with_nearest_wrong                                            |
| ---------- | --------- | ---- | ---------- | ------------ | ----------- | --------------------- | --------------------------------- | --------------------------------------------------------------------------- |
| P0011      | T3        | 1    | 0.021      | 0.008        | 12          | none                  | medical_context,financial_context | occupation,family_structure,medical_context,hobby_or_affiliation,rare_event |
| P0032      | T3        | 1    | 0.016      | 0.003        | 5           | none                  | financial_context,legal_context   | employer_type,financial_context,schedule_pattern                            |
| P0101      | T3        | 1    | 0.015      | 0.000        | 27          | none                  | financial_context                 | medical_context,financial_context,rare_event                                |
| P0117      | T1        | 1    | 0.014      | 0.004        | 5           | none                  | none                              | medical_context,financial_context,legal_context,hobby_or_affiliation        |

## Top-3 Non-Top-1 Residual Matches

| persona_id | risk_tier | rank | score_true | score_margin | estimated_k | residual_exact_fields | residual_coarse_fields                           | shared_fields_with_nearest_wrong                                              |
| ---------- | --------- | ---- | ---------- | ------------ | ----------- | --------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------- |
| P0004      | T2        | 2    | 0.013      | -0.000       | 16          | none                  | financial_context                                | city,education,schedule_pattern                                               |
| P0008      | T3        | 2    | 0.013      | -0.003       | 17          | none                  | financial_context                                | employer_type,hobby_or_affiliation                                            |
| P0009      | T1        | 2    | 0.011      | -0.004       | 27          | none                  | none                                             | family_structure,financial_context,schedule_pattern                           |
| P0028      | T2        | 2    | 0.014      | -0.001       | 8           | none                  | family_structure,financial_context,legal_context | employer_type,financial_context,legal_context,hobby_or_affiliation,rare_event |
| P0037      | T2        | 2    | 0.011      | -0.002       | 20          | none                  | financial_context                                | education,family_structure,financial_context,hobby_or_affiliation             |
| P0039      | T1        | 2    | 0.006      | -0.000       | 20          | none                  | none                                             | medical_context,legal_context,schedule_pattern                                |
| P0041      | T3        | 2    | 0.015      | -0.004       | 17          | none                  | financial_context                                | family_structure,financial_context,schedule_pattern                           |
| P0056      | T3        | 2    | 0.020      | -0.002       | 10          | none                  | medical_context,financial_context                | family_structure,financial_context,schedule_pattern,rare_event                |
| P0097      | T2        | 2    | 0.014      | -0.002       | 6           | none                  | financial_context,legal_context                  | education,financial_context,hobby_or_affiliation,rare_event                   |
| P0103      | T2        | 2    | 0.012      | -0.012       | 5           | none                  | financial_context,legal_context                  | city,family_structure,financial_context                                       |
| P0104      | T3        | 2    | 0.013      | -0.002       | 27          | none                  | financial_context                                | financial_context,legal_context,schedule_pattern                              |
| P0109      | T2        | 2    | 0.014      | -0.001       | 13          | none                  | medical_context,financial_context                | occupation,family_structure,medical_context,rare_event                        |
| P0119      | T3        | 2    | 0.012      | -0.010       | 6           | none                  | financial_context,legal_context                  | medical_context,financial_context,legal_context,rare_event                    |
| P0014      | T3        | 3    | 0.014      | -0.007       | 5           | none                  | medical_context,financial_context,legal_context  | employer_type,education,family_structure,medical_context                      |
| P0019      | T2        | 3    | 0.010      | -0.013       | 13          | none                  | medical_context,financial_context                | city,legal_context                                                            |
| P0033      | T1        | 3    | 0.006      | -0.005       | 15          | none                  | none                                             | occupation,medical_context,hobby_or_affiliation                               |
| P0044      | T3        | 3    | 0.013      | -0.002       | 8           | none                  | financial_context,legal_context                  | employer_type,financial_context,hobby_or_affiliation                          |
| P0057      | T1        | 3    | 0.006      | -0.002       | 8           | none                  | none                                             | city,employer_type,education,hobby_or_affiliation                             |
| P0061      | T2        | 3    | 0.016      | -0.007       | 7           | none                  | medical_context,financial_context                | city,education,schedule_pattern,hobby_or_affiliation                          |
| P0099      | T1        | 3    | 0.005      | -0.003       | 13          | none                  | none                                             | education,medical_context,hobby_or_affiliation                                |
| P0106      | T2        | 3    | 0.010      | -0.002       | 16          | none                  | financial_context                                | city,occupation,family_structure                                              |
