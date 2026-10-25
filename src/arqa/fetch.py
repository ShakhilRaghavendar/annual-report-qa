"""
fetch.py — download the annual-report PDFs listed in data/sources.csv.

Why a CSV and not a crawler: there is no EDGAR-style API for Indian filings.
Each company publishes its report on its own investor-relations page, with
its own URL scheme. Twenty hand-checked URLs in a CSV is simpler, faster and
more honest than a scraper that breaks every quarter.

Run:
    python -m arqa.fetch                 # download everything not yet present
    python -m arqa.fetch --force         # re-download even if the file exists
    python -m arqa.fetch --only INFY     # one ticker

Output:
    data/raw/<TICKER>_<FY>.pdf   e.g. data/raw/INFY_FY25.pdf
    A summary table at the end: which downloads succeeded, failed, or were skipped.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from tqdm import tqdm

# --- Paths -----------------------------------------------------------------
# Path(__file__) is this file; .parents[2] walks up src/arqa -> src -> repo root.
# Resolving paths from the file (not the current working directory) means the
# script works no matter which folder you run it from.
ROOT = Path(__file__).resolve().parents[2]
SOURCES_CSV = ROOT / "data" / "sources.csv"
RAW_DIR = ROOT / "data" / "raw"

# Some IR sites refuse requests with no User-Agent (they assume a bot).
# A plain browser-like header is enough; nothing sneaky.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) annual-report-qa/0.1 (personal research project)",
    "Accept": "application/pdf,*/*",
}


@dataclass
class Source:
    """One row of sources.csv."""
    company: str
    ticker: str
    fy: str
    url: str
    part: str = ""   # "" for the main report; e.g. "fs" when a company splits
                     # its report into several PDFs (ICICI Bank does)

    @property
    def filename(self) -> str:
        suffix = f"_{self.part}" if self.part else ""
        return f"{self.ticker}_{self.fy}{suffix}.pdf"

    @property
    def path(self) -> Path:
        return RAW_DIR / self.filename


def load_sources(csv_path: Path = SOURCES_CSV) -> list[Source]:
    """Read sources.csv into a list of Source objects. Skips rows with no URL."""
    sources: list[Source] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("url") or "").strip()
            if not url or url.upper() == "NOT_FOUND":
                continue
            sources.append(
                Source(
                    company=row["company"].strip(),
                    ticker=row["ticker"].strip().upper(),
                    fy=row["fy"].strip().upper(),
                    url=url,
                    part=(row.get("part") or "").strip().lower(),
                )
            )
    return sources


def download(src: Source, force: bool = False, timeout: int = 60) -> str:
    """
    Download one PDF. Returns a short status string:
      "ok", "skipped (exists)", or "failed: <reason>".

    We stream to disk in chunks so a 50 MB report doesn't sit in memory, and we
    check the first bytes are '%PDF' — a surprising number of 'PDF links' return
    an HTML error page with a 200 status.
    """
    if src.path.exists() and not force:
        return "skipped (exists)"

    try:
        with requests.get(src.url, headers=HEADERS, stream=True, timeout=timeout, allow_redirects=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0)) or None
            tmp = src.path.with_suffix(".part")
            first_bytes = b""
            with tmp.open("wb") as out, tqdm(
                total=total, unit="B", unit_scale=True, desc=src.filename, leave=False
            ) as bar:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    if not chunk:
                        continue
                    if not first_bytes:
                        first_bytes = chunk[:8]
                    out.write(chunk)
                    bar.update(len(chunk))

        if not first_bytes.startswith(b"%PDF"):
            tmp.unlink(missing_ok=True)
            return "failed: response was not a PDF (probably an HTML page)"

        tmp.rename(src.path)
        return "ok"

    except requests.RequestException as e:
        # Covers timeouts, DNS errors, 403/404 etc. Keep the message short.
        return f"failed: {type(e).__name__}: {str(e)[:80]}"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    force = "--force" in argv
    only = None
    if "--only" in argv:
        only = argv[argv.index("--only") + 1].upper()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    if only:
        sources = [s for s in sources if s.ticker == only]

    if not sources:
        print(f"No sources to fetch. Check {SOURCES_CSV}")
        return 1

    results: list[tuple[Source, str]] = []
    for src in sources:
        status = download(src, force=force)
        results.append((src, status))
        print(f"  {src.filename:<22} {status}")

    # Summary
    ok = sum(1 for _, s in results if s == "ok")
    skipped = sum(1 for _, s in results if s.startswith("skipped"))
    failed = [(src, s) for src, s in results if s.startswith("failed")]
    print(f"\nDone. {ok} downloaded, {skipped} already present, {len(failed)} failed.")
    if failed:
        print("\nFailed (fix the URL in data/sources.csv, or download by hand into data/raw/):")
        for src, s in failed:
            print(f"  {src.filename:<22} {s}")
            print(f"      {src.url}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
