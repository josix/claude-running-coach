---
description: Pull recent activities from Strava and apply same adaptive pipeline as /run-log. Requires Strava connection (v2 feature).
argument-hint: "[--days N, default 1]"
---

# /run-sync

## Purpose

Automatically import your most recent Strava activities into the training log without a manual interview. Each imported activity goes through the same analysis and adaptation pipeline as `/run-log`.

**v1 status**: Strava sync is a v2 feature. In v1, this command returns a friendly message and instructs you to use `/run-log` for manual logging.

## Inputs

- **--days N** (optional): Look back N days for Strava activities. Default is 1 (yesterday + today). Max is 7.

## Action

Delegate to **DataFetcher**. DataFetcher will:

1. Check `storage/users.json` → `integrations.strava.connected`. If `false` or the file does not exist, return:
   > Strava not connected. Use `/run-log` for manual logging, or run `/run-init --connect strava` (v2 feature) to enable sync.

2. **(v2 behavior, not yet active)** Call `fetch-strava-activity` to pull activities from the Strava MCP within the `--days` window. Deduplicate against existing `workouts.json` entries by `strava_activity_id`. For each new activity, run `analyze-workout` then hand to **Coach** for `adapt-plan`.

Updates `storage/workouts.json`, `storage/daily_state.json`, and possibly `storage/plan.json` + `storage/users.json` when adaptation fires (same as `/run-log`).

## v1 Reminder

Use `/run-log` for manual workout entry. The `/run-sync` workflow will be fully functional once Strava MCP integration ships in v2. To prepare, run `/run-init --connect strava` to save your intent, so migration requires no re-onboarding.
