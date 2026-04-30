# Taper Protocol — Instructions

## Inputs

- `weeks`: the full list of week dicts from `plan.json.weeks` (populated with `target_volume_min` and `days`).
- `race_date`: ISO YYYY-MM-DD of race day (from `plan.json.goal.race_date`).

## How to invoke the helper

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/taper-protocol/scripts')
from taper import apply_taper

plan  = json.load(open('storage/plan.json'))
weeks = plan['weeks']
race_date = plan['goal']['race_date']

tapered_weeks = apply_taper(weeks, race_date)
print(json.dumps(tapered_weeks[-3:], indent=2))  # inspect last 3 weeks
"
```

`apply_taper` returns a new list (deep copy). Pass the result back to the caller to replace `plan.weeks`.

## Taper curve

| Week | Volume | Quality | Notes |
|---|---|---|---|
| Race-week-2 (if total weeks ≥ 18) | 80% of peak | Preserved | Moderate reduction begins |
| Race-week-1 | 60% of peak | Keep 1 T or I session | Long run capped at 60% of normal |
| Race week | 40% of peak | 1 short shakeout (≤ 20 min E or strides) + Race day | All other quality → short E |

"Peak" = `max(target_volume_min)` across all non-taper weeks.

## Steps

1. Identify the `weeks` list and `race_date`.
2. Call `apply_taper(weeks, race_date)`.
3. The function internally:
   - Finds the race day within the last week's days and marks it `type: "Race"`.
   - Converts extra quality sessions in race week to short shakeouts (≤ 20 min Easy).
   - In race-week-1: keeps exactly 1 quality session (T or I); converts extras to E; reduces long run by 40%.
   - In race-week-2 (if plan has ≥ 18 weeks): sets volume to 80% of peak, no session-level changes.
4. Return the modified weeks list to the caller.
5. The caller (`build-training-plan`) writes the full plan to `storage/plan.json`.

## Output

Modified weeks list. Example last 2 weeks (24-week plan, peak=360 min):

```json
[
  {
    "week_number": 23, "phase": "taper", "taper": true,
    "target_volume_min": 216,
    "days": [
      { "date": "2026-10-06", "type": "E", "duration_min": 45 },
      { "date": "2026-10-08", "type": "T", "duration_min": 40, "notes": "Last quality session" },
      { "date": "2026-10-10", "type": "L", "duration_min": 72, "notes": "60% of normal long run" },
      { "date": "2026-10-11", "type": "Rest" }
    ]
  },
  {
    "week_number": 24, "phase": "taper", "taper": true,
    "target_volume_min": 144,
    "days": [
      { "date": "2026-10-13", "type": "E", "duration_min": 20, "notes": "Short shakeout" },
      { "date": "2026-10-14", "type": "E", "duration_min": 20, "notes": "Strides opener" },
      { "date": "2026-10-15", "type": "Race", "duration_min": 0, "notes": "Race day" }
    ]
  }
]
```

## Examples

**16-week plan (no race-week-2 taper):**
- Week 15 (race-week-1): volume ×0.60; 1 T session preserved; long run cut 40%
- Week 16 (race week): volume ×0.40; 1 shakeout + race day; all other quality→E≤20min

**24-week plan (full 3-week taper):**
- Week 22: volume ×0.80 (mild reduction)
- Week 23: volume ×0.60; 1 T session; long run capped
- Week 24: volume ×0.40; 2 shakeouts + race day

## Edge cases

- **`peak_volume` is 0** (plan has no `target_volume_min` set): `apply_taper` falls back to summing day durations. Ensure `build-training-plan` sets `target_volume_min` before calling this skill.
- **Race day not found in last week's days**: `apply_taper` appends a stub race day entry. The `plan-integrity-check` hook will validate.
- **Plan has only 8 weeks** (minimum): only race week gets the full taper (-60%). Race-week-1 is treated as peak week minus minor reduction.
- **Race date changes mid-plan**: re-invoke this skill on the updated weeks list; the function will re-identify which weeks are in the taper window.
