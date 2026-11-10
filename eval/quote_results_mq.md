# Gold quote retrieved — retrieval at sentence granularity (no LLM)

| retriever | k | all quote / page | factual quote / page | conceptual quote / page | cross_year quote / page | unit_trap quote / page | avg tokens/q | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hybrid+rerank+expand | 4 | **0.94** / 0.97 (62) | **0.95** / 1.00 (22) | **0.95** / 1.00 (20) | **0.90** / 0.90 (10) | **0.90** / 0.90 (10) | 5149 | 5.63 |
| hybrid+rerank+mq+expand | 4 | **0.94** / 0.95 (62) | **0.95** / 0.95 (22) | **0.95** / 1.00 (20) | **1.00** / 1.00 (10) | **0.80** / 0.80 (10) | 5083 | 18.60 |
| hybrid+rerank+mq | 5 | **0.87** / 0.92 (62) | **0.86** / 0.95 (22) | **0.95** / 0.95 (20) | **1.00** / 1.00 (10) | **0.60** / 0.70 (10) | 2626 | 107.10 |
| hybrid+mq+expand | 4 | **0.85** / 0.89 (62) | **0.86** / 0.91 (22) | **0.90** / 0.90 (20) | **0.70** / 0.80 (10) | **0.90** / 0.90 (10) | 5166 | 0.65 |

quote = the gold sentence is inside a passage the model would be given; page = a gold page overlaps a passage (the generous check). avg tokens/q = passage text handed to the model per question.

**hybrid+rerank+expand k=4 quote misses (4):** TCS-FY24-02, BAJFINANCE-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank+mq+expand k=4 quote misses (4):** TCS-FY24-02, BAJFINANCE-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-06
**hybrid+rerank+mq k=5 quote misses (8):** HDFCBANK-FY25-01, INFY-FY25-01, INFY-FY25-07, TCS-FY24-02, BAJFINANCE-FY25-06, TATAMOTORS-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-06
**hybrid+mq+expand k=4 quote misses (9):** INFY-FY25-03, TCS-FY24-02, RELIANCE-FY24-06, TATAMOTORS-FY25-03, TATAMOTORS-FY25-05, SUNPHARMA-FY25-05, HINDUNILVR-FY25-01, HINDUNILVR-FY25-05, LT-FY25-05
