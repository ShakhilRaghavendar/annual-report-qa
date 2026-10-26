from arqa.chunk import chunk_section, paragraphs_with_pages
from arqa.parse import PAGE_SEP


def _section(pages: list[str], first_page: int = 10) -> dict:
    return {"company": "Test", "ticker": "TEST", "fy": "FY25", "part": "",
            "section": "MD&A", "section_key": "mdna",
            "page_start": first_page, "page_end": first_page + len(pages) - 1,
            "text": PAGE_SEP.join(pages)}


def test_paragraphs_carry_their_page_number():
    pages = ["para one\n\npara two", "para three"]
    out = paragraphs_with_pages(PAGE_SEP.join(pages), first_page=7)
    assert out == [("para one", 7), ("para two", 7), ("para three", 8)]


def test_chunks_record_page_ranges_and_lose_no_text():
    # 3 pages of ~300 tokens each -> chunks of <=500 tokens spanning page boundaries
    page = " ".join(f"word{i}" for i in range(300))
    sec = _section([page, page.replace("word", "alpha"), page.replace("word", "beta")])
    chunks = chunk_section(sec)
    assert all(c.n_tokens <= 520 for c in chunks)
    assert chunks[0].page_start == 10
    assert chunks[-1].page_end == 12
    # every page's text appears in some chunk
    joined = " ".join(c.text for c in chunks)
    for token in ("word299", "alpha0", "beta150"):
        assert token in joined
    assert chunks[0].chunk_id.startswith("TEST_FY25:mdna:")


def test_tiny_fragments_are_dropped():
    sec = _section(["42"])          # a page that is only a page number
    assert chunk_section(sec) == []
