"""
ask.py — the command line.

    python -m arqa.ask "What free cash flow did Infosys generate in FY25?" --ticker INFY --fy FY25
    python -m arqa.ask "How did Retail EBITDA move?" --ticker RELIANCE --fy FY24 --fy FY25
    python -m arqa.ask "..." --ticker TCS --fy FY25 --retriever bm25 --k 8 --json

--ticker and --fy are filters: they tell the system which report(s) to read,
as a user would. Leave them off to search all 24 reports (slower, less precise).
"""

from __future__ import annotations

import json
import sys

import typer

from arqa.answer import DEFAULT_K, DEFAULT_RETRIEVER, answer

app = typer.Typer(add_completion=False, help="Ask a question of the annual reports.")


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question, in your own words."),
    ticker: str | None = typer.Option(None, "--ticker", "-t", help="e.g. INFY, HDFCBANK, RELIANCE"),
    fy: list[str] = typer.Option([], "--fy", "-y", help="FY24 or FY25; repeat for a cross-year question"),
    retriever: str = typer.Option(DEFAULT_RETRIEVER, "--retriever", "-r", help="bm25 | dense | hybrid | hybrid+rerank"),
    k: int = typer.Option(DEFAULT_K, "--k", help="passages to read (per year for cross-year)"),
    model: str | None = typer.Option(None, "--model", help="override LLM_MODEL"),
    as_json: bool = typer.Option(False, "--json", help="print the full Answer as JSON"),
    show_passages: bool = typer.Option(False, "--passages", help="also list every retrieved passage"),
) -> None:
    fys: str | list[str] | None = None
    if len(fy) == 1:
        fys = fy[0].upper()
    elif fy:
        fys = [y.upper() for y in fy]
    a = answer(question, ticker=ticker.upper() if ticker else None, fy=fys, k=k, retriever=retriever, model=model)
    if as_json:
        print(json.dumps(a.to_dict(), ensure_ascii=False, indent=2))
        return
    print()
    print(a.render())
    if show_passages:
        print("\nRetrieved:")
        for p in a.passages:
            print("  " + p.as_text())
    print()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    app()
