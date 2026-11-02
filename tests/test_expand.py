"""Context expansion, with the chunk table faked."""

from arqa import retrieve as R
from arqa.retrieve import Hit


def _chunk(row, text, sec="mdna", page=10, fy="FY25"):
    return {"chunk_id": f"T_{fy}:{sec}:{row:04d}", "ticker": "T", "fy": fy, "part": "", "section": sec,
            "section_key": sec, "page_start": page, "page_end": page, "text": text, "n_tokens": 10, "row": row}


OV1 = "the quick brown fox jumps over the lazy dog near the riverbank today "   # ~70 chars, like the chunker's overlap
OV2 = "net interest income grew by thirteen per cent to a record level this year "
META = [
    _chunk(0, "alpha one " + OV1, page=9),
    _chunk(1, OV1 + "middle text " + OV2),           # overlaps chunk 0 and chunk 2
    _chunk(2, OV2 + "six seven", page=11),
    _chunk(3, "eight nine", sec="risk_management", page=12),   # different section: never joined
]


def test_expand_widens_to_neighbours_in_the_same_section_and_dedupes_overlap(monkeypatch):
    monkeypatch.setattr(R, "_meta", lambda: META)
    out = R.expand_hits([Hit(chunk=META[1], score=1.0, rank=1)])
    assert len(out) == 1
    c = out[0].chunk
    assert c["expanded_from"] == ["T_FY25:mdna:0000", "T_FY25:mdna:0001", "T_FY25:mdna:0002"]
    assert c["text"] == "alpha one " + OV1 + "middle text " + OV2 + "six seven"   # overlaps removed, nothing lost
    assert (c["page_start"], c["page_end"]) == (9, 11)
    assert c["chunk_id"] == "T_FY25:mdna:0001"                          # the centre keeps its identity


def test_expand_stops_at_section_boundary(monkeypatch):
    monkeypatch.setattr(R, "_meta", lambda: META)
    out = R.expand_hits([Hit(chunk=META[2], score=1.0, rank=1)])
    assert out[0].chunk["expanded_from"] == ["T_FY25:mdna:0001", "T_FY25:mdna:0002"]   # not chunk 3


def test_touching_windows_merge_into_the_higher_ranked_hit(monkeypatch):
    monkeypatch.setattr(R, "_meta", lambda: META)
    hits = [Hit(chunk=META[0], score=2.0, rank=1), Hit(chunk=META[2], score=1.0, rank=2)]
    out = R.expand_hits(hits)
    assert len(out) == 1 and out[0].chunk["chunk_id"] == "T_FY25:mdna:0000"
    assert out[0].chunk["expanded_from"] == ["T_FY25:mdna:0000", "T_FY25:mdna:0001", "T_FY25:mdna:0002"]


def test_top_n_expansion_widens_only_the_best_hits(monkeypatch):
    monkeypatch.setattr(R, "_meta", lambda: META)
    hits = [Hit(chunk=META[0], score=2.0, rank=1), Hit(chunk=META[3], score=1.0, rank=2)]
    out = R.expand_hits(hits, top=1)
    assert out[0].chunk["expanded_from"] == ["T_FY25:mdna:0000", "T_FY25:mdna:0001"]   # widened
    assert out[1].chunk["expanded_from"] == ["T_FY25:risk_management:0003"]           # left alone
