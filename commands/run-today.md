---
description: Show today's workout card.
argument-hint: ""
---

# /run-today

## Purpose

Display a concrete, ready-to-execute workout card for today. Run this at the start of every training day to get your prescribed session with resolved paces and any carry-forward notes from yesterday.

## Action

Delegate to **Coach**. Coach will call `generate-daily-workout`, which:

1. Reads `storage/plan.json` to look up today's date in the week schedule (matching by `days[].date`).
2. Reads `storage/users.json` to resolve today's target paces from the current VDOT pace table.
3. Reads `storage/daily_state.json` to pull the carry-forward warm-up cue and fatigue flags set after yesterday's workout.
4. Renders the workout card in Markdown.

## Output Format

```
Today's Workout — Week X (Build Phase)
Date: YYYY-MM-DD

Type: T — Threshold (comfortably hard; speak a few words, not a full sentence)
Duration: 40 min

Structure:
  • 10 min E — Easy warm-up (conversational pace; you can chat in full sentences) (@ 5:24/km or RPE 4)
  • 20 min Threshold (@ 4:24/km or RPE 7)  (RPE — Rate of Perceived Exertion: 1 = walking, 10 = all-out sprint)
  • 10 min Easy cool-down (@ 5:24/km or RPE 4)

Carry-forward: Calves felt tight last session — extend dynamic warm-up by 5 min.

Run /run-log when done to record your workout.
```

If today is a **Rest day**, the card simply says: "Today is a Rest day. Recovery is training. No running prescribed."

If no user profile exists (`storage/users.json` not found), prompt the runner to run `/run-init` first.
