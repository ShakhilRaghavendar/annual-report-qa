"""
Tests for parse.py that need no PDFs: heading detection and section splitting
on synthetic page text. Run with:  pytest -q
"""

from arqa.parse import detect_heading, split_into_sections


def test_detects_mdna_heading_variants():
    assert detect_heading("Management Discussion and Analysis\nFY25 was a year of...") == "mdna"
    assert detect_heading("MANAGEMENT'S DISCUSSION & ANALYSIS") == "mdna"
    assert detect_heading("MD&A\nOverview") == "mdna"


def test_detects_directors_report_and_risk():
    assert detect_heading("Board's Report\nDear Members,") == "directors_report"
    assert detect_heading("Directors' Report") == "directors_report"
    assert detect_heading("Enterprise Risk Management\nOur framework...") == "risk_management"


def test_ignores_long_body_lines():
    # Same words, but inside a long paragraph line -> not a heading.
    body = "In this section of the management discussion and analysis we describe " * 3
    assert detect_heading(body) is None


def test_ignores_headings_deep_in_page():
    # Heading-like line appears after 15 non-empty lines -> treated as body text.
    filler = "\n".join(f"line {i}" for i in range(20))
    assert detect_heading(filler + "\nRisk Management") is None


def test_split_assigns_pages_and_does_not_lose_text():
    pages = [
        "Cover page",                                   # p1 -> front_matter
        "Chairman's Message\nDear Shareholders, ...",   # p2 -> chairman_letter
        "continued letter text",                        # p3 -> chairman_letter
        "Management Discussion and Analysis\nIndia...", # p4 -> mdna
        "Management Discussion and Analysis\nmore",     # p5 -> same section (running header)
        "Board's Report\nYour Directors present...",    # p6 -> directors_report
    ]
    sections = split_into_sections(pages, company="Test Co", ticker="TEST", fy="FY25")
    keys = [(s.section_key, s.page_start, s.page_end) for s in sections]
    assert keys == [
        ("front_matter", 1, 1),
        ("chairman_letter", 2, 3),
        ("mdna", 4, 5),
        ("directors_report", 6, 6),
    ]
    # Nothing dropped: every page's text appears in exactly one section.
    joined = "\n".join(s.text for s in sections)
    for p in pages:
        assert p.splitlines()[0] in joined
