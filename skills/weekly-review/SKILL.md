---
name: weekly-review
description: "Aggregates the past 7 days of completed workouts: total mileage, quality session adherence, fatigue indicators (RPE creep, HR drift). Decides hold/advance/recovery for the next week. Use for /run-week."
---

# Weekly Review

Computes a structured summary of the past training week by comparing `workouts.json` actuals against `plan.json` prescriptions for that week number. The deterministic aggregation (volume, quality counts, RPE creep, HR drift) runs in `scripts/weekly.py`. Claude renders the results as a human-readable report and, if the verdict is `recovery`, triggers `adapt-plan` to insert a recovery week.

## When to use

- The user runs `/run-week` (optionally with `--week N`; defaults to the current plan week).
- Coach performs an automated end-of-week check after the last workout of the week is logged.

## Outputs

A weekly summary dict appended to `storage/progress.json.weekly_summaries` and a Markdown report displayed to the user. If verdict is `recovery`, `plan.json` is also modified via `adapt-plan`.

See `body.md` for full instructions and `scripts/weekly.py` for the aggregation logic.
