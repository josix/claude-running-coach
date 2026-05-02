# Fetch Garmin Activity — Instructions

## Prerequisites

- `users.json.integrations.garmin.connected == true` — if false, abort with a prompt to run `/run-init --connect garmin`.
- `mcp__garmin__garmin_sync`, `mcp__garmin__garmin_query`, and `mcp__garmin__garmin_activity_detail` available in tool list.

---

## High-level flow

1. **Refresh** the local DB by calling `garmin_sync(refresh=true)`. This is the only step that touches Garmin live — it triggers SeleniumBase UC mode (undetected Chrome) to satisfy Cloudflare, downloads new activities, and writes them to the local SQLite. Auth and Cloudflare failures surface here.
2. **List** recent running activity IDs via `garmin_query` against the `activity` table (the `garmin_activities` tool returns key fields but **omits `activity_id`**, which is required for dedup, so we use SQL).
3. **Detail** each activity via `garmin_activity_detail(activity_id=...)` to get the full record (activity summary + splits + HR zones + weather + running dynamics).
4. **Normalize, dedupe, analyze, adapt** — same pipeline as Strava and manual logging.

---

## Step 1 — Refresh the local DB

Call `mcp__garmin__garmin_sync(refresh=true)`. Parse the JSON-string result. Expected shape:

```json
{
  "today": "2026-05-02",
  "latest_data_date": "2026-05-01",
  "is_stale": false,
  "freshness_by_table": {...},
  "last_sync": { "sync_date": "...", "status": "success", ... },
  "last_sync_ago": "5 minutes ago",
  "sync": { "status": "success", "result": {...} }
}
```

Decision rules:
- If `sync.status == "success"`: continue to Step 2.
- If `sync.status == "error"` and the error message mentions auth keywords (`unauthorized`, `401`, `mfa`, `login`, `password`, `credentials`): set `last_sync_status = "error:auth"`, surface the message, abort. Tell the user to re-run `garmin-givemydata` in a terminal to re-prompt for credentials.
- If the error message mentions `cloudflare`, `403`, `429`, `bot`, or `clearance`: set `last_sync_status = "error:auth"` (Cloudflare = effectively an auth failure), surface the message, abort. Tell the user the `cf_clearance` cookie expired (often because their egress IP changed) and to re-run `garmin-givemydata` in a terminal.
- If the error mentions `network`, `timeout`, `dns`, `connection`: set `last_sync_status = "error:network"`, surface the message, abort.
- Any other error: set `last_sync_status = "error:unknown"`, surface verbatim, abort.

If `garmin_sync` succeeds but `latest_data_date` is older than today by more than the requested window, log a warning but continue — read tools still work against whatever data is local.

**Note**: The full sync can take 30–120 seconds depending on history size. Set MCP tool timeouts accordingly.

---

## Step 2 — List recent running activity IDs

Determine the date range. Default: last 7 days. The user may pass a date override via `/run-sync <date>`.

Call `mcp__garmin__garmin_query` with:

```sql
SELECT activity_id, activity_type, start_time_local, distance_meters, moving_duration_seconds
FROM activity
WHERE activity_type IN ('running', 'track_running', 'trail_running', 'treadmill_running', 'virtual_run', 'indoor_running')
  AND DATE(start_time_local) >= '<YYYY-MM-DD start>'
  AND DATE(start_time_local) <= '<YYYY-MM-DD end>'
ORDER BY start_time_local DESC
LIMIT 100
```

Parse the JSON-string result. Each row is a dict with `activity_id`, `activity_type`, `start_time_local`, etc. Empty result is fine — just nothing to sync.

For each row, extract `activity_id` (integer) and the date portion of `start_time_local` (split on space, take `[0]` → `"2026-05-01"`).

---

## Step 3 — Fetch detail for each activity

For each `activity_id` from Step 2:

1. Call `mcp__garmin__garmin_activity_detail(activity_id=<id>)`. Parse the JSON-string result into a `detail` dict.
2. Call `normalize_activity(detail)` from `garmin_normalize.py`.
3. If `None` is returned, skip silently (non-run, too short, no distance, or missing activity_id).

The normalized dict keys: `duration_min`, `distance_km`, `avg_pace_per_km_s`, `avg_hr`, `max_hr`, `rpe` (always None), `splits`, `notes` (always empty), `garmin_activity_id`.

**Note**: `rpe` is always `None` — Garmin activities have no description field for parsing perceived exertion. Coach should treat null `rpe` as "unknown" (not as 0).

---

## Step 4 — Deduplicate

Use `is_duplicate(workouts, "garmin", normalized["garmin_activity_id"])` from `garmin_normalize.py` to check whether the activity is already in `workouts.json`. Skip if duplicate.

For same-date conflicts between sources (e.g., the user has Strava and Garmin both connected for the same run), use `upsert_workout(workouts, new_workout, preferred_source)`:

- If incoming `source == preferred_source` and an existing entry from a different source is on the same date: mark the existing entry as `superseded_by: <new_id>` (kept in the file for history) and append the new one.
- If incoming `source != preferred_source` and `preferred_source` already has an entry on that date: skip the incoming entry.

**Important**: Use `is_duplicate` and `upsert_workout` from `garmin_normalize.py`, not from `strava_normalize.py` — they are duplicated by design for source isolation.

---

## Step 5 — Build the full workout record

For each accepted normalized activity, build:

```json
{
  "id": "wkt-YYYY-MM-DD-NNN",
  "date": "<YYYY-MM-DD from start_time_local>",
  "source": "garmin",
  "prescribed": "<look up from plan.json by date, or null>",
  "actual": "<the normalized dict from normalize_activity>",
  "analysis": "<call analyze-workout skill>"
}
```

`NNN` handles multi-session days — increment per existing entry on that date.

---

## Step 6 — Analyze and upsert

1. Call the `analyze-workout` skill with the `actual` dict and the `prescribed` workout (if found in `plan.json` for that date). Receive an `analysis` dict with `completion_pct`, `pace_delta_pct`, `rpe_delta`, `hr_drift_bpm`, `verdict`.
2. Call `upsert_workout(workouts, new_workout, preferred_source)` to merge the record into the in-memory list.
3. Hand the analysis off to Coach for `adapt-plan`.

After processing all activities, write the full updated `workouts` array back to `storage/workouts.json` in a single read-modify-write — never write individual records.

---

## Step 7 — Update integration status

Set `users.json.integrations.garmin`:
- `last_sync_at` → current ISO 8601 timestamp.
- `last_sync_status` → `"ok"`.

If a daily-state update is appropriate for the most recent activity, update `daily_state.json` accordingly.

---

## Error handling summary

| Error condition | `last_sync_status` | User message |
|---|---|---|
| `garmin_sync` returns auth-related error | `error:auth` | "Garmin auth expired or Cloudflare session lost. Run `garmin-givemydata` in a terminal to re-authenticate (it will prompt for email/password/MFA), then re-run `/run-sync`." |
| `garmin_sync` returns Cloudflare/bot-detection error | `error:auth` | "Garmin's Cloudflare protection rejected the request — most often because your egress IP changed since the last successful sync (cf_clearance is IP-bound). Run `garmin-givemydata` from the same network/IP you'll keep using." |
| MCP tool unavailable | `error:mcp_unavailable` | "garmin-givemydata MCP server not available — check your MCP config and that `garmin-mcp` is on PATH." |
| Network error during sync | `error:network` | "Network error reaching Garmin — check your connection." |
| `garmin_query` SQLite error (e.g., schema drift) | `error:unknown` | Surface verbatim error; suggest `garmin-givemydata --status` for diagnosis. |
| Any other error | `error:unknown` | Surface verbatim error message. |

**On any error, do not write partial results to `workouts.json`.** Update `users.json.integrations.garmin.last_sync_status` with the error code, then report to the user.

---

## Field defaults when Garmin data is missing

- No `avg_hr` → `avg_hr = null`, `max_hr = null`. `analyze-workout` handles null gracefully.
- Empty splits array → `splits = []`; HR drift will not be computed.
- `distance_km == 0` or `duration_min < 5` → activity skipped entirely (returns `None`).
- `rpe` is always `null` — Garmin activities have no description field.
- The trailing tiny "overshoot" split (e.g., 5 m / 1 s) is automatically dropped by `normalize_activity` to avoid garbage paces.
