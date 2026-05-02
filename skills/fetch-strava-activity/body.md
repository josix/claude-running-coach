# Fetch Strava Activity — Instructions

## Prerequisites

- `users.json.integrations.strava.connected == true` — if false, abort with a prompt to run `/run-init --connect strava`.
- `mcp__strava__get-recent-activities` available in tool list (and `mcp__strava__get-all-activities` if a date-range query is needed for `--days > 1`).

---

## Normalization

Field mapping is implemented in `scripts/strava_normalize.py` — call `normalize_activity(activity_dict)` on each Strava activity. You do not need to perform field mapping manually; the Python helper handles all transforms and filters.

The helper returns `None` to skip if:
- `sport_type` / `type` is not in `{Run, TrailRun, VirtualRun}` — skip silently
- `moving_time` < 300 seconds (< 5 min) — skip silently
- `distance == 0` or missing — skip silently

On a successful return, the dict contains: `duration_min`, `distance_km`, `avg_pace_per_km_s`, `avg_hr`, `max_hr`, `rpe`, `splits`, `notes`, `strava_activity_id`.

---

## Deduplication

Use `is_duplicate(workouts, source, source_activity_id)` from `strava_normalize.py` to check if an activity is already in `workouts.json` before processing it.

For same-date conflicts between sources, use `upsert_workout(workouts, new_workout, preferred_source)` which implements the `preferred_source` tiebreaker:

- If incoming source matches `preferred_source` and there's an existing entry from a different source on that date: mark the existing entry as `superseded_by: <new_id>`, keep it, and append the new one.
- If incoming source does not match `preferred_source` and the preferred source already has an entry on that date: skip the incoming entry.

---

## What to do with the normalized record

After receiving a normalized dict from `normalize_activity`:

1. **Build the full workout record**:
   ```json
   {
     "id": "wkt-YYYY-MM-DD-NNN",
     "date": "<activity start date>",
     "source": "strava",
     "prescribed": "<look up from plan.json by date, or null>",
     "actual": "<the normalized dict from normalize_activity>",
     "analysis": "<call analyze-workout skill>"
   }
   ```

2. **Call `analyze-workout`** with the `actual` dict and the `prescribed` workout (if found in `plan.json` for that date). The skill returns an `analysis` dict with `completion_pct`, `pace_delta_pct`, `rpe_delta`, `hr_drift_bpm`, `verdict`.

3. **Call `upsert_workout(workouts, new_workout, preferred_source)`** to add the record to the in-memory workouts list with proper deduplication.

4. **After processing all activities**, write the full updated `workouts` array back to `storage/workouts.json` in a single write (read-modify-write — never write individual records).

5. **Update `daily_state.json`** for the most recent activity processed.

6. **Update `users.json.integrations.strava`**: set `last_sync_at` to current ISO 8601 timestamp and `last_sync_status` to `"ok"`.

7. **Hand off to Coach** with each `analyze-workout` result for `adapt-plan`.

---

## Error handling

| Error condition | `last_sync_status` | User message |
|---|---|---|
| Rate limit (429 / "rate limit" in error) | `error:rate_limit` | "Strava rate limit reached — retry in 15 minutes." |
| Auth failure (token/client_id/401 in error) | `error:auth` | "Strava auth expired — re-run `/run-init --connect strava`." |
| MCP tool unavailable | `error:mcp_unavailable` | "Strava MCP server not available — check MCP config." |
| Network failure (timeout/dns/connection in error) | `error:network` | "Strava sync failed due to a network issue — check connectivity and retry." |
| Any other error | `error:unknown` | Surface verbatim error message |

**On any error, do not write partial results to `workouts.json`.** Update `users.json.integrations.strava.last_sync_status` with the error code, then report to the user.

---

## Field defaults when Strava data is missing

- No `average_heartrate` → `avg_hr = null`, `max_hr = null`. `analyze-workout` handles null gracefully.
- No `description` → `notes = ""`; RPE will not be parsed.
- No `splits_metric` → `splits = []`; HR drift will not be computed.
- `average_speed = 0` → `avg_pace_per_km_s = null` (the activity is still kept if distance and moving_time are valid).
