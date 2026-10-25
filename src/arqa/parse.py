"""
parse.py — turn an annual-report PDF into a list of sections with page numbers.

This is the hard, unglamorous part of the project. Indian annual reports are
designed documents: multi-column layouts, headings that are images, chapter
names that differ by company ("Management Discussion and Analysis" is a
chapter at Infosys and a sub-heading inside the Directors' Report elsewhere).

v0 strategy (deliberately simple; we tune it per company after seeing real PDFs):
  1. Extract text page by page with PyMuPDF, keeping the page number.
  2. Scan each page for lines that look like one of our TARGET section headings
     (regex match, case-insensitive, short line, mostly letters).
  3. A heading match opens a new section; every following page belongs to it
     until the next heading match.
  4. Pages before the first match go to a "front_matter" bucket; anything we
     couldn't classify stays as "other" so nothing is silently lost.

Run:
    python -m arqa.parse                       # parse everything in data/raw
    python -m arqa.parse --only INFY_FY25      # one file
    python -m arqa.parse --report              # print the per-file section table only

Output:
    data/processed/<TICKER>_<FY>.jsonl   one JSON object per section:
        {"company","ticker","fy","section","section_key","page_start","page_end","text"}
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# --- The sections we care about ------------------------------------------------
# key -> list of regex patterns that identify the heading line.
# Order matters only for the report; matching is independent.
# Keep patterns loose: "Management Discussion & Analysis", "Management's
# Discussion and Analysis", "MD&A" should all hit the same key.
TARGET_SECTIONS: dict[str, list[str]] = {
    "chairman_letter": [
        r"^(chairman|chairperson|ceo|md\s*&\s*ceo|managing director)['’]?s?\s+(message|letter|statement|address|communiqu[eé])",
        r"^(message|letter)\s+from\s+the\s+(chairman|ceo|managing director)",
        r"^dear\s+(share|stake)holders",
    ],
    "mdna": [
        r"^management['’]?s?\s+discussion\s+(and|&)\s+analysis",
        r"^md\s*&\s*a\b",
    ],
    "directors_report": [
        r"^(board['’]?s?|directors['’]?)\s+report",
        r"^report\s+of\s+the\s+(board|directors)",
    ],
    "risk_management": [
        r"^(enterprise\s+)?risk\s+management",
        r"^risks?\s+(and|&)\s+(opportunities|mitigation|concerns)",
        r"^(key|principal)\s+risks?",
    ],
    "financial_statements": [
        r"^consolidated\s+(financial\s+statements|balance\s+sheet)",
        r"^(independent\s+)?auditor['’]?s?\s+report\s+on\s+(the\s+)?consolidated",
        r"^notes\s+(forming\s+part\s+of|to)\s+(the\s+)?consolidated",
    ],
}

# Compile once. Each entry: (section_key, compiled_regex)
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (key, re.compile(p, re.IGNORECASE)) for key, pats in TARGET_SECTIONS.items() for p in pats
]

# A heading is a SHORT line. Body text that happens to start with "risk management"
# mid-paragraph should not open a new section. 90 chars is generous.
MAX_HEADING_LEN = 90


@dataclass
class Section:
    company: str
    ticker: str
    fy: str
    section: str        # human label, e.g. "Management Discussion & Analysis"
    section_key: str    # stable key, e.g. "mdna"
    page_start: int     # 1-based, inclusive
    page_end: int       # 1-based, inclusive
    text: str


SECTION_LABELS = {
    "front_matter": "Front matter",
    "chairman_letter": "Chairman / CEO letter",
    "mdna": "Management Discussion & Analysis",
    "directors_report": "Directors' Report",
    "risk_management": "Risk Management",
    "financial_statements": "Consolidated Financial Statements",
    "other": "Other",
}


def extract_pages(pdf_path: Path) -> list[str]:
    """Return a list of page texts; index 0 is page 1."""
    doc = fitz.open(pdf_path)
    pages: list[str] = []
    for page in doc:
        # "text" mode gives reading-order text; good enough for v0.
        # Multi-column layouts can interleave columns — we'll revisit with
        # page.get_text("blocks") if it bites us.
        pages.append(page.get_text("text"))
    doc.close()
    return pages


def detect_heading(page_text: str) -> str | None:
    """
    Look at the first ~15 non-empty lines of a page for a target heading.
    Headings sit at the top of a page in nearly every annual report, so we don't
    scan the whole page — that would catch running headers and cross-references.
    Returns the section_key or None.
    """
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    for ln in lines[:15]:
        if len(ln) > MAX_HEADING_LEN:
            continue
        for key, pat in _PATTERNS:
            if pat.search(ln):
                return key
    return None


def split_into_sections(pages: list[str], company: str, ticker: str, fy: str) -> list[Section]:
    """Walk the pages, opening a new section whenever a heading is detected."""
    sections: list[Section] = []
    current_key = "front_matter"
    current_start = 1
    buffer: list[str] = []

    def flush(end_page: int) -> None:
        text = "\n".join(buffer).strip()
        if text:
            sections.append(
                Section(
                    company=company, ticker=ticker, fy=fy,
                    section=SECTION_LABELS.get(current_key, current_key),
                    section_key=current_key,
                    page_start=current_start, page_end=end_page, text=text,
                )
            )

    for i, page_text in enumerate(pages, start=1):
        key = detect_heading(page_text)
        # Open a new section only if the heading differs from the current one;
        # running headers repeat the chapter name on every page.
        if key and key != current_key:
            flush(end_page=i - 1)
            current_key, current_start, buffer = key, i, []
        buffer.append(page_text)

    flush(end_page=len(pages))
    return sections


def parse_file(pdf_path: Path, company: str | None = None) -> list[Section]:
    """Parse one PDF named <TICKER>_<FY>.pdf into sections."""
    stem = pdf_path.stem                      # e.g. "INFY_FY25"
    ticker, _, fy = stem.partition("_")
    company = company or ticker               # sources.csv has the nice name; fine for v0
    pages = extract_pages(pdf_path)
    return split_into_sections(pages, company=company, ticker=ticker, fy=fy)


def write_jsonl(sections: list[Section], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")


def report(sections: list[Section]) -> str:
    """A compact table: section, pages, characters — so you can eyeball a parse."""
    rows = [f"  {'section':<36} {'pages':>9} {'chars':>9}"]
    for s in sections:
        pages = f"{s.page_start}-{s.page_end}"
        rows.append(f"  {s.section:<36} {pages:>9} {len(s.text):>9,}")
    found = {s.section_key for s in sections}
    missing = [SECTION_LABELS[k] for k in TARGET_SECTIONS if k not in found]
    if missing:
        rows.append(f"  MISSING: {', '.join(missing)}")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
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
