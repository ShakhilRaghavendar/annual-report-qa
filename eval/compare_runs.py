"""
compare_runs.py — before/after table for two answer-eval runs.

    python eval/compare_runs.py eval/answers_run1.jsonl eval/answers.jsonl

Prints a markdown table (and writes eval/compare.md) with correct / partial /
wrong / cited-gold-page per run, by question kind, plus the list of questions
whose verdict changed. The second file may also carry retrieval_ok.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "compare.md"
KINDS = ["all", "factual", "conceptual", "cross_year", "unit_trap"]


def load(path: str) -> dict[str, dict]:
    return {r["id"]: r for r in (json.loads(l) for l in open(path, encoding="utf-8") if l.strip())}


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    c = Counter(r["verdict"] for r in rows)
    return {"n": n, "correct": c["correct"] / n, "partial": c["partial"] / n, "wrong": c["wrong"] / n,
            "cite": sum(1 for r in rows if r["citation_ok"]) / n,
            "retrieved": (sum(1 for r in rows if r.get("retrieval_ok")) / n) if any("retrieval_ok" in r for r in rows) else None}


def main(a_path: str, b_path: str, out: str | None = None) -> None:
    a, b = load(a_path), load(b_path)
    ids = [i for i in a if i in b]
    by_kind: dict[str, list[str]] = defaultdict(list)
    for i in ids:
        by_kind[a[i]["kind"]].append(i)
        by_kind["all"].append(i)
    lines = [f"# Answer eval: {Path(a_path).stem} vs {Path(b_path).stem} ({len(ids)} questions in both)", "",
             "| kind | n | correct | partial | wrong | cited gold page | gold page retrieved (run 2) |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for kd in KINDS:
        q = by_kind.get(kd)
        if not q:
            continue
        sa, sb = summarise([a[i] for i in q]), summarise([b[i] for i in q])
        ret = f"{sb['retrieved']:.2f}" if sb["retrieved"] is not None else "—"
        lines.append(f"| {kd} | {sa['n']} | {sa['correct']:.2f} → **{sb['correct']:.2f}** | {sa['partial']:.2f} → {sb['partial']:.2f} | "
                     f"{sa['wrong']:.2f} → {sb['wrong']:.2f} | {sa['cite']:.2f} → **{sb['cite']:.2f}** | {ret} |")
    changed = [(i, a[i]["verdict"], b[i]["verdict"]) for i in ids if a[i]["verdict"] != b[i]["verdict"]]
    better = [x for x in changed if (x[1], x[2]) in {("wrong", "correct"), ("wrong", "partial"), ("partial", "correct")}]
    worse = [x for x in changed if x not in better]
    lines += ["", f"Verdict improved on {len(better)}, worsened on {len(worse)}.", ""]
    if better:
        lines.append("Improved: " + ", ".join(f"{i} ({x}→{y})" for i, x, y in better))
    if worse:
        lines.append("Worsened: " + ", ".join(f"{i} ({x}→{y})" for i, x, y in worse))
    wrong2 = [b[i] for i in ids if b[i]["verdict"] == "wrong"]
    if wrong2 and any("retrieval_ok" in r for r in wrong2):
        rf = sum(1 for r in wrong2 if not r.get("retrieval_ok"))
        lines += ["", f"Run 2's {len(wrong2)} wrong answers: {rf} retrieval failures (gold page never shown to the model), {len(wrong2) - rf} reading failures (shown and still missed)."]
    md = "\n".join(lines) + "\n"
    (Path(out) if out else OUT).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    main(*sys.argv[1:4])
