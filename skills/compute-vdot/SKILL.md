---
name: compute-vdot
description: "Translates a recent race result (distance + time) into a VDOT fitness score and the corresponding training pace table (E/M/T/I/R per km). Use during /run-init and /run-race-recap when the user has a fresh race or time-trial result."
---

# Compute VDOT

Converts a single race performance (distance + finish time) into a VDOT fitness score using Jack Daniels' tables, then derives the five training paces (Easy, Marathon, Threshold, Interval, Repetition) from that score. All pace values are stored in `users.json.current_fitness` for use by every downstream skill.

## When to use

- The user completes `/run-init` and provides a recent race or time-trial result.
- The user completes `/run-race-recap` with a new race finish time.
- `adapt-plan` returns action `vdot_bump` (3 consecutive "over" workouts), requiring a VDOT re-computation.

## Outputs

A VDOT float (1 decimal precision) and a paces dict written to `storage/users.json` under `current_fitness.vdot` and `current_fitness.paces`. Also returns the values in-memory for immediate downstream use by `build-training-plan`.

See `body.md` for full instructions and `scripts/vdot.py` for the deterministic logic.
