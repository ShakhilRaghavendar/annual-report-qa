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
| 1 | Fetch + parse 20 reports | 24 PDFs fetched (ICICI ships its report as parts); parser v1 labels ~15/20 main reports correctly — see parsing notes |
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

The parser finds chapter headings in the top lines of each page (PyMuPDF, `sort=True`), ranks competing matches by specificity, and treats governance / BRSR / standalone / AGM-notice headings as *closers* so a chapter can't swallow what follows it. Things the first run on real reports taught it:

- **"Dear Shareholders" is not a heading.** HDFC Bank's Directors' Report opens with it; a generic pattern for it mislabelled the whole report as the Chairman's letter. Specific headings now outrank generic ones.
- **Nav strips.** L&T and HUL print "Corporate Overview | Management Discussion and Analysis | …" at the top of every page. Any line recurring on ≥25% of pages is treated as boilerplate.
- **Two-line headings.** L&T sets "Chairman's / Statement" on two lines; adjacent short lines are also tried joined.
- **Nested chapters.** At HDFC Bank the MD&A sits inside the Directors' Report; at HUL the chapter is literally "Report of Board of Directors and Management Discussion and Analysis". A sub-heading below a chapter's running header opens a sub-section; one-page flapping between the two is merged afterwards.
- **Reliance** titles the letter "Chairman and Managing Director's Statement" and splits the MD&A into "Management Discussion and Analysis — Business Overview / Financial Performance / Risk and Governance".
- **ICICI Bank** publishes the Integrated Report, Board's Report and financial statements as separate PDFs; `sources.csv` has a `part` column for that.
- **chromadb** 0.5 has no Python 3.13 Windows wheel for its HNSW dependency (needs a C++ toolchain), so the vector index is FAISS.

Open issues (as of parser v1): HDFC Bank FY25 Directors' Report falls into "Other"; TCS MD&A not detected; HUL consolidated financials not detected; ICICI Board's Report heading not recognised; L&T "Risk Management" still absorbs the Integrated Report chapters that follow it. `python -m arqa.parse --peek <STEM> <page> …` shows exactly what the parser sees on a page.
