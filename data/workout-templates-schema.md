# Workout Templates Schema

File: `data/workout-templates.json`

## Purpose

A static, read-only library of reusable workout patterns organized by training phase and session type. The `build-training-plan` skill selects and composes templates from this library when generating the macrocycle week-by-week, filling in the `days` array of each week in `plan.json`. Templates encode the workout structure (warm-up, main set, cool-down) and a coach-notes template string that is rendered with runner-specific pace values at prescription time.

## Top-Level Structure

```json
{
  "templates": [ ... ]
}
```

## Template Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique template identifier, conventionally `"<phase>-<type>-<duration_min>"` (e.g., `"base-E-35"`, `"build-T-40"`) |
| `phase` | string | Training phase this template belongs to: `"base"`, `"build"`, `"peak"`, or `"taper"` |
| `type` | string | Workout type: `"E"` (easy), `"L"` (long), `"T"` (threshold), `"I"` (interval), `"R"` (repetition), `"M"` (marathon-pace), `"Strides"`, or `"Recovery"` |
| `duration_min` | integer | Total prescribed session duration in minutes (including warm-up and cool-down) |
| `structure` | string | Human-readable breakdown of the workout (e.g., `"10 min easy WU, 20 min @ T, 10 min easy CD"`) |
| `notes_template` | string | Coach note shown to the runner at prescription time; may be empty. Should not include raw pace values — the renderer substitutes actual paces from `users.json` |

## Enumerations

**Phase values**: `base` | `build` | `peak` | `taper`

**Type values**: `E` | `L` | `T` | `I` | `R` | `M` | `Strides` | `Recovery`

## Notes

- A template describes the *shape* of a workout, not the specific paces. Paces are resolved at plan-generation time from `users.json current_fitness.paces`.
- `notes_template` may reference pace zones symbolically (e.g., `"@ T pace"`) but must not embed raw numbers; the renderer substitutes actual seconds-per-km values.
- Multiple templates may share the same `phase` and `type` but differ in `duration_min`, covering the progressive volume increases across weeks.
- The library should cover all phase × type combinations that appear in a standard 24-week marathon block.

## Example Entry

```json
{
  "id": "build-T-40",
  "phase": "build",
  "type": "T",
  "duration_min": 40,
  "structure": "10 min easy WU, 20 min @ T, 10 min easy CD",
  "notes_template": "RPE should plateau at 7 — if it keeps climbing, cut the T block short"
}
```

## See Also

See `workout-templates.json` for the full template library. Content is sourced separately by the data team.
