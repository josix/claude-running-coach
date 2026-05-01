---
description: Pull recent Strava activities and apply the same adaptive pipeline as /run-log. Requires Strava connection (run /run-init --connect strava first).
argument-hint: "[--days N]"
---

# /run-sync

## Purpose

Automatically import your most recent Strava activities into the training log without a manual interview. Each imported activity goes through the same analysis and adaptation pipeline as `/run-log`.

## Inputs

- **--days N** (optional): Look back N days for Strava activities. Default is 1. Max is 7. Values above 7 are clamped to 7 with a one-line warning. Values below 1 are an error.

## Action

Delegate to **DataFetcher**. DataFetcher will:

1. **Check connection** — read `storage/users.json` → `integrations.strava.connected`. If `false` or the file does not exist:
   > Strava is not connected. Use `/run-log` for manual logging, or run `/run-init --connect strava` to connect your Strava account.

2. **Parse `--days N`** — default 1, clamp 1..7.

3. **Fetch activities** — call the Strava MCP to retrieve activities in the lookback window.

4. **Normalize** — call `normalize_activity` from `strava_normalize.py` for each activity. Skip non-runs, activities < 5 minutes, and zero-distance activities.

5. **Upsert** — for each normalized activity, call `upsert_workout` with `preferred_source` from `users.json`. Handles deduplication and same-date conflicts.

6. **Analyze + adapt** — call `analyze-workout` for each new activity, then hand results to Coach for `adapt-plan`.

7. **Update storage** — write `workouts.json`, `daily_state.json`, and `users.json` sync metadata.

8. **Report** — summarize synced activities with counts and verdicts.

Updates `storage/workouts.json`, `storage/daily_state.json`, and possibly `storage/plan.json` + `storage/users.json` when adaptation fires.

## Failure modes

If DataFetcher encounters an error, it will report the relevant message and record `last_sync_status` in `users.json.integrations.strava`:

| What the user sees | Cause | What to do |
|---|---|---|
| "Strava rate limit reached — retry in 15 minutes." | Strava API rate limit (429) | Wait 15 minutes and re-run |
| "Strava auth expired — re-run `/run-init --connect strava`." | Token expired or revoked | Re-run the Strava probe to refresh the connection |
| "Strava MCP server not available — check MCP config." | MCP server not loaded | Check Claude Code MCP configuration, restart if needed |
| Verbatim error message | Unexpected API error | Investigate the error; try again or use `/run-log` |

On any error, no partial results are written to `workouts.json`.
