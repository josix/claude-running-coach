# Recovery Protocol — Instructions

## Inputs

- `trigger`: one of `"post-race"`, `"red-flag-fatigue"`, `"injury"`.
- `date`: ISO YYYY-MM-DD of the event (race day, fatigue flag date, or injury date).
- `storage/plan.json`: the plan to modify.
- `storage/daily_state.json`: the state to reset.

## Steps

### Trigger: `post-race`

Implements the 4+3 protocol per the user's training knowledge base: "post-race: minimum 4 days complete rest, then return with 30-40 min easy jog."

1. Identify the 7 days starting the day after `date`.
2. Days 1-4: set `type: "Rest"`, `duration_min: 0`, `notes: "Post-race rest (mandatory)"`.
3. Days 5-7: set `type: "Recovery"`, `duration_min: 30`, `target_pace: "easy"`, `notes: "Easy jog — RPE ≤ 4"`. When reading these instructions aloud to the user, gloss RPE on its first mention: "(RPE — Rate of Perceived Exertion: 1 = walking, 10 = all-out sprint)".
4. Day 8: resume the scheduled workout from the original plan (shift subsequent days if needed).
5. Write modified `plan.json`. Update `daily_state.json`: reset `consecutive_misses=0`, `consecutive_ahead=0`, set `carry_forward.fatigue_flag="post-race-recovery"`.
6. Tell user: "4-day complete rest starts tomorrow, then 3 easy recovery jogs. You'll be back on full training {date+8}."

### Trigger: `red-flag-fatigue`

3+1 protocol for systemic fatigue before it becomes injury.

1. Identify the next 4 training days starting from `date + 1`.
2. Days 1-3: set `type: "Rest"`.
3. Day 4: set `type: "Recovery"`, `duration_min: 25`, `notes: "Gentle return — stop if RPE > 5"`.
4. Resume plan from day 5, but drop one intensity step on the first quality session back (T→E, I→T, R→I).
5. Reset `consecutive_misses=0` in `daily_state.json`.
6. Tell user: "Three rest days, then a gentle jog. Next quality session will be stepped down one level as a precaution."

### Trigger: `injury`

Conservative injury block for v1.

1. Prompt user: "Where does it hurt, and how would you rate the pain 1-10? (1=mild discomfort, 10=cannot weight bear)" — for context only, not for diagnosis.
2. Regardless of the answer: insert 7 consecutive Rest days starting from `date`.
3. Add a note to all 7 days: "Injury rest — consult a physiotherapist before returning."
4. After 7 days: insert a single Recovery day (25 min easy) with note "Return if symptom-free. If pain persists, extend rest and seek medical advice."
5. Do NOT attempt to prescribe a return-to-run protocol beyond day 8 — tell the user to get physio clearance first.
6. Reset state counters. Set `carry_forward.fatigue_flag="injury"`.

## Output

Modified `plan.json` (days mutated in-place for the recovery window). Example post-race block:

```json
[
  { "date": "2026-10-16", "type": "Rest", "duration_min": 0, "notes": "Post-race rest (mandatory)" },
  { "date": "2026-10-17", "type": "Rest", "duration_min": 0, "notes": "Post-race rest (mandatory)" },
  { "date": "2026-10-18", "type": "Rest", "duration_min": 0, "notes": "Post-race rest (mandatory)" },
  { "date": "2026-10-19", "type": "Rest", "duration_min": 0, "notes": "Post-race rest (mandatory)" },
  { "date": "2026-10-20", "type": "Recovery", "duration_min": 30, "target_pace": "easy", "notes": "Easy jog — RPE ≤ 4" },
  { "date": "2026-10-21", "type": "Recovery", "duration_min": 30, "target_pace": "easy", "notes": "Easy jog — RPE ≤ 4" },
  { "date": "2026-10-22", "type": "Recovery", "duration_min": 35, "target_pace": "easy", "notes": "Easy jog — RPE ≤ 4" }
]
```

## Edge cases

- **Recovery window overlaps the end of plan**: extend `plan.json.macrocycle.end_date` by the recovery duration and append the extra days.
- **User disputes rest requirement** ("I feel fine, can I run tomorrow?"): explain the protocol firmly but not rigidly — for post-race, note that cellular repair continues even without perceived fatigue. Defer to their judgment but log the override in `notes`.
- **Plan has no future days** (race was the last planned event): insert recovery days as additional entries after the final week. Note that the user may want to `/run-replan` for a new goal after recovery.
- **Injury trigger on a rest day**: begin counting from the next day; the rest day itself counts as day 1 of the block.
