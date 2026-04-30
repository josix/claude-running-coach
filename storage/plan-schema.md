# Plan Schema

File: `storage/plan.json`

## Purpose

Stores the full training macrocycle: goal race metadata, phase structure, and a day-by-day prescription for every week from start date to race date. The Coach generates this file during `/run-init` and mutates it when the `adapt-plan` skill fires a strike rule. The plan is the single source of truth for what the runner should do on any given day.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Schema version; currently `1` |
| `goal` | object | Race goal metadata (see Goal Object below) |
| `methodology` | string | Training methodology applied: `"polarized"` |
| `macrocycle` | object | High-level phase structure (see Macrocycle Object below) |
| `weeks` | object[] | Array of week objects, one per training week (see Week Object below) |
| `last_modified_at` | string | ISO 8601 timestamp of the most recent plan write |
| `last_modified_reason` | string | Human-readable reason for the last modification (e.g., `"initial generation"`, `"recovery week inserted"`) |

## Goal Object

| Field | Type | Description |
|-------|------|-------------|
| `race` | string | Race type: `"marathon"`, `"half_marathon"`, `"10K"`, `"5K"` |
| `target_time_s` | integer | Goal finish time in seconds |
| `race_date` | string | ISO date of race day (e.g., `"2027-01-01"`) |
| `race_name` | string | Human-readable race name |

## Macrocycle Object

| Field | Type | Description |
|-------|------|-------------|
| `start_date` | string | ISO date of the first day of training |
| `end_date` | string | ISO date of race day (matches `goal.race_date`) |
| `total_weeks` | integer | Total number of training weeks (8–24) |
| `phases` | object[] | Array of phase descriptors (see Phase Object below) |

## Phase Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Phase name: `"base"`, `"build"`, `"peak"`, or `"taper"` |
| `start_week` | integer | First week number of this phase (1-indexed) |
| `end_week` | integer | Last week number of this phase |
| `focus` | string | Short description of the training emphasis for this phase |

## Week Object

| Field | Type | Description |
|-------|------|-------------|
| `week_number` | integer | 1-indexed week number within the macrocycle |
| `phase` | string | Phase this week belongs to: `"base"`, `"build"`, `"peak"`, or `"taper"` |
| `target_volume_min` | integer | Total prescribed running volume for the week in minutes |
| `target_long_run_min` | integer | Duration of the designated long run in minutes |
| `days` | object[] | Array of 7 day objects covering Mon–Sun (see Day Object below) |

## Day Object

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | ISO date for this training day (e.g., `"2026-07-01"`) |
| `dow` | string | Day of week abbreviation: `"Mon"`, `"Tue"`, `"Wed"`, `"Thu"`, `"Fri"`, `"Sat"`, `"Sun"` |
| `type` | string | Workout type: `"E"` (easy), `"L"` (long), `"T"` (threshold), `"I"` (interval), `"R"` (repetition), `"M"` (marathon-pace), `"Strides"`, `"Recovery"`, or `"Rest"` |
| `duration_min` | integer | Prescribed workout duration in minutes; `0` for rest days |
| `target_pace` | string\|null | Pace key referencing `users.json current_fitness.paces` (e.g., `"easy"`, `"threshold"`); `null` for rest |
| `notes` | string | Coach notes for this session (warm-up instructions, effort cues, etc.) |

## Written by

Coach (initial generation via `build-training-plan`; subsequent mutations via `adapt-plan` when strike rules fire, and via `taper-protocol` and `recovery-protocol` for special blocks). The `PostToolUse` hook `plan-integrity-check.sh` validates the file after every write.

## Example

See `plan.example.json` for a full example with one illustrative week. In production, `weeks` contains one entry per week across the full macrocycle (up to 24 entries).
