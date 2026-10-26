"""
run_eval.py — score every retriever against data/eval/questions.jsonl.

A retrieved chunk is a HIT for a gold passage when it comes from the same
report (ticker + fy + part) and its page range overlaps the gold pages.
Page-level matching is what makes the eval set writable by a human: you note
which page the answer is on, not which chunk.

Metrics at k (default 5), averaged over questions:
  hit_rate   1 if ANY gold passage was hit in the top k, else 0
  recall@k   share of gold passages hit in the top k
  mrr        1 / rank of the first hit (0 if none)

Each question is run with a metadata filter for its ticker and FY — the
system is told which report to look in, as a user would. (An unfiltered
variant is a later experiment.)

Run:
    python eval/run_eval.py                      # all retrievers
    python eval/run_eval.py --retrievers bm25    # a subset, comma-separated
    python eval/run_eval.py --k 10
Writes eval/results.md and prints it.
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

from arqa.retrieve import get_retriever  # noqa: E402

QUESTIONS = ROOT / "data" / "eval" / "questions.jsonl"
RESULTS = ROOT / "eval" / "results.md"
DEFAULT_RETRIEVERS = ["bm25", "dense", "hybrid", "hybrid+rerank"]


def load_questions() -> list[dict]:
    with QUESTIONS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def hit(chunk: dict, gold: dict) -> bool:
    if chunk["ticker"] != gold["ticker"] or chunk["fy"] != gold["fy"]:
        return False
    if chunk.get("part", "") != gold.get("part", ""):
        return False
    pages = set(gold["pages"])
    return any(p in pages for p in range(chunk["page_start"], chunk["page_end"] + 1))


def score_question(q: dict, hits: list) -> dict:
    golds = q["gold"]
    found = [False] * len(golds)
    first_rank = 0
    for h in hits:
        for gi, g in enumerate(golds):
            if not found[gi] and hit(h.chunk, g):
                found[gi] = True
                if first_rank == 0:
                    first_rank = h.rank
    return {
        "hit_rate": 1.0 if any(found) else 0.0,
        "recall": sum(found) / len(golds),
        "mrr": (1.0 / first_rank) if first_rank else 0.0,
    }


def evaluate(retriever_name: str, questions: list[dict], k: int) -> tuple[dict, dict, list]:
    r = get_retriever(retriever_name)
    per_kind: dict[str, list[dict]] = defaultdict(list)
    misses = []
    t0 = time.time()
    for q in questions:
        filters = {"ticker": q["ticker"], "fy": q["fy"]}
        hits = r.search(q["question"], k=k, filters=filters)
        s = score_question(q, hits)
        per_kind[q["kind"]].append(s)
        per_kind["all"].append(s)
        if s["hit_rate"] == 0:
            misses.append((q["id"], [f"p{h.chunk['page_start']}-{h.chunk['page_end']}" for h in hits]))
    elapsed = time.time() - t0

    def avg(rows, key):
        return sum(x[key] for x in rows) / len(rows) if rows else 0.0

    summary = {kind: {m: avg(rows, m) for m in ("hit_rate", "recall", "mrr")} | {"n": len(rows)}
               for kind, rows in per_kind.items()}
    return summary, {"seconds": elapsed, "per_q": elapsed / max(len(questions), 1)}, misses


def render(results: dict, k: int, n_questions: int, timing: dict, misses: dict) -> str:
    kinds = ["all", "factual", "conceptual", "cross_year", "unit_trap"]
    lines = [f"# Retrieval results (k = {k}, {n_questions} questions)", ""]
    lines.append("| retriever | " + " | ".join(f"{kd} (n)" for kd in kinds) + " | s/q |")
    lines.append("| --- |" + " --- |" * (len(kinds) + 1))
    for name, summary in results.items():
        cells = []
        for kd in kinds:
            s = summary.get(kd)
            cells.append(f"hit {s['hit_rate']:.2f} · R@{k} {s['recall']:.2f} · MRR {s['mrr']:.2f} ({s['n']})" if s else "—")
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {timing[name]['per_q']:.2f} |")
    lines += ["", "hit = share of questions with any gold page in the top k; R@k = share of gold passages found; MRR = mean reciprocal rank of the first hit.", ""]
    for name, m in misses.items():
        if m:
            lines.append(f"**{name} missed:** " + "; ".join(f"{qid} (got {', '.join(pg) or 'nothing'})" for qid, pg in m))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrievers", default=",".join(DEFAULT_RETRIEVERS))
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    questions = load_questions()
    if not questions:
        print(f"No questions in {QUESTIONS}")
        return 1
    results, timing, misses = {}, {}, {}
    for name in args.retrievers.split(","):
        name = name.strip()
        print(f"evaluating {name} ...", flush=True)
        results[name], timing[name], misses[name] = evaluate(name, questions, args.k)
    md = render(results, args.k, len(questions), timing, misses)
    RESULTS.write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"wrote {RESULTS}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())
