---
description: One-time onboarding — interview the runner about goal, fitness, training days, lifestyle. Generates users.json + plan.json.
argument-hint: "[--connect strava]"
---

# /run-init

## Purpose

Set up a brand-new runner profile and generate a personalized training plan. This command collects your race goal, current fitness level, and lifestyle constraints, then builds a full macrocycle tailored to your target date.

Run this once when starting the plugin for the first time. You can also re-run it with `--connect strava` to save your Strava connection intent, or after a major life event to trigger a fresh `/run-replan`.

## Action

Delegate to **Coach**. Coach will:

1. **Interview the runner** — one question at a time — collecting:
   - Goal race (marathon, half, 10K, 5K, or custom distance)
   - Target finish time
   - Race date
   - Recent race result or time-trial result (used to seed VDOT — if none, Coach will offer a time-trial plan)
   - Available training days per week (which days of the week)
   - Lifestyle context (typical sleep hours, stress level, prior weekly mileage, injury history)
   - Methodology preference (polarized default; pyramidal available)
   - Unit preference (time default; distance available)

2. **Call `compute-vdot`** — translates the race result into a VDOT score and full E/M/T/I/R pace table.

3. **Call `build-training-plan`** — constructs the full macrocycle (base → build → peak → taper) from today through the race date, respecting the 8-week minimum and 24-week maximum. Selects weekly templates from `data/workout-templates.json`.

4. **Write `storage/users.json`** — saves the full user profile including fitness baseline and preferences.

5. **Write `storage/plan.json`** — saves the generated macrocycle with all weeks and days.

If `--connect strava` is supplied: set `users.integrations.strava.connected = true` as a v2 migration intent flag and inform the user that Strava sync will be available in v2. No OAuth flow is initiated in v1.

## Output

After completion, display:
- A welcome message with the runner's name and goal
- VDOT score and the five training paces (Easy, Marathon, Threshold, Interval, Repetition)
- A macrocycle overview: phase names, week ranges, and focus areas
- Today's first prescribed workout (so the runner knows what to expect immediately)
- A prompt to run `/run-today` to see today's full workout card

## Notes

If `storage/users.json` already exists, ask the runner whether to overwrite or start fresh. Preserving the existing file and running `/run-replan` instead is often the better choice after a mid-cycle event.
