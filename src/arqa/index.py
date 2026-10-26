"""
index.py — build the BM25 and dense (FAISS) indexes over data/chunks.jsonl.

Two indexes over the SAME chunks, so the eval compares retrievers, not corpora:

  BM25   — classic keyword scoring (rank-bm25). Strong on exact terms:
           "IRDAI", "Jio", "net interest margin", figures.
  Dense  — sentence-transformer embeddings in a FAISS inner-product index
           (vectors are L2-normalised, so inner product == cosine). Strong on
           paraphrase: "how did attrition change" vs "employee turnover".

Run:
    python -m arqa.index              # builds both into index_store/
    python -m arqa.index --bm25-only  # skip the (slow, CPU) embedding step

Embedding ~20k chunks with bge-small on a laptop CPU takes 10–20 minutes.
The model is downloaded once from Hugging Face (~130 MB) and cached.
"""

from __future__ import annotations

import json
import pickle
import re
import sys
import time
from pathlib import Path

import numpy as np

from arqa.chunk import CHUNKS_PATH

ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "index_store"
BM25_PATH = INDEX_DIR / "bm25.pkl"
FAISS_PATH = INDEX_DIR / "dense.faiss"
META_PATH = INDEX_DIR / "chunks_meta.jsonl"

EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # 384-dim, fast on CPU, good on English finance text
EMBED_BATCH = 64

_TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens for BM25. Keeps digits (so '2025' and '6.5' matter)."""
    return _TOKEN.findall(text.lower())


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def build_bm25(chunks: list[dict]) -> None:
    from rank_bm25 import BM25Okapi

    t0 = time.time()
    corpus = [tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(corpus)
    with BM25_PATH.open("wb") as f:
        pickle.dump(bm25, f)
    print(f"BM25: {len(chunks):,} chunks in {time.time() - t0:.1f}s -> {BM25_PATH.name}")


def build_dense(chunks: list[dict]) -> None:
    import faiss
    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    model = SentenceTransformer(EMBED_MODEL, device="cpu")
    texts = [c["text"] for c in chunks]
    emb = model.encode(texts, batch_size=EMBED_BATCH, show_progress_bar=True,
                       convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(FAISS_PATH))
    print(f"Dense: {emb.shape[0]:,} x {emb.shape[1]} in {time.time() - t0:.0f}s -> {FAISS_PATH.name}")


def write_meta(chunks: list[dict]) -> None:
    """Everything except the text, in index order, so retrievers can map row -> chunk."""
    with META_PATH.open("w", encoding="utf-8") as f:
        for row, c in enumerate(chunks):
            f.write(json.dumps({**c, "row": row}, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not CHUNKS_PATH.exists():
        print(f"{CHUNKS_PATH} not found. Run `python -m arqa.chunk` first.")
        return 1
    INDEX_DIR.mkdir(exist_ok=True)
    chunks = load_chunks()
    write_meta(chunks)
    build_bm25(chunks)
    if "--bm25-only" not in argv:
        build_dense(chunks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
