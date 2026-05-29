# Weekly Review — Instructions

## Inputs

- `storage/workouts.json`: all completed workouts (filter by week dates).
- `storage/plan.json`: macrocycle plan with week definitions.
- `week_number`: target week (1-indexed). Default: determine current week from today's date and `plan.json.macrocycle.start_date`.
- `storage/progress.json`: append the summary here.

## How to invoke the helper

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/weekly-review/scripts')
from weekly import weekly_review

workouts = json.load(open('storage/workouts.json'))['workouts']
plan     = json.load(open('storage/plan.json'))
result   = weekly_review(workouts, plan, week_number=3)
print(json.dumps(result, indent=2))
"
```

Replace `week_number=3` with the target week number.

## Steps

1. Determine `week_number`: if the user passed `--week N` use N; otherwise compute from today's date vs `plan.json.macrocycle.start_date` (days elapsed // 7 + 1).
2. Read `storage/workouts.json` and `storage/plan.json`.
3. Call `weekly_review(workouts, plan, week_number)` from `scripts/weekly.py`. The function returns:
   - `completed_volume_min`, `prescribed_volume_min`, `completion_ratio`
   - `quality_completed`, `quality_prescribed`
   - `fatigue_indicators`: `{avg_rpe, rpe_creep, hr_drift_avg}`
   - `verdict`: `"hold"`, `"advance"`, or `"recovery"`
   - `notes`: one-line human summary
4. If `verdict == "recovery"`: directly insert a recovery week by running:

   ```bash
   cd "${CLAUDE_PLUGIN_ROOT}"
   python3 -c "
   import sys, json, copy
   sys.path.insert(0, 'skills/adapt-plan/scripts')
   from adapt import insert_recovery_week
   plan = json.load(open('storage/plan.json'))
   new_plan = insert_recovery_week(plan, '$(date +%Y-%m-%d)')
   json.dump(new_plan, open('storage/plan.json', 'w'), indent=2)
   "
   ```

   Inform the user: "Recovery needed — inserting a recovery week (volume cut to 70%, one quality session removed)."
5. Append the summary to `storage/progress.json.weekly_summaries`. Also update `progress.rolling_7d` and `progress.rolling_28d`.
6. Render the Markdown report (see Output section).

## Output

Weekly summary dict appended to `progress.json`:

```json
{
  "week_number": 3,
  "completed_volume_min": 215,
  "prescribed_volume_min": 240,
  "completion_ratio": 0.896,
  "quality_completed": 1,
  "quality_prescribed": 2,
  "fatigue_indicators": { "avg_rpe": 5.8, "rpe_creep": 0.6, "hr_drift_avg": 2.1 },
  "verdict": "hold",
  "notes": "Hold steady: 90% volume completion, 1/2 quality sessions, avg RPE 5.8. Continue plan as-is."
}
```

Markdown report format:

```
## Week 3 Review — {date range}

**Volume:** {completed_volume_min} / {prescribed_volume_min} min ({pct}%)
**Quality Sessions:** {quality_completed} / {quality_prescribed}
**Avg RPE:** {avg_rpe} | RPE Creep vs last week: {rpe_creep}  (RPE — Rate of Perceived Exertion: 1 = walking, 10 = all-out sprint; RPE Creep = trending upward at same effort, a fatigue signal)
**HR Drift Avg:** {hr_drift_avg} bpm  (HR drift — heart rate creeping up at steady effort; a fatigue or heat signal)

**Verdict: HOLD / ADVANCE / RECOVERY**

{notes}

{if recovery: "Inserting a recovery week — volume cut to 70%, one quality session removed."}
```

## Examples

**Strong week (advance):**
230/240 min, 2/2 quality, avg RPE 5.2, rpe_creep=0.1 → verdict="advance"
Report: "Strong week — advancing volume by 10% next week."

**Tired week (recovery):**
155/240 min, 1/2 quality, avg RPE 7.1, rpe_creep=1.4 → verdict="recovery"
Report: "Recovery needed — inserting recovery week." adapt-plan fires.

## Edge cases

- **Week not found in plan**: `weekly_review` raises `ValueError`. Tell the user the week number is out of range.
- **No workouts logged for the week**: `completed_volume_min=0`, `quality_completed=0`, `completion_ratio=0.0`. Verdict will be `"recovery"` unless all days were rest days in the plan.
- **Week 1** (no previous week for rpe_creep): `rpe_creep=None`; treat as neutral for verdict computation.
- **`progress.json` does not exist**: create it from `storage/progress.example.json` template before appending.
