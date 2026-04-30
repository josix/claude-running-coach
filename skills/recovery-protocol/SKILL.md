---
name: recovery-protocol
description: "Inserts a post-race or injury-flag recovery block into plan.json: 4 days rest + 3 easy jog days (post-race), or 3 rest + 1 recovery (red-flag-fatigue), or 7 rest days (injury). Use after /run-race-recap or when adapt-plan returns red_flag_recovery."
---

# Recovery Protocol

Inserts a structured recovery block into `plan.json` based on the trigger type. Post-race recovery follows the user's training knowledge preference: minimum 4 days complete rest followed by a gradual return with 30-40 minute easy jogs. The red-flag-fatigue block is shorter. Injury blocks are conservative and include a physio referral note. Plan modifications are written by Coach (the single writer of `plan.json`).

## When to use

- `/run-race-recap` is run after a goal race — triggers post-race recovery.
- `adapt-plan` returns action `red_flag_recovery` — triggers the fatigue protocol.
- The user reports an injury during `/run-log` or in conversation — triggers the injury protocol.

## Outputs

Modified `storage/plan.json` with rest and recovery days inserted, replacing or shifting the upcoming training days. Also updates `storage/daily_state.json` to reset consecutive counters.

See `body.md` for exact block definitions and `references/post-race-protocol.md` for the source rationale.
