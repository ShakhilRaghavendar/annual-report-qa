# Gold quote retrieved — retrieval at sentence granularity (no LLM)

| retriever | k | all quote / page | factual quote / page | conceptual quote / page | cross_year quote / page | unit_trap quote / page | avg tokens/q | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hybrid+rerank | 6 | **0.90** / 0.95 (62) | **0.91** / 1.00 (22) | **0.95** / 0.95 (20) | **0.90** / 0.90 (10) | **0.80** / 0.90 (10) | 3185 | 3.53 |
| hybrid+rerank | 7 | **0.92** / 0.95 (62) | **0.95** / 1.00 (22) | **0.95** / 0.95 (20) | **0.90** / 0.90 (10) | **0.80** / 0.90 (10) | 3722 | 3.13 |
| hybrid+rerank+expand | 4 | **0.94** / 0.97 (62) | **0.95** / 1.00 (22) | **0.95** / 1.00 (20) | **0.90** / 0.90 (10) | **0.90** / 0.90 (10) | 5149 | 3.12 |
| hybrid+rerank+expand3 | 5 | **0.92** / 0.97 (62) | **0.91** / 1.00 (22) | **0.95** / 1.00 (20) | **0.90** / 0.90 (10) | **0.90** / 0.90 (10) | 4912 | 3.23 |
| hybrid+rerank+expand2 | 5 | **0.90** / 0.97 (62) | **0.91** / 1.00 (22) | **0.95** / 1.00 (20) | **0.90** / 0.90 (10) | **0.80** / 0.90 (10) | 4169 | 3.94 |

quote = the gold sentence is inside a passage the model would be given; page = a gold page overlaps a passage (the generous check). avg tokens/q = passage text handed to the model per question.

**hybrid+rerank k=6 quote misses (6):** INFY-FY25-01, TCS-FY24-02, BAJFINANCE-FY25-06, TATAMOTORS-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank k=7 quote misses (5):** INFY-FY25-01, BAJFINANCE-FY25-06, TATAMOTORS-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank+expand k=4 quote misses (4):** TCS-FY24-02, BAJFINANCE-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank+expand3 k=5 quote misses (5):** INFY-FY25-01, TCS-FY24-02, BAJFINANCE-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank+expand2 k=5 quote misses (6):** INFY-FY25-01, TCS-FY24-02, BAJFINANCE-FY25-06, TATAMOTORS-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
