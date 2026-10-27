"""
answer.py — retrieve, read, answer with citations, normalise money to ₹ crore.

    from arqa.answer import answer
    a = answer("What free cash flow did Infosys generate in FY25?", ticker="INFY", fy="FY25")
    print(a.render())

Flow
  1. Retrieve k chunks (default: hybrid + cross-encoder rerank, the best
     retriever on the eval set). A cross-year question (fy=["FY24","FY25"])
     retrieves k chunks PER YEAR — the eval showed cross-year is a retrieval-
     budget problem, not a relevance one.
  2. Number the passages [1]..[n] and ask the LLM for a JSON object:
     answer text with [n] citations, the figures it used (value + unit AS
     WRITTEN), and found=false when the passages don't contain the answer.
  3. Post-process in code, not in the prompt: every INR figure is converted to
     ₹ crore with arqa.units (lakh → ÷100, million → ÷10, billion → ×100),
     citations are mapped back to company / FY / section / page. The model
     never does arithmetic it can get wrong.

The rupee glyph in extracted text is unreliable (backtick, "H", "C", "I"…
depending on the font), so the prompt tells the model to read the currency
from context ("… crore", "US$") and never from the symbol.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict

from arqa import llm
from arqa.retrieve import Hit, get_retriever
from arqa.units import TO_CRORE, format_crore, to_crore

DEFAULT_RETRIEVER = "hybrid+rerank"
DEFAULT_K = 5
MAX_PASSAGE_CHARS = 2200   # ~500 tokens; chunks are ≤520 tokens anyway

SYSTEM_PROMPT = """You are an analyst answering questions about Indian listed companies strictly from excerpts of their annual reports.

Rules
- Use ONLY the numbered passages. If they do not contain the answer, set "found": false and say what is missing. Never use outside knowledge, never estimate.
- Cite every claim with the passage number in square brackets, e.g. [2]. Put the citation right after the sentence it supports.
- Keep the answer to 1–4 sentences. Lead with the number or the fact; then the comparison or reason if the passage gives one.
- Money: Indian reports state amounts in ₹ crore, ₹ lakh, ₹ million, ₹ billion, or US$ million/billion. Report every amount in the "figures" list with the unit EXACTLY as the passage states it. The currency symbol in the text is often garbled (a backtick, "H", "C", "I" or similar) — decide the currency from the words around the number ("crore", "lakh" => INR; "US$", "USD", "$" => USD), never from the symbol. Do not convert units yourself; the caller converts.
- When the passages give BOTH a ₹ figure and a foreign-currency figure for the same item, answer with the ₹ figure and mention the other. Prefer a ₹ figure from any passage over a US$ figure, even if the US$ one is in a higher-ranked passage.
- If the question asks for ₹ crore but the passages only give a US$ figure, that still counts as FOUND: answer with the US$ figure and say the report states it in US$ only. "found": false is only for when the item itself is not in the passages.
- Write the rupee sign as ₹ in the answer. The passages may show it as a backtick, "C", "H", "I" or another stray letter in front of a number — never copy that letter.
- Percentages and counts go in "figures" too, with unit "percent" or "count".

Respond with a single JSON object, no prose outside it:
{
  "found": true,
  "answer": "… [1] … [3]",
  "figures": [
    {"label": "net interest income FY25", "value": 122670.1, "unit": "crore", "currency": "INR", "citation": 1}
  ]
}
"unit" must be one of: crore, lakh, million, billion, thousand, percent, count, other."""


@dataclass
class Figure:
    label: str
    value: float
    unit: str
    currency: str
    citation: int | None
    crore: float | None = None        # filled in by code for INR amounts

    def as_text(self) -> str:
        if self.unit in ("percent",):
            return f"{self.label}: {self.value:g}%"
        if self.unit in ("count", "other"):
            return f"{self.label}: {self.value:g}"
        stated = f"{self.currency} {self.value:,} {self.unit}".replace("INR", "₹")
        if self.crore is not None and self.unit != "crore":
            return f"{self.label}: {stated} = {format_crore(self.crore)}"
        if self.crore is not None:
            return f"{self.label}: {format_crore(self.crore)}"
        return f"{self.label}: {stated} (stated in {self.currency} only; no ₹ figure on the cited page)"


@dataclass
class Citation:
    n: int
    ticker: str
    fy: str
    part: str
    section: str
    page_start: int
    page_end: int
    chunk_id: str

    def as_text(self) -> str:
        pages = f"p.{self.page_start}" if self.page_start == self.page_end else f"pp.{self.page_start}–{self.page_end}"
        part = f" ({self.part})" if self.part else ""
        return f"[{self.n}] {self.ticker} {self.fy}{part}, {self.section}, {pages}"


@dataclass
class Answer:
    question: str
    found: bool
    answer: str
    figures: list[Figure]
    citations: list[Citation]          # only the passages the answer actually cites
    passages: list[Citation]           # everything that was retrieved, for debugging
    model: str
    retriever: str
    latency_s: float
    raw: str = field(default="", repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d

    def render(self) -> str:
        lines = [self.answer.strip() if self.found else f"Not found in the retrieved passages. {self.answer.strip()}"]
        if self.figures:
            lines += ["", "Figures:"] + [f"  • {f.as_text()}" for f in self.figures]
        if self.citations:
            lines += ["", "Sources:"] + [f"  {c.as_text()}" for c in self.citations]
        lines += ["", f"({self.retriever}, {self.model}, {self.latency_s:.1f}s)"]
        return "\n".join(lines)


# --- retrieval ---------------------------------------------------------------------

def retrieve(question: str, ticker: str | None, fy: str | list[str] | None,
             k: int = DEFAULT_K, retriever: str = DEFAULT_RETRIEVER) -> list[Hit]:
    r = get_retriever(retriever)
    fys = [fy] if isinstance(fy, str) else list(fy or [])
    base = {"ticker": ticker} if ticker else {}
    if len(fys) <= 1:
        filters = base | ({"fy": fys[0]} if fys else {})
        return r.search(question, k=k, filters=filters or None)
    # cross-year: an equal budget per year, then interleave so [1] is FY24's best, [2] FY25's best...
    per_year = [r.search(question, k=k, filters=base | {"fy": y}) for y in fys]
    hits: list[Hit] = []
    for row in zip(*per_year):
        hits.extend(row)
    for rank, h in enumerate(hits, start=1):
        h.rank = rank
    return hits


def _passage_block(hits: list[Hit]) -> str:
    parts = []
    for n, h in enumerate(hits, start=1):
        c = h.chunk
        pages = f"p.{c['page_start']}" if c["page_start"] == c["page_end"] else f"pp.{c['page_start']}-{c['page_end']}"
        text = c["text"][:MAX_PASSAGE_CHARS]
        parts.append(f"[{n}] {c['ticker']} {c['fy']} — {c['section']}, {pages}\n{text}")
    return "\n\n".join(parts)


# --- parsing the model's reply -----------------------------------------------------

_CITE = re.compile(r"(?:\[|【)\s*(\d+)\s*(?:\]|】)|passage\s+(\d+)", re.IGNORECASE)
# A stray letter/backtick standing in for ₹ before an Indian amount: "C 23,082 crore", "`45,588 crore", "H 416,661 crore".
_BAD_RUPEE = re.compile(r"(?<![A-Za-z0-9])[`CHIJKLD]\s?(?=\d[\d,]*(?:\.\d+)?\s*(?:crore|lakh|million|billion|cr\b|lakhs|crores))", re.IGNORECASE)


def scrub_rupee(text: str) -> str:
    return _BAD_RUPEE.sub("₹", text)
_UNIT_ALIASES = {"crores": "crore", "cr": "crore", "lakhs": "lakh", "lacs": "lakh", "lac": "lakh",
                 "mn": "million", "millions": "million", "bn": "billion", "billions": "billion",
                 "%": "percent", "pct": "percent", "nos": "count", "number": "count"}


def _norm_unit(u: str) -> str:
    u = (u or "").strip().lower().rstrip(".")
    return _UNIT_ALIASES.get(u, u)


def _to_float(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", "").replace("₹", "").replace("$", "").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def parse_reply(raw: str, n_passages: int) -> tuple[bool, str, list[Figure], list[int]]:
    """JSON → (found, answer, figures, cited passage numbers). Tolerant of
    fences and stray prose around the object."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[s.find("{"):]
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    data = json.loads(s[start:end + 1])
    found = bool(data.get("found", True))
    text = scrub_rupee(str(data.get("answer", "")).strip())
    figures: list[Figure] = []
    for f in data.get("figures") or []:
        value = _to_float(f.get("value"))
        if value is None:
            continue
        unit = _norm_unit(str(f.get("unit", "")))
        cur = str(f.get("currency", "")).upper().replace("RS", "INR").replace("₹", "INR") or ("INR" if unit in TO_CRORE else "")
        cit = f.get("citation")
        cit = int(cit) if isinstance(cit, (int, float, str)) and str(cit).isdigit() and 1 <= int(cit) <= n_passages else None
        fig = Figure(label=str(f.get("label", "")).strip(), value=value, unit=unit, currency=cur, citation=cit)
        if cur == "INR" and unit in TO_CRORE:
            fig.crore = to_crore(value, unit)
        figures.append(fig)
    cited = []
    for m in _CITE.finditer(text):
        n = int(m.group(1) or m.group(2))
        if 1 <= n <= n_passages and n not in cited:
            cited.append(n)
    # No [n] in the prose but the figures say where they came from: use that.
    if not cited:
        cited = [f.citation for f in figures if f.citation and f.citation not in cited]
        cited = list(dict.fromkeys(cited))
    # The model sometimes answers with the figure and still says found=false
    # when the unit differs from the one asked for. A figure IS a finding.
    if figures and not found:
        found = True
    text = text.replace("【", "[").replace("】", "]")
    return found, text, figures, cited


# --- the whole thing ---------------------------------------------------------------

def answer(question: str, ticker: str | None = None, fy: str | list[str] | None = None,
           k: int = DEFAULT_K, retriever: str = DEFAULT_RETRIEVER, model: str | None = None) -> Answer:
    t0 = time.time()
    hits = retrieve(question, ticker, fy, k=k, retriever=retriever)
    model = model or llm.model_name("model")
    if not hits:
        return Answer(question, False, "No passages matched the filters.", [], [], [], model, retriever, time.time() - t0)

    scope = " / ".join(x for x in [ticker or "", (", ".join(fy) if isinstance(fy, list) else fy) or ""] if x)
    user = (f"Question: {question}\n" + (f"Scope: {scope}\n" if scope else "") +
            f"\nPassages:\n\n{_passage_block(hits)}")
    raw = llm.chat([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
                   model=model, json_mode=True)
    try:
        found, text, figures, cited = parse_reply(raw, len(hits))
    except (ValueError, json.JSONDecodeError):
        found, text, figures, cited = False, f"The model's reply could not be parsed: {raw[:200]}", [], []

    def cite(n: int, h: Hit) -> Citation:
        c = h.chunk
        return Citation(n, c["ticker"], c["fy"], c.get("part", ""), c["section"],
                        c["page_start"], c["page_end"], c["chunk_id"])

    passages = [cite(n, h) for n, h in enumerate(hits, start=1)]
    citations = [passages[n - 1] for n in cited]
    return Answer(question, found, text, figures, citations, passages, model, retriever, time.time() - t0, raw)
