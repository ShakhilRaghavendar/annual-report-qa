"""
retrieve.py — one interface, four retrievers.

    Retriever.search(query, k, filters) -> list[Hit]

  BM25Retriever    keyword scoring
  DenseRetriever   embedding similarity (FAISS)
  HybridRetriever  BM25 + dense, fused with Reciprocal Rank Fusion
  Reranked         any retriever, re-ordered by a cross-encoder

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


# --- factory -------------------------------------------------------------------------
_CACHE: dict[str, object] = {}


def get_retriever(name: str):
    """'bm25' | 'dense' | 'hybrid' | 'hybrid+rerank' — instances are cached (models load once)."""
    if name in _CACHE:
        return _CACHE[name]
    if name == "bm25":
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
