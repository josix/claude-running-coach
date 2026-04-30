# Fetch Strava Activity — Instructions

## v1 Stub Behavior

Strava integration is planned for v2. When this skill is invoked in v1, return the following message and stop:

> "Strava sync is coming in v2 — for now, use `/run-log` to manually record your workout. Your data will be preserved and fully compatible when Strava sync arrives."

Do not attempt any MCP tool calls or file writes.

---

## v2 Full Implementation (reference — do not implement in v1)

### Inputs

- `--days N`: lookback window in days (from `/run-sync --days N`; default 1).
- `storage/users.json`: `integrations.strava.connected` must be `true`.
- `storage/workouts.json`: existing entries to deduplicate against.
- `storage/plan.json`: prescribed workouts for date lookup.

### Steps

1. Check `users.json.integrations.strava.connected`. If `false`, abort with: "Strava not connected. Run `/run-init --connect strava` to set up the integration."
2. Call the Strava MCP tool (discover tool name at runtime — expected: `mcp__strava-mcp__get-recent-activities` or similar) with `days=N`.
3. Filter returned activities: keep only `type == "Run"`. Skip Walk, Hike, Ride, etc.
4. For each Run activity, normalize fields:

   | Strava field | Internal field | Transform |
   |---|---|---|
   | `distance` (m) | `distance_km` | ÷ 1000 |
   | `moving_time` (s) | `duration_min` | ÷ 60 |
   | `average_speed` (m/s) | `avg_pace_per_km_s` | `1000 / average_speed` |
   | `average_heartrate` | `avg_hr` | direct |
   | `max_heartrate` | `max_hr` | direct |
   | `splits_metric[].average_speed` | `splits[].pace_per_km_s` | `1000 / avg_speed` |
   | `splits_metric[].average_heartrate` | `splits[].avg_hr` | direct |
   | `description` | `notes` | parse "RPE: N" or "feeling: N/10" patterns |
   | `id` | `strava_activity_id` | direct |

5. Deduplicate: check `workouts.json` for any existing entry with matching `strava_activity_id`. Skip duplicates.
6. For each new activity, look up the prescribed workout for `activity.start_date_local` from `plan.json`.
7. Call `analyze-workout` with actual + prescribed dicts.
8. Append normalized workout record to `workouts.json` (read-modify-write).
9. Call `adapt-plan` with the analysis delta.
10. Report to user: "Synced {N} new activities. {summary of verdicts}."

### Field defaults when Strava data is missing

- No `average_heartrate` → `avg_hr = null`, `max_hr = null`. analyze-workout handles null gracefully.
- No `description` → `notes = null`; RPE will not be parsed (analyze-workout skips RPE delta).
- No `splits_metric` → `splits = []`; HR drift will not be computed.

## Edge cases

- **MCP tool name differs at runtime**: log a warning and fall back to the v1 stub message.
- **Activity type is Walk or Hike**: skip silently.
- **Strava API rate limit exceeded**: surface the error and suggest retrying in 15 minutes.
- **`avg_speed` is 0** (stationary activity): skip; would produce infinite pace.
