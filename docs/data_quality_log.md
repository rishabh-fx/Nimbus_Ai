# Data-quality and assumptions log

Owner: Rishabh. Covers FR-01 (understand and document) and FR-02 (load and clean data).

## 1. Metric definitions in our own words

| Metric | What it tells us |
|---|---|
| Adoption | Of all the people we pay a licence for, the share who actually used the tool in the most recent week. A low figure means we are paying for seats nobody uses. |
| Weekly active users change | How much the number of weekly users grew or shrank between the first and the last of the three weeks, as a share of the first week. A positive figure means usage is growing; a negative one means people are dropping off. |
| Return on investment (ROI) | For every rupee spent so far, how much we have gained or lost after getting that rupee back. Above zero means the initiative has earned more than it cost; below zero means it has not yet paid for itself. |
| Average monthly benefit | The benefit delivered so far, spread evenly over the whole months the initiative has been live. It shows the typical value one month brings in. |
| Payback period (months) | How many months of benefit, at the average monthly rate so far, it takes to earn back everything spent to date. A shorter period means the money is recovered sooner. |
| Run-rate versus plan | If the average monthly benefit continued for a full year, how that yearly total compares with the benefit that was planned for the year. At 1.0 the initiative is exactly on plan; below 1.0 it is behind; above 1.0 it is ahead. |
| Portfolio status | A traffic-light summary of each initiative. Green means it is well used (adoption of 60% or more) and has earned more than it cost (ROI above zero). Red means it is barely used (adoption below 30%) or is losing money (ROI below zero). Amber is everything in between. The code checks Green first, then Red, then falls back to Amber. |

## 2. Assumptions

| # | Assumption | Where it is applied |
|---|---|---|
| 1 | The data is synthetic. No data files were supplied, so `backend/seed_db.py` generates six initiatives and plants six data-quality issues on purpose. | `seed_db.py` |
| 2 | Dates written with slashes are day/month/year. | `clean_data.py`, `DATE_FORMATS` |
| 3 | One lakh is 100,000 rupees. All money is reported in INR. | `clean_data.py`, `UNIT_TO_INR` |
| 4 | A negative cost is a sign error, not a refund. The absolute value is used and the row is flagged for owner review. | `clean_data.py`, `fix_negative_cost` |
| 5 | A missing usage value is left empty, never estimated. The scorecard uses the first and latest weeks that have a value. | `clean_data.py`, `flag_missing_usage`; `tools.py` |
| 6 | Only exact repeat rows are treated as duplicates. Two rows for the same initiative and week with different values stop the run, because we cannot know which is right. | `clean_data.py`, `check_conflicting_rows` |
| 7 | An unknown metric name or money unit stops the run instead of being silently dropped or misread. | `clean_data.py` |
| 8 | Months live counts whole months from go-live to the reporting date, 15 Nov 2026. | `tools.py`, `months_live`, `AS_OF` |
| 9 | Usage covers three weeks; "first" is week 1 and "latest" is week 3. | `seed_db.py`, `tools.py` |

## 3. Clarification question for the client

Should "months live" count partial months, and as of which date? Average monthly benefit,
payback and run-rate versus plan all depend on it. Until answered, we count whole months as of
the reporting date (assumption 8), so the figures can be recomputed if the answer differs.

## 4. Planted issues and how each was handled

The full row-by-row record, with before and after values, is in `outputs/changelog.md`
(12 entries, regenerated on every run of `python -m backend.clean_data`).

| # | Issue | Where | Handling | Metrics affected |
|---|---|---|---|---|
| 1 | Mixed date formats | CP-02, PM-01 go-live dates | Converted to YYYY-MM-DD | Months live, so average monthly benefit, payback, run-rate |
| 2 | ID casing and stray spaces | ` cp-02` in all three files | Trimmed and upper-cased | All metrics for CP-02 (rows would not join otherwise) |
| 3 | Duplicate row | BOT-02 week 2 usage | Exact repeat removed, first kept | None here (week 2 is neither first nor latest), but prevents double counting |
| 4 | Missing value | PM-02 week 2 usage | Left empty and logged | None here (week 2 is neither first nor latest) |
| 5 | Mixed money units | CP-01, BOT-02 in INR lakh | Multiplied by 100,000 | Average monthly benefit and run-rate versus plan. ROI and payback are ratios and do not change |
| 6 | Negative cost | BOT-01 | Absolute value used, flagged | ROI, payback and status |
| + | Three names for one metric | `WAU`, `weekly_active_users`, `active_users_wk` | Mapped to `weekly_active_users` | Adoption and WAU change |

Worked illustration of issue 6 (hand calculation, not a scorecard figure): with the raw cost of
-2,000,000 and benefit of 2,700,000, ROI would be (2,700,000 + 2,000,000) / -2,000,000 = -2.35,
which would mark BOT-01 Red. After the fix the scorecard gives ROI 0.35 and, with adoption at 60%,
status Green.

## 5. How this is tested

`tests/test_clean_data.py` (11 tests) checks that the cleaned files have six unique IDs, ISO
dates, one row per initiative and week, money in INR with no negative cost, that every planted
issue appears in the change log with before, after and effect, that raw files are untouched, and
that unknown units, unknown metric names, conflicting rows and unknown date formats stop the run.

## 6. Known limitations

- Rules cover the issue types we planted. A new kind of issue (for example a different currency)
  stops the run with an error and needs a rule added.
- The sign-error assumption for negative cost needs confirmation from the data owner.
- With only three weeks of usage, WAU change is sensitive to a single unusual week.
