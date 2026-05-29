---
description: Force a full plan regeneration (use after injury, life event, or race change).
argument-hint: "[--reason \"...\"]"
---

# /run-replan

## Purpose

Regenerate the training plan from scratch starting from today, while preserving your historical workout data and progress records. Use this when something significant has changed — an injury, a new race date, a race cancellation, a long break, or a major shift in fitness.

## Inputs

- **--reason "..."** (optional but recommended): A brief description of why you are replanning. Saved in `plan.json` → `last_modified_reason` for future reference.

## Action

Delegate to **Coach**. Coach will:

1. **Confirm the current state** — Ask the runner:
   - Has the race date or goal changed?
   - Has fitness changed significantly (e.g., coming back from injury, returning from a break)?
   - Any new constraints (different training days, lifestyle changes)?

2. **Re-derive VDOT if needed** — If the runner reports a meaningful fitness change, call `compute-vdot` with a new race result or updated estimate. Otherwise, use the existing VDOT from `users.json`.

3. **Call `build-training-plan`** — Regenerate `plan.json` from today's date through the (possibly updated) race date. The new plan replaces all future weeks; past weeks already in `workouts.json` are unaffected.

4. **Write `storage/plan.json`** — Save the new macrocycle with `last_modified_reason` recorded.

5. **Preserve history** — `storage/users.json` history fields and `storage/progress.json` (including all weekly summaries, VDOT history, and race results) are never deleted during a replan.

## Output

After replanning:
1. Summary of what changed (race date, VDOT, phases, total weeks remaining)
2. New macrocycle overview: phase names, week ranges, focus areas
3. A prompt to run `/run-today` to see the first workout of the new plan

> Jargon in this output (VDOT, macrocycle, Base/Build/Peak/Taper phases, etc.) is glossed on first use per the persona rule in `agents/coach.md`. Term definitions: see `references/glossary.md`.

## When to Use

- Injury → rest period → return to training
- Race cancelled or moved to a new date
- Life event causing a training break of 2+ weeks
- Significant unexpected fitness improvement (e.g., after a strong race result — consider `/run-race-recap` instead)
