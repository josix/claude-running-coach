---
name: adapt-plan
description: "Applies 1/2/3-strike adjustment rules to plan.json based on a single workout's analysis dict. Mutates plan only when thresholds fire. Called after every workout log."
---

# Adapt Plan

Reads the analysis verdict from `analyze-workout`, updates the consecutive miss/ahead counters in `daily_state.json`, and applies the appropriate adaptation rule to `plan.json` when a threshold fires. The strike-rule logic is fully deterministic and implemented in `scripts/adapt.py`. Claude's role is to invoke the script, interpret the returned `action`, and — for `vdot_bump` — trigger `compute-vdot` to regenerate paces before re-resolving future plan entries.

## When to use

- Immediately after `analyze-workout` returns a verdict, called by `log-workout` or `fetch-strava-activity`.
- When `adapt-plan` returns `red_flag_recovery` and a recovery block must be inserted.

## Outputs

Updated `storage/plan.json` (if action mutates the plan) and updated `storage/daily_state.json` (always). Returns the action string to the caller for display.

See `body.md` for full instructions and `scripts/adapt.py` for the rule engine.
