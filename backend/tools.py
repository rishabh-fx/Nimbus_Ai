"""Owner: Lakshya. Governed scorecard: the ONLY place numbers are created.

The LLM never calculates. It calls get_scorecard() and explains what comes back.
Formulas (as of AS_OF):
  adoption         = latest WAU / licensed users
  wau_change       = (latest WAU - first WAU) / first WAU
  roi              = (benefit - cost) / cost
  avg_monthly      = benefit / whole months live
  payback_months   = cost / avg_monthly
  run_rate_vs_plan = avg_monthly * 12 / planned annual benefit
  status           = Green if adoption >= 0.60 and roi > 0; Red if adoption < 0.30 or roi < 0; else Amber
"""
from datetime import date
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
AS_OF = date(2026, 11, 15)
SOURCE = "data/clean/initiatives.csv, usage.csv, finance.csv (scorecard v1)"
METRICS = ["adoption", "wau_change", "roi", "avg_monthly_benefit",
           "payback_months", "run_rate_vs_plan", "status"]


def months_live(go_live, as_of=AS_OF):
    """Whole months between go-live and as_of (a month counts only once its day is reached)."""
    d = pd.to_datetime(go_live).date()
    m = (as_of.year - d.year) * 12 + (as_of.month - d.month)
    if as_of.day < d.day:
        m -= 1
    return max(m, 0)


def safe_div(a, b):
    """Division that returns None instead of crashing on missing data or zero."""
    if a is None or b is None or pd.isna(a) or pd.isna(b) or b == 0:
        return None
    return float(a) / float(b)


def rnd(x, n=4):
    return None if x is None else round(float(x), n)


def status_for(adoption, roi):
    if adoption is None or roi is None:
        return "Unknown"
    if adoption >= 0.60 and roi > 0:
        return "Green"
    if adoption < 0.30 or roi < 0:
        return "Red"
    return "Amber"


def build_scorecard():
    ini = pd.read_csv(CLEAN / "initiatives.csv")
    use = pd.read_csv(CLEAN / "usage.csv")
    fin = pd.read_csv(CLEAN / "finance.csv").set_index("initiative_id")
    rows = []
    for _, i in ini.iterrows():
        iid = i["initiative_id"]
        notes = []
        u = (use[use["initiative_id"] == iid]
             .dropna(subset=["weekly_active_users"])
             .sort_values("week"))
        if u.empty:
            first = latest = None
            notes.append("no usage data")
        else:
            first = u.iloc[0]["weekly_active_users"]
            latest = u.iloc[-1]["weekly_active_users"]
        cost = fin.loc[iid, "cost_to_date"] if iid in fin.index else None
        benefit = fin.loc[iid, "realised_benefit_to_date"] if iid in fin.index else None
        if cost is None:
            notes.append("no finance data")
        months = months_live(i["go_live_date"])

        adoption = safe_div(latest, i["licensed_users"])
        wau_change = safe_div(None if latest is None else latest - first, first)
        roi = safe_div(None if benefit is None else benefit - cost, cost)
        avg_monthly = safe_div(benefit, months)
        payback = safe_div(cost, avg_monthly)
        run_rate = safe_div(None if avg_monthly is None else avg_monthly * 12,
                            i["planned_annual_benefit"])
        if months == 0:
            notes.append("live less than a month: monthly metrics undefined")
        if avg_monthly == 0:
            notes.append("zero benefit: payback undefined")

        rows.append({
            "initiative_id": iid, "name": i["name"], "months_live": months,
            "licensed_users": int(i["licensed_users"]),
            "latest_wau": None if latest is None else int(latest),
            "cost_to_date": rnd(cost, 2), "realised_benefit_to_date": rnd(benefit, 2),
            "planned_annual_benefit": rnd(i["planned_annual_benefit"], 2),
            "adoption": rnd(adoption), "wau_change": rnd(wau_change), "roi": rnd(roi),
            "avg_monthly_benefit": rnd(avg_monthly, 2), "payback_months": rnd(payback, 2),
            "run_rate_vs_plan": rnd(run_rate), "status": status_for(adoption, roi),
            "notes": notes,
        })
    return rows


def get_scorecard(initiative=None, metric=None):
    """Tool exposed to the LLM. Filter by initiative (ID or name) and/or a single metric."""
    rows = build_scorecard()
    if initiative:
        key = initiative.strip().upper()
        rows = [r for r in rows
                if r["initiative_id"] == key or r["name"].lower() == initiative.strip().lower()]
        if not rows:
            return {"found": False, "error": f"Unknown initiative: {initiative}", "source": SOURCE}
    if metric:
        if metric not in METRICS:
            return {"found": False, "error": f"Unknown metric '{metric}'. Valid: {METRICS}",
                    "source": SOURCE}
        rows = [{"initiative_id": r["initiative_id"], "name": r["name"], metric: r[metric]}
                for r in rows]
    return {"found": True, "as_of": str(AS_OF), "rows": rows, "source": SOURCE}


if __name__ == "__main__":
    for r in build_scorecard():
        print(r["initiative_id"], r["status"], r["adoption"], r["roi"], r["payback_months"])
