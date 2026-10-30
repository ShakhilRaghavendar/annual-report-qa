# Answer eval: answers_run2 vs answers (45 questions in both)

| kind | n | correct | partial | wrong | cited gold page | gold page retrieved (run 2) |
| --- | --- | --- | --- | --- | --- | --- |
| all | 45 | 0.62 → **0.58** | 0.20 → 0.24 | 0.18 → 0.18 | 0.84 → **0.84** | 0.98 |
| factual | 16 | 0.81 → **0.81** | 0.00 → 0.00 | 0.19 → 0.19 | 0.88 → **0.88** | 1.00 |
| conceptual | 15 | 0.40 → **0.33** | 0.53 → 0.53 | 0.07 → 0.13 | 0.87 → **0.93** | 1.00 |
| cross_year | 7 | 0.71 → **0.71** | 0.00 → 0.29 | 0.29 → 0.00 | 0.86 → **0.86** | 1.00 |
| unit_trap | 7 | 0.57 → **0.43** | 0.14 → 0.14 | 0.29 → 0.43 | 0.71 → **0.57** | 0.86 |

Verdict improved on 3, worsened on 5.

Improved: INFY-FY25-06 (wrong→partial), TCS-FY25-03 (wrong→correct), HDFCBANK-FY25-06 (wrong→partial)
Worsened: RELIANCE-FY24-03 (correct→partial), RELIANCE-FY25-04 (partial→wrong), HDFCBANK-FY25-05 (partial→wrong), ICICIBANK-FY25-06 (correct→wrong), BAJFINANCE-FY25-04 (correct→partial)

Run 2's 8 wrong answers: 1 retrieval failures (gold page never shown to the model), 7 reading failures (shown and still missed).
