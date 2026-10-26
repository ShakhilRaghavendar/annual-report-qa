"""
parse.py — turn an annual-report PDF into a list of sections with page numbers.

This is the hard, unglamorous part of the project. Indian annual reports are
designed documents: multi-column layouts, headings that are images, chapter
names that differ by company ("Management Discussion and Analysis" is a
chapter at Infosys, a sub-heading inside the Board's Report at HUL, and
"Management Discussion and Analysis — Business Overview" at Reliance).

v1 strategy (v0 lessons are in the README's "parsing notes"):
  1. Extract text page by page with PyMuPDF, with sort=True so the page header
     (where chapter names live) comes out first, not wherever the PDF's internal
     block order happens to put it.
  2. Scan the first N non-empty lines of each page for a heading we recognise.
     Two kinds: TARGET sections we want to keep, and CLOSER headings (governance
     report, BRSR, standalone statements, AGM notice) that we don't want but
     must detect, otherwise the previous section swallows them.
  3. When several patterns match on one page, the most specific wins. v0 let a
     generic "Dear Shareholders" pattern beat "DIRECTORS' REPORT" — that is why
     HDFC's Directors' Report was labelled as the Chairman's letter.
  4. A heading opens a new section; a repeated heading (running header) does not.

Run:
    python -m arqa.parse                       # parse everything in data/raw
    python -m arqa.parse --only INFY_FY25      # one file
    python -m arqa.parse --report              # print the per-file section table only

Output:
    data/processed/<TICKER>_<FY>.jsonl   one JSON object per section:
        {"company","ticker","fy","part","section","section_key","page_start","page_end","text"}
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PAGE_SEP = "\f"   # page boundary inside a section's text

# --- Headings ------------------------------------------------------------------
# Each entry: (section_key, priority, regex). Higher priority wins when more than
# one pattern matches on the same page. Keep patterns anchored at the start of
# the line (^) so table-of-contents rows like "58  Board's report" don't fire.
#
# Apostrophes: PDFs use ' (U+0027) and ’ (U+2019) interchangeably — hence ['’].
APOS = "['’]"

HEADINGS: list[tuple[str, int, str]] = [
    # --- target sections --------------------------------------------------
    ("directors_report", 90, rf"^(board|directors){APOS}?s?\s+report\b"),
    ("directors_report", 90, r"^report\s+of\s+(the\s+)?board\s+of\s+directors"),   # HUL
    ("directors_report", 90, r"^report\s+of\s+the\s+(board|directors)\b"),

    ("mdna", 85, rf"^management{APOS}?s?\s+discussion\s+(and|&)\s+analysis"),
    ("mdna", 85, r"^md\s*&\s*a\b"),

    ("financial_statements", 80, r"^consolidated\s+(financial\s+statements|balance\s+sheet|statement\s+of\s+profit)"),
    ("financial_statements", 80, rf"^(independent\s+)?auditor{APOS}?s?\s+report\s+on\s+(the\s+)?consolidated"),
    ("financial_statements", 80, r"^notes\s+(forming\s+part\s+of|to)\s+(the\s+)?consolidated"),

    ("risk_management", 70, r"^(enterprise\s+|integrated\s+)?risk\s+management\b"),
    ("risk_management", 70, r"^risks?\s+(and|&)\s+(opportunities|mitigation|concerns)"),
    ("risk_management", 70, r"^(key|principal|material)\s+risks?\b"),

    ("chairman_letter", 60, rf"^(chairman|chairperson|ceo|cmd|md|managing\s+director)(\s*(and|&)\s*(managing\s+director|ceo|md))?{APOS}?s?\s+(message|letter|statement|address|review|communiqu)"),
    ("chairman_letter", 60, r"^(message|letter|statement)\s+from\s+(the\s+)?(chairman|chairperson|ceo|managing\s+director)"),
    ("chairman_letter", 60, r"^from\s+the\s+(chairman|ceo)"),

    # --- closers: chapters we don't keep, but must recognise so they END the
    #     previous section instead of being absorbed into it -----------------
    ("other", 50, r"^(report\s+on\s+)?corporate\s+governance(\s+report)?\b"),
    ("other", 50, r"^business\s+responsibility\s+(and|&)\s+sustainability"),
    ("other", 50, r"^brsr\b"),
    ("other", 50, r"^standalone\s+(financial\s+statements|balance\s+sheet|statement\s+of\s+profit)"),
    ("other", 50, rf"^(independent\s+)?auditor{APOS}?s?\s+report\s+on\s+(the\s+)?standalone"),
    ("other", 50, r"^notice\s+(of|is\s+hereby|convening)\b"),
    ("other", 50, r"^notice$"),
    ("other", 50, r"^(secretarial\s+audit|dividend\s+distribution\s+policy|nomination\s+and\s+remuneration)"),
    ("other", 50, r"^(ten|10|five|5)[-\s]year\s+(financial\s+)?(highlights|summary)"),
    ("other", 50, r"^(form\s+aoc|form\s+mgt|form\s+mr)[-\s]?\d"),
    # L&T's MD&A region is a run of chapters: "Overall Financial Review",
    # "Infrastructure Projects Segment", "IT & Technology Services Segment"...
    # None are sections we keep, but each must close the one before it.
    ("other", 40, r"^(overall\s+)?financial\s+review\b"),
    ("other", 40, r"^[a-z&,\s]{3,50}\s+segment$"),
    ("other", 40, r"^(integrated\s+report|value\s+creation|our\s+capitals|(financial|human|intellectual|social|natural|manufactured)\s+capital)$"),
]

_PATTERNS: list[tuple[str, int, re.Pattern[str]]] = [
    (key, prio, re.compile(pat, re.IGNORECASE)) for key, prio, pat in HEADINGS
]


def _squash_pattern(pat: str) -> str:
    """Derive a pattern that matches the same heading with ALL whitespace removed.
    TCS's PDF font encoding scatters spaces inside words ('Man ag ement
    Discussion an d Anal ysis'); matching a space-stripped copy of the line
    against a space-stripped pattern sidesteps that entirely."""
    return (
        pat.replace(r"[-\s]?", "-?").replace(r"[-\s]", "-?")
           .replace(r"\s+", "").replace(r"\s*", "").replace(r"\b", "")
    )


_SQUASHED_PATTERNS: list[tuple[str, int, re.Pattern[str]]] = [
    (key, prio, re.compile(_squash_pattern(pat), re.IGNORECASE)) for key, prio, pat in HEADINGS
]
_WS = re.compile(r"\s+")

# Headings sit at the top of a page. We look a little deeper than v0 (15 → 20
# lines) because some designed pages carry a logo line, a page number and a
# running "Integrated Annual Report 2024-25" label above the chapter name.
TOP_LINES = 20
# A heading is a SHORT line; body text that happens to start with "risk
# management" mid-sentence should not open a new section.
MAX_HEADING_LEN = 90

SECTION_LABELS = {
    "front_matter": "Front matter",
    "chairman_letter": "Chairman / CEO letter",
    "mdna": "Management Discussion & Analysis",
    "directors_report": "Directors' Report",
    "risk_management": "Risk Management",
    "financial_statements": "Consolidated Financial Statements",
    "other": "Other",
}
TARGET_KEYS = ["chairman_letter", "mdna", "directors_report", "risk_management", "financial_statements"]


@dataclass
class Section:
    company: str
    ticker: str
    fy: str
    part: str           # "" for the main report; e.g. "fs" for ICICI's separate financial-statements PDF
    section: str        # human label
    section_key: str    # stable key
    page_start: int     # 1-based, inclusive
    page_end: int       # 1-based, inclusive
    text: str


# --- Text extraction ---------------------------------------------------------------
def extract_pages(pdf_path: Path) -> list[str]:
    """Return a list of page texts; index 0 is page 1. Imported lazily so the
    pure-logic functions below can be unit-tested without PyMuPDF installed."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    # sort=True orders blocks top-to-bottom, left-to-right. Without it, the
    # running header can come out AFTER the body text and heading detection
    # on the "top lines" misses it (the HDFC Directors' Report problem).
    pages = [page.get_text("text", sort=True) for page in doc]
    doc.close()
    return pages


# --- Heading detection -------------------------------------------------------------
# Table-of-contents rows look like headings but aren't: "Chairman's Message ....... 08"
_TOC_ROW = re.compile(r"\.{3,}\s*\d*\s*$")
# Running headers often carry the page number: "79    Management Discussion and
# Analysis" or "Management Discussion and Analysis     80" (TCS). Strip it before
# matching rather than discarding the line.
_EDGE_PAGE_NO = re.compile(r"^\d{1,3}\s+|\s+\d{1,3}$")


def clean_heading_text(ln: str) -> str:
    return _EDGE_PAGE_NO.sub("", ln).strip()
# ...and some contents pages put the page number FIRST ("67  Board's Report", TCS).
# A page where many top lines start with a small number is a contents page.
_LEADING_PAGE_NO = re.compile(r"^\d{1,3}\s+\S")
TOC_PAGE_MIN_ROWS = 5


def is_contents_page(lines: list[str]) -> bool:
    numbered = sum(1 for ln in lines if _LEADING_PAGE_NO.match(ln))
    titled = any(re.match(r"^(contents?|what'?s inside|inside this report|index)\b", ln, re.I) for ln in lines[:4])
    return numbered >= TOC_PAGE_MIN_ROWS or (titled and numbered >= 2)
# A line that recurs at the top of this share of pages is a navigation band or
# running label ("Integrated Annual Report 2024-25"), not a chapter heading.
BOILERPLATE_SHARE = 0.25


# Invisible characters PDFs leave behind: zero-width spaces/joiners, soft hyphens,
# BOMs, bidi marks. HUL pads 'Consolidated Balance Sheet' with ~70 of them, which
# pushed the line past MAX_HEADING_LEN and hid the heading.
_INVISIBLE = re.compile(r"[​-‏ - ⁠﻿­]")
_MULTI_WS = re.compile(r"[ \t ]+")


def normalise_line(ln: str) -> str:
    ln = _INVISIBLE.sub("", ln)
    return _MULTI_WS.sub(" ", ln).strip()


def top_lines(page_text: str) -> list[str]:
    """The first TOP_LINES non-empty lines of a page, normalised."""
    out = []
    for raw in page_text.splitlines():
        ln = normalise_line(raw)
        if ln:
            out.append(ln)
            if len(out) == TOP_LINES:
                break
    return out


def find_boilerplate(pages: list[str]) -> set[str]:
    """Lines that appear in the top region of >= BOILERPLATE_SHARE of pages.
    L&T and HUL print a nav strip ('Corporate Overview | Management Discussion
    and Analysis | ...') on every page; without this filter every page looks
    like the start of the MD&A.

    A line that IS a target heading is never boilerplate, however often it
    repeats: ICICI's Board's Report PDF carries 'BOARD'S REPORT' on all 49
    pages, and that running header is exactly what tells us what the file is."""
    if len(pages) < 8:
        return set()
    counts: dict[str, int] = {}
    for p in pages:
        for ln in set(top_lines(p)):
            if len(ln) <= MAX_HEADING_LEN:
                counts[ln] = counts.get(ln, 0) + 1
    threshold = max(4, int(len(pages) * BOILERPLATE_SHARE))
    out = set()
    for ln, c in counts.items():
        if c < threshold:
            continue
        hit = _match_heading(ln)
        if hit and hit[0] in TARGET_KEYS:
            continue
        out.add(ln)
    return out


CONTENTS_PAGES_WITHIN = 15   # a contents page lives at the front of the report


def heading_candidates(page_text: str, boilerplate: set[str] = frozenset(), page_no: int = 1) -> list[tuple[int, int, str]]:
    """
    All headings found in the top lines of a page, as (priority, -line_index, key),
    best first. Adjacent short lines are also tried joined ("Chairman's" +
    "Statement" at L&T), and TOC rows / boilerplate lines are skipped.
    The contents-page check only applies to the front of the report: a balance
    sheet also has many lines starting with a number (note numbers) — HUL's
    consolidated statements were skipped as a 'contents page' before this.
    """
    lines = top_lines(page_text)
    if page_no <= CONTENTS_PAGES_WITHIN and is_contents_page(lines):
        return []
    texts: list[tuple[int, str]] = []
    usable = [None if (ln in boilerplate or len(ln) > MAX_HEADING_LEN or _TOC_ROW.search(ln))
              else clean_heading_text(ln) for ln in lines]
    for idx, ln in enumerate(usable):
        if not ln:
            continue
        texts.append((idx, ln))
        # Titles set on two or three lines: "Chairman's / Statement" (L&T),
        # "Management / Discussion and / Analysis" (TCS).
        joined = ln
        for extra in usable[idx + 1: idx + 3]:
            if not extra:
                break
            joined = f"{joined} {extra}"
            if len(joined) > MAX_HEADING_LEN:
                break
            texts.append((idx, joined))

    found: list[tuple[int, int, str]] = []
    for idx, text in texts:
        hit = _match_heading(text)
        if hit:
            found.append((hit[1], -idx, hit[0]))
    found.sort(reverse=True)
    return found


def _match_heading(text: str) -> tuple[str, int] | None:
    """(key, priority) for the first pattern that matches `text`, trying the
    normal patterns first and then the whitespace-stripped ones."""
    for key, prio, pat in _PATTERNS:
        if pat.search(text):
            return key, prio
    squashed = _WS.sub("", text)
    for key, prio, pat in _SQUASHED_PATTERNS:
        if pat.search(squashed):
            return key, prio
    return None


def detect_heading(page_text: str, current_key: str | None = None, boilerplate: set[str] = frozenset(), page_no: int = 1) -> str | None:
    """
    Return the section_key this page should open, or None to stay in the
    current section. The best heading that is NOT the current section wins —
    so a chapter's running header is ignored, but a sub-chapter heading below
    it (HDFC's MD&A inside the Directors' Report) is honoured.
    """
    for _prio, _negidx, key in heading_candidates(page_text, boilerplate, page_no):
        if key != current_key:
            return key
    return None


def split_into_sections(pages: list[str], company: str, ticker: str, fy: str, part: str = "") -> list[Section]:
    """Walk the pages, opening a new section whenever a different heading is detected."""
    boilerplate = find_boilerplate(pages)
    sections: list[Section] = []
    current_key = "front_matter"
    current_start = 1
    buffer: list[str] = []

    def flush(end_page: int) -> None:
        # Pages are joined with a form feed (\f) so downstream code (chunk.py)
        # can recover page numbers: page_start + number of \f before a chunk.
        text = PAGE_SEP.join(p.strip() for p in buffer).strip()
        if text:
            sections.append(
                Section(
                    company=company, ticker=ticker, fy=fy, part=part,
                    section=SECTION_LABELS.get(current_key, current_key),
                    section_key=current_key,
                    page_start=current_start, page_end=end_page, text=text,
                )
            )

    for i, page_text in enumerate(pages, start=1):
        key = detect_heading(page_text, current_key, boilerplate, page_no=i)
        if key and key != current_key:
            flush(end_page=i - 1)
            current_key, current_start, buffer = key, i, []
        buffer.append(page_text)

    flush(end_page=len(pages))
    return merge_flapping(sections)


def merge_flapping(sections: list[Section], max_pages: int = 2) -> list[Section]:
    """
    Top-of-page heuristics flap when a chapter's running header and a
    sub-heading alternate (HUL: Board's Report / MD&A / Board's Report / MD&A,
    one page each). A short section (<= max_pages) sandwiched between two
    sections of the same key is absorbed into them — unless that would
    dissolve a target section into 'other', which we never do.
    """
    changed = True
    while changed and len(sections) >= 3:
        changed = False
        for i in range(1, len(sections) - 1):
            prev, cur, nxt = sections[i - 1], sections[i], sections[i + 1]
            short = (cur.page_end - cur.page_start + 1) <= max_pages
            same_neighbours = prev.section_key == nxt.section_key and prev.section_key != cur.section_key
            protect = cur.section_key in TARGET_KEYS and prev.section_key == "other"
            if short and same_neighbours and not protect:
                merged = Section(
                    company=prev.company, ticker=prev.ticker, fy=prev.fy, part=prev.part,
                    section=prev.section, section_key=prev.section_key,
                    page_start=prev.page_start, page_end=nxt.page_end,
                    text=PAGE_SEP.join([prev.text, cur.text, nxt.text]),
                )
                sections[i - 1:i + 2] = [merged]
                changed = True
                break
    return sections


# --- File-level helpers ------------------------------------------------------------
def parse_stem(stem: str) -> tuple[str, str, str]:
    """'INFY_FY25' -> ('INFY','FY25',''); 'ICICIBANK_FY25_fs' -> ('ICICIBANK','FY25','fs')."""
    bits = stem.split("_")
    ticker = bits[0]
    fy = bits[1] if len(bits) > 1 else ""
    part = "_".join(bits[2:]) if len(bits) > 2 else ""
    return ticker, fy, part


def parse_file(pdf_path: Path, company: str | None = None) -> list[Section]:
    ticker, fy, part = parse_stem(pdf_path.stem)
    pages = extract_pages(pdf_path)
    return split_into_sections(pages, company=company or ticker, ticker=ticker, fy=fy, part=part)


def write_jsonl(sections: list[Section], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")


def report(sections: list[Section]) -> str:
    """A compact table so you can eyeball a parse. 'Other' rows are collapsed to
    one line per run because they are the chapters we deliberately drop."""
    rows = [f"  {'section':<36} {'pages':>9} {'chars':>9}"]
    for s in sections:
        pages = f"{s.page_start}-{s.page_end}"
        rows.append(f"  {s.section:<36} {pages:>9} {len(s.text):>9,}")
    found = {s.section_key for s in sections}
    missing = [SECTION_LABELS[k] for k in TARGET_KEYS if k not in found]
    if missing:
        rows.append(f"  MISSING: {', '.join(missing)}")
    return "\n".join(rows)


def peek(stem: str, page_numbers: list[int]) -> None:
    """Debug helper: show the top lines of given pages exactly as the parser sees
    them, plus the heading candidates. Usage: python -m arqa.parse --peek HDFCBANK_FY25 203 209"""
    pdf = RAW_DIR / f"{stem}.pdf"
    pages = extract_pages(pdf)
    bp = find_boilerplate(pages)
    print(f"{pdf.name}: {len(pages)} pages; boilerplate lines: {sorted(bp)[:6]}")
    for n in page_numbers:
        text = pages[n - 1]
        print(f"\n--- page {n} ---")
        for i, ln in enumerate(top_lines(text)):
            flag = " [boilerplate]" if ln in bp else ""
            print(f"  {i:>2}: {ln[:100]}{flag}")
        print(f"  candidates: {heading_candidates(text, bp, page_no=n)[:5]}")


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252, which cannot print ₹ or the "ﬁ"
    # ligature that PDFs are full of. Print UTF-8 and never crash on a glyph.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    argv = sys.argv[1:] if argv is None else argv
    if "--peek" in argv:
        i = argv.index("--peek")
        peek(argv[i + 1], [int(x) for x in argv[i + 2:]])
        return 0
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    report_only = "--report" in argv

    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if only:
        pdfs = [p for p in pdfs if p.stem.upper() == only.upper()]
    if not pdfs:
        print(f"No PDFs found in {RAW_DIR}. Run `python -m arqa.fetch` first.")
        return 1

    for pdf in pdfs:
        print(f"\n{pdf.name}")
        try:
            sections = parse_file(pdf)
        except Exception as e:  # keep going; one bad PDF shouldn't stop the batch
            print(f"  ERROR: {type(e).__name__}: {e}")
            continue
        print(report(sections))
        if not report_only:
            write_jsonl(sections, PROCESSED_DIR / f"{pdf.stem}.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
