"""Owner: Harsh + Kishlay. Locks the evaluation thresholds so a later change cannot silently regress.

Runs on the deterministic offline path (no API key, no cost) so CI and the demo laptop agree.
"""
import pytest

from backend import evaluate


@pytest.fixture(scope="module")
def results(monkeypatch_module=None):
    cases = evaluate.load_cases()
    return cases, evaluate.retrieval_scores(cases)


def test_eval_set_is_well_formed():
    cases = evaluate.load_cases()
    assert len(cases) >= 18
    assert len({c["id"] for c in cases}) == len(cases)          # unique ids
    valid = {"scorecard", "charter", "mixed", "not_found", "refused"}
    assert all(c["expect_type"] in valid for c in cases)
    assert all(c["expect_type"] in ("charter", "mixed") for c in cases if c["expect_sections"])
    for t in valid:                                              # every behaviour is covered
        assert any(c["expect_type"] == t for c in cases)


def test_retrieval_hit_at_1_is_perfect(results):
    _, retr = results
    assert retr, "no retrieval cases found"
    assert all(r["hit@1"] for r in retr), [r["id"] for r in retr if not r["hit@1"]]


def test_routing_and_guardrails(monkeypatch, results):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cases, retr = results
    rows = evaluate.agent_scores(cases)
    assert all(r["grounded"] for r in rows), [r["id"] for r in rows if not r["grounded"]]
    assert all(r["fallback_ok"] for r in rows), [r["id"] for r in rows if not r["fallback_ok"]]
    assert all(r["content_ok"] for r in rows), [r["id"] for r in rows if not r["content_ok"]]
    assert all(r["type_ok"] for r in rows), [(r["id"], r["expect_type"], r["got_type"])
                                             for r in rows if not r["type_ok"]]
    refused = [r for r in rows if r["expect_type"] == "refused"]
    assert all(r["type_ok"] for r in refused), "an adversarial case was not refused"


def test_report_is_written(tmp_path, monkeypatch, results):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cases, retr = results
    rows = evaluate.agent_scores(cases)
    path = evaluate.write_report(rows, retr, tmp_path / "eval_report.md")
    text = path.read_text(encoding="utf-8")
    assert "## Summary" in text and "Retrieval hit@1" in text and "## Failures" in text
