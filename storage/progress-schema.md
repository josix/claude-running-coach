# Progress Schema

File: `storage/progress.json`

## Purpose

Stores rolling aggregate statistics and longitudinal trend data used by the Coach to make weekly decisions (hold / advance / recovery week). It also records the full VDOT history and race results for long-term progress tracking. This file is kept intentionally small — raw workout data lives in `workouts.json`; `progress.json` holds only aggregated summaries.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Schema version; currently `1` |
| `rolling_7d` | object | Aggregate stats for the trailing 7 days (see Rolling 7-Day Object below) |
| `rolling_28d` | object | Aggregate stats for the trailing 28 days (see Rolling 28-Day Object below) |
| `weekly_summaries` | object[] | One summary entry per completed week (see Weekly Summary Object below) |
| `vdot_history` | object[] | Chronological log of every VDOT update (see VDOT History Object below) |
| `race_results` | object[] | Log of race-day results captured via `/run-race-recap` (see Race Result Object below) |
| `last_updated_at` | string | ISO 8601 timestamp of the most recent write |

## Rolling 7-Day Object

| Field | Type | Description |
|-------|------|-------------|
| `mileage_km` | number | Total distance run in the last 7 days |
| `duration_min` | integer | Total running time in the last 7 days in minutes |
| `avg_rpe` | number | Average RPE across all logged workouts in the window |
| `quality_sessions_completed` | integer | Count of T/I/R sessions completed in the window |
| `quality_sessions_prescribed` | integer | Count of T/I/R sessions prescribed in the window |

## Rolling 28-Day Object

| Field | Type | Description |
|-------|------|-------------|
| `mileage_km` | number | Total distance run in the last 28 days |
| `vdot_trend` | string | Signed decimal string representing VDOT change over 28 days (e.g., `"+0.3"`, `"-0.5"`, `"0.0"`) |
| `avg_resting_signal` | string | Composite resting readiness signal: `"stable"`, `"declining"`, or `"improving"` |

## Weekly Summary Object

| Field | Type | Description |
|-------|------|-------------|
| `week_number` | integer | References `plan.json weeks[].week_number` |
| `completed_volume_min` | integer | Total minutes actually run during the week |
| `prescribed_volume_min` | integer | Total minutes prescribed by the plan for the week |
| `verdict` | string | Coach decision: `"hold"`, `"advance"`, or `"recovery"` |
| `notes` | string | Coach's free-text rationale for the verdict |

## VDOT History Object

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date when VDOT was updated |
| `vdot` | number | New VDOT value |
| `trigger` | string | What triggered the update (e.g., `"5K time-trial"`, `"3x consecutive over"`, `"race result"`) |

## Race Result Object

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO race date |
| `race` | string | Race type (e.g., `"marathon"`, `"10K"`) |
| `race_name` | string | Race name |
| `finish_time_s` | integer | Official finish time in seconds |
| `new_vdot` | number | VDOT computed from the race result |

## Written by

Coach (during `/run-week` via `weekly-review`, and during `/run-race-recap` and `adapt-plan` when rolling stats are recomputed after a workout is logged).

## Example

See `progress.example.json` for a full example showing initial empty state. In production, `weekly_summaries`, `vdot_history`, and `race_results` grow over the training cycle.
