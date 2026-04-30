# Generate Daily Workout — Instructions

## Inputs

- `storage/plan.json`: locate today's day-entry by date.
- `storage/daily_state.json`: carry-forward cues (warm_up_cue, fatigue_flag, recurring_red_flags).
- `storage/users.json`: paces dict (`current_fitness.paces`) and `preferences.workout_unit`.

## Steps

1. Read `storage/plan.json`. Scan all `weeks[].days[]` for an entry where `date == today` (ISO YYYY-MM-DD). If today is not found, skip to the "out of range" edge case.
2. Extract the day entry: `type`, `duration_min`, `target_pace`, `notes`.
3. If `type == "Rest"` or `type == "Recovery"`, skip to the rest-day branch.
4. Resolve `target_pace` key to seconds/km: look up `users.json.current_fitness.paces[target_pace + "_per_km_s"]`. Convert to `mm:ss` format for display.
5. If `users.json.preferences.workout_unit == "distance"`, convert `duration_min` to km: `km = duration_min / (pace_s / 60)`. Round to 1 decimal.
6. Read `storage/daily_state.json`. Extract `carry_forward.warm_up_cue` and `carry_forward.fatigue_flag`.
7. Render the Markdown card (see Output section).

## Output

Markdown card format:

```markdown
## Today's Workout — {date} ({day_of_week})

**Type:** {type} ({full name, e.g. "Easy Run"})
**Duration:** {duration_min} min  (or **Distance:** {km} km if unit=distance)
**Target Pace:** {mm:ss}/km  ({zone name})
**RPE Expectation:** {expected_rpe}/10

### Structure
{notes / structure from plan template}

### Warm-up Cue
{warm_up_cue from daily_state, or "Standard 5-min dynamic warm-up" if empty}

{fatigue_flag block if fatigue_flag != "none"}
```

Workout type → full name mapping:
- `E` → Easy Run, `L` → Long Run, `T` → Threshold Run, `I` → Interval Session,
- `R` → Repetition Session, `M` → Marathon-Pace Run, `Strides` → Strides,
- `Recovery` → Recovery Jog, `Rest` → Rest Day

## Examples

**Easy Run:**

```
## Today's Workout — 2026-05-05 (Tuesday)

**Type:** E (Easy Run)
**Duration:** 35 min
**Target Pace:** 5:24/km  (Easy zone)
**RPE Expectation:** 4/10

### Structure
Easy throughout — conversational pace. Include 4×20s strides at the end.

### Warm-up Cue
Calves felt tight last session — extend dynamic warm-up by 5 min.
```

**Rest Day:**

```
## Today's Workout — 2026-05-06 (Wednesday)

**Type:** Rest Day

Rest is part of the plan. Your next workout: Thursday 2026-05-07 (Easy Run, 35 min).
```

## Edge cases

- **Today is a Rest day**: render an encouragement message and show the next scheduled workout date and type.
- **Today not in plan** (out of range or plan not initialized): display "No workout found for today. If your plan has ended or not been created yet, run `/run-replan` or `/run-init`."
- **`warm_up_cue` is empty string**: fall back to "Standard 5-min dynamic warm-up."
- **`fatigue_flag` is not "none"**: prepend a warning banner: "Fatigue flag active: {flag}. Consider reducing intensity today."
- **Recurring red flags present**: list them below the fatigue flag banner with dates.
