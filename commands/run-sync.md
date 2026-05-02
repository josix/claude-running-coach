---
description: Pull recent activities from the connected provider (Strava or Garmin Connect) and apply the same adaptive pipeline as /run-log. Requires at least one connection (run /run-init --connect strava|garmin first).
argument-hint: "[--days N]"
---

# /run-sync

## Purpose

Automatically import your most recent running activities into the training log without a manual interview. Each imported activity goes through the same analysis and adaptation pipeline as `/run-log`.

## Inputs

- **--days N** (optional): Look back N days for activities. Default is 1. Max is 7. Values above 7 are clamped to 7 with a one-line warning. Values below 1 are an error.

## Action

Delegate to **DataFetcher**. DataFetcher will:

1. **Check connection** — read `storage/users.json` → `integrations`. If neither `integrations.strava.connected` nor `integrations.garmin.connected` is `true` (or the file does not exist):
   > No activity source is connected. Use `/run-log` for manual logging, or run `/run-init --connect strava` or `/run-init --connect garmin` to connect an account first.

2. **Auto-detect provider** — if exactly one provider is connected, use it. If both are connected, use `integrations.preferred_source` as the tiebreaker.

3. **Parse `--days N`** — default 1, clamp 1..7.

4. **Fetch activities** — call the appropriate MCP to retrieve activities in the lookback window.
   - Strava: `mcp__strava__get-recent-activities` / `mcp__strava__get-all-activities`
   - Garmin (via `nrvim/garmin-givemydata`): `mcp__garmin__garmin_sync(refresh=true)` to refresh the local SQLite, then `mcp__garmin__garmin_query` to list run activity_ids in the date range, then `mcp__garmin__garmin_activity_detail(activity_id=...)` per activity for the full record (splits + HR zones + weather are bundled in the detail response).

5. **Normalize** — call `normalize_activity` from the provider-specific script. Skip non-runs, activities < 5 minutes, and zero-distance activities.

6. **Upsert** — for each normalized activity, call `upsert_workout` with `preferred_source` from `users.json`. Handles deduplication and same-date conflicts.

7. **Analyze + adapt** — call `analyze-workout` for each new activity, then hand results to Coach for `adapt-plan`.

8. **Update storage** — write `workouts.json`, `daily_state.json`, and `users.json` sync metadata for the active provider.

9. **Report** — summarize synced activities with counts and verdicts.

Updates `storage/workouts.json`, `storage/daily_state.json`, and possibly `storage/plan.json` + `storage/users.json` when adaptation fires.

## Failure modes

If DataFetcher encounters an error, it will report the relevant message and record `last_sync_status` in `users.json.integrations.<provider>`:

| What the user sees | Cause | What to do |
|---|---|---|
| "Strava rate limit reached — retry in 15 minutes." | Strava API rate limit (429) | Wait 15 minutes and re-run |
| "Strava auth expired — re-run `/run-init --connect strava`." | Strava token expired or revoked | Re-run the Strava probe to refresh the connection |
| "Strava MCP server not available — check MCP config." | Strava MCP server not loaded | Check Claude Code MCP configuration, restart if needed |
| "Strava sync failed due to a network issue — check connectivity and retry." | Network/DNS/timeout during Strava call | Check connectivity and retry once your network is stable |
| "Garmin authentication failed or MFA needed." | Garmin credential / MFA error from `garmin_sync` | Run `garmin-givemydata` in a terminal to re-prompt for email / password / MFA, then re-run `/run-sync` |
| "Garmin Cloudflare check failed — re-run `garmin-givemydata` from your usual network." | Cloudflare rejected the sync (cf_clearance expired or IP changed) | The `cf_clearance` cookie is bound to your egress IP. Re-run `garmin-givemydata` from a stable IP, then re-run `/run-sync` |
| "Garmin Connect MCP server not available — check MCP config." | `mcp__garmin__*` tools not loaded | Install `nrvim/garmin-givemydata` via `uv tool install garmin-givemydata` (or pipx), register `garmin-mcp` under namespace `garmin` in your Claude Code MCP config, and restart |
| "Network error reaching Garmin." | Connectivity / DNS / timeout during `garmin_sync` | Check connection; retry once your network is stable |
| "Garmin sync failed (uncategorized error)." | Unexpected error from `garmin_sync`, `garmin_query`, or `garmin_activity_detail` | Run `garmin-givemydata --status` for diagnosis; surface verbatim error to the user |
| Verbatim error message | Unexpected API error | Investigate the error; try again or use `/run-log` |

On any error, no partial results are written to `workouts.json`.
