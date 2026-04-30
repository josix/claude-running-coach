# Adapt Plan — Instructions

## Inputs

- `plan`: the full plan dict read from `storage/plan.json`.
- `state`: the full state dict read from `storage/daily_state.json`.
- `delta`: the analysis dict returned by `analyze-workout` (`{verdict, completion_pct, pace_delta_pct, rpe_delta, hr_drift_bpm}`).
- `today`: ISO YYYY-MM-DD of the workout being evaluated.

## How to invoke the helper

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/adapt-plan/scripts')
from adapt import adapt

plan  = json.load(open('storage/plan.json'))
state = json.load(open('storage/daily_state.json'))
delta = json.loads('$DELTA_JSON')  # substitute actual delta dict
today = '2026-05-05'

new_plan, new_state, action = adapt(plan, state, delta, today)
print(json.dumps({'action': action, 'new_state': new_state}, indent=2))
"
```

In practice, pass `plan`, `state`, and `delta` as Python dicts inline. The function is pure (inputs unmodified, returns deep copies).

## Steps

1. Read `storage/plan.json` and `storage/daily_state.json`.
2. Call `adapt(plan, state, delta, today)` from `scripts/adapt.py`. It returns `(new_plan, new_state, action)`.
3. Handle the returned `action`:

   - **`no_change`**: update state only; no plan write.
   - **`monitor`**: update state only; tell user "Noted — watching for a pattern before adjusting."
   - **`reduce_next_quality`**: write `new_plan` to `plan.json`; tell user "Next quality session has been stepped down one intensity level."
   - **`recovery_week`**: write `new_plan` to `plan.json`; tell user "Three consecutive misses — inserting a recovery week (70% volume, one fewer quality session)." Reset `consecutive_misses` to 0.
   - **`vdot_bump`**: do NOT write plan immediately. First, invoke `compute-vdot` to regenerate paces from the most recent race in `progress.json.vdot_history` (increment VDOT by 1 if no recent race available). Update `users.json.current_fitness`. Then re-resolve all future `target_pace` entries in `new_plan` (they remain as keys, not baked-in values — no plan rewrite needed for keys). Write `users.json` and `new_state`. Tell user "Three consecutive strong workouts — VDOT bumped to {new_vdot}. Training paces updated."
   - **`red_flag_recovery`**: invoke the `recovery-protocol` skill with trigger `"red-flag-fatigue"`. Write `new_plan` and `new_state`.

4. Always write `new_state` to `storage/daily_state.json`.
5. If `plan_was_modified` (action in `reduce_next_quality`, `recovery_week`, `red_flag_recovery`): write `new_plan` to `storage/plan.json`. The `plan-integrity-check` hook will validate automatically.

## Action enum reference

| Action | Strike count | Plan change |
|---|---|---|
| `no_change` | on-target | None |
| `monitor` | miss ×1 | None |
| `reduce_next_quality` | miss ×2 | Next T/I/R downgraded one step |
| `recovery_week` | miss ×3 | Next week: volume ×0.70, 1 quality → E |
| `vdot_bump` | ahead ×3 | Paces updated in users.json |
| `red_flag_recovery` | aborted with high drift+RPE ×2 in 14d | Recovery week inserted |

## Examples

**Verdict "under", miss #2:**
→ action=`reduce_next_quality`; next Thursday's T session becomes E session.

**Verdict "over", ahead #3:**
→ action=`vdot_bump`; VDOT 47→48; all future paces updated; user told to feel proud.

**Verdict "aborted" with hr_drift=9, rpe_delta=3, second flag in 14 days:**
→ action=`red_flag_recovery`; recovery-protocol invoked with "red-flag-fatigue".

## Edge cases

- **Plan is empty or exhausted** (no future weeks): `_insert_recovery_week` appends a stub recovery week. Log a warning and tell user the plan is near its end.
- **`vdot_bump` but no recent race**: increment VDOT by 1.0 as a heuristic. Use `paces_for_vdot(new_vdot)` to regenerate.
- **Concurrent writes**: always read `plan.json` fresh at the start of this skill call; never use a cached version from earlier in the conversation.
