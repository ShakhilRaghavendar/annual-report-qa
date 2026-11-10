"""MultiQuery: fuse the original question's hits with its rewrites' — no LLM, no index."""

from arqa import retrieve as R
from arqa.retrieve import Hit, MultiQuery


def _hit(cid, rank):
    return Hit(chunk={"chunk_id": cid, "row": hash(cid) % 1000, "text": cid}, score=1.0, rank=rank)


class FakeBase:
    name = "fake"

    def __init__(self, table):
        self.table = table      # query -> ordered chunk ids
        self.calls = []

    def search(self, query, k=5, filters=None):
        self.calls.append(query)
        return [_hit(c, r) for r, c in enumerate(self.table.get(query, [])[:k], start=1)]


def test_rewrites_rescue_a_chunk_the_original_question_missed(monkeypatch):
    monkeypatch.setattr(R, "rewrite_query", lambda q, n=3: ["profit after tax stood at", "PAT crore"])
    base = FakeBase({"how much money did they make": ["A", "B"],
                     "profit after tax stood at": ["GOLD", "A"],
                     "PAT crore": ["GOLD", "C"]})
    hits = MultiQuery(base).search("how much money did they make", k=3)
    assert base.calls == ["how much money did they make", "profit after tax stood at", "PAT crore"]
    ids = [h.chunk["chunk_id"] for h in hits]
    assert "GOLD" in ids and len(ids) == 3
    assert [h.rank for h in hits] == [1, 2, 3]


def test_original_question_outweighs_a_single_rewrite(monkeypatch):
    monkeypatch.setattr(R, "rewrite_query", lambda q, n=3: ["rewrite"])
    base = FakeBase({"q": ["A", "B"], "rewrite": ["B", "A"]})
    hits = MultiQuery(base, orig_weight=2.0).search("q", k=2)
    assert hits[0].chunk["chunk_id"] == "A"       # 2/61 + 1/62 beats 2/62 + 1/61


def test_no_rewrites_means_plain_passthrough(monkeypatch):
    monkeypatch.setattr(R, "rewrite_query", lambda q, n=3: [])
    base = FakeBase({"q": ["A", "B", "C"]})
    hits = MultiQuery(base).search("q", k=2)
    assert [h.chunk["chunk_id"] for h in hits] == ["A", "B"]


def test_factory_nests_mq_inside_expand():
    r = R.get_retriever.__doc__
    assert "+mq" in r
    # parse order only — no models loaded
    name = "hybrid+rerank+mq+expand"
    base, _, n = name.rpartition("+expand")
    assert base.endswith("+mq") and n == ""
