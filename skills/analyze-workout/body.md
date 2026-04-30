# Analyze Workout — Instructions

## Inputs

- `actual` dict: `{duration_min, distance_km, avg_pace_per_km_s, avg_hr, max_hr, rpe, splits, notes}`. Fields may be null.
- `prescribed` dict: `{type, duration_min, target_pace_per_km_s, notes}`. May be empty dict `{}` for unplanned runs.

## How to invoke the helper

Preferred — pipe JSON through stdin:

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/analyze-workout/scripts')
from analyze import analyze
data = json.load(sys.stdin)
print(json.dumps(analyze(data['actual'], data['prescribed']), indent=2))
"
```

Simpler one-liner with inline data:

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/analyze-workout/scripts')
from analyze import analyze
actual = {'duration_min': 38, 'distance_km': 7.8, 'avg_pace_per_km_s': 270, 'avg_hr': 168, 'rpe': 7, 'splits': []}
prescribed = {'type': 'T', 'duration_min': 40, 'target_pace_per_km_s': 264}
print(json.dumps(analyze(actual, prescribed), indent=2))
"
```

## Steps

1. Call `analyze(actual, prescribed)` from `scripts/analyze.py`. The function handles null fields gracefully.
2. The function computes:
   - `completion_pct`: `(actual.duration_min / prescribed.duration_min) × 100`. If prescribed duration is 0, defaults to 100%.
   - `pace_delta_pct`: `((actual_pace - target_pace) / target_pace) × 100`. Positive = slower. Null if pace data is missing.
   - `rpe_delta`: `actual.rpe - expected_rpe_for_type`. Expected RPE by type: E=4, L=5, M=6, T=7, I=8, R=9, Strides=5, Recovery=3.
   - `hr_drift_bpm`: avg HR of second half of splits minus first half. Null if splits absent or HR not in splits.
   - `verdict`: determined by threshold logic (see below).
3. Return the result dict to the caller (logged by log-workout into workouts.json).

## Verdict thresholds (DESIGN.md §4)

| Condition | Threshold |
|---|---|
| `aborted` | `completion_pct < 50` |
| `under` | Any **two** of: `completion_pct < 80`, `pace_delta_pct > +5`, `rpe_delta > +2` |
| `over` | `rpe_delta < -1` alone, OR BOTH `pace_delta_pct < -3` AND `rpe_delta <= 0` |
| `on-target` | None of the above |

## Output

```json
{
  "completion_pct": 95.0,
  "pace_delta_pct": 2.3,
  "rpe_delta": 0,
  "hr_drift_bpm": 4.0,
  "verdict": "on-target"
}
```

## Examples

**Threshold run slightly slow, slightly hard:**
actual: 38 min / pace 270 s/km / RPE 7 → prescribed: 40 min / pace 264 s/km / type T (expected RPE 7)
→ completion_pct=95, pace_delta_pct=+2.3, rpe_delta=0 → verdict="on-target"

**Short, slow, hard Easy run:**
actual: 20 min / pace 350 s/km / RPE 7 → prescribed: 35 min / pace 324 s/km / type E (expected RPE 4)
→ completion_pct=57, pace_delta_pct=+8, rpe_delta=+3 → two under signals → verdict="under"

## Edge cases

- **`prescribed` is empty dict** (unplanned run): `completion_pct=100`, `pace_delta_pct=None`, `rpe_delta=None` → verdict defaults to `"on-target"`.
- **No pace data** (`avg_pace_per_km_s=None`): skip pace delta; verdict computed from completion and RPE only.
- **No RPE data**: skip RPE delta; verdict computed from completion and pace only.
- **Splits have no HR**: `hr_drift_bpm` returns null; does not affect verdict.
