# Daily State Schema

File: `storage/daily_state.json`

## Purpose

A single-record file that carries context forward from the most recently logged workout into the next training day. It tracks consecutive miss and "ahead" counts for the strike-rule engine, and stores the warm-up cue and fatigue flags that `generate-daily-workout` injects into tomorrow's workout card. This file is rewritten in full after every workout is logged.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Schema version; currently `1` |
| `as_of_date` | string | ISO date of the most recently logged workout (e.g., `"2026-01-01"`) |
| `carry_forward` | object | Context to inject into the next workout card (see Carry Forward Object below) |
| `consecutive_misses` | integer | Number of consecutive workouts where the verdict was `"under"` or `"aborted"`; resets to `0` after an on-target session or a recovery-week insertion |
| `consecutive_ahead` | integer | Number of consecutive workouts where the verdict was `"over"`; resets to `0` after an on-target session or a VDOT bump |
| `last_workout_id` | string\|null | ID of the most recently logged workout (references `workouts.json`); `null` before any workout is logged |
| `last_workout_quality` | string\|null | Verdict of the last workout: `"on-target"`, `"under"`, `"over"`, `"aborted"`, or `null` |

## Carry Forward Object

| Field | Type | Description |
|-------|------|-------------|
| `warm_up_cue` | string | A one-sentence warm-up reminder derived from the last workout's notes and analysis (e.g., `"calves felt tight — extend dynamic warm-up by 5 min"`); empty string if no cue |
| `fatigue_flag` | string | Current fatigue status: `"none"`, `"mild"`, or `"high"` |
| `recurring_red_flags` | object[] | Array of red-flag events accumulated over the last 14 days (see Red Flag Object below); used to trigger early recovery weeks |

## Red Flag Object

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date when the red flag was recorded |
| `signal` | string | Signal identifier (e.g., `"high_drift_high_rpe"`) |

## Written by

WorkoutLogger (via `/run-log`) and DataFetcher (via `/run-sync`). These two agents never run simultaneously — the orchestrator routes to exactly one per command invocation.

## Example

See `daily_state.example.json` for a full example.
