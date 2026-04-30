---
name: build-training-plan
description: "Generates a complete macrocycle (base/build/peak/taper) from a runner's goal, target race date, available training days, and current VDOT. Writes plan.json. Use during /run-init and /run-replan."
---

# Build Training Plan

Constructs a full periodized training macrocycle from the user's race goal, target date, current VDOT, and lifestyle constraints. Produces a week-by-week plan with daily workout prescriptions drawn from `data/workout-templates.json`, enforcing the 3-up-1-down volume progression and polarized methodology. The final 2-3 taper weeks are shaped by the `taper-protocol` skill.

## When to use

- The user completes `/run-init` and all profile fields are populated in `storage/users.json`.
- The user runs `/run-replan` (race date change, injury recovery, or schedule reset).
- A VDOT bump from `adapt-plan` makes paces stale enough to warrant regenerating the remainder of the plan.

## Outputs

A fully populated `storage/plan.json` with phases, weekly prescriptions, and day-level workout cards. The file is written atomically and then validated by the `plan-integrity-check` hook.

See `body.md` for full instructions and `scripts/macrocycle.py` for the date-math and phase-split logic.
