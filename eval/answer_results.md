# Answer results (62 questions, retriever = hybrid+rerank, model = openai/gpt-oss-120b)

| kind | n | correct | partial | wrong | not found | citation ok | gold page retrieved | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all | 62 | 0.63 | 0.15 | 0.23 | 0.18 | 0.61 | 0.00 | 43.1 |
| factual | 22 | 0.82 | 0.00 | 0.18 | 0.14 | 0.59 | 0.00 | 16.6 |
| conceptual | 20 | 0.45 | 0.35 | 0.20 | 0.00 | 0.85 | 0.00 | 16.0 |
| cross_year | 10 | 0.60 | 0.20 | 0.20 | 0.30 | 0.30 | 0.00 | 44.7 |
| unit_trap | 10 | 0.60 | 0.00 | 0.40 | 0.50 | 0.50 | 0.00 | 153.9 |

correct/partial/wrong = LLM-judge verdict against the gold answer; citation ok = a cited passage overlaps a gold page (hard check); gold page retrieved = a gold page was among the passages the model was given; not found = the system declined to answer.

Of the 14 wrong answers, 14 never had a gold page retrieved (retrieval failure) and 0 had it and still missed (reading failure).

## Not correct

| id | verdict | citation ok | gold retrieved | judge's reason |
| --- | --- | --- | --- | --- |
| HDFCBANK-FY25-01 | wrong | no | no | The system answer incorrectly states that the information was not found, while the gold answer provides the net interest income figure and growth percentage. |
| INFY-FY25-01 | wrong | no | no | The system answer gives free cash flow in US$4.1 billion, while the gold answer states ₹34,549 crore; the units and figures do not match. |
| SUNPHARMA-FY25-01 | wrong | no | no | The system answer incorrectly states the information was not found, while the gold answer provides the revenue figure and growth. |
| INFY-FY25-03 | wrong | no | no | The system answer omitted the total active client count of 1,869, which is a key fact in the gold answer. |
| INFY-FY25-05 | partial | yes | no | The system answer includes most of the key measures but omits operational agility controls, tariff/trade restriction mitigation, acquisitions, and the opportunity angle. |
| INFY-FY25-06 | partial | no | no | The system correctly states the FY25 figure but omits the FY24 figure, which is required. |
| RELIANCE-FY24-03 | partial | yes | no | The system answer correctly states the 2035 Net Carbon Zero target and the pivotal role of the New Energy business, but it omits key details from the gold answer such as the Dhirubhai Ambani Green Energy Giga Complex, carbon capture technologies, ESG Committee, and the expectation of becoming a lead |
| RELIANCE-FY25-04 | wrong | yes | no | The system answer omitted the specific EBITDA decline percentage (11.9%) and the amount (₹54,988 crore) that are present in the gold answer. |
| HDFCBANK-FY25-05 | wrong | yes | no | The system answer omits the key tailwinds cited in the gold answer (credit‑deposit ratio reduction, large‑scale deposit mobilisation, mortgage business size and CASA uptake) and therefore does not convey the same facts. |
| HDFCBANK-FY25-06 | partial | no | no | The system correctly states the FY24 CSR spend but fails to provide the FY25 figure, which is required. |
| HDFCBANK-FY25-07 | wrong | no | no | The system answer omitted the available figure (US$10.83 billion) and incorrectly stated the information was not found. |
| ICICIBANK-FY24-04 | partial | yes | no | The system answer includes most governance elements and standards but omits the enterprise risk management framework, KRIs/dashboards, Data Leakage/Loss Prevention system, and ISO 27001 certification details. |
| BAJFINANCE-FY25-06 | wrong | no | no | The system answer incorrectly states that the information was not found, whereas the gold answer provides the figure ₹0.2882 crore. |
| TATAMOTORS-FY25-04 | partial | yes | no | The system answer includes some key points (Range Rover 2026, core facilities, supply chain) but omits the four‑door GT Jaguar BEV, price parity strategy, and Agratas battery plant details. |
| TATAMOTORS-FY25-06 | wrong | no | no | The system answer states the information was not found, while the gold answer provides the figure US$237.47 million. |
| SUNPHARMA-FY25-05 | wrong | no | no | The system answer omits the Halol facility, misstates dates, and does not match the gold answer’s facts and figures. |
| HINDUNILVR-FY25-03 | partial | yes | no | The system answer correctly states the 40% digital spend and the in‑house media planning tool, but omits details about targeting different brands and consumer cohorts, deployment time savings, AI technology, and influencer partnerships. |
| HINDUNILVR-FY24-04 | wrong | no | no | The system answer omits the Supply Chain Nerve Center example and misstates the programme’s focus, so it does not match the gold answer. |
| HINDUNILVR-FY25-05 | wrong | no | no | The system answer incorrectly states that the FY 2024-25 figure is missing, whereas the gold answer provides both FY 2023-24 and FY 2024-25 revenue figures. |
| LT-FY25-02 | wrong | no | no | The system answer incorrectly states that the information was not found, while the gold answer provides the order book size and international share. |
| LT-FY25-03 | partial | yes | no | The system answer mentions diversification and monitoring but omits the specific risk assessment at bidding, sovereign client focus, contract structuring, hedging, and contingency planning described in the gold answer. |
| LT-FY24-04 | partial | yes | no | The system answer correctly identifies the long‑term (7‑10 years) and short‑term (annual) horizons, but it gives a medium‑term horizon of 5‑7 years instead of the 5‑year horizon specified in the gold answer. |
| LT-FY25-05 | wrong | no | no | The system provides different profit figures and growth percentages than the gold answer. |
