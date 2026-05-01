---
name: fetch-strava-activity
description: "Pulls recent run activities from the Strava MCP server, normalizes them to the workouts.json schema using strava_normalize.py helpers, deduplicates by strava_activity_id with preferred_source tiebreaker, and runs the same analyze-workout + adapt-plan pipeline as manual logging. Requires users.integrations.strava.connected = true."
---

# Fetch Strava Activity

Connects to the Strava MCP server, retrieves recent run activities, normalizes each to the internal workout schema via `scripts/strava_normalize.py`, deduplicates against existing `workouts.json` entries, and runs the same `analyze-workout` + `adapt-plan` pipeline as manual logging.

## When to use

- DataFetcher agent is invoked via `/run-sync`.
- `users.json.integrations.strava.connected == true` (set by a successful `/run-init --connect strava` probe).

## Normalization

Field mapping is implemented in `scripts/strava_normalize.py` — call `normalize_activity(activity_dict)` on each Strava activity. The function returns `None` for non-run activities, activities shorter than 5 minutes, or activities with zero distance; skip those silently.

## Outputs

Normalized workout records appended to `storage/workouts.json` (via `upsert_workout` from `strava_normalize.py`), analysis and adapt-plan signals applied, `users.json.integrations.strava.last_sync_at` and `last_sync_status` updated.

See `body.md` for the full step-by-step instructions, error handling, and deduplication semantics.
