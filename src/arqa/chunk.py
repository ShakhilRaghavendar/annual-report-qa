"""
chunk.py — split parsed sections into retrieval chunks with page numbers.

Why not just embed whole sections: an MD&A is 40 pages. A retriever needs
units small enough that a hit means "the answer is here", large enough that a
paragraph's context survives. ~500 tokens with ~80 tokens of overlap is the
boring, well-tested default.

Structure-aware: we split on paragraph boundaries first and only cut inside a
paragraph when it is too long on its own. Page numbers come from the \f
markers parse.py leaves between pages, so every chunk knows the page range it
was cut from — that is what citations and the eval's gold pages key on.

Run:
    python -m arqa.chunk            # data/processed/*.jsonl -> data/chunks.jsonl
    python -m arqa.chunk --stats    # only print counts

Each output line:
    {"chunk_id","ticker","fy","part","section","section_key",
     "page_start","page_end","text","n_tokens"}
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import tiktoken

from arqa.parse import PROCESSED_DIR, PAGE_SEP, TARGET_KEYS

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = ROOT / "data" / "chunks.jsonl"

CHUNK_TOKENS = 500
OVERLAP_TOKENS = 80
MIN_CHUNK_TOKENS = 40          # drop fragments that are just a page number
INDEXED_KEYS = set(TARGET_KEYS)  # governance/BRSR/standalone chapters are not indexed in v1

_enc = tiktoken.get_encoding("cl100k_base")


def n_tokens(text: str) -> int:
    return len(_enc.encode(text))


@dataclass
class Chunk:
    chunk_id: str
    ticker: str
    fy: str
    part: str
    section: str
    section_key: str
    page_start: int
    page_end: int
    text: str
    n_tokens: int


def paragraphs_with_pages(section_text: str, first_page: int) -> list[tuple[str, int]]:
    """Split section text into (paragraph, page_number). Pages are separated
    by PAGE_SEP; paragraphs by blank lines or single newlines in PDF text
    (PyMuPDF emits one line per visual line, so we join lines inside a page
    and split on double newlines when present, else treat ~every 6 lines as a
    paragraph)."""
    out: list[tuple[str, int]] = []
    for offset, page_text in enumerate(section_text.split(PAGE_SEP)):
        page_no = first_page + offset
        blocks = [b.strip() for b in page_text.split("\n\n") if b.strip()]
        if len(blocks) <= 1:
            # No blank-line structure: group lines into pseudo-paragraphs.
            lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
            blocks = [" ".join(lines[i:i + 6]) for i in range(0, len(lines), 6)]
        else:
            blocks = [" ".join(b.split()) for b in blocks]
        out.extend((b, page_no) for b in blocks if b)
    return out


def _split_long(text: str, limit: int) -> list[str]:
    """Cut a single over-long paragraph into token-sized pieces at sentence ends when possible."""
    ids = _enc.encode(text)
    if len(ids) <= limit:
        return [text]
    pieces, start = [], 0
    while start < len(ids):
        end = min(start + limit, len(ids))
        piece = _enc.decode(ids[start:end])
        if end < len(ids):
            cut = max(piece.rfind(". "), piece.rfind("; "))
            if cut > len(piece) // 2:
                piece = piece[: cut + 1]
                end = start + len(_enc.encode(piece))
        pieces.append(piece.strip())
        start = end
    return pieces


def chunk_section(sec: dict, chunk_tokens: int = CHUNK_TOKENS, overlap: int = OVERLAP_TOKENS) -> list[Chunk]:
    paras = paragraphs_with_pages(sec["text"], sec["page_start"])
    # expand over-long paragraphs first
    units: list[tuple[str, int]] = []
    for p, pg in paras:
        for piece in _split_long(p, chunk_tokens):
            units.append((piece, pg))

    chunks: list[Chunk] = []
    buf: list[tuple[str, int, int]] = []   # (text, page, tokens)
    buf_tokens = 0
    stem = f"{sec['ticker']}_{sec['fy']}" + (f"_{sec['part']}" if sec.get("part") else "")

    def emit() -> None:
        nonlocal buf, buf_tokens
        if not buf:
            return
        text = "\n".join(t for t, _, _ in buf)
        tok = n_tokens(text)
        if tok >= MIN_CHUNK_TOKENS:
            chunks.append(Chunk(
                chunk_id=f"{stem}:{sec['section_key']}:{len(chunks):04d}",
                ticker=sec["ticker"], fy=sec["fy"], part=sec.get("part", ""),
                section=sec["section"], section_key=sec["section_key"],
                page_start=min(pg for _, pg, _ in buf), page_end=max(pg for _, pg, _ in buf),
                text=text, n_tokens=tok,
            ))
        # keep the tail as overlap for the next chunk
        kept, kept_tokens = [], 0
        for item in reversed(buf):
            if kept_tokens + item[2] > overlap:
                break
            kept.insert(0, item)
            kept_tokens += item[2]
        buf, buf_tokens = kept, kept_tokens

    for text, pg in units:
        tok = n_tokens(text)
        if buf_tokens + tok > chunk_tokens and buf:
            emit()
        buf.append((text, pg, tok))
        buf_tokens += tok
    if buf:
        # final flush without overlap carry-over
        text = "\n".join(t for t, _, _ in buf)
        if n_tokens(text) >= MIN_CHUNK_TOKENS:
            chunks.append(Chunk(
                chunk_id=f"{stem}:{sec['section_key']}:{len(chunks):04d}",
                ticker=sec["ticker"], fy=sec["fy"], part=sec.get("part", ""),
                section=sec["section"], section_key=sec["section_key"],
                page_start=min(pg for _, pg, _ in buf), page_end=max(pg for _, pg, _ in buf),
                text=text, n_tokens=n_tokens(text),
            ))
    return chunks


def chunk_all(processed_dir: Path = PROCESSED_DIR) -> list[Chunk]:
    out: list[Chunk] = []
    for path in sorted(processed_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                sec = json.loads(line)
                if sec["section_key"] not in INDEXED_KEYS:
                    continue
                out.extend(chunk_section(sec))
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    chunks = chunk_all()
    if not chunks:
        print(f"No sections found in {PROCESSED_DIR}. Run `python -m arqa.parse` first.")
        return 1
    by_file: dict[str, int] = {}
    for c in chunks:
        key = f"{c.ticker}_{c.fy}" + (f"_{c.part}" if c.part else "")
        by_file[key] = by_file.get(key, 0) + 1
    for k, v in sorted(by_file.items()):
        print(f"  {k:<26} {v:>6} chunks")
    total_tokens = sum(c.n_tokens for c in chunks)
    print(f"\n{len(chunks):,} chunks, {total_tokens:,} tokens, "
          f"avg {total_tokens // max(len(chunks), 1)} tokens/chunk")
    if "--stats" in argv:
        return 0
    with CHUNKS_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    print(f"wrote {CHUNKS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
