# Answer results (45 questions, retriever = hybrid+rerank, model = openai/gpt-oss-120b)

| kind | n | correct | partial | wrong | not found | citation ok | gold page retrieved | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all | 45 | 0.62 | 0.20 | 0.18 | 0.07 | 0.84 | 0.98 | 22.2 |
| factual | 16 | 0.81 | 0.00 | 0.19 | 0.06 | 0.88 | 1.00 | 21.1 |
| conceptual | 15 | 0.40 | 0.53 | 0.07 | 0.00 | 0.87 | 1.00 | 18.9 |
| cross_year | 7 | 0.71 | 0.00 | 0.29 | 0.00 | 0.86 | 1.00 | 37.5 |
| unit_trap | 7 | 0.57 | 0.14 | 0.29 | 0.29 | 0.71 | 0.86 | 16.5 |

correct/partial/wrong = LLM-judge verdict against the gold answer; citation ok = a cited passage overlaps a gold page (hard check); gold page retrieved = a gold page was among the passages the model was given; not found = the system declined to answer.

Of the 8 wrong answers, 1 never had a gold page retrieved (retrieval failure) and 7 had it and still missed (reading failure).

## Not correct

| id | verdict | citation ok | gold retrieved | judge's reason |
| --- | --- | --- | --- | --- |
| HDFCBANK-FY25-01 | wrong | no | yes | The system answer incorrectly states that the information was not found, while the gold answer provides the net interest income figure and growth percentage. |
| INFY-FY25-01 | wrong | no | yes | The system answer gives the free cash flow in US$4.1 billion, while the gold answer states ₹34,549 crore; the units and figures do not match. |
| SUNPHARMA-FY25-01 | partial | yes | yes | The system answer correctly states the US$ amount and growth rate but omits the required ₹ crore figure. |
| SUNPHARMA-FY25-02 | partial | yes | yes | The system answer correctly states the revenue percentages and trend, but omits the additional fact that 26 specialty products are marketed globally. |
| INFY-FY25-03 | wrong | yes | yes | The system answer omitted the total active client count, which is a required fact. |
| INFY-FY25-05 | partial | yes | yes | The system answer includes most of the key measures but omits operational agility controls, acquisitions strategy, and the opportunity angle mentioned in the gold answer. |
| INFY-FY25-06 | wrong | yes | yes | The system omitted the FY24 figure of 7.9 million, which is required by the gold answer. |
| TCS-FY25-03 | wrong | yes | yes | The system answer omits the specific margin figures (30 bps drop to 24.3% from 24.6%) that are present in the gold answer. |
| TCS-FY24-04 | partial | yes | yes | The system answer correctly explains the gap but omits the reported growth figures (6.8%/3.4% constant currency) present in the gold answer. |
| RELIANCE-FY25-04 | partial | yes | yes | The system answer mentions the main reasons for the EBITDA decline and the factors that cushioned it, but it omits the specific figures (11.9% decline to ₹54,988 crore) and the revenue growth details (11.0% to ₹6,26,921 crore) provided in the gold answer. |
| HDFCBANK-FY25-05 | partial | yes | yes | The system answer mentions merger completion and a stronger balance sheet but omits the credit‑deposit ratio reduction, large‑scale deposit mobilisation, and mortgage details that are key in the gold answer. |
| HDFCBANK-FY25-06 | wrong | no | yes | The system answer omitted the FY25 CSR spend figure, which is present in the gold answer. |
| HDFCBANK-FY25-07 | wrong | no | yes | The system answer states the information was not found, but the gold answer provides a figure (US$10.83 billion). |
| ICICIBANK-FY24-04 | partial | yes | yes | The system answer includes most governance entities and standards but omits the enterprise risk management framework, KRIs/dashboards, Data Leakage/Loss Prevention system, and ISO 27001 certification details. |
| BAJFINANCE-FY25-06 | wrong | no | no | The system answer incorrectly states that the information was not found, whereas the gold answer provides the figure ₹0.2882 crore. |
| TATAMOTORS-FY25-03 | partial | yes | yes | The system answer captures the intent of sharper strategic focus and empowerment of each business, but omits key details such as the inclusion of JLR, the expected benefits of strategic clarity, agility, focused execution, value creation, better customer experiences, rewarding careers, and long-term |
| TATAMOTORS-FY25-04 | partial | yes | yes | The system answer mentions some mitigation actions (facility upgrades, supply chain, BEV models) but omits key facts such as the Reimagine strategy, the four‑door GT Jaguar BEV, price parity in India, and the Agratas battery cell plants. |
