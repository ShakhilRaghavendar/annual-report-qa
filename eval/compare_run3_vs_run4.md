# Answer eval: answers_run3 vs answers_run4 (62 questions in both)

| kind | n | correct | partial | wrong | cited gold page | gold page retrieved (run 2) |
| --- | --- | --- | --- | --- | --- | --- |
| all | 62 | 0.58 → **0.74** | 0.23 → 0.11 | 0.19 → 0.15 | 0.82 → **0.85** | 0.97 |
| factual | 22 | 0.82 → **0.91** | 0.00 → 0.05 | 0.18 → 0.05 | 0.86 → **0.91** | 1.00 |
| conceptual | 20 | 0.30 → **0.60** | 0.55 → 0.25 | 0.15 → 0.15 | 0.90 → **0.90** | 1.00 |
| cross_year | 10 | 0.60 → **0.70** | 0.20 → 0.10 | 0.20 → 0.20 | 0.80 → **0.70** | 0.90 |
| unit_trap | 10 | 0.60 → **0.70** | 0.10 → 0.00 | 0.30 → 0.30 | 0.60 → **0.80** | 0.90 |

Verdict improved on 13, worsened on 4.

Improved: HDFCBANK-FY25-01 (wrong→correct), INFY-FY25-01 (wrong→correct), SUNPHARMA-FY25-02 (partial→correct), INFY-FY25-06 (partial→correct), TCS-FY24-04 (partial→correct), ICICIBANK-FY25-06 (wrong→correct), BAJFINANCE-FY25-04 (partial→correct), TATAMOTORS-FY25-03 (partial→correct), SUNPHARMA-FY25-05 (wrong→partial), HINDUNILVR-FY24-04 (partial→correct), LT-FY25-02 (wrong→correct), LT-FY25-03 (partial→correct), LT-FY25-05 (wrong→partial)
Worsened: SUNPHARMA-FY25-01 (partial→wrong), RELIANCE-FY24-03 (partial→wrong), HDFCBANK-FY25-06 (partial→wrong), BAJFINANCE-FY24-02 (correct→partial)

Run 2's 9 wrong answers: 2 retrieval failures (gold page never shown to the model), 7 reading failures (shown and still missed).
