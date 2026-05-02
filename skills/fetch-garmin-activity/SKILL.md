---
name: fetch-garmin-activity
description: "Pulls recent run activities from the garmin-givemydata MCP server: triggers garmin_sync to refresh the local SQLite, queries activity IDs in the requested date range, fetches per-activity detail (with splits, HR zones, weather, running dynamics), normalizes to workouts.json schema via garmin_normalize.py, deduplicates by garmin_activity_id with preferred_source tiebreaker, and runs the same analyze-workout + adapt-plan pipeline as manual logging. Requires users.integrations.garmin.connected = true."
---

# Fetch Garmin Activity

Connects to the `nrvim/garmin-givemydata` MCP server (the `Taxuspt/garmin_mcp` server is no longer supported — Garmin's March 2026 Cloudflare deployment broke `garth`-based servers). Triggers a live sync to refresh the local SQLite DB, queries recent run activity IDs, fetches per-activity detail, normalizes each to the internal workout schema via `scripts/garmin_normalize.py`, deduplicates against existing `workouts.json` entries, and runs the same `analyze-workout` + `adapt-plan` pipeline as manual logging.

## When to use

- DataFetcher agent is invoked via `/run-sync`.
- `users.json.integrations.garmin.connected == true` (set by a successful `/run-init --connect garmin` probe).

## Architecture

`garmin-givemydata` exposes a SQLite-backed MCP server. Read tools (`garmin_activities`, `garmin_activity_detail`, `garmin_query`, `garmin_user_profile`) hit the local DB only and never touch Garmin live. The single tool that does live Garmin access is `garmin_sync`, which uses SeleniumBase UC mode (undetected Chrome) to bypass Cloudflare. This means **all auth/Cloudflare failures surface in the `garmin_sync` step** — the read tools afterwards always succeed (or surface SQLite errors, not network errors).

## Normalization

Field mapping is implemented in `scripts/garmin_normalize.py` — call `normalize_activity(detail)` on each `garmin_activity_detail` response. The detail dict has top-level keys `activity`, `splits`, `hr_zones`, `weather`, `exercise_sets`, `running_dynamics` — pass the whole dict, not just `activity`. The function returns `None` for non-run activities, activities shorter than 5 minutes, activities with zero distance, or activities missing `activity_id`; skip those silently.

## Outputs

Normalized workout records appended to `storage/workouts.json` (via `upsert_workout` from `garmin_normalize.py`), analysis and adapt-plan signals applied, `users.json.integrations.garmin.last_sync_at` and `last_sync_status` updated.

See `body.md` for the full step-by-step instructions, error handling, and deduplication semantics.
