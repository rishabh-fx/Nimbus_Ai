"""Owner: Rishabh. Checks that cleaning fixes every planted issue and logs it."""
import pandas as pd
import pytest
from backend import clean_data


@pytest.fixture(scope="module")
def cleaned(tmp_path_factory):
    """Run the cleaning once on the real raw files, writing to a temporary folder."""
    out = tmp_path_factory.mktemp("clean")
    log = clean_data.main(clean_dir=out, out_dir=out)
    return {"log": log, "dir": out,
            "ini": pd.read_csv(out / "initiatives.csv"),
            "use": pd.read_csv(out / "usage.csv"),
            "fin": pd.read_csv(out / "finance.csv")}


def test_six_clean_unique_ids(cleaned):
    ids = list(cleaned["ini"]["initiative_id"])
    assert sorted(ids) == ["BOT-01", "BOT-02", "CP-01", "CP-02", "PM-01", "PM-02"]
    assert set(cleaned["use"]["initiative_id"]) == set(ids)
    assert set(cleaned["fin"]["initiative_id"]) == set(ids)


def test_dates_are_iso(cleaned):
    assert cleaned["ini"]["go_live_date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    cp02 = cleaned["ini"].set_index("initiative_id").loc["CP-02", "go_live_date"]
    assert cp02 == "2026-08-15"          # was 15/08/2026


def test_one_row_per_initiative_and_week(cleaned):
    assert not cleaned["use"].duplicated(subset=["initiative_id", "week"]).any()
    assert len(cleaned["use"]) == 18     # 6 initiatives x 3 weeks


def test_missing_value_is_not_guessed(cleaned):
    use = cleaned["use"]
    row = use[(use["initiative_id"] == "PM-02") & (use["week"] == 2)]
    assert row["weekly_active_users"].isna().all()


def test_money_is_in_inr_and_cost_not_negative(cleaned):
    fin = cleaned["fin"].set_index("initiative_id")
    assert fin.loc["CP-01", "cost_to_date"] == 4_000_000      # was 40 lakh
    assert fin.loc["BOT-02", "realised_benefit_to_date"] == 1_600_000
    assert fin.loc["BOT-01", "cost_to_date"] == 2_000_000     # was -2,000,000
    assert (fin["cost_to_date"] >= 0).all()


def test_every_planted_issue_is_logged(cleaned):
    issues = " | ".join(e["issue"] for e in cleaned["log"])
    for expected in ["Mixed date format", "ID casing", "Duplicate row", "Missing value",
                     "Unit INR_lakh", "Negative cost", "Inconsistent metric name"]:
        assert expected in issues
    assert all(e["before"] and e["after"] and e["effect"] for e in cleaned["log"])
    assert (cleaned["dir"] / "changelog.md").read_text(encoding="utf-8").count("\n| ") >= len(cleaned["log"])


def test_raw_files_are_not_modified(cleaned):
    raw = pd.read_csv(clean_data.RAW / "finance.csv")
    assert " cp-02" in list(raw["initiative_id"])    # raw still has the planted issue


def test_unknown_unit_stops_the_run():
    fin = pd.DataFrame({"initiative_id": ["X-01"], "cost_to_date": [1.0],
                        "realised_benefit_to_date": [2.0], "unit": ["USD"]})
    with pytest.raises(ValueError):
        clean_data.convert_units(fin, [])


def test_unknown_metric_name_stops_the_run():
    use = pd.DataFrame({"initiative_id": ["X-01"], "week": [1], "metric": ["logins"], "value": [5]})
    with pytest.raises(ValueError):
        clean_data.standardise_metric_names(use, [])


def test_conflicting_rows_stop_the_run():
    use = pd.DataFrame({"initiative_id": ["X-01", "X-01"], "week": [1, 1], "value": [5, 9]})
    with pytest.raises(ValueError):
        clean_data.check_conflicting_rows(use)


def test_unknown_date_format_raises():
    with pytest.raises(ValueError):
        clean_data.parse_date("Aug 15 2026")
