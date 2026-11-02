# Gold quote retrieved — retrieval at sentence granularity (no LLM)

| retriever | k | all quote / page | factual quote / page | conceptual quote / page | cross_year quote / page | unit_trap quote / page | avg tokens/q | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hybrid+rerank | 5 | **0.89** / 0.95 (62) | **0.86** / 1.00 (22) | **0.95** / 0.95 (20) | **0.90** / 0.90 (10) | **0.80** / 0.90 (10) | 2652 | 6.36 |
| hybrid+rerank | 8 | **0.92** / 0.95 (62) | **0.95** / 1.00 (22) | **0.95** / 0.95 (20) | **0.90** / 0.90 (10) | **0.80** / 0.90 (10) | 4240 | 5.07 |
| hybrid+rerank+expand | 3 | **0.87** / 0.89 (62) | **0.86** / 0.86 (22) | **0.90** / 0.95 (20) | **0.80** / 0.80 (10) | **0.90** / 0.90 (10) | 3934 | 4.66 |
| hybrid+rerank+expand | 5 | **0.94** / 0.97 (62) | **0.95** / 1.00 (22) | **0.95** / 1.00 (20) | **0.90** / 0.90 (10) | **0.90** / 0.90 (10) | 6451 | 4.59 |
| bm25 | 5 | **0.85** / 0.87 (62) | **0.86** / 0.91 (22) | **0.90** / 0.85 (20) | **0.80** / 0.80 (10) | **0.80** / 0.90 (10) | 2652 | 0.14 |
| bm25+expand | 5 | **0.89** / 0.87 (62) | **0.91** / 0.91 (22) | **0.90** / 0.85 (20) | **0.80** / 0.80 (10) | **0.90** / 0.90 (10) | 6172 | 0.15 |

quote = the gold sentence is inside a passage the model would be given; page = a gold page overlaps a passage (the generous check). avg tokens/q = passage text handed to the model per question.

**hybrid+rerank k=5 quote misses (7):** HDFCBANK-FY25-01, INFY-FY25-01, TCS-FY24-02, BAJFINANCE-FY25-06, TATAMOTORS-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank k=8 quote misses (5):** INFY-FY25-01, BAJFINANCE-FY25-06, TATAMOTORS-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**hybrid+rerank+expand k=3 quote misses (8):** INFY-FY25-01, TCS-FY24-02, HDFCBANK-FY25-05, BAJFINANCE-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-01, HINDUNILVR-FY25-05, LT-FY25-05
**hybrid+rerank+expand k=5 quote misses (4):** TCS-FY24-02, BAJFINANCE-FY25-06, SUNPHARMA-FY25-05, HINDUNILVR-FY25-05
**bm25 k=5 quote misses (9):** HDFCBANK-FY25-01, INFY-FY25-04, BAJFINANCE-FY24-02, BAJFINANCE-FY25-05, TATAMOTORS-FY25-01, TATAMOTORS-FY25-03, TATAMOTORS-FY25-06, HINDUNILVR-FY25-05, HINDUNILVR-FY25-06
**bm25+expand k=5 quote misses (7):** HDFCBANK-FY25-01, INFY-FY25-04, BAJFINANCE-FY25-05, TATAMOTORS-FY25-01, TATAMOTORS-FY25-03, HINDUNILVR-FY25-05, HINDUNILVR-FY25-06
