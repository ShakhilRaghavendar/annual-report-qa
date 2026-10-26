# Retrieval results (k = 5, 4 questions)

| retriever | all (n) | factual (n) | conceptual (n) | cross_year (n) | unit_trap (n) | s/q |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | hit 0.50 · R@5 0.50 · MRR 0.31 (4) | hit 0.00 · R@5 0.00 · MRR 0.00 (2) | hit 1.00 · R@5 1.00 · MRR 0.25 (1) | — | hit 1.00 · R@5 1.00 · MRR 1.00 (1) | 0.09 |
| dense | hit 0.75 · R@5 0.62 · MRR 0.35 (4) | hit 0.50 · R@5 0.25 · MRR 0.10 (2) | hit 1.00 · R@5 1.00 · MRR 0.20 (1) | — | hit 1.00 · R@5 1.00 · MRR 1.00 (1) | 0.07 |
| hybrid | hit 0.50 · R@5 0.50 · MRR 0.33 (4) | hit 0.00 · R@5 0.00 · MRR 0.00 (2) | hit 1.00 · R@5 1.00 · MRR 0.33 (1) | — | hit 1.00 · R@5 1.00 · MRR 1.00 (1) | 0.14 |
| hybrid+rerank | hit 0.75 · R@5 0.62 · MRR 0.58 (4) | hit 0.50 · R@5 0.25 · MRR 0.50 (2) | hit 1.00 · R@5 1.00 · MRR 0.33 (1) | — | hit 1.00 · R@5 1.00 · MRR 1.00 (1) | 2.52 |

hit = share of questions with any gold page in the top k; R@k = share of gold passages found; MRR = mean reciprocal rank of the first hit.

**bm25 missed:** HDFCBANK-FY25-01 (got p11-12, p51-52, p57-60, p39-40, p38-39); INFY-FY25-01 (got p75-76, p32-33, p33-34, p16-17, p35-35)
**dense missed:** INFY-FY25-01 (got p32-33, p283-284, p275-277, p279-280, p317-318)
**hybrid missed:** HDFCBANK-FY25-01 (got p51-52, p38-39, p47-48, p204-205, p50-51); INFY-FY25-01 (got p32-33, p16-17, p33-34, p283-284, p75-76)
**hybrid+rerank missed:** INFY-FY25-01 (got p32-33, p16-17, p283-284, p306-307, p293-294)
