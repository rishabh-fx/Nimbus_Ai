"""Owner: Harsh + Kishlay. Retrieval, citations, not-found and injection filtering."""
from backend.rag import load_chunks, search_charters


def test_every_charter_has_five_sections():
    chunks, _ = load_chunks()
    by_id = {}
    for c in chunks:
        by_id.setdefault(c["initiative_id"], set()).add(c["section"])
    assert len(by_id) == 6
    assert all(len(s) == 5 for s in by_id.values())


def test_why_red_finds_risks_with_citation():
    r = search_charters("why is it red", "PM-01")
    assert r["found"]
    top = r["results"][0]
    assert top["section"] == "Risks"
    assert top["file"] == "data/charters/PM-01.md"
    assert "pipeline" in top["text"].lower()


def test_unknown_topic_is_not_found():
    assert search_charters("2027 budget", "CP-01")["found"] is False
    assert search_charters("cafeteria menu")["found"] is False


def test_injection_is_removed_but_real_metrics_kept():
    r = search_charters("success metrics", "BOT-02")
    text = r["results"][0]["text"].lower()
    assert "ignore all previous instructions" not in text
    assert "containment rate" in text
    assert any(b["file"].endswith("BOT-02.md") for b in r["blocked"])
