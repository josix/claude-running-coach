---
name: generate-daily-workout
description: "Renders today's workout card from plan.json and daily_state.json as a Markdown block. Use for every /run-today invocation. No writes — pure read-and-render."
---

# Generate Daily Workout

Looks up today's date in `plan.json`, resolves the target pace key to actual seconds/km from `users.json`, applies carry-forward cues from `daily_state.json`, and emits a formatted Markdown workout card for the user. No storage files are written.

## When to use

- The user runs `/run-today` and wants to see their prescribed workout.
- Coach needs to surface the day's prescription after completing `/run-init` or `/run-replan`.

## Outputs

A Markdown workout card displayed in the conversation. Contains workout type, duration (or distance if the user prefers that unit), target pace, RPE expectation, workout structure, warm-up cue from the previous session, and any active fatigue flags.

See `body.md` for full rendering instructions.
