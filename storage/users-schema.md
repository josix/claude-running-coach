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
| `birth_date` | string | ISO date (e.g., `"1996-05-07"`). Optional; preferred over `age` when present (age derivable). |
| `height_cm` | number | Body height in centimeters. Optional. |

## Fitness Object

| Field | Type | Description |
|-------|------|-------------|
| `vdot` | number | Current VDOT score (Jack Daniels formula); canonical fitness metric |
| `vdot_source` | string | How the VDOT was determined (e.g., `"5K time-trial"`, `"10K race"`) |
| `vdot_source_date` | string | ISO date of the performance used to compute VDOT |
| `vdot_source_result` | object | `{ "distance_m": integer, "time_s": integer }` — the raw performance |
| `paces` | object | Derived training paces in seconds per km (see Paces Object below) |
| `weekly_mileage_baseline_km` | number | Current weekly volume baseline; used by macrocycle builder for ramp-up math |
| `hr_zones` | object | HR-derived training zones (see HR Zones Object). Optional. |
| `form_metrics` | object | Cadence and form cues (see Form Metrics Object). Optional. |
| `baseline_run` | object | Snapshot of a representative easy run, used for HR/pace calibration (see Baseline Run Object). Optional. |
| `garmin_vo2max` | object | Garmin watch VO2max estimate, captured opportunistically (see Garmin VO2max Object). Optional. |
| `garmin_race_predictions` | object | Latest Garmin race-time predictions (see Garmin Race Predictions Object). Optional. |

## Paces Object

| Field | Type | Description |
|-------|------|-------------|
| `easy_per_km_s` | integer | Easy/recovery pace (seconds per km); ~65–79% vVO2max |
| `marathon_per_km_s` | integer | Marathon goal pace (seconds per km) |
| `threshold_per_km_s` | integer | Threshold/tempo pace (seconds per km); ~83–88% vVO2max |
| `interval_per_km_s` | integer | Interval pace (seconds per km); ~95–100% vVO2max |
| `repetition_per_km_s` | integer | Repetition/speed pace (seconds per km); >100% vVO2max |

## HR Zones Object

| Field | Type | Description |
|-------|------|-------------|
| `hrmax_bpm` | integer | Maximum heart rate in bpm. |
| `hrmax_source` | string | Provenance, e.g., `"user-reported"`, `"Garmin auto-detected"`. |
| `lthr_bpm` | integer | Lactate threshold heart rate in bpm. |
| `lthr_source` | string | Provenance for `lthr_bpm`. |
| `easy_hr_range_bpm` | integer[2] | `[low, high]` Easy/Z2 HR range. |
| `marathon_hr_range_bpm` | integer[2] | `[low, high]` Marathon-pace HR range. |
| `threshold_hr_range_bpm` | integer[2] | `[low, high]` Threshold/T HR range. |
| `interval_hr_range_bpm` | integer[2] | `[low, high]` Interval/I HR range. |
| `easy_hr_cap_bpm` | integer | Hard cap above which the run is no longer "easy". |
| `calibration_note` | string | Free-text rationale for the zone choices (data points used). |

## Form Metrics Object

| Field | Type | Description |
|-------|------|-------------|
| `current_cadence_spm` | integer | Current average running cadence (steps per minute). |
| `target_cadence_spm` | integer | Target cadence for the runner to drift toward. |
| `form_cue` | string | Free-text coaching cue. |

## Baseline Run Object

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date of the baseline run. |
| `duration_min` | integer | Run duration in minutes. |
| `avg_pace_per_km_s` | integer | Average pace in seconds per km. |
| `avg_hr` | integer | Average heart rate in bpm. |
| `max_hr` | integer | Peak heart rate in bpm. |
| `cadence_spm` | integer | Average cadence (steps per minute). |
| `perceived_effort` | string | One of `"easy"`, `"moderate"`, `"hard"`. |

## Garmin VO2max Object

| Field | Type | Description |
|-------|------|-------------|
| `value` | number | Garmin's VO2max estimate. |
| `source` | string | E.g., `"Garmin watch algorithm"`. |
| `note` | string | Free-text reconciliation note vs current VDOT. |

## Garmin Race Predictions Object

| Field | Type | Description |
|-------|------|-------------|
| `snapshot_date` | string | ISO date when Garmin emitted these predictions. |
| `times` | object | `{ "5k_s": int, "10k_s": int, "half_s": int, "marathon_s": int }` — predicted finish times in seconds. |

## Preferences Object

| Field | Type | Description |
|-------|------|-------------|
| `workout_unit` | string | `"time"` (default) or `"distance"` — controls how workout cards are presented |
| `methodology` | string | Training methodology: `"polarized"` (default) \| `"pyramidal"` |
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
| `injury_history` | object[] | Past injuries as objects: `{ area: string, status: string, guidance: string }` — guides Coach context. Empty list when none. |
| `constraints_notes` | string | Free-text scheduling notes (e.g., `"no running on weekday mornings"`) |
| `sleep_pattern_note` | string | Free-text recent sleep observations (e.g., last 7 days). Optional. |
| `strength_placement` | object | External strength training placement guidance (see Strength Placement Object). Optional. |

## Strength Placement Object

External strength training the runner performs separately. The plugin does not prescribe strength workouts; this object documents how strength fits around running so the Coach can reason about same-day load.

| Field | Type | Description |
|-------|------|-------------|
| `frequency_per_week` | integer | Number of strength sessions per week. |
| `scheduled_days` | string[] | Day-of-week codes the user does strength (e.g., `["Tue","Sat"]`). |
| `placement` | string | Free-text placement note (e.g., `"post-run, same-day double (1-3h after run)"`). |
| `focus` | string | Free-text training focus (e.g., `"ITBS rehab — hip abduction, glute med/max"`). |
| `avoid` | string | Free-text contraindications (e.g., `"heavy back squat, deep loaded knee flexion"`). |
| `managed_externally` | boolean | `true` — the plugin does not prescribe these sessions. |
| `rationale` | string | Why the plugin doesn't prescribe (e.g., `"v1 plugin scope excludes strength prescription"`). |

## Integrations Object

| Field | Type | Description |
|-------|------|-------------|
| `preferred_source` | string | `"manual"` \| `"strava"` \| `"garmin"`. Tiebreaker for same-date workouts arriving from multiple sources. Defaults to `"manual"`; flips to the most-recently-connected provider after a successful probe via `probe-strava-connection` or `probe-garmin-connection`. |
| `strava` | object | See Strava Object below. |
| `garmin` | object | See Garmin Object below. |

## Strava Object

| Field | Type | Description |
|-------|------|-------------|
| `connected` | boolean | `true` only after `probe-strava-connection` returns `ok`. Never set `true` from the `--connect` flag alone. |
| `athlete_id` | integer\|null | Strava athlete numeric id, captured from `get-athlete-profile` response. |
| `connected_at` | string (ISO 8601)\|null | When the probe last succeeded. |
| `last_sync_at` | string (ISO 8601)\|null | When DataFetcher last successfully ingested activities. |
| `last_sync_status` | string\|null | `null` \| `"ok"` \| `"error:auth"` \| `"error:rate_limit"` \| `"error:mcp_unavailable"` \| `"error:network"` \| `"error:unknown"` |

## Garmin Object

The plugin targets the `nrvim/garmin-givemydata` MCP server (SQLite-backed, Cloudflare-bypassing). The probe verifies DB readiness, not live Garmin auth — auth/Cloudflare failures only surface at `/run-sync` time.

| Field | Type | Description |
|-------|------|-------------|
| `connected` | boolean | `true` only after `probe-garmin-connection` returns `ok`. Never set `true` from the `--connect` flag alone. |
| `garmin_user_id` | string\|integer\|null | Garmin profile ID, captured from `social_profile.profileId` via `garmin_user_profile`. |
| `email` | string\|null | Garmin login email, captured from `social_profile.userName` via the probe. Optional. |
| `display_name` | string\|null | Optional human-readable name extracted from `social_profile.fullName` (preferred). May be `null` or omitted if Garmin returned only a UUID-form `displayName`. |
| `connected_at` | string (ISO 8601)\|null | When the probe last succeeded. |
| `last_sync_at` | string (ISO 8601)\|null | When DataFetcher last successfully ingested activities. |
| `last_sync_status` | string\|null | `null` \| `"ok"` \| `"error:auth"` \| `"error:db_empty"` \| `"error:mcp_unavailable"` \| `"error:network"` \| `"error:unknown"`. `"error:db_empty"` is unique to Garmin and means the local SQLite has no profile rows yet — fix by running `garmin-givemydata` once. |
| `last_sync_imported` | integer\|null | Count of new activities ingested in the last `/run-sync`. |
| `last_sync_enriched` | integer\|null | Count of activities updated/cross-referenced (e.g., merged with Strava) in the last `/run-sync`. |
| `data_freshness_date` | string (ISO date)\|null | Most-recent activity date observed in the local SQLite. |

## Written by

Coach (during `/run-init` and `/run-race-recap`; `current_fitness.vdot` also updated by `adapt-plan` when 3+ consecutive "over" workouts trigger a VDOT bump).

## Example

See `users.example.json` for a full example.
