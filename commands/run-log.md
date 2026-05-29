---
description: Manually log a completed workout. Triggers adaptive plan iteration.
argument-hint: "[date YYYY-MM-DD, defaults to today]"
---

# /run-log

## Purpose

Record a completed workout through a short, conversational interview. After capture, the plugin computes how the workout compared to what was prescribed and adapts the plan if the strike rules fire.

Run this after every training session (or at the end of the day if you prefer to batch).

## Inputs

- **date** (optional): The date of the workout in `YYYY-MM-DD` format. Defaults to today. Useful for logging a workout from yesterday or earlier (within 14-day window).

## Action

Delegate to **WorkoutLogger**. WorkoutLogger will:

1. Call `log-workout` — conduct a one-question-at-a-time conversational interview to capture:
   - Duration (required)
   - Distance (optional)
   - Average HR (optional)
   - RPE 1–10 (required)
   - Splits (optional)
   - Free-text notes (optional)

2. Call `analyze-workout` — compare actual vs. prescribed (from `plan.json` for that date) and compute:
   - Completion % (actual duration / prescribed duration)
   - Pace delta % (actual avg pace vs. target pace, if distance provided)
   - RPE delta (actual RPE vs. expected RPE for this workout type)
   - HR drift (intra-session, if HR provided)
   - Verdict: `on-target`, `under`, `over`, or `aborted`

3. Write the complete workout record (with analysis) to `storage/workouts.json`.
4. Update `storage/daily_state.json` with carry-forward fields.
5. Hand the analysis result to **Coach** for `adapt-plan`.

**Coach** then applies the strike rules:
- 1 consecutive miss → monitor (no plan change)
- 2 consecutive misses → reduce next quality session intensity by one step
- 3 consecutive misses → insert a recovery week starting next week
- 3 consecutive "over" workouts → increment VDOT by 1 and regenerate remaining paces

Updates `storage/workouts.json`, `storage/daily_state.json`, and possibly `storage/plan.json` + `storage/users.json` if the strike rules fire.

## Output

After logging:
1. Confirmation of what was recorded (date, type, duration, RPE, verdict)
2. Any plan adaptation that fired (or "Plan unchanged — on target, great work!")
3. A prompt to run `/run-today` tomorrow morning

> Jargon in this output (RPE, verdict, VDOT bump, strike rules, etc.) is glossed on first use per the persona rule in `agents/coach.md`. Term definitions: see `references/glossary.md`.
