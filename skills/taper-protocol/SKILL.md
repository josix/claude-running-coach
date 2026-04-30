---
name: taper-protocol
description: "Specialized logic for the final 2-3 weeks before race day: -20%/-40%/-60% volume curve, intensity preservation in race-week-minus-1, race-day shakeout. Called by build-training-plan during plan generation and triggerable mid-cycle if race date changes."
---

# Taper Protocol

Modifies the final 2-3 weeks of the training plan into a calibrated taper curve that reduces volume progressively while preserving intensity. Runs `scripts/taper.py:apply_taper` on the existing weeks list and returns a modified copy. The taper is integrated automatically into every `build-training-plan` call and can be re-applied independently if the race date shifts.

## When to use

- `build-training-plan` calls this skill at step 7 (final 2-3 weeks of the generated plan).
- `/run-replan` changes the race date, bringing new weeks into the taper window.
- `adapt-plan` detects the user is within 3 weeks of race day during a mid-cycle vdot_bump.

## Outputs

A modified weeks list (non-destructive — returns deep copies). The caller (`build-training-plan` or `adapt-plan`) writes the final plan to `storage/plan.json`.

See `body.md` for the exact taper curve and invocation pattern and `scripts/taper.py` for the implementation.
