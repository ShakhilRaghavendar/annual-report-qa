# Answer results (62 questions, retriever = hybrid+rerank, model = openai/gpt-oss-120b)

| kind | n | correct | partial | wrong | not found | citation ok | gold page retrieved | gold quote retrieved | s/q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all | 62 | 0.58 | 0.23 | 0.19 | 0.06 | 0.82 | 0.95 | 0.83 | 24.3 |
| factual | 22 | 0.82 | 0.00 | 0.18 | 0.05 | 0.86 | 1.00 | 1.00 | 21.1 |
| conceptual | 20 | 0.30 | 0.55 | 0.15 | 0.00 | 0.90 | 0.95 | 0.80 | 19.9 |
| cross_year | 10 | 0.60 | 0.20 | 0.20 | 0.00 | 0.80 | 0.90 | 0.75 | 44.2 |
| unit_trap | 10 | 0.60 | 0.10 | 0.30 | 0.30 | 0.60 | 0.90 | 0.67 | 20.0 |

correct/partial/wrong = LLM-judge verdict against the gold answer; citation ok = a cited passage overlaps a gold page (hard check); gold page retrieved = a gold page was among the passages the model was given (page-level, generous); gold quote retrieved = the gold sentence itself was inside a passage the model was given (the honest retrieval check); not found = the system declined to answer.

Of the 12 wrong answers, 3 never had a gold page retrieved (retrieval failure) and 9 had it and still missed (reading failure).

## Not correct

| id | verdict | citation ok | gold retrieved | judge's reason |
| --- | --- | --- | --- | --- |
| HDFCBANK-FY25-01 | wrong | no | yes | The system answer omitted the net interest income amount, providing only the growth percentage. |
| INFY-FY25-01 | wrong | no | yes | The system answer gives free cash flow in US$4.1 billion, while the gold answer states ₹34,549 crore; the units and figures do not match. |
| SUNPHARMA-FY25-01 | partial | yes | yes | The system answer gives the revenue in US$ but omits the requested ₹ crore figure, though the growth percentage matches. |
| SUNPHARMA-FY25-02 | partial | yes | yes | The system answer correctly states the revenue percentages and trend, but omits the additional fact that 26 specialty products are marketed globally. |
| INFY-FY25-03 | wrong | yes | yes | The system answer omitted the total active client count, which is a required fact. |
| INFY-FY25-05 | partial | yes | yes | The system answer includes most of the key mitigation measures but omits acquisitions to expand into new areas or regions and the opportunity for clients seeking cost takeout and vendor consolidation. |
| INFY-FY25-06 | partial | yes | yes | The system correctly states the FY25 figure but omits the FY24 figure of 7.9 million. |
| TCS-FY24-04 | partial | yes | yes | The system answer captures the explanation but omits the specific growth figures (6.8% and 3.4% constant currency) provided in the gold answer. |
| RELIANCE-FY24-03 | partial | no | yes | The system answer mentions the Net Carbon Zero goal and the New Energy business’s role, but omits the 2035 target, the Giga Complex, carbon capture, ESG Committee, and the global provider claim. |
| RELIANCE-FY25-04 | wrong | yes | yes | The system answer omits the specific EBITDA decline figure (11.9% to ₹54,988 crore) that is present in the gold answer. |
| HDFCBANK-FY25-05 | wrong | yes | yes | The system answer omits the credit‑deposit ratio reduction, large‑scale deposit mobilisation, and mortgage business details that are key facts in the gold answer. |
| HDFCBANK-FY25-06 | partial | no | yes | The system answer correctly states the FY24 CSR spend but omits the FY25 figure provided in the gold answer. |
| HDFCBANK-FY25-07 | wrong | no | yes | The system answer incorrectly states that the information was not found, whereas the gold answer provides the figure (US$10.83 billion). |
| ICICIBANK-FY24-04 | partial | yes | yes | The system answer includes most governance elements and standards but omits the enterprise risk management framework, cross‑functional reporting to the IT Strategy Committee, NCIIPC, ISO 27001 certification, and the Data Leakage/Loss Prevention system. |
| ICICIBANK-FY25-06 | wrong | no | yes | The system answer gives the figure in billions but does not provide the requested amount in ₹ crore. |
| BAJFINANCE-FY25-04 | partial | yes | yes | The system answer includes all key facts and figures but omits the next‑step details (Conversational IVR and Pay Over Voice) mentioned in the gold answer. |
| BAJFINANCE-FY25-06 | wrong | no | no | The system answer incorrectly states that the information was not found, whereas the gold answer provides the figure ₹0.2882 crore. |
| TATAMOTORS-FY25-03 | partial | yes | yes | The system answer captures the reason for the demerger and some of the Chairman’s expectations, but it omits several key benefits mentioned in the gold answer such as strategic clarity, agility, customer experience, rewarding careers, and long-term shareholder returns. |
| TATAMOTORS-FY25-04 | partial | yes | yes | The system answer includes the launch of the first fully electric Range Rover and a four‑door Jaguar BEV in 2026 and mentions upgrading core facilities and supply chain, but it omits the Reimagine strategy, the price parity achievement in India, and the Agratas battery cell plants in the UK and Indi |
| SUNPHARMA-FY25-05 | wrong | no | no | The system answer omits the Halol facility, misstates Mohali’s status, and fails to provide the complete set of facts and figures from the gold answer. |
| HINDUNILVR-FY25-03 | partial | yes | yes | The system answer correctly states the 40% digital spend and the in‑house media‑planning tool using category‑specific data, but it omits the details about consumer cohorts, deployment time reduction, AI technology, and influencer partnerships. |
| HINDUNILVR-FY24-04 | partial | yes | yes | The system answer correctly mentions the Agile Innovation Hub but omits the Supply Chain Nerve Center example and adds unrelated sustainability details. |
| HINDUNILVR-FY25-05 | wrong | no | no | The FY 2023-24 revenue figure differs (21,900 vs 21,767 crores). |
| LT-FY25-02 | wrong | no | yes | The system answer incorrectly states the information was not found, while the gold answer provides the order book size and international share. |
| LT-FY25-03 | partial | yes | yes | The system answer includes some risk mitigation aspects such as diversification and monitoring, but omits key elements from the gold answer like country risk assessments at bidding, reliance on sovereign or creditworthy clients, and specific mitigations such as contract structuring, hedging, and con |
| LT-FY25-05 | wrong | yes | yes | The system answer gives a different profit figure for FY 2023-24 (₹13,059 crore) than the gold answer (₹9,304.33 crore). |
