---
description: Post-race recap — log race result, recompute VDOT, insert recovery protocol.
argument-hint: ""
---

# /run-race-recap

## Purpose

Record your race result, update your fitness baseline with a fresh VDOT computation, and automatically insert the post-race recovery protocol into your plan. Run this within 24 hours of finishing a race.

## Action

Delegate to **Coach**. Coach will:

1. **Capture the race result** through a short interview:
   - Race name and distance
   - Official finish time (or chip time)
   - Conditions (weather, course difficulty, notes)
   - How it felt (free text)

2. **Append to `storage/progress.json` → `race_results[]`** — saves the race record with date, distance, time, and notes.

3. **Call `compute-vdot`** — recompute VDOT from the race result. Update `storage/users.json` → `current_fitness.vdot`, `vdot_source`, `vdot_source_date`, `vdot_source_result`, and the full `paces` table. Also append the new VDOT entry to `progress.json` → `vdot_history[]`.

4. **Call `recovery-protocol`** with trigger `"post-race"` — inserts the standard post-race recovery block into `plan.json` starting from tomorrow:
   - Days 1–4: Complete rest
   - Days 5–7: Recovery pace (30–40 min, RPE 3–4)
   - Day 8+: Resume Easy training per the existing plan (or replan if the race was the goal race)

5. **If this was the goal race**: Ask the runner whether they want to set a new goal and run `/run-init` for a fresh cycle, or take a break.

## Output

After completion:
1. Race result confirmation (distance, time, pace, VDOT before → after)
2. Updated pace table (new E, M, T, I, R paces)
3. Recovery schedule for the next 7 days
4. A note on when to expect the next quality training session

> Jargon in this output (VDOT, pace codes E/M/T/I/R, recovery week, etc.) is glossed on first use per the persona rule in `agents/coach.md`. Term definitions: see `references/glossary.md`.
