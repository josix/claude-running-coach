# Users Schema

File: `storage/users.json`

## Purpose

Stores the single user's profile, fitness baseline, training preferences, and integration status. This is the authoritative record of who the runner is and what they can do today. The Coach agent populates this file during `/run-init` and updates `current_fitness` whenever a new VDOT is computed (e.g., after a race or time-trial).

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Schema version; currently `1` |
| `user_id` | string | Always `"default"` in v1 (single-user plugin) |
| `created_at` | string | ISO 8601 timestamp of initial profile creation |
| `profile` | object | Demographic info (see Profile Object below) |
| `current_fitness` | object | Current VDOT and derived pace table (see Fitness Object below) |
| `preferences` | object | Training and UX preferences (see Preferences Object below) |
| `lifestyle` | object | Sleep, stress, injury history, and scheduling constraints (see Lifestyle Object below) |
| `integrations` | object | Third-party integration status (see Integrations Object below) |

## Profile Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Runner's display name |
| `age` | integer | Runner's age in years |
| `sex` | string | `"M"` or `"F"` — used by some VDOT HR-zone formulas |
| `weight_kg` | number | Body weight in kilograms |

## Fitness Object

| Field | Type | Description |
|-------|------|-------------|
| `vdot` | number | Current VDOT score (Jack Daniels formula); canonical fitness metric |
| `vdot_source` | string | How the VDOT was determined (e.g., `"5K time-trial"`, `"10K race"`) |
| `vdot_source_date` | string | ISO date of the performance used to compute VDOT |
| `vdot_source_result` | object | `{ "distance_m": integer, "time_s": integer }` — the raw performance |
| `paces` | object | Derived training paces in seconds per km (see Paces Object below) |
| `weekly_mileage_baseline_km` | number | Current weekly volume baseline; used by macrocycle builder for ramp-up math |

## Paces Object

| Field | Type | Description |
|-------|------|-------------|
| `easy_per_km_s` | integer | Easy/recovery pace (seconds per km); ~65–79% vVO2max |
| `marathon_per_km_s` | integer | Marathon goal pace (seconds per km) |
| `threshold_per_km_s` | integer | Threshold/tempo pace (seconds per km); ~83–88% vVO2max |
| `interval_per_km_s` | integer | Interval pace (seconds per km); ~95–100% vVO2max |
| `repetition_per_km_s` | integer | Repetition/speed pace (seconds per km); >100% vVO2max |

## Preferences Object

| Field | Type | Description |
|-------|------|-------------|
| `workout_unit` | string | `"time"` (default) or `"distance"` — controls how workout cards are presented |
| `methodology` | string | Training methodology: `"polarized"` (default) |
| `training_days` | string[] | Days of the week available for running, e.g., `["Tue","Thu","Sat","Sun"]` |
| `rest_days_sacred` | boolean | If `true`, the adapter never inserts make-up workouts on rest days |
| `long_run_day` | string | Day designated for the long run (e.g., `"Sun"`) |
| `quality_days` | string[] | Days eligible for T/I/R quality sessions; no back-to-back quality enforced |
| `language` | string | Locale for workout card output (e.g., `"zh-TW"`, `"en"`) |

## Lifestyle Object

| Field | Type | Description |
|-------|------|-------------|
| `typical_sleep_hours` | number | Average nightly sleep; used as a passive fatigue signal |
| `stress_level` | string | `"low"`, `"moderate"`, or `"high"` — informs initial volume setting |
| `injury_history` | string[] | Free-text descriptions of past injuries (for Coach context) |
| `constraints_notes` | string | Free-text scheduling notes (e.g., `"no running on weekday mornings"`) |

## Integrations Object

| Field | Type | Description |
|-------|------|-------------|
| `preferred_source` | string | `"manual"` \| `"strava"` \| `"garmin"`. Tiebreaker for same-date workouts arriving from multiple sources. Defaults to `"manual"`; flips to `"strava"` only after a successful probe via `probe-strava-connection`. |
| `strava` | object | See Strava Object below. |
| `garmin` | object | Reserved for v2 Garmin Connect integration. See Garmin Object below. |

## Strava Object

| Field | Type | Description |
|-------|------|-------------|
| `connected` | boolean | `true` only after `probe-strava-connection` returns `ok`. Never set `true` from the `--connect` flag alone. |
| `athlete_id` | integer\|null | Strava athlete numeric id, captured from `get-athlete` response. |
| `connected_at` | string (ISO 8601)\|null | When the probe last succeeded. |
| `last_sync_at` | string (ISO 8601)\|null | When DataFetcher last successfully ingested activities. |
| `last_sync_status` | string\|null | `null` \| `"ok"` \| `"error:auth"` \| `"error:rate_limit"` \| `"error:mcp_unavailable"` \| `"error:network"` \| `"error:unknown"` |

## Garmin Object

| Field | Type | Description |
|-------|------|-------------|
| `connected` | boolean | Reserved; not wired in v0.2.0. |
| `user_id` | string\|null | Reserved. |
| `connected_at` | string\|null | Reserved. |
| `last_sync_at` | string\|null | Reserved. |
| `last_sync_status` | string\|null | Reserved. |

## Written by

Coach (during `/run-init` and `/run-race-recap`; `current_fitness.vdot` also updated by `adapt-plan` when 3+ consecutive "over" workouts trigger a VDOT bump).

## Example

See `users.example.json` for a full example.
