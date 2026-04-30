---
name: analyze-workout
description: "Computes adherence delta between actual and prescribed workout: pace deviation %, completion %, HR drift, RPE delta. Returns a structured signal dict. Called automatically after log-workout or fetch-strava-activity."
---

# Analyze Workout

Given an actual workout and its prescribed counterpart, computes a structured adherence signal dict using the threshold rules from DESIGN.md §4. The verdict (`on-target`, `under`, `over`, `aborted`) drives the downstream `adapt-plan` strike rules. This skill is never invoked directly by the user — it is always called programmatically by `log-workout` or `fetch-strava-activity`.

## When to use

- Immediately after `log-workout` captures user input.
- Immediately after `fetch-strava-activity` normalizes a Strava activity.
- When re-analyzing historical workouts (e.g., after a data correction).

## Outputs

A dict `{completion_pct, pace_delta_pct, rpe_delta, hr_drift_bpm, verdict}` stored in `workouts.json[].analysis` and returned in-memory to the caller for immediate use by `adapt-plan`.

See `body.md` for full instructions and `scripts/analyze.py` for the deterministic delta computation.
