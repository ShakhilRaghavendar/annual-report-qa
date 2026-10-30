"""
run_answer_eval.py — score the ANSWERS, not just the retrieval.

For each question in data/eval/questions.jsonl:
  1. answer() it (retriever + LLM), with the question's ticker/FY as filters.
  2. citation_ok  — hard check, no model involved: does any cited passage's
     page range overlap a gold page of the same report? (A right answer with
     a wrong citation is a hallucination that happens to be true.)
  3. verdict      — an LLM judge (a cheaper model) compares the system's answer
     with the gold answer: "correct" | "partial" | "wrong". The judge sees the
     question, the gold answer and the system answer — never the passages —
     so it grades the answer, not the retrieval.

Every result is appended to eval/answers.jsonl as it is produced, keyed by
question id, and the script SKIPS ids already there. So it can be stopped
(Ctrl-C, a rate limit, the daily token cap on Groq's free tier) and re-run
later; it picks up where it left off. Delete the file to start over.

Run:
    python eval/run_answer_eval.py                     # all 62, resumable
    python eval/run_answer_eval.py --limit 10          # the first 10 unscored
    python eval/run_answer_eval.py --ids INFY-FY25-02,TCS-FY25-01
    python eval/run_answer_eval.py --retriever bm25 --out eval/answers_bm25.jsonl
Writes eval/answer_results.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arqa import llm  # noqa: E402
from arqa.answer import DEFAULT_RETRIEVER, answer  # noqa: E402

QUESTIONS = ROOT / "data" / "eval" / "questions.jsonl"
DEFAULT_OUT = ROOT / "eval" / "answers.jsonl"
RESULTS = ROOT / "eval" / "answer_results.md"

JUDGE_PROMPT = """You grade answers to questions about company annual reports.

Compare the SYSTEM ANSWER with the GOLD ANSWER. Judge only whether the system answer states the same facts and figures as the gold answer. Minor wording differences, rounding to the same magnitude, or extra correct context do not matter. A unit error (lakh vs crore, million vs crore, US$ vs ₹) is WRONG. If the system says the answer was not found but the gold answer exists, that is WRONG.

Respond with a JSON object: {"verdict": "correct" | "partial" | "wrong", "reason": "<one sentence>"}
- correct: the key fact(s)/figure(s) match.
- partial: some of the key facts match, or the figure is right but a requested comparison/second figure is missing.
- wrong: the main fact or figure is missing, different, or in the wrong unit."""


def load_questions() -> list[dict]:
    with QUESTIONS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_done(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def _overlaps(c: dict, gold: list[dict]) -> bool:
    """Does passage c come from a gold report and touch a gold page (or an
    accepted alternate page — the same fact often appears in the highlights,
    the letter and the Directors' Report)?"""
    for g in gold:
        if c["ticker"] != g["ticker"] or c["fy"] != g["fy"] or c.get("part", "") != g.get("part", ""):
            continue
        pages = set(g["pages"]) | set(g.get("alt_pages", []))
        if any(c["page_start"] <= p <= c["page_end"] for p in pages):
            return True
    return False


def citation_ok(ans: dict, gold: list[dict]) -> bool:
    return any(_overlaps(c, gold) for c in ans["citations"])


def retrieval_ok(ans: dict, gold: list[dict]) -> bool:
    """Was a gold page among the passages the model was GIVEN? Page-level —
    generous, because a page is split across several chunks."""
    return any(_overlaps(c, gold) for c in ans["passages"])


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def quote_retrieved(ans: dict, gold: list[dict]) -> bool:
    """Was the gold QUOTE itself inside a chunk the model was given? This is
    the honest retrieval check: HDFC's NII sentence sits in chunk #13 of a
    page the retriever served as chunk #14, which doesn't contain it."""
    texts = [_norm(t) for t in ans.get("passage_texts", [])]
    for g in gold:
        q = _norm(g.get("quote", ""))
        if q and any(q in t for t in texts):
            return True
    return False


def judge(q: dict, system_answer: str, found: bool) -> tuple[str, str]:
    sys_text = system_answer if found else f"NOT FOUND. {system_answer}"
    user = (f"QUESTION: {q['question']}\n\nGOLD ANSWER: {q['answer']}\n\nSYSTEM ANSWER: {sys_text}")
    raw = llm.chat([{"role": "system", "content": JUDGE_PROMPT}, {"role": "user", "content": user}],
                   model=llm.model_name("judge"), json_mode=True, max_tokens=200, reasoning="low")
    try:
        s = raw[raw.find("{"): raw.rfind("}") + 1]
        d = json.loads(s)
        v = str(d.get("verdict", "")).lower().strip()
        return (v if v in ("correct", "partial", "wrong") else "wrong"), str(d.get("reason", ""))[:300]
    except (ValueError, json.JSONDecodeError):
        return "wrong", f"judge reply unparseable: {raw[:100]}"


def render(rows: list[dict], retriever: str, model: str) -> str:
    kinds = ["all", "factual", "conceptual", "cross_year", "unit_trap"]
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_kind[r["kind"]].append(r)
        by_kind["all"].append(r)
    lines = [f"# Answer results ({len(rows)} questions, retriever = {retriever}, model = {model})", "",
             "| kind | n | correct | partial | wrong | not found | citation ok | gold page retrieved | gold quote retrieved | s/q |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for kd in kinds:
        rs = by_kind.get(kd)
        if not rs:
            continue
        n = len(rs)
        c = Counter(r["verdict"] for r in rs)
        nf = sum(1 for r in rs if not r["found"])
        cit = sum(1 for r in rs if r["citation_ok"])
        lat = sum(r["latency_s"] for r in rs) / n
        ret = sum(1 for r in rs if r.get("retrieval_ok"))
        qr = [r for r in rs if "quote_retrieved" in r]
        qcol = f"{sum(1 for r in qr if r['quote_retrieved'])/len(qr):.2f}" if qr else "—"
        lines.append(f"| {kd} | {n} | {c['correct']/n:.2f} | {c['partial']/n:.2f} | {c['wrong']/n:.2f} | {nf/n:.2f} | {cit/n:.2f} | {ret/n:.2f} | {qcol} | {lat:.1f} |")
    lines += ["", "correct/partial/wrong = LLM-judge verdict against the gold answer; citation ok = a cited passage overlaps a gold page (hard check); "
              "gold page retrieved = a gold page was among the passages the model was given (page-level, generous); "
              "gold quote retrieved = the gold sentence itself was inside a passage the model was given (the honest retrieval check); not found = the system declined to answer.", ""]
    wrong = [r for r in rows if r["verdict"] == "wrong"]
    if wrong:
        r_fail = sum(1 for r in wrong if not r.get("retrieval_ok"))
        lines += [f"Of the {len(wrong)} wrong answers, {r_fail} never had a gold page retrieved (retrieval failure) and {len(wrong) - r_fail} had it and still missed (reading failure).", ""]
    bad = [r for r in rows if r["verdict"] != "correct"]
    if bad:
        lines.append("## Not correct")
        lines.append("")
        lines.append("| id | verdict | citation ok | gold retrieved | judge's reason |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in bad:
            lines.append(f"| {r['id']} | {r['verdict']} | {'yes' if r['citation_ok'] else 'no'} | {'yes' if r.get('retrieval_ok') else 'no'} | {r['reason'].replace('|', '/')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retriever", default=DEFAULT_RETRIEVER)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="score at most this many new questions")
    ap.add_argument("--ids", default="", help="comma-separated question ids to (re)score")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between questions (rate limits)")
    args = ap.parse_args()
    out = Path(args.out)

    questions = load_questions()
    done = load_done(out)
    want = set(args.ids.split(",")) if args.ids else None
    todo = [q for q in questions if (want and q["id"] in want) or (not want and q["id"] not in done)]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(done)} already scored, {len(todo)} to do, retriever={args.retriever}, model={llm.model_name('model')}, judge={llm.model_name('judge')}", flush=True)

    for i, q in enumerate(todo, start=1):
        fy = q["fy"] if len(q["fy"]) > 1 else q["fy"][0]
        try:
            a = answer(q["question"], ticker=q["ticker"], fy=fy, k=args.k, retriever=args.retriever)
            ad = a.to_dict()
            ad["passage_texts"] = [h.chunk["text"] for h in a.hits]
            verdict, reason = judge(q, a.answer, a.found)
        except Exception as e:  # noqa: BLE001 — keep going, record the failure
            print(f"  {q['id']}: ERROR {e}", flush=True)
            if "rate" in str(e).lower() or "429" in str(e):
                print("Rate/daily limit hit — stop here and re-run later; progress is saved.", flush=True)
                break
            continue
        row = {"id": q["id"], "kind": q["kind"], "ticker": q["ticker"], "fy": q["fy"],
               "question": q["question"], "gold_answer": q["answer"],
               "found": ad["found"], "answer": ad["answer"], "figures": ad["figures"],
               "citations": ad["citations"], "citation_ok": citation_ok(ad, q["gold"]),
               "passages": [f"{p['ticker']} {p['fy']}{' '+p['part'] if p['part'] else ''} p{p['page_start']}-{p['page_end']}" for p in ad["passages"]],
               "retrieval_ok": retrieval_ok(ad, q["gold"]),
               "passage_ids": [p["chunk_id"] for p in ad["passages"]],
               "quote_retrieved": quote_retrieved(ad, q["gold"]),
               "verdict": verdict, "reason": reason, "latency_s": round(ad["latency_s"], 2),
               "model": ad["model"], "retriever": ad["retriever"]}
        done[q["id"]] = row
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  [{i}/{len(todo)}] {q['id']}: {verdict:8s} cite={'ok' if row['citation_ok'] else 'NO'} retrieved={'ok' if row['retrieval_ok'] else 'NO'} quote={'ok' if row['quote_retrieved'] else 'NO'}  {ad['latency_s']:.1f}s", flush=True)
        time.sleep(args.pause)

    rows = [done[q["id"]] for q in questions if q["id"] in done]
    if rows:
        md = render(rows, args.retriever, rows[-1]["model"])
        RESULTS.write_text(md, encoding="utf-8")
        print("\n" + md + f"\nwrote {RESULTS} ({len(rows)} of {len(questions)} questions scored)")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
