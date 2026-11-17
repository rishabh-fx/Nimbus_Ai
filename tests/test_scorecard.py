"""Owner: Lakshya. Every scorecard number is checked against a hand-calculated table."""
import pytest
from backend.tools import build_scorecard, get_scorecard, months_live, status_for

EXPECTED = {
    # id: adoption, wau_change, roi, months, avg_monthly, payback, run_rate, status
    "CP-01": (0.68, 0.2143, 0.50, 6, 1_000_000, 4.0, 1.2, "Green"),
    "CP-02": (0.25, -0.3333, -0.70, 3, 300_000, 10.0, 0.6, "Red"),
    "BOT-01": (0.60, 0.1538, 0.35, 9, 300_000, 6.67, 1.2, "Green"),
    "BOT-02": (0.45, 0.20, 0.0667, 4, 400_000, 3.75, 0.96, "Amber"),
    "PM-01": (0.70, 0.20, -0.20, 8, 500_000, 10.0, 0.75, "Red"),
    "PM-02": (0.50, 0.1111, 0.0, 2, 500_000, 2.0, 1.5, "Amber"),
}


@pytest.mark.parametrize("iid", list(EXPECTED))
def test_scorecard_matches_hand_calculation(iid):
    row = {r["initiative_id"]: r for r in build_scorecard()}[iid]
    adoption, wau, roi, months, monthly, payback, run_rate, status = EXPECTED[iid]
    assert row["adoption"] == pytest.approx(adoption, abs=1e-3)
    assert row["wau_change"] == pytest.approx(wau, abs=1e-3)
    assert row["roi"] == pytest.approx(roi, abs=1e-3)
    assert row["months_live"] == months
    assert row["avg_monthly_benefit"] == pytest.approx(monthly, abs=1)
    assert row["payback_months"] == pytest.approx(payback, abs=0.01)
    assert row["run_rate_vs_plan"] == pytest.approx(run_rate, abs=1e-3)
    assert row["status"] == status


def test_boundaries():
    assert status_for(0.60, 0.01) == "Green"   # adoption exactly 60% counts
    assert status_for(0.50, 0.0) == "Amber"    # ROI exactly 0 is not Red
    assert status_for(0.29, 0.5) == "Red"
    assert status_for(None, 0.5) == "Unknown"
    assert months_live("2026-11-16") == 0      # not yet a full month


def test_tool_filters_and_errors():
    assert get_scorecard("pm-01")["rows"][0]["status"] == "Red"
    assert get_scorecard("Churn Predictor")["rows"][0]["initiative_id"] == "PM-02"
    assert get_scorecard("XX-99")["found"] is False
    assert get_scorecard(metric="salary")["found"] is False
    assert set(get_scorecard(metric="roi")["rows"][0]) == {"initiative_id", "name", "roi"}
