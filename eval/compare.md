# Answer eval: answers_run1 vs answers (62 questions in both)

| kind | n | correct | partial | wrong | cited gold page | gold page retrieved (run 2) |
| --- | --- | --- | --- | --- | --- | --- |
| all | 62 | 0.63 → **0.58** | 0.15 → 0.23 | 0.23 → 0.19 | 0.61 → **0.82** | 0.95 |
| factual | 22 | 0.82 → **0.82** | 0.00 → 0.00 | 0.18 → 0.18 | 0.59 → **0.86** | 1.00 |
| conceptual | 20 | 0.45 → **0.30** | 0.35 → 0.55 | 0.20 → 0.15 | 0.85 → **0.90** | 0.95 |
| cross_year | 10 | 0.60 → **0.60** | 0.20 → 0.20 | 0.20 → 0.20 | 0.30 → **0.80** | 0.90 |
| unit_trap | 10 | 0.60 → **0.60** | 0.00 → 0.10 | 0.40 → 0.30 | 0.50 → **0.60** | 0.90 |

Verdict improved on 4, worsened on 5.

Improved: SUNPHARMA-FY25-01 (wrong→partial), TATAMOTORS-FY25-06 (wrong→correct), HINDUNILVR-FY24-04 (wrong→partial), LT-FY24-04 (partial→correct)
Worsened: SUNPHARMA-FY25-02 (correct→partial), TCS-FY24-04 (correct→partial), ICICIBANK-FY25-06 (correct→wrong), BAJFINANCE-FY25-04 (correct→partial), TATAMOTORS-FY25-03 (correct→partial)

Run 2's 12 wrong answers: 3 retrieval failures (gold page never shown to the model), 9 reading failures (shown and still missed).
