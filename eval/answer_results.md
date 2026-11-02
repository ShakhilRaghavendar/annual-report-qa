# Answer results (62 questions, retriever = hybrid+rerank+expand, model = openai/gpt-oss-120b)

| kind | n | correct | partial | wrong | not found | citation ok | gold page retrieved | gold quote retrieved | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all | 62 | 0.74 | 0.11 | 0.15 | 0.03 | 0.85 | 0.97 | 0.94 | 38.5 |
| factual | 22 | 0.91 | 0.05 | 0.05 | 0.00 | 0.91 | 1.00 | 0.95 | 34.8 |
| conceptual | 20 | 0.60 | 0.25 | 0.15 | 0.00 | 0.90 | 1.00 | 0.95 | 38.6 |
| cross_year | 10 | 0.70 | 0.10 | 0.20 | 0.00 | 0.70 | 0.90 | 0.90 | 43.8 |
| unit_trap | 10 | 0.70 | 0.00 | 0.30 | 0.20 | 0.80 | 0.90 | 0.90 | 40.9 |

correct/partial/wrong = LLM-judge verdict against the gold answer; citation ok = a cited passage overlaps a gold page (hard check); gold page retrieved = a gold page was among the passages the model was given (page-level, generous); gold quote retrieved = the gold sentence itself was inside a passage the model was given (the honest retrieval check); not found = the system declined to answer.

Of the 9 wrong answers, 2 never had a gold page retrieved (retrieval failure) and 7 had it and still missed (reading failure).

## Not correct

| id | verdict | citation ok | gold retrieved | judge's reason |
| --- | --- | --- | --- | --- |
| SUNPHARMA-FY25-01 | wrong | yes | yes | The system answer omitted the required ₹ crore figure, providing only the US$ amount. |
| INFY-FY25-03 | wrong | yes | yes | The system answer omitted the total active client count, which is a key fact in the gold answer. |
| INFY-FY25-05 | partial | yes | yes | The system answer includes most of the key measures but omits monitoring geopolitical/macro scenarios, operational agility controls, and the opportunity from client cost takeout and vendor consolidation. |
| RELIANCE-FY24-03 | wrong | yes | yes | The system answer gives a different target year (2070) and omits the specific 2035 goal, the mention of the Dhirubhai Ambani Green Energy Giga Complex, and the role of the New Energy and New Materials business as a major green energy provider, making the facts inconsistent with the gold answer. |
| RELIANCE-FY25-04 | wrong | yes | yes | The system answer omits the specific EBITDA decline percentage (11.9%) and the amount (₹54,988 crore) that are present in the gold answer. |
| HDFCBANK-FY25-05 | wrong | no | yes | The system answer omits the key tailwinds cited in the gold answer (reduction in credit‑deposit ratio, large‑scale deposit mobilisation, mortgage business details) and adds unrelated points, so the facts do not match. |
| HDFCBANK-FY25-06 | wrong | no | yes | The system answer omitted the FY25 CSR spend figure, which is a key fact in the gold answer. |
| HDFCBANK-FY25-07 | wrong | no | yes | The system answer incorrectly states that the information was not found, whereas the gold answer provides the figure (US$10.83 billion). |
| ICICIBANK-FY24-04 | partial | yes | yes | The system answer includes most governance entities and standards but omits key details such as KRIs/dashboards, periodic audits, Data Leakage/Loss Prevention system, and ISO 27001‑certified Data Centre and SOC. |
| BAJFINANCE-FY24-02 | partial | yes | yes | The system answer gives the FY2024 PAT figure and the 23% growth rate but omits the FY2023 PAT figure, so it does not fully match the gold answer. |
| BAJFINANCE-FY25-06 | wrong | no | no | The system answer incorrectly states the information is not found, while the gold answer provides the figure ₹0.2882 crore. |
| TATAMOTORS-FY25-04 | partial | yes | yes | The system answer includes most key facts (BEV launches, investment, price parity, battery facilities) but omits the Reimagine strategy name and the mention of Tata Group’s Agratas building battery cell plants in the UK and India. |
| SUNPHARMA-FY25-05 | partial | no | yes | The system answer lists the facilities and mentions corrective actions, but it does not state the CAPA completion status for Halol or the ongoing CAPA implementation for Mohali and Dadra, and it mislabels Halol as OAI instead of import alert. |
| HINDUNILVR-FY25-03 | partial | yes | yes | The system answer correctly states the 40% digital spend and the in‑house media planning tool, but omits the AI‑based technology, influencer ecosystem, deployment time reduction, and consumer cohort customization mentioned in the gold answer. |
| HINDUNILVR-FY25-05 | wrong | no | no | The system answer omitted the FY 2023‑24 revenue figure (₹21,767 crores) that is present in the gold answer. |
| LT-FY25-05 | partial | no | yes | The system answer provides the correct profit figures (within rounding) but omits the requested percentage growth for each year. |
