"""
run_quote_eval.py — "was the gold sentence in what we'd hand the model?", with NO LLM.

Run 3 taught us the page-level retrieval check was generous: a page is split
across several chunks and the gold sentence can sit in a neighbour of the
chunk that was retrieved. This script measures retrieval at the granularity
that matters for answering — the quote — for several retriever configurations,
on all 62 questions, in a few minutes on a laptop. No API calls, no daily cap.

For each question: retrieve exactly as answer.py would (filters by ticker and
year; cross-year questions get one search per year), then check whether any
gold quote is a substring of any passage text.

Run:
    python eval/run_quote_eval.py
    python eval/run_quote_eval.py --configs "hybrid+rerank:5,hybrid+rerank+expand:5" --k 5
Writes eval/quote_results.md and eval/quote_results.json (for the chart).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arqa.answer import retrieve  # noqa: E402

QUESTIONS = ROOT / "data" / "eval" / "questions.jsonl"
OUT_MD = ROOT / "eval" / "quote_results.md"
OUT_JSON = ROOT / "eval" / "quote_results.json"

# (retriever name, k) pairs. The expanded variants hand the model more text per
# question — that cost is reported alongside, as average tokens per question.
DEFAULT_CONFIGS = [
    ("hybrid+rerank", 5),
    ("hybrid+rerank", 8),
    ("hybrid+rerank+expand", 3),
    ("hybrid+rerank+expand", 5),
    ("bm25", 5),
    ("bm25+expand", 5),
]


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def load_questions() -> list[dict]:
    with QUESTIONS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def page_hit(chunk: dict, gold: list[dict]) -> bool:
    for g in gold:
        if chunk["ticker"] != g["ticker"] or chunk["fy"] != g["fy"] or chunk.get("part", "") != g.get("part", ""):
            continue
        pages = set(g["pages"]) | set(g.get("alt_pages", []))
        if any(chunk["page_start"] <= p <= chunk["page_end"] for p in pages):
            return True
    return False


def evaluate(name: str, k: int, questions: list[dict]) -> dict:
    per_kind: dict[str, list[dict]] = defaultdict(list)
    misses = []
    tokens = []
    t0 = time.time()
    for q in questions:
        fy = q["fy"] if len(q["fy"]) > 1 else q["fy"][0]
        hits = retrieve(q["question"], q["ticker"], fy, k=k, retriever=name)
        texts = [_norm(h.chunk["text"]) for h in hits]
        quote = any(_norm(g["quote"]) in t for g in q["gold"] if g.get("quote") for t in texts)
        page = any(page_hit(h.chunk, q["gold"]) for h in hits)
        tokens.append(sum(h.chunk.get("n_tokens", 0) for h in hits))
        row = {"quote": quote, "page": page}
        per_kind[q["kind"]].append(row)
        per_kind["all"].append(row)
        if not quote:
            misses.append(q["id"])
    summary = {kind: {"n": len(rows),
                      "quote": sum(r["quote"] for r in rows) / len(rows),
                      "page": sum(r["page"] for r in rows) / len(rows)}
               for kind, rows in per_kind.items()}
    return {"retriever": name, "k": k, "summary": summary, "misses": misses, "n": len(questions),
            "avg_tokens": sum(tokens) / len(tokens), "seconds": time.time() - t0}


def render(results: list[dict]) -> str:
    kinds = ["all", "factual", "conceptual", "cross_year", "unit_trap"]
    lines = ["# Gold quote retrieved — retrieval at sentence granularity (no LLM)", "",
             "| retriever | k | " + " | ".join(f"{kd} quote / page" for kd in kinds) + " | avg tokens/q | s/q |",
             "| --- | --- |" + " --- |" * (len(kinds) + 2)]
    for r in results:
        cells = []
        for kd in kinds:
            s = r["summary"].get(kd)
            cells.append(f"**{s['quote']:.2f}** / {s['page']:.2f} ({s['n']})" if s else "—")
        lines.append(f"| {r['retriever']} | {r['k']} | " + " | ".join(cells) +
                     f" | {r['avg_tokens']:.0f} | {r['seconds'] / r['n']:.2f} |")
    lines += ["", "quote = the gold sentence is inside a passage the model would be given; page = a gold page overlaps a passage (the generous check). avg tokens/q = passage text handed to the model per question.", ""]
    for r in results:
        if r["misses"]:
            lines.append(f"**{r['retriever']} k={r['k']} quote misses ({len(r['misses'])}):** " + ", ".join(r["misses"]))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="", help='comma-separated "retriever:k", e.g. "hybrid+rerank:5,bm25+expand:5"')
    args = ap.parse_args()
    configs = DEFAULT_CONFIGS
    if args.configs:
        configs = [(c.split(":")[0], int(c.split(":")[1])) for c in args.configs.split(",")]
    questions = load_questions()
    results = []
    for name, k in configs:
        print(f"{name} k={k} ...", flush=True)
        r = evaluate(name, k, questions)
        results.append(r)
        print(f"  quote {r['summary']['all']['quote']:.2f}  page {r['summary']['all']['page']:.2f}  "
              f"avg tokens {r['avg_tokens']:.0f}  ({r['seconds']:.0f}s)", flush=True)
    md = render(results)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n" + md + f"\nwrote {OUT_MD} and {OUT_JSON}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
