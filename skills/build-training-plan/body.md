# Build Training Plan — Instructions

## Inputs

- `storage/users.json`: must be fully populated with `current_fitness.vdot`, `preferences.training_days`, `preferences.long_run_day`, `preferences.quality_days`, `preferences.methodology`.
- Goal object (from `/run-init` interview or existing `plan.json.goal`): `{race, target_time_s, race_date, race_name}`.
- `data/workout-templates.json`: template library (read-only, plugin-distributed).

## How to invoke the helper

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/build-training-plan/scripts')
from macrocycle import build_macrocycle
result = build_macrocycle('2026-04-30', '2026-10-15', ['Tue','Thu','Sat','Sun'])
print(json.dumps(result, indent=2))
"
```

`build_macrocycle` returns the skeleton: `{start_date, end_date, total_weeks, phases, weeks}`. Each week has `week_number`, `phase`, `target_volume_min=0`, `target_long_run_min=0`, `days=[]`. Claude fills in the days and volumes in the steps below.

## Steps

1. Read `storage/users.json` and confirm VDOT, training_days, long_run_day, and quality_days are all set.
2. Call `build_macrocycle(start_date, race_date, training_days)` to get the phase skeleton. If it raises `ValueError` (< 8 weeks), tell the user their race date is too soon and offer to create a race-prep plan without full periodization.
3. Determine the **baseline weekly volume** from `users.json.current_fitness.weekly_mileage_baseline_km`. Convert km to minutes using Easy pace: `baseline_min = baseline_km / (easy_per_km_s / 60)`. Round to nearest 5.
4. Assign `target_volume_min` per week using the **3-up-1-down** rule:
   - Weeks 1-3: +10%, +15%, +20% over baseline (capped at peak appropriate for phase)
   - Week 4: baseline × 0.80 (cutback week)
   - Repeat pattern. Peak volume in the build/peak phase should not exceed 1.5× baseline.
5. For each week, populate `days[]` by iterating over all 7 days of that week:
   - `long_run_day` → type `L`, longest duration of the week (from `target_long_run_min`)
   - `quality_days` → type `T`, `I`, or `R` based on phase (base=Strides, build=T/I, peak=I/M)
   - Remaining training_days → type `E`
   - All other days → type `Rest`
   - Select the matching template from `data/workout-templates.json` using `{phase}-{type}-{duration}` pattern
6. Enforce constraints:
   - No back-to-back quality days (if quality_days are adjacent, move one to the nearest non-adjacent training day)
   - Rest days never receive make-up workouts (`rest_days_sacred: true`)
   - Long run RPE-driven: always add note "RPE-driven, do not check pace"
7. Apply taper to the final 2-3 weeks by invoking the `taper-protocol` skill (which calls `taper.py:apply_taper`).
8. Build the complete `plan.json` structure per DESIGN.md §3.2 and write to `storage/plan.json`.
9. Display a summary to the user: total weeks, phase breakdown, first week's workouts.

## Output

`storage/plan.json` written with full macrocycle. Structure:

```json
{
  "version": 1,
  "goal": { "race": "marathon", "target_time_s": 14400, "race_date": "2026-10-15" },
  "methodology": "polarized",
  "macrocycle": { "start_date": "...", "total_weeks": 24, "phases": [...] },
  "weeks": [ { "week_number": 1, "phase": "base", "target_volume_min": 240, "days": [...] } ],
  "last_modified_at": "...",
  "last_modified_reason": "initial generation"
}
```

## Examples

**Marathon goal, 24 weeks, Tue/Thu/Sat/Sun training:**

- Week 1 (base): Tue E-35, Thu E-35, Sat E-40 + strides, Sun L-80, Mon/Wed/Fri Rest
- Week 11 (build): Tue E-40, Thu T-45, Sat I-50, Sun L-90, others Rest
- Week 23 (taper): cut volume to 60% of peak, preserve 1 T session

## Edge cases

- **Race date < 8 weeks away**: `build_macrocycle` raises `ValueError`. Offer a "race-prep" label: skip base/build structure, go straight to peak + taper for remaining weeks.
- **Race date > 24 weeks away**: `build_macrocycle` caps at 24 weeks. Inform the user; note the pre-block period is "general fitness" and suggest a replan when within 24 weeks.
- **quality_days adjacent** (e.g., Sat+Sun): shift one quality session to the closest non-adjacent training day, log a warning in `plan.json.last_modified_reason`.
- **Insufficient training days** (< 3): plan is possible but warn user that polarized methodology works best with 4+ days/week.
