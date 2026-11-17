# Nimbus AI value report (as of 2026-11-15)

Source: data/clean/initiatives.csv, usage.csv, finance.csv (scorecard v1)

## Summary

- **Green** (2): CP-01, BOT-01
- **Amber** (2): BOT-02, PM-02
- **Red** (2): CP-02, PM-01

## Scorecard

| ID | Name | Status | Adoption | WAU change | ROI | Payback (months) | Run-rate vs plan |
|---|---|---|---|---|---|---|---|
| CP-01 | HR Policy Copilot | Green | 68.0% | 21.4% | 50.0% | 4.0 | 120.0% |
| CP-02 | Sales Copilot | Red | 25.0% | -33.3% | -70.0% | 10.0 | 60.0% |
| BOT-01 | IT Helpdesk Bot | Green | 60.0% | 15.4% | 35.0% | 6.67 | 120.0% |
| BOT-02 | Customer FAQ Bot | Amber | 45.0% | 20.0% | 6.7% | 3.75 | 96.0% |
| PM-01 | Demand Forecasting Model | Red | 70.0% | 20.0% | -20.0% | 10.0 | 75.0% |
| PM-02 | Churn Predictor | Amber | 50.0% | 11.1% | 0.0% | 2.0 | 150.0% |

## Needs attention

- **CP-02 (Sales Copilot) - Red**: adoption 25.0% is below 30%; ROI -70.0%: cost Rs 3,000,000 exceeds benefit Rs 900,000.
- **PM-01 (Demand Forecasting Model) - Red**: ROI -20.0%: cost Rs 5,000,000 exceeds benefit Rs 4,000,000.
- **BOT-02 (Customer FAQ Bot) - Amber**: adoption 45.0% and ROI 6.7% are below the Green bar.
- **PM-02 (Churn Predictor) - Amber**: adoption 50.0% and ROI 0.0% are below the Green bar.

## Method

- Adoption = latest weekly active users / licensed users.
- ROI = (realised benefit - cost) / cost.
- Payback = cost / (benefit / whole months live).
- Run-rate vs plan = average monthly benefit x 12 / planned annual benefit.
- Status: Green if adoption >= 60% and ROI > 0; Red if adoption < 30% or ROI < 0; else Amber.
- All figures come from backend/tools.py. Data fixes are listed in outputs/changelog.md.
