# Compute VDOT — Instructions

## Inputs

- `distance_m` (int): race distance in metres. Supported values: `5000`, `10000`, `21097`, `42195`.
- `time_s` (int): finish time in seconds.
- `storage/users.json`: write target for the resulting VDOT and paces.

## How to invoke the helper

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/compute-vdot/scripts')
from vdot import vdot_from_race, paces_for_vdot
vdot = vdot_from_race(5000, 1440)
paces = paces_for_vdot(vdot)
print(json.dumps({'vdot': vdot, 'paces': paces}, indent=2))
"
```

Replace `5000` and `1440` with the user's actual distance and time.

## Steps

1. Confirm the user's race distance is one of the supported values: 5 km, 10 km, half-marathon, marathon. If the user provides a different distance (e.g., 8 km), ask them to pick the closest supported distance.
2. Convert user-provided time to seconds if given in `mm:ss` or `h:mm:ss` format.
3. Run the Bash one-liner above with the correct arguments. `vdot_from_race` interpolates linearly between the two nearest rows in `data/vdot-table.json`.
4. Run `paces_for_vdot(vdot)` to get the five training paces (all in seconds/km).
5. Read `storage/users.json`, update `current_fitness.vdot`, `current_fitness.vdot_source`, `current_fitness.vdot_source_date`, `current_fitness.vdot_source_result`, and `current_fitness.paces`. Write the file back.
6. Display to the user: VDOT score and all five paces formatted as `mm:ss / km`.

## Output

```json
{
  "vdot": 47.0,
  "paces": {
    "easy_per_km_s": 324,
    "marathon_per_km_s": 282,
    "threshold_per_km_s": 264,
    "interval_per_km_s": 240,
    "repetition_per_km_s": 222
  }
}
```

Written to `storage/users.json.current_fitness`.

## Examples

**5 km in 24:00 (1440 s):**

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/compute-vdot/scripts')
from vdot import vdot_from_race, paces_for_vdot
vdot = vdot_from_race(5000, 1440)
paces = paces_for_vdot(vdot)
print(json.dumps({'vdot': round(vdot, 1), 'paces': paces}, indent=2))
"
```

Expected output: VDOT ~47, Easy ~5:24/km, Threshold ~4:24/km.

**Marathon in 4:00:00 (14400 s):**

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
python3 -c "
import sys, json
sys.path.insert(0, 'skills/compute-vdot/scripts')
from vdot import vdot_from_race, paces_for_vdot
vdot = vdot_from_race(42195, 14400)
paces = paces_for_vdot(vdot)
print(json.dumps({'vdot': round(vdot, 1), 'paces': paces}, indent=2))
"
```

## Edge cases

- **Unsupported distance**: `vdot_from_race` raises `ValueError`. Ask the user to pick the closest supported distance (5 km, 10 km, half, full).
- **Missing `data/vdot-table.json`**: raises `FileNotFoundError`. The table is plugin-distributed and should always be present; surface the error and tell the user to reinstall or check the plugin's `data/` directory.
- **VDOT out of table range (< 30 or > 85)**: `_find_bracket` clamps to the nearest edge row. Inform the user that their result is outside the calibrated range and paces are estimates.
- **`storage/users.json` does not exist**: Create it from `storage/users.example.json` template before writing.
