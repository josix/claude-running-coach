# Workouts Schema

File: `storage/workouts.json`

## Purpose

An append-only log of every completed workout, keyed by date and a sequence number. Each entry records both what was prescribed and what was actually done, along with the analysis verdict computed at log time by the `analyze-workout` skill. This file is the raw data source for rolling progress stats and for the strike-rule engine in `adapt-plan`.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Schema version; currently `1` |
| `workouts` | object[] | Ordered array of workout entries, one per completed session (see Workout Object below) |

## Workout Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique workout ID in the format `wkt-YYYY-MM-DD-NNN`, where NNN handles multi-session days (e.g., `"wkt-2026-01-01-001"`) |
| `date` | string | ISO date the workout was performed |
| `source` | string | How the workout was captured: `"manual"` (via `/run-log`) or `"strava"` (via `/run-sync`) |
| `strava_activity_id` | string\|null | Strava activity ID for deduplication; `null` for manually logged workouts |
| `prescribed` | object | What the plan called for (see Prescribed Object below) |
| `actual` | object | What the runner actually did (see Actual Object below) |
| `analysis` | object | Computed adherence metrics (see Analysis Object below) |

## Prescribed Object

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Workout type from plan: `"E"`, `"L"`, `"T"`, `"I"`, `"R"`, `"M"`, `"Strides"`, `"Recovery"` |
| `duration_min` | integer | Prescribed workout duration in minutes |
| `target_pace_per_km_s` | integer | Target pace in seconds per km (resolved from `users.json paces` at log time) |
| `notes` | string | Original coach notes from the plan day |

## Actual Object

| Field | Type | Description |
|-------|------|-------------|
| `duration_min` | number | Actual workout duration in minutes |
| `distance_km` | number | Actual distance covered in kilometres |
| `avg_pace_per_km_s` | integer | Average pace in seconds per km |
| `avg_hr` | integer\|null | Average heart rate in bpm; `null` if not available |
| `max_hr` | integer\|null | Peak heart rate in bpm; `null` if not available |
| `rpe` | integer | Runner's perceived exertion on a 1–10 scale |
| `splits` | object[] | Array of per-km split objects `{ "km": integer, "pace_per_km_s": integer }`; may be empty |
| `notes` | string | Free-text notes from the runner |

## Analysis Object

| Field | Type | Description |
|-------|------|-------------|
| `completion_pct` | number | Actual duration ÷ prescribed duration × 100 |
| `pace_delta_pct` | number | Signed percentage: positive means slower than target, negative means faster |
| `rpe_delta` | integer | Signed difference: actual RPE minus expected RPE for this workout type |
| `hr_drift_bpm` | number\|null | Intra-session heart rate drift (last-km avg HR minus first-km avg HR); `null` if HR data unavailable |
| `verdict` | string | Overall workout verdict: `"on-target"`, `"under"`, `"over"`, or `"aborted"` |

## Written by

WorkoutLogger / DataFetcher. The `analyze-workout` skill computes the `analysis` block before the entry is appended; once written, entries are never modified.

## Example

See `workouts.example.json` for a full example entry showing all fields.
