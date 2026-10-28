# Answer eval: answers_run1 vs answers (45 questions in both)

| kind | n | correct | partial | wrong | cited gold page | gold page retrieved (run 2) |
| --- | --- | --- | --- | --- | --- | --- |
| all | 45 | 0.69 → **0.62** | 0.13 → 0.20 | 0.18 → 0.18 | 0.64 → **0.84** | 0.98 |
| factual | 16 | 0.81 → **0.81** | 0.00 → 0.00 | 0.19 → 0.19 | 0.56 → **0.88** | 1.00 |
| conceptual | 15 | 0.60 → **0.40** | 0.27 → 0.53 | 0.13 → 0.07 | 0.93 → **0.87** | 1.00 |
| cross_year | 7 | 0.71 → **0.71** | 0.29 → 0.00 | 0.00 → 0.29 | 0.43 → **0.86** | 1.00 |
| unit_trap | 7 | 0.57 → **0.57** | 0.00 → 0.14 | 0.43 → 0.29 | 0.43 → **0.71** | 0.86 |

Verdict improved on 4, worsened on 6.

Improved: SUNPHARMA-FY25-01 (wrong→partial), RELIANCE-FY24-03 (partial→correct), RELIANCE-FY25-04 (wrong→partial), HDFCBANK-FY25-05 (wrong→partial)
Worsened: SUNPHARMA-FY25-02 (correct→partial), INFY-FY25-06 (partial→wrong), TCS-FY25-03 (correct→wrong), TCS-FY24-04 (correct→partial), HDFCBANK-FY25-06 (partial→wrong), TATAMOTORS-FY25-03 (correct→partial)

Run 2's 8 wrong answers: 1 retrieval failures (gold page never shown to the model), 7 reading failures (shown and still missed).
