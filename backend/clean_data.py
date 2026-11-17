"""Owner: Rishabh. Cleans data/raw -> data/clean and records every fix in outputs/changelog.md.

Each data-quality issue has its own small function. Every function that changes
something adds a row to the change log with the value before, the value after and
which scorecard metrics the fix affects. Raw files are only read, never written.

Output contract (read by tools.py):
  initiatives.csv: initiative_id, name, type, go_live_date (YYYY-MM-DD), licensed_users, planned_annual_benefit
  usage.csv:       initiative_id, week, weekly_active_users
  finance.csv:     initiative_id, cost_to_date, realised_benefit_to_date   (all INR)

Run from repo root: python -m backend.clean_data
"""
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "outputs"

# Every name a source file may use for weekly active users -> the one standard name.
METRIC_ALIASES = {"WAU": "weekly_active_users", "active_users_wk": "weekly_active_users",
                  "weekly_active_users": "weekly_active_users"}
# How many rupees one unit of each money unit is worth.
UNIT_TO_INR = {"INR": 1, "INR_lakh": 100_000}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")   # assumption: slash dates are day/month/year


def log_fix(log, file, initiative, field, issue, before, after, effect):
    """Add one row to the change log."""
    log.append({"file": file, "initiative": initiative, "field": field, "issue": issue,
                "before": before, "after": after, "effect": effect})


def norm_id(x):
    """' cp-02' -> 'CP-02'."""
    return str(x).strip().upper()


def parse_date(s):
    """Return the date as YYYY-MM-DD, or raise if it is in a format we do not know."""
    s = str(s).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unrecognised date: {s}")


# ---------- one function per issue ----------
def clean_ids(df, file, log):
    """Issue 2: ID casing and stray spaces. Logged once per distinct bad ID per file."""
    for bad in sorted(set(df["initiative_id"]) - set(df["initiative_id"].map(norm_id))):
        log_fix(log, file, norm_id(bad), "initiative_id", "ID casing / stray spaces",
                f"'{bad}'", f"'{norm_id(bad)}'",
                "Rows now join across the three files; without this the initiative "
                "would have no usage or finance data, so all metrics")
    df["initiative_id"] = df["initiative_id"].map(norm_id)
    return df


def clean_dates(ini, log):
    """Issue 1: mixed date formats -> YYYY-MM-DD."""
    for i, r in ini.iterrows():
        new_date = parse_date(r["go_live_date"])
        if new_date != r["go_live_date"]:
            log_fix(log, "initiatives", r["initiative_id"], "go_live_date", "Mixed date format",
                    r["go_live_date"], new_date,
                    "Months live, so avg monthly benefit, payback and run-rate vs plan")
        ini.at[i, "go_live_date"] = new_date
    return ini


def standardise_metric_names(use, log):
    """Three names for one metric -> weekly_active_users. Unknown names stop the run."""
    unknown = sorted(set(use["metric"]) - set(METRIC_ALIASES))
    if unknown:
        raise ValueError(f"Unknown metric name(s) in usage.csv: {unknown}. Add them to METRIC_ALIASES.")
    for m in sorted(set(use["metric"]) - {"weekly_active_users"}):
        log_fix(log, "usage", "all", "metric", "Inconsistent metric name",
                m, "weekly_active_users", "Adoption and WAU change (all usage rows read as one metric)")
    use["metric"] = use["metric"].map(METRIC_ALIASES)
    return use


def drop_exact_duplicates(use, log):
    """Issue 3: a row repeated exactly. Keep the first copy."""
    for _, d in use[use.duplicated(keep="first")].iterrows():
        log_fix(log, "usage", d["initiative_id"], f"week {d['week']}", "Duplicate row",
                "2 identical rows", "1 row",
                "One row per initiative and week; adoption and WAU change are not double counted")
    return use.drop_duplicates(keep="first")


def check_conflicting_rows(use):
    """Same initiative and week with different values: we cannot know which is right, so stop."""
    clash = use[use.duplicated(subset=["initiative_id", "week"], keep=False)]
    if not clash.empty:
        raise ValueError("Conflicting usage rows (same initiative and week, different values):\n"
                         f"{clash.to_string(index=False)}")


def flag_missing_usage(use, log):
    """Issue 4: missing value. Kept empty and logged, never guessed."""
    for _, m in use[use["value"].isna()].iterrows():
        log_fix(log, "usage", m["initiative_id"], f"week {m['week']}", "Missing value",
                "(empty)", "(left empty)",
                "Not guessed. The scorecard skips this week when picking the first and latest week")
    return use


def convert_units(fin, log):
    """Issue 5: mixed money units -> INR. Unknown units stop the run."""
    unknown = sorted(set(fin["unit"]) - set(UNIT_TO_INR))
    if unknown:
        raise ValueError(f"Unknown money unit(s) in finance.csv: {unknown}. Add them to UNIT_TO_INR.")
    for i, r in fin.iterrows():
        factor = UNIT_TO_INR[r["unit"]]
        if factor != 1:
            cost, benefit = r["cost_to_date"] * factor, r["realised_benefit_to_date"] * factor
            log_fix(log, "finance", r["initiative_id"], "cost_to_date, realised_benefit_to_date",
                    f"Unit {r['unit']} instead of INR",
                    f"cost {r['cost_to_date']:g}, benefit {r['realised_benefit_to_date']:g} ({r['unit']})",
                    f"cost {cost:,.0f}, benefit {benefit:,.0f} (INR)",
                    "Avg monthly benefit and run-rate vs plan (the plan is in INR). "
                    "ROI and payback are ratios, so they do not change")
            fin.at[i, "cost_to_date"], fin.at[i, "realised_benefit_to_date"] = cost, benefit
    return fin


def fix_negative_cost(fin, log):
    """Issue 6: a cost cannot be negative. Assumed to be a sign error; flagged for review."""
    for i, r in fin.iterrows():
        if r["cost_to_date"] < 0:
            log_fix(log, "finance", r["initiative_id"], "cost_to_date",
                    "Negative cost (assumed sign error, flagged for owner review)",
                    f"{r['cost_to_date']:,.0f}", f"{abs(r['cost_to_date']):,.0f}",
                    "ROI, payback and status (a negative cost would give a meaningless ROI)")
            fin.at[i, "cost_to_date"] = abs(r["cost_to_date"])
    return fin


def validate(ini, use, fin):
    """Final checks. If any fails, the scorecard must not run on this data."""
    ids = list(ini["initiative_id"])
    assert len(ids) == len(set(ids)), "duplicate initiative IDs"
    assert set(fin["initiative_id"]) == set(ids), "finance IDs do not match initiatives"
    assert set(use["initiative_id"]) == set(ids), "usage IDs do not match initiatives"
    assert (ini["licensed_users"] > 0).all(), "licensed_users must be positive"
    assert (fin["cost_to_date"] >= 0).all(), "cost must not be negative after cleaning"


def write_changelog(log, out_dir):
    lines = ["# Data change log", "",
             "Generated by backend/clean_data.py from data/raw/. The data is synthetic; "
             "the issues were planted on purpose.", "",
             "| # | File | Initiative | Field | Issue | Before | After | Effect on metrics |",
             "|---|---|---|---|---|---|---|---|"]
    for n, e in enumerate(log, 1):
        lines.append(f"| {n} | {e['file']} | {e['initiative']} | {e['field']} | {e['issue']} | "
                     f"{e['before']} | {e['after']} | {e['effect']} |")
    (out_dir / "changelog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(raw_dir=RAW, clean_dir=CLEAN, out_dir=OUT):
    clean_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = []

    ini = pd.read_csv(raw_dir / "initiatives.csv", dtype=str)
    ini = clean_ids(ini, "initiatives", log)
    ini = clean_dates(ini, log)
    ini["licensed_users"] = ini["licensed_users"].astype(int)
    ini["planned_annual_benefit"] = ini["planned_annual_benefit"].astype(float)

    use = pd.read_csv(raw_dir / "usage.csv", dtype={"initiative_id": str, "metric": str})
    use = clean_ids(use, "usage", log)
    use = standardise_metric_names(use, log)
    use = drop_exact_duplicates(use, log)
    check_conflicting_rows(use)
    use = flag_missing_usage(use, log)
    use = use.rename(columns={"value": "weekly_active_users"})[["initiative_id", "week", "weekly_active_users"]]

    fin = pd.read_csv(raw_dir / "finance.csv", dtype={"initiative_id": str, "unit": str})
    fin[["cost_to_date", "realised_benefit_to_date"]] = fin[["cost_to_date", "realised_benefit_to_date"]].astype(float)
    fin = clean_ids(fin, "finance", log)
    fin = convert_units(fin, log)
    fin = fix_negative_cost(fin, log)
    fin = fin[["initiative_id", "cost_to_date", "realised_benefit_to_date"]]

    validate(ini, use, fin)
    ini.to_csv(clean_dir / "initiatives.csv", index=False)
    use.to_csv(clean_dir / "usage.csv", index=False)
    fin.to_csv(clean_dir / "finance.csv", index=False)
    write_changelog(log, out_dir)
    print(f"Clean data written to {clean_dir}; {len(log)} fixes logged in {out_dir / 'changelog.md'}")
    return log


if __name__ == "__main__":
    main()
