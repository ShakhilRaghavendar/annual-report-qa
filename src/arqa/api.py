"""
api.py — the same answerer behind an HTTP endpoint.

    uvicorn arqa.api:app --reload          # http://127.0.0.1:8000/docs

    POST /ask
    {"question": "What free cash flow did Infosys generate in FY25?", "ticker": "INFY", "fy": ["FY25"]}

    -> {"found": true, "answer": "...[1]", "figures": [...], "citations": [...], "model": ..., "latency_s": ...}

    GET /health        -> {"status": "ok", "chunks": 6809, "reports": 24}
    GET /reports       -> the (ticker, fy, part) combinations in the index

The index and models load lazily on the first request (30–60 s on a laptop)
and stay in memory after that.
"""

from __future__ import annotations

from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from arqa.answer import DEFAULT_K, DEFAULT_RETRIEVER, answer
from arqa.retrieve import _meta

app = FastAPI(
    title="Annual Report Q&A",
    description="Cited answers from Indian listed-company annual reports (hybrid RAG). Figures normalised to ₹ crore.",
    version="1.0.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=5, examples=["What was Reliance Retail's EBITDA in FY24 and FY25?"])
    ticker: str | None = Field(None, examples=["RELIANCE"])
    fy: list[str] = Field(default_factory=list, examples=[["FY24", "FY25"]])
    k: int = Field(DEFAULT_K, ge=1, le=12)
    retriever: str = Field(DEFAULT_RETRIEVER, pattern=r"^(bm25|dense|hybrid|hybrid\+rerank)$")


@app.get("/health")
def health() -> dict:
    meta = _meta()
    reports = {(m["ticker"], m["fy"], m.get("part", "")) for m in meta}
    return {"status": "ok", "chunks": len(meta), "reports": len(reports)}


@app.get("/reports")
def reports() -> list[dict]:
    counts = Counter((m["ticker"], m["fy"], m.get("part", "")) for m in _meta())
    return [{"ticker": t, "fy": fy, "part": part, "chunks": n}
            for (t, fy, part), n in sorted(counts.items())]


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    fys = [y.upper() for y in req.fy]
    fy: str | list[str] | None = fys[0] if len(fys) == 1 else (fys or None)
    try:
        a = answer(req.question, ticker=req.ticker.upper() if req.ticker else None, fy=fy,
                   k=req.k, retriever=req.retriever)
    except RuntimeError as e:  # missing API key and the like
        raise HTTPException(status_code=503, detail=str(e)) from e
    return a.to_dict()
