"""Print the cached query rewrites for the questions given on the command line
(default: the four that miss in every configuration), so the rewrite prompt can
be judged by eye.   python eval/show_rewrites.py [ID ...]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arqa.retrieve import REWRITE_CACHE  # noqa: E402

STUBBORN = ["BAJFINANCE-FY25-06", "SUNPHARMA-FY25-05", "HINDUNILVR-FY25-05", "TCS-FY24-02"]


def main(ids: list[str]) -> None:
    qs = {}
    with (ROOT / "data" / "eval" / "questions.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                q = json.loads(line)
                qs[q["id"]] = q
    cache = json.loads(REWRITE_CACHE.read_text(encoding="utf-8")) if REWRITE_CACHE.exists() else {}
    print(f"{len(cache)} questions have cached rewrites\n")
    for i in ids or STUBBORN:
        q = qs.get(i)
        if not q:
            print(f"{i}: not in questions.jsonl"); continue
        print(f"== {i}\n   Q: {q['question']}")
        gold = q["gold"][0].get("quote", "")
        if gold:
            print(f"   gold sentence: {gold[:160]}{'…' if len(gold) > 160 else ''}")
        for r in cache.get(q["question"], ["(no rewrites cached)"]):
            print(f"   -> {r}")
        print()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    main(sys.argv[1:])
