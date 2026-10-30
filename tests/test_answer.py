"""The answerer, with the LLM and the index faked — no network, no model files."""

import json

import pytest

from arqa import answer as A
from arqa.retrieve import Hit


def _hit(n, ticker="INFY", fy="FY25", p=15, text="Free cash flow was `34,549 crore, the highest ever."):
    return Hit(chunk={"chunk_id": f"{ticker}_{fy}:front_matter:{n:04d}", "ticker": ticker, "fy": fy, "part": "",
                      "section": "Front matter", "section_key": "front_matter",
                      "page_start": p, "page_end": p, "text": text, "row": n}, score=1.0, rank=n)


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search(self, query, k=5, filters=None):
        self.calls.append(filters)
        return self.hits[:k]


def test_parse_reply_converts_units_and_maps_citations():
    raw = json.dumps({
        "found": True,
        "answer": "Free cash flow was ₹34,549 crore [1]. R&D spend was ₹31,776 million [2].",
        "figures": [
            {"label": "FCF FY25", "value": "34,549", "unit": "crore", "currency": "INR", "citation": 1},
            {"label": "R&D", "value": 31776, "unit": "million", "currency": "INR", "citation": 2},
            {"label": "specialty revenue", "value": 1216, "unit": "million", "currency": "USD", "citation": 2},
            {"label": "growth", "value": 17.1, "unit": "%", "currency": "", "citation": 9},
        ],
    })
    found, text, figs, cited = A.parse_reply(raw, n_passages=3)
    assert found and cited == [1, 2]
    assert figs[0].crore == 34549.0
    assert figs[1].crore == pytest.approx(3177.6)          # ₹ million → crore
    assert figs[2].crore is None and figs[2].currency == "USD"
    assert figs[3].unit == "percent" and figs[3].citation is None   # [9] is out of range


def test_parse_reply_tolerates_code_fences_and_prose():
    raw = "Here you go:\n```json\n{\"found\": false, \"answer\": \"Not in passages.\", \"figures\": []}\n```"
    found, text, figs, cited = A.parse_reply(raw, 2)
    assert not found and text == "Not in passages." and figs == [] and cited == []


def test_answer_end_to_end_with_fakes(monkeypatch):
    fake = FakeRetriever([_hit(1), _hit(2, p=33, text="Dividends were `17,814 crore, 51.6% of FCF.")])
    monkeypatch.setattr(A, "get_retriever", lambda name: fake)
    monkeypatch.setattr(A.llm, "chat", lambda messages, **kw: json.dumps({
        "found": True, "answer": "FCF was ₹34,549 crore [1].",
        "figures": [{"label": "FCF", "value": 34549, "unit": "crore", "currency": "INR", "citation": 1}]}))
    monkeypatch.setattr(A.llm, "model_name", lambda role="model": "fake-model")

    a = A.answer("What was FCF?", ticker="INFY", fy="FY25")
    assert fake.calls == [{"ticker": "INFY", "fy": "FY25"}]
    assert a.found and a.citations[0].page_start == 15 and len(a.passages) == 2
    assert "₹ 34,549.00 crore" in a.render()
    assert "[1] INFY FY25, Front matter, p.15" in a.render()


def test_cross_year_retrieves_once_per_year_and_interleaves(monkeypatch):
    fy24 = FakeRetriever([_hit(1, fy="FY24", p=10), _hit(2, fy="FY24", p=11)])
    fy25 = FakeRetriever([_hit(1, fy="FY25", p=7), _hit(2, fy="FY25", p=8)])

    class Router:
        def search(self, q, k=5, filters=None):
            return (fy24 if filters["fy"] == "FY24" else fy25).search(q, k, filters)

    monkeypatch.setattr(A, "get_retriever", lambda name: Router())
    hits = A.retrieve("EBITDA?", "RELIANCE", ["FY24", "FY25"], k=2)
    assert [(h.chunk["fy"], h.chunk["page_start"], h.rank) for h in hits] == [
        ("FY24", 10, 1), ("FY25", 7, 2), ("FY24", 11, 3), ("FY25", 8, 4)]


def test_unparseable_reply_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(A, "get_retriever", lambda name: FakeRetriever([_hit(1)]))
    monkeypatch.setattr(A.llm, "chat", lambda messages, **kw: "I cannot help with that.")
    monkeypatch.setattr(A.llm, "model_name", lambda role="model": "fake-model")
    a = A.answer("?", ticker="INFY", fy="FY25")
    assert not a.found and "could not be parsed" in a.answer


def test_garbled_rupee_glyphs_are_scrubbed_from_answer_text():
    assert A.scrub_rupee("EBITDA of C 23,082 crore and `45,588 crore; H 416,661 crore") == \
        "EBITDA of ₹23,082 crore and ₹45,588 crore; ₹416,661 crore"
    # real words and US$ are untouched
    assert A.scrub_rupee("Chapter I covers 12 million people; US$ 4.1 billion") == "Chapter I covers 12 million people; US$ 4.1 billion"


def test_citations_fall_back_to_figures_and_accept_cjk_brackets():
    raw = json.dumps({"found": False, "answer": "Payout ratio was 43.01%【2】.",
                      "figures": [{"label": "payout", "value": 43.01, "unit": "percent", "currency": "", "citation": 2}]})
    found, text, figs, cited = A.parse_reply(raw, 3)
    assert cited == [2] and text == "Payout ratio was 43.01%[2]."
    assert found is True          # a figure was extracted, so it was found
    raw = json.dumps({"found": True, "answer": "No markers here.",
                      "figures": [{"label": "x", "value": 1, "unit": "crore", "currency": "INR", "citation": 3}]})
    assert A.parse_reply(raw, 3)[3] == [3]


def test_amount_in_prose_is_parsed_when_figures_list_is_empty():
    raw = json.dumps({"found": False, "answer": "The report gives standalone PAT as ₹ 472.27 billion, not in crore. [1]", "figures": []})
    found, text, figs, cited = A.parse_reply(raw, 2)
    assert found and cited == [1]
    assert figs[0].unit == "billion" and figs[0].crore == pytest.approx(47227.0)
