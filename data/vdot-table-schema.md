# VDOT Table Schema

File: `data/vdot-table.json`

## Purpose

A static, read-only lookup table mapping integer VDOT scores (30–85) to training paces and race-time predictions, derived from Jack Daniels' Running Formula tables. The `compute-vdot` skill loads this file to resolve a VDOT score into the five canonical training paces and to cross-check predicted finish times. All values are integers (seconds per km or seconds total) to avoid floating-point ambiguity.

## Source Attribution

Values must faithfully reproduce the published tables from: *Daniels' Running Formula*, Jack Daniels (3rd edition, Human Kinetics). The file must include a `"source"` top-level field crediting this work.

## Top-Level Structure

```json
{
  "source": "Daniels' Running Formula, Jack Daniels, 3rd ed. (Human Kinetics)",
  "rows": [ ... ]
}
```

## Row Object

One row per integer VDOT value from 30 to 85 inclusive (56 rows total).

| Field | Type | Description |
|-------|------|-------------|
| `vdot` | integer | VDOT score (30–85) |
| `easy_per_km_s` | integer | Easy/recovery pace ceiling in seconds per km (~65–79% vVO2max) |
| `marathon_per_km_s` | integer | Marathon pace in seconds per km |
| `threshold_per_km_s` | integer | Threshold/tempo pace in seconds per km (~83–88% vVO2max) |
| `interval_per_km_s` | integer | Interval pace in seconds per km (~95–100% vVO2max) |
| `repetition_per_km_s` | integer | Repetition/speed pace in seconds per km (>100% vVO2max) |
| `predicted_5k_s` | integer | Predicted 5 K finish time in seconds |
| `predicted_10k_s` | integer | Predicted 10 K finish time in seconds |
| `predicted_half_s` | integer | Predicted half-marathon finish time in seconds |
| `predicted_marathon_s` | integer | Predicted marathon finish time in seconds |

## Notes

- All pace fields store the **slower end** of the Daniels pace range for that zone; the `compute-vdot` skill applies zone-specific range logic at prescription time.
- VDOT values outside the 30–85 range are not represented. The `compute-vdot` script clamps inputs and warns when extrapolation would be needed.
- Pace values decrease (get faster) as VDOT increases.
- Predicted race times are single-effort estimates; real performance varies with course and conditions.

## Example Row

```json
{
  "vdot": 40,
  "easy_per_km_s": 360,
  "marathon_per_km_s": 318,
  "threshold_per_km_s": 300,
  "interval_per_km_s": 276,
  "repetition_per_km_s": 258,
  "predicted_5k_s": 1620,
  "predicted_10k_s": 3360,
  "predicted_half_s": 7380,
  "predicted_marathon_s": 15300
}
```

## See Also

See `vdot-table.json` for the full table. Content is sourced separately by the data team.
