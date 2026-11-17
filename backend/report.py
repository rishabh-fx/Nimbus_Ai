"""Owner: Kunal. Weekly value report (markdown) built only from the governed scorecard.

Run from repo root: python -m backend.report
"""
from pathlib import Path

from backend import tools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"


def pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def inr(x):
    return "n/a" if x is None else f"Rs {x:,.0f}"


def weekly_report(path=None):
    rows = tools.build_scorecard()
    path = path or OUT / "weekly_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = {s: [r["initiative_id"] for r in rows if r["status"] == s] for s in ("Green", "Amber", "Red")}

    lines = [f"# Nimbus AI value report (as of {tools.AS_OF})", "",
             f"Source: {tools.SOURCE}", "",
             "## Summary", ""]
    for status, ids in counts.items():
        lines.append(f"- **{status}** ({len(ids)}): {', '.join(ids) if ids else 'none'}")
    lines += ["", "## Scorecard", "",
              "| ID | Name | Status | Adoption | WAU change | ROI | Payback (months) | Run-rate vs plan |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['initiative_id']} | {r['name']} | {r['status']} | {pct(r['adoption'])} | "
                     f"{pct(r['wau_change'])} | {pct(r['roi'])} | {r['payback_months']} | "
                     f"{pct(r['run_rate_vs_plan'])} |")

    lines += ["", "## Needs attention", ""]
    attention = [r for r in rows if r["status"] in ("Red", "Amber")]
    for r in sorted(attention, key=lambda r: (r["status"] != "Red", r["initiative_id"])):
        reason = []
        if r["adoption"] is not None and r["adoption"] < 0.30:
            reason.append(f"adoption {pct(r['adoption'])} is below 30%")
        if r["roi"] is not None and r["roi"] < 0:
            reason.append(f"ROI {pct(r['roi'])}: cost {inr(r['cost_to_date'])} exceeds "
                          f"benefit {inr(r['realised_benefit_to_date'])}")
        if not reason:
            reason.append(f"adoption {pct(r['adoption'])} and ROI {pct(r['roi'])} are below the Green bar")
        lines.append(f"- **{r['initiative_id']} ({r['name']}) - {r['status']}**: {'; '.join(reason)}.")
        if r["notes"]:
            lines.append(f"  - Data notes: {'; '.join(r['notes'])}.")
    if not attention:
        lines.append("- None.")

    lines += ["", "## Method", "",
              "- Adoption = latest weekly active users / licensed users.",
              "- ROI = (realised benefit - cost) / cost.",
              "- Payback = cost / (benefit / whole months live).",
              "- Run-rate vs plan = average monthly benefit x 12 / planned annual benefit.",
              "- Status: Green if adoption >= 60% and ROI > 0; Red if adoption < 30% or ROI < 0; else Amber.",
              "- All figures come from backend/tools.py. Data fixes are listed in outputs/changelog.md.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(f"Wrote {weekly_report()}")
