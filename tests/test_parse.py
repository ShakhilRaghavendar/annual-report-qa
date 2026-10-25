"""
Tests for parse.py that need no PDFs: heading detection, boilerplate
filtering, section splitting and the merge pass, on synthetic page text.
Each test documents a real failure seen on the Nifty 50 reports.
Run with:  pytest -q
"""

from arqa.parse import (
    detect_heading,
    find_boilerplate,
    heading_candidates,
    merge_flapping,
    parse_stem,
    split_into_sections,
    Section,
)


# --- heading variants seen in the wild --------------------------------------------
def test_mdna_variants():
    assert detect_heading("Management Discussion and Analysis\nFY25 was...") == "mdna"
    assert detect_heading("MANAGEMENT'S DISCUSSION & ANALYSIS") == "mdna"
    assert detect_heading("Management Discussion and Analysis — Business Overview") == "mdna"  # Reliance
    assert detect_heading("MD&A\nOverview") == "mdna"


def test_directors_report_variants():
    assert detect_heading("DIRECTORS’ REPORT\nDear Shareholders,") == "directors_report"  # HDFC, curly apostrophe
    assert detect_heading("Board's report\nDear members,") == "directors_report"          # Infosys
    assert detect_heading("Report of Board of Directors and\nManagement Discussion and Analysis") == "directors_report"  # HUL


def test_chairman_variants():
    assert detect_heading("Chairman's Message\nDear Shareholders") == "chairman_letter"
    assert detect_heading("Chairman and Managing Director’s Statement") == "chairman_letter"  # Reliance
    assert detect_heading("Chairman’s\nStatement\nDear Shareholders") == "chairman_letter"    # L&T, two lines


def test_dear_shareholders_alone_is_not_a_heading():
    # v0 bug: the Directors' Report opens "Dear Shareholders," and was labelled as the letter.
    assert detect_heading("Dear Shareholders,\nYour Directors present the 31st Annual Report") is None


def test_specific_heading_beats_generic_on_same_page():
    page = "DIRECTORS’ REPORT\nDear Shareholders,\nYour Directors take pleasure..."
    assert detect_heading(page) == "directors_report"


def test_closers_end_a_section():
    assert detect_heading("Corporate Governance Report\nPhilosophy...") == "other"
    assert detect_heading("Business Responsibility and Sustainability Report") == "other"
    assert detect_heading("Standalone Financial Statements") == "other"
    assert detect_heading("Notice of the 31st Annual General Meeting") == "other"


def test_toc_rows_and_long_lines_ignored():
    assert detect_heading("Chairman's Message ........................ 08") is None
    assert detect_heading("Risk Management   42") is None
    body = "In this section of the management discussion and analysis we describe " * 3
    assert detect_heading(body) is None


def test_running_header_does_not_reopen_but_subheading_does():
    page = "DIRECTORS’ REPORT\nManagement Discussion and Analysis\nMacroeconomic developments..."
    assert detect_heading(page, current_key="directors_report") == "mdna"   # HDFC p209
    assert detect_heading("DIRECTORS’ REPORT\nbody text", current_key="directors_report") is None


# --- boilerplate (nav bands) -------------------------------------------------------
def test_nav_band_is_treated_as_boilerplate():
    nav = "Management Discussion and Analysis"
    pages = [f"{nav}\npage {i} body text" for i in range(10)]
    bp = find_boilerplate(pages)
    assert nav in bp
    assert heading_candidates(pages[3], bp) == []


# --- splitting + merging ------------------------------------------------------------
def test_split_assigns_pages_and_does_not_lose_text():
    pages = [
        "Cover page",
        "Chairman's Message\nDear Shareholders, ...",
        "continued letter text",
        "Management Discussion and Analysis\nIndia...",
        "Management Discussion and Analysis\nmore",       # running header: same section
        "Board's Report\nYour Directors present...",
        "Corporate Governance Report\n...",                # closer -> other
        "Consolidated Balance Sheet\n...",
    ]
    sections = split_into_sections(pages, company="Test Co", ticker="TEST", fy="FY25")
    keys = [(s.section_key, s.page_start, s.page_end) for s in sections]
    assert keys == [
        ("front_matter", 1, 1),
        ("chairman_letter", 2, 3),
        ("mdna", 4, 5),
        ("directors_report", 6, 6),
        ("other", 7, 7),
        ("financial_statements", 8, 8),
    ]
    joined = "\n".join(s.text for s in sections)
    for p in pages:
        assert p.splitlines()[0] in joined


def _sec(key, start, end):
    return Section("C", "T", "FY25", "", key, key, start, end, f"{key}:{start}-{end}")


def test_merge_flapping_absorbs_short_sandwiched_sections():
    secs = [_sec("directors_report", 55, 55), _sec("mdna", 56, 56), _sec("directors_report", 57, 57),
            _sec("mdna", 58, 58), _sec("directors_report", 59, 59), _sec("mdna", 60, 65)]
    out = merge_flapping(secs)
    assert [(s.section_key, s.page_start, s.page_end) for s in out] == [
        ("directors_report", 55, 59), ("mdna", 60, 65)]
    assert "mdna:56-56" in out[0].text   # text is kept, just relabelled


def test_merge_never_dissolves_a_target_section_into_other():
    secs = [_sec("other", 33, 34), _sec("risk_management", 35, 35), _sec("other", 36, 49)]
    assert [s.section_key for s in merge_flapping(secs)] == ["other", "risk_management", "other"]


def test_parse_stem_handles_parts():
    assert parse_stem("INFY_FY25") == ("INFY", "FY25", "")
    assert parse_stem("ICICIBANK_FY25_fs") == ("ICICIBANK", "FY25", "fs")
