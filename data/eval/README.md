# Writing the evaluation questions

The eval set is the most valuable thing in this repo. It is written **by hand, by someone who reads annual reports**, before any retriever is tuned — so it can't be fitted to the system.

## Target: 60 questions, 6 per company

| Kind | Per company | What it tests |
| --- | --- | --- |
| `factual` | 2 | A specific figure or fact. "What was HUL's consolidated revenue from operations in FY25?" Keyword-heavy; BM25 should do well. |
| `conceptual` | 2 | A theme stated in different words than the report uses. "What risks does Bajaj Finance see in unsecured lending?" Paraphrase-heavy; dense retrieval should do well. |
| `cross_year` | 1 | How something changed between FY24 and FY25. "How did Tata Motors' commentary on JLR demand change from FY24 to FY25?" Needs both years. |
| `unit_trap` | 1 | A figure the report states in lakh / million / USD, asked for in ₹ crore. "What was Infosys' free cash flow in FY25, in ₹ crore?" Catches lakh/crore/million mistakes. |

## One question per line in `questions.jsonl`

```json
{"id": "HDFCBANK-FY25-01", "ticker": "HDFCBANK", "fy": ["FY25"], "kind": "factual",
 "question": "What was HDFC Bank's net interest income in FY25?",
 "answer": "₹ 1,22,893 crore (approx.)",
 "gold": [{"ticker": "HDFCBANK", "fy": "FY25", "pages": [209, 210], "quote": "Net interest income grew"}],
 "unit_as_stated": "crore"}
```

Field by field:

- `id` — `TICKER-FY-NN`. Unique.
- `ticker` — the company's NSE symbol as in `data/sources.csv`.
- `fy` — a list; one year normally, both for `cross_year`.
- `kind` — one of the four above.
- `question` — written the way an analyst would ask it, not the way the report phrases it. That gap is what we're measuring.
- `answer` — a short reference answer in your words. Figures in ₹ crore.
- `gold` — **where the answer is**: one entry per passage, with the PDF page numbers (the viewer's page counter, not the number printed on the page — they differ) and a short quote (5–10 words copied from the page) so the eval can double-check the page. 1–3 entries.
- `unit_as_stated` — for `unit_trap` only: the unit the report actually uses (`lakh`, `million`, `usd_million`, ...).

## How to find gold pages fast

Open the PDF in your browser, Ctrl-F a distinctive phrase, note the page number in the viewer. For `data/raw/TICKER_FY.pdf` that viewer page number is exactly what the parser uses.

## Rules

1. Don't look at what the retriever returns while writing questions. Write them from the reports.
2. Don't write questions whose answer is a whole table. One fact, one theme.
3. Vary the sections: MD&A, Directors' Report, risk, chairman's letter, notes to accounts.
4. If the answer isn't in the report, it's not a question for this set.
5. Keep the tone neutral; the question shouldn't contain the answer.
