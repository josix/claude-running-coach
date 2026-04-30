---
name: log-workout
description: "Conversationally captures a completed workout (duration, distance, RPE, HR, splits, notes) and writes it to workouts.json. Triggers analyze-workout and adapt-plan downstream. Use for /run-log."
---

# Log Workout

Conducts a short, friendly post-workout interview to collect the user's actual session data, then assembles it into a normalized record and appends it to `storage/workouts.json`. After writing, it calls `analyze-workout` to compute the adherence delta and `adapt-plan` to apply any necessary strike-rule adjustments.

## When to use

- The user runs `/run-log` (with optional date argument, defaulting to today).
- The user wants to manually record a workout that was not synced via Strava.

## Outputs

A new workout record appended to `storage/workouts.json`, an updated `storage/daily_state.json` with carry-forward cues, and potential modifications to `storage/plan.json` if strike rules fire. The conversation ends with a brief summary of the logged workout and the analysis verdict.

See `body.md` for the interview flow and full record schema.
