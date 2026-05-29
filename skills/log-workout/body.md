# Log Workout — Instructions

## Inputs

- Target date: from `/run-log [date]` argument, or today's date if omitted.
- `storage/plan.json`: look up the prescribed workout for the target date.
- `storage/workouts.json`: existing workout log (read before appending).
- `storage/daily_state.json`: carry-forward state (read before updating).

## Steps

1. Look up the prescribed workout for the target date from `plan.json`. Note its `type`, `duration_min`, `target_pace`, and `notes`. If no prescription exists for that date, mark as "unplanned".
2. Greet the user with the prescribed workout summary: "You had a {type} run scheduled for {duration_min} min at {pace}/km. How did it go?" — on first mention of the type code, append its gloss from `references/glossary.md` in parentheses (e.g., "You had a T — Threshold (comfortably hard; speak a few words, not a full sentence) run scheduled…").
3. Conduct a **one-question-at-a-time** conversational interview:
   - "How long did you run?" (duration in minutes or hh:mm)
   - "How far?" (optional — distance in km or miles; skip if user says "didn't track")
   - "Average heart rate?" (optional — in bpm; skip if "didn't track")
   - "RPE on a scale of 1–10? (RPE — Rate of Perceived Exertion: 1 = walking, 10 = all-out sprint)" (always ask — foundational signal)
   - "Any splits to log?" (optional — e.g., "5:20, 5:15, 5:30 per km"; skip if "no")
   - "Any notes or how did it feel?" (free text; optional)
4. Parse user responses and build the `actual` dict:
   - Convert duration to minutes (float). Convert distance to km if given in miles (× 1.60934).
   - Compute `avg_pace_per_km_s` if both duration_min and distance_km are available: `(duration_min * 60) / distance_km`.
   - Parse splits as a list of `{km, pace_per_km_s}` objects.
5. Generate workout ID: `wkt-{date}-{NNN}` where NNN is the count of existing workouts on that date + 1 (zero-padded to 3 digits).
6. Call the `analyze-workout` skill with `actual` and `prescribed` to get the `analysis` dict.
7. Build the complete workout record per DESIGN.md §3.4 schema and append to `workouts.json` (read-modify-write).
8. Call the `adapt-plan` skill with the analysis delta to apply strike rules.
9. Update `daily_state.json`:
   - Set `as_of_date`, `last_workout_id`, `last_workout_quality` (from analysis verdict).
   - Derive `warm_up_cue` from the session (e.g., "Hamstrings tight today — stretch before next run").
   - Update `consecutive_misses` / `consecutive_ahead` from adapt-plan's new_state.
10. Confirm to the user: "Logged! {type} — {duration_min} min, RPE {rpe}, verdict: {verdict}." If plan was modified, explain what changed.

## Output

```json
{
  "id": "wkt-2026-05-05-001",
  "date": "2026-05-05",
  "source": "manual",
  "strava_activity_id": null,
  "prescribed": { "type": "E", "duration_min": 35, "target_pace_per_km_s": 324, "notes": "..." },
  "actual": {
    "duration_min": 36,
    "distance_km": 6.6,
    "avg_pace_per_km_s": 327,
    "avg_hr": 142,
    "max_hr": 155,
    "rpe": 4,
    "splits": [],
    "notes": "felt good, slightly windy"
  },
  "analysis": { "completion_pct": 103, "pace_delta_pct": 0.9, "rpe_delta": 0, "hr_drift_bpm": null, "verdict": "on-target" }
}
```

## Examples

**On-target Easy run:**
User: "36 minutes / 6.6 km / HR 142 / RPE 4 / no splits / felt good"
→ completion_pct=103, pace_delta_pct=+0.9%, verdict="on-target"
→ No plan change, carry-forward: "Standard warm-up is working well."

**Under-target Threshold run (2nd miss):**
User: "30 min / RPE 9 / couldn't hold pace — had to bail at 30 min"
→ completion_pct=75, pace_delta_pct=+6%, rpe_delta=+2, verdict="under"
→ adapt-plan fires "reduce_next_quality": next quality session downgraded T→E

## Edge cases

- **Workout on a rest day**: log it with `prescribed: null` and note "unplanned" in the actual.notes field. Run analyze-workout with `prescribed={}` (empty dict — analyze handles null prescribed gracefully).
- **User provides no distance**: leave `distance_km` and `avg_pace_per_km_s` as null; analyze-workout will skip pace delta computation.
- **User provides miles**: convert to km before storing (1 mile = 1.60934 km).
- **Multiple workouts same day**: NNN counter increments (wkt-2026-05-05-002, etc.).
- **`workouts.json` does not exist**: create it from `storage/workouts.example.json` template.
