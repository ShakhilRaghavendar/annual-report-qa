# Annual Report Q&A — hybrid RAG over Indian listed-company annual reports

> Work in progress. Ask a question about a Nifty 50 company's annual report and get a cited answer, in ₹ crore, with the passages it came from. Built to compare retrieval strategies honestly, not to demo a chatbot.

## Why

Indian annual reports are 200–400-page designed PDFs. The answer to "what did HDFC Bank say about credit costs in FY25?" is in there — usually in the MD&A or a note to the accounts — but finding it is a Ctrl-F exercise. And unlike US 10-Ks, every company lays its report out differently, so the parsing is real engineering, not a library call.

## What's in v1

- 10 Nifty 50 companies × FY24 and FY25 = 20 reports
- Section-aware parsing (Chairman's letter, MD&A, Directors' Report, Risk Management, consolidated financials)
- Three retrievers behind one interface: BM25, dense vector, hybrid (RRF) + cross-encoder reranker
- Cited answers with company / FY / section / page; figures normalised to ₹ crore
- A 60-question evaluation set with gold passages and a script that scores every retriever

## Status

| Week | Milestone | Status |
| --- | --- | --- |
| 1 | Fetch + parse 20 reports | in progress |
| 2 | Eval set, BM25 + vector indexes | |
| 3 | Hybrid, rerank, cited answers | |
| 4 | README with results, API, v1.0 | |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install -e .
copy .env.example .env          # then add an API key
```

## Run

```bash
python -m arqa.fetch            # download PDFs listed in data/sources.csv
python -m arqa.parse            # PDFs -> data/processed/*.jsonl
pytest -q
```

## Results

_Coming in week 2._

## Parsing notes by company

_Coming in week 1 — which reports parsed cleanly, which needed special handling, and why._
