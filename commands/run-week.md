---
description: Weekly review — past 7 days rollup, fatigue check, hold/advance/recovery decision.
argument-hint: "[--week N, defaults to current]"
---

# /run-week

## Purpose

Get a structured review of the past 7 days — completed vs. prescribed volume, quality session adherence, fatigue indicators, and a coach decision on whether to hold, advance, or trigger a recovery week.

Run this once at the end of each training week (or any time you want a mid-week check-in).

## Inputs

- **--week N** (optional): Review week number N from the macrocycle instead of the current week. Useful for reviewing previous weeks.

## Action

Delegate to **Coach**. Coach will call `weekly-review`, which:

1. Reads `storage/workouts.json` for all entries in the target week's date range.
2. Reads `storage/plan.json` to retrieve the prescribed volume and session types for that week.
3. Reads `storage/daily_state.json` for fatigue signals (consecutive misses, consecutive ahead, recurring red flags).
4. Computes the weekly summary:
   - Completed vs. prescribed duration (minutes)
   - Quality session adherence (completed / prescribed quality sessions)
   - Average RPE for the week
   - HR drift trend (if HR data present)
   - Fatigue verdict: stable / fatigued / fresh

5. Makes a hold / advance / recovery decision:
   - **Hold**: Repeat the current week template (incomplete adherence or elevated fatigue)
   - **Advance**: Move to next week as planned
   - **Recovery**: Insert an unscheduled recovery week (volume −30–40%, drop one quality session)

6. Writes the weekly summary to `storage/progress.json` → `weekly_summaries[]`.
7. Updates `storage/progress.json` → `rolling_7d` and `rolling_28d` stats.

## Output

```
Weekly Review — Week 3 (Base Phase)

Completed: 215 min / 240 min prescribed (90%)
Quality sessions (workouts at T, I, R, or M intensity): 1 / 2 completed
Average RPE: 5.2 / 10  (RPE — Rate of Perceived Exertion: 1 = walking, 10 = all-out sprint)
HR Drift Avg: 1.8 bpm  (HR drift — heart rate creeping up at steady effort; a fatigue/heat signal)
Fatigue: Stable

Decision: ADVANCE — Week 4 (recovery week — ~70% volume to absorb training, −20% volume)

Next week focus: Maintain aerobic base. Wednesday is your scheduled recovery step-back.
```
