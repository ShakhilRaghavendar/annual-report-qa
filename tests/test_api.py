"""The HTTP layer, with the answerer and the index faked."""

from fastapi.testclient import TestClient

from arqa import api
from arqa.answer import Answer, Citation


def _fake_answer(question, ticker=None, fy=None, k=5, retriever="hybrid+rerank", model=None):
    c = Citation(1, ticker or "INFY", "FY25", "", "Front matter", 15, 15, "INFY_FY25:front_matter:0019")
    return Answer(question, True, "FCF was ₹34,549 crore [1].", [], [c], [c], "fake", retriever, 0.1)


def test_ask_returns_answer_json(monkeypatch):
    monkeypatch.setattr(api, "answer", _fake_answer)
    client = TestClient(api.app)
    r = client.post("/ask", json={"question": "What was FCF?", "ticker": "infy", "fy": ["fy25"]})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] and body["citations"][0]["page_start"] == 15
    assert "raw" not in body


def test_ask_validates_input(monkeypatch):
    monkeypatch.setattr(api, "answer", _fake_answer)
    client = TestClient(api.app)
    assert client.post("/ask", json={"question": "hi"}).status_code == 422          # too short
    assert client.post("/ask", json={"question": "long enough?", "retriever": "magic"}).status_code == 422


def test_health_counts_reports(monkeypatch):
    monkeypatch.setattr(api, "_meta", lambda: [
        {"ticker": "INFY", "fy": "FY25", "part": ""}, {"ticker": "INFY", "fy": "FY25", "part": ""},
        {"ticker": "ICICIBANK", "fy": "FY25", "part": "fs"}])
    r = TestClient(api.app).get("/health").json()
    assert r == {"status": "ok", "chunks": 3, "reports": 2}
