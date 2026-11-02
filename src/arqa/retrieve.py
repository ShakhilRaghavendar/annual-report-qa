"""
retrieve.py — one interface, four retrievers.

    Retriever.search(query, k, filters) -> list[Hit]

  BM25Retriever    keyword scoring
  DenseRetriever   embedding similarity (FAISS)
  HybridRetriever  BM25 + dense, fused with Reciprocal Rank Fusion
  Reranked         any retriever, re-ordered by a cross-encoder
  Expanded         any retriever, each hit widened to its neighbouring chunks

Reciprocal Rank Fusion: each list contributes 1/(k0 + rank) per document and
the sums are sorted. It needs no score calibration between BM25 (unbounded)
and cosine (0..1), which is why it is the default way to combine them.

Filters restrict by metadata before ranking: {"ticker": "HDFCBANK", "fy": "FY25"}.
A question about HDFC Bank FY25 should never be answered from Infosys FY24 —
and the cross-year eval questions need both years without the others.

Usage:
    from arqa.retrieve import get_retriever
    r = get_retriever("hybrid")
    for hit in r.search("What did Bajaj Finance say about unsecured lending risk?", k=5):
        print(hit.score, hit.chunk["ticker"], hit.chunk["page_start"], hit.chunk["text"][:80])
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import numpy as np

from arqa.index import BM25_PATH, EMBED_MODEL, FAISS_PATH, META_PATH, tokenize

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class Hit:
    chunk: dict
    score: float
    rank: int


# --- shared data --------------------------------------------------------------------
@lru_cache(maxsize=1)
def _meta() -> list[dict]:
    with META_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _allowed(filters: dict | None) -> np.ndarray | None:
    """Boolean mask over chunk rows for metadata filters; None means no filter."""
    if not filters:
        return None
    meta = _meta()
    mask = np.ones(len(meta), dtype=bool)
    for key, want in filters.items():
        wants = {want} if isinstance(want, str) else set(want)
        mask &= np.array([m.get(key, "") in wants for m in meta])
    return mask


def _to_hits(order: Iterable[int], scores: np.ndarray, k: int) -> list[Hit]:
    meta = _meta()
    hits = []
    for rank, i in enumerate(order, start=1):
        hits.append(Hit(chunk=meta[i], score=float(scores[i]), rank=rank))
        if rank == k:
            break
    return hits


# --- retrievers ----------------------------------------------------------------------
class BM25Retriever:
    name = "bm25"

    def __init__(self) -> None:
        with BM25_PATH.open("rb") as f:
            self.bm25 = pickle.load(f)

    def scores(self, query: str) -> np.ndarray:
        return np.asarray(self.bm25.get_scores(tokenize(query)), dtype=np.float32)

    def search(self, query: str, k: int = 5, filters: dict | None = None) -> list[Hit]:
        s = self.scores(query)
        mask = _allowed(filters)
        if mask is not None:
            s = np.where(mask, s, -np.inf)
        order = np.argsort(-s)
        order = [i for i in order if np.isfinite(s[i]) and s[i] > 0][:k]
        return _to_hits(order, s, k)


class DenseRetriever:
    name = "dense"

    def __init__(self) -> None:
        import faiss
        from sentence_transformers import SentenceTransformer

        self.index = faiss.read_index(str(FAISS_PATH))
        self.model = SentenceTransformer(EMBED_MODEL, device="cpu")

    def scores(self, query: str) -> np.ndarray:
        q = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
        # exact search over all rows: we need full scores for filtering and fusion
        n = self.index.ntotal
        sims, ids = self.index.search(q, n)
        s = np.full(n, -np.inf, dtype=np.float32)
        s[ids[0]] = sims[0]
        return s

    def search(self, query: str, k: int = 5, filters: dict | None = None) -> list[Hit]:
        s = self.scores(query)
        mask = _allowed(filters)
        if mask is not None:
            s = np.where(mask, s, -np.inf)
        order = [i for i in np.argsort(-s) if np.isfinite(s[i])][:k]
        return _to_hits(order, s, k)


class HybridRetriever:
    name = "hybrid"

    def __init__(self, bm25: BM25Retriever | None = None, dense: DenseRetriever | None = None,
                 k0: int = 60, depth: int = 50) -> None:
        self.bm25 = bm25 or BM25Retriever()
        self.dense = dense or DenseRetriever()
        self.k0 = k0        # RRF constant; 60 is the value from the original paper
        self.depth = depth  # how many from each list take part in the fusion

    def search(self, query: str, k: int = 5, filters: dict | None = None) -> list[Hit]:
        fused: dict[int, float] = {}
        for retr in (self.bm25, self.dense):
            for h in retr.search(query, k=self.depth, filters=filters):
                i = h.chunk["row"]
                fused[i] = fused.get(i, 0.0) + 1.0 / (self.k0 + h.rank)
        order = sorted(fused, key=fused.get, reverse=True)[:k]
        scores = np.zeros(len(_meta()), dtype=np.float32)
        for i, v in fused.items():
            scores[i] = v
        return _to_hits(order, scores, k)


class Reranked:
    """Wrap any retriever: fetch `depth` candidates, re-score with a cross-encoder, keep k."""

    def __init__(self, base, depth: int = 20) -> None:
        from sentence_transformers import CrossEncoder

        self.base = base
        self.depth = depth
        self.model = CrossEncoder(RERANK_MODEL, device="cpu")
        self.name = f"{base.name}+rerank"

    def search(self, query: str, k: int = 5, filters: dict | None = None) -> list[Hit]:
        cands = self.base.search(query, k=self.depth, filters=filters)
        if not cands:
            return []
        pairs = [(query, h.chunk["text"]) for h in cands]
        scores = self.model.predict(pairs)
        order = np.argsort(-scores)[:k]
        return [Hit(chunk=cands[i].chunk, score=float(scores[i]), rank=r)
                for r, i in enumerate(order, start=1)]


# --- context expansion ---------------------------------------------------------------
def _overlap_join(a: str, b: str, max_probe: int = 800) -> str:
    """Join two consecutive chunks, dropping the text the chunker repeated
    (chunks overlap by ~80 tokens): the longest suffix of `a` that is a prefix of `b`."""
    probe = min(len(a), len(b), max_probe)
    for n in range(probe, 40, -1):
        if a.endswith(b[:n]):
            return a + b[n:]
    return a + "\n" + b


def _same_section(x: dict, y: dict) -> bool:
    return (x["ticker"], x["fy"], x.get("part", ""), x["section_key"]) == \
           (y["ticker"], y["fy"], y.get("part", ""), y["section_key"])


def expand_hits(hits: list[Hit], before: int = 1, after: int = 1, top: int | None = None) -> list[Hit]:
    """Widen each hit to [row-before, row+after] within its section. Windows of
    different hits that touch are merged into the higher-ranked one, so the
    model never sees the same text twice. Why: run 3 showed the gold sentence
    sitting in chunk #13 while the retriever served chunk #14 of the same page.

    The merged chunk keeps the centre hit's chunk_id and gains
    `expanded_from` (the chunk ids it now spans) and a page range covering all.
    `top`: widen only the first `top` hits (by rank); the rest stay single
    chunks — the budget goes where the reranker is most confident."""
    meta = _meta()
    windows: list[tuple[Hit, set[int]]] = []
    for i, h in enumerate(hits):
        c = h.chunk
        row = c["row"]
        rows = {row}
        widen = top is None or i < top
        for d in range(1, (before if widen else 0) + 1):
            if row - d >= 0 and _same_section(meta[row - d], c):
                rows.add(row - d)
        for d in range(1, (after if widen else 0) + 1):
            if row + d < len(meta) and _same_section(meta[row + d], c):
                rows.add(row + d)
        for _, w in windows:
            if w & rows:
                w |= rows
                break
        else:
            windows.append((h, rows))
    out = []
    for rank, (h, rows) in enumerate(windows, start=1):
        parts = [meta[r] for r in sorted(rows)]
        text = parts[0]["text"]
        for p in parts[1:]:
            text = _overlap_join(text, p["text"])
        merged = {**h.chunk, "text": text, "centre_text": h.chunk["text"], "centre_tokens": h.chunk.get("n_tokens", 0),
                  "page_start": min(p["page_start"] for p in parts),
                  "page_end": max(p["page_end"] for p in parts),
                  "n_tokens": sum(p.get("n_tokens", 0) for p in parts),
                  "expanded_from": [p["chunk_id"] for p in parts]}
        out.append(Hit(chunk=merged, score=h.score, rank=rank))
    return out


class Expanded:
    """Wrap any retriever: run it, then widen each hit to its neighbours."""

    def __init__(self, base, before: int = 1, after: int = 1, top: int | None = None) -> None:
        self.base = base
        self.before, self.after, self.top = before, after, top
        self.name = f"{base.name}+expand" + (f"{top}" if top else "")

    def search(self, query: str, k: int = 5, filters: dict | None = None) -> list[Hit]:
        return expand_hits(self.base.search(query, k=k, filters=filters), self.before, self.after, self.top)


# --- factory -------------------------------------------------------------------------
_CACHE: dict[str, object] = {}


def get_retriever(name: str):
    """'bm25' | 'dense' | 'hybrid' | 'hybrid+rerank', each optionally with '+expand'
    (every hit widened to its neighbouring chunks) or '+expandN' (only the top N hits).
    Instances are cached (models load once)."""
    if name in _CACHE:
        return _CACHE[name]
    if "+expand" in name:
        base, _, n = name.rpartition("+expand")     # "+expand" widens all hits; "+expand3" the top 3
        r = Expanded(get_retriever(base), top=int(n) if n else None)
    elif name == "bm25":
        r = BM25Retriever()
    elif name == "dense":
        r = DenseRetriever()
    elif name == "hybrid":
        r = HybridRetriever(_CACHE.get("bm25") or get_retriever("bm25"),
                            _CACHE.get("dense") or get_retriever("dense"))
    elif name == "hybrid+rerank":
        r = Reranked(get_retriever("hybrid"))
    else:
        raise ValueError(f"unknown retriever {name!r}")
    _CACHE[name] = r
    return r
