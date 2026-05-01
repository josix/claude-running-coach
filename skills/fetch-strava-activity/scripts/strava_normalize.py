"""
strava_normalize.py — Pure helper functions for Strava activity normalization.

No I/O. All functions are deterministic and side-effect-free.
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SPORT_TYPES = {"Run", "TrailRun", "VirtualRun"}
MIN_MOVING_TIME_S = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def normalize_activity(strava_activity: dict) -> Optional[dict]:
    """Convert a Strava API activity dict to an internal ``actual`` workout sub-record.

    Returns ``None`` to skip the activity if any of:
    - ``sport_type`` / ``type`` is not in {``Run``, ``TrailRun``, ``VirtualRun``}
    - ``moving_time`` < 300 seconds (< 5 min)
    - ``distance`` == 0 or missing

    Returns a dict with keys matching the workouts-schema.md ``actual`` sub-record:
    - ``duration_min``        : int   — round(moving_time / 60)
    - ``distance_km``         : float — round(distance / 1000, 2)
    - ``avg_pace_per_km_s``   : int | None — 1000 / average_speed if speed > 0 else None
    - ``avg_hr``              : int | None — round(average_heartrate) if present
    - ``max_hr``              : int | None — round(max_heartrate) if present
    - ``rpe``                 : int | None — parsed from description
    - ``splits``              : list[{km, pace_per_km_s}]
    - ``notes``               : str
    - ``strava_activity_id``  : str
    """
    # --- sport type filter ---
    sport_type = strava_activity.get("sport_type") or strava_activity.get("type") or ""
    if sport_type not in VALID_SPORT_TYPES:
        return None

    # --- duration filter ---
    moving_time = strava_activity.get("moving_time", 0) or 0
    if moving_time < MIN_MOVING_TIME_S:
        return None

    # --- distance filter ---
    distance = strava_activity.get("distance", 0) or 0
    if not distance:
        return None

    # --- pace ---
    average_speed = strava_activity.get("average_speed", 0) or 0
    if average_speed > 0:
        avg_pace_per_km_s: Optional[int] = round(1000 / average_speed)
    else:
        avg_pace_per_km_s = None

    # --- HR ---
    raw_avg_hr = strava_activity.get("average_heartrate")
    avg_hr: Optional[int] = round(raw_avg_hr) if raw_avg_hr is not None else None

    raw_max_hr = strava_activity.get("max_heartrate")
    max_hr: Optional[int] = round(raw_max_hr) if raw_max_hr is not None else None

    # --- RPE from description ---
    description = strava_activity.get("description") or ""
    rpe = parse_rpe_from_notes(description)

    # --- splits ---
    splits_metric = strava_activity.get("splits_metric") or []
    splits = []
    for idx, split in enumerate(splits_metric, start=1):
        split_speed = split.get("average_speed", 0) or 0
        if split_speed > 0:
            pace_s = round(1000 / split_speed)
        else:
            pace_s = None
        splits.append({"km": idx, "pace_per_km_s": pace_s})

    # --- activity id ---
    activity_id = strava_activity.get("id")

    return {
        "duration_min": round(moving_time / 60),
        "distance_km": round(distance / 1000, 2),
        "avg_pace_per_km_s": avg_pace_per_km_s,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "rpe": rpe,
        "splits": splits,
        "notes": description,
        "strava_activity_id": str(activity_id) if activity_id is not None else None,
    }


def parse_rpe_from_notes(text: Optional[str]) -> Optional[int]:
    """Parse RPE integer from free-text notes.

    Matches (case-insensitive):
    - ``RPE: N`` / ``RPE N`` / ``RPE=N``
    - ``feeling: N/10`` / ``feeling N/10``

    Returns an int in the range 1–10, or ``None`` if no match or out-of-range.
    """
    if not text:
        return None

    # Pattern 1: RPE: N, RPE N, RPE=N  (N can be 1 or 2 digits)
    m = re.search(r"\brpe\s*[=:]\s*(\d+)", text, re.IGNORECASE)
    if not m:
        # Also match "rpe N" without punctuation
        m = re.search(r"\brpe\s+(\d+)\b", text, re.IGNORECASE)

    if not m:
        # Pattern 2: feeling: N/10, feeling N/10
        m = re.search(r"\bfeeling\s*:?\s*(\d+)\s*/\s*10\b", text, re.IGNORECASE)

    if m:
        value = int(m.group(1))
        if 1 <= value <= 10:
            return value
        return None

    return None


def is_duplicate(workouts: list[dict], source: str, source_activity_id: str) -> bool:
    """Return ``True`` iff any existing workout has a matching (source, id) pair.

    For ``source='strava'``, checks ``workout.get('strava_activity_id') == source_activity_id``.
    Forward-compatible: ``source='garmin'`` would check ``'garmin_activity_id'``.
    """
    id_field = f"{source}_activity_id"
    for workout in workouts:
        actual = workout.get("actual") or {}
        # Check both top-level and nested in actual
        if workout.get(id_field) == source_activity_id:
            return True
        if actual.get(id_field) == source_activity_id:
            return True
    return False


def upsert_workout(
    workouts: list[dict],
    new_workout: dict,
    preferred_source: str,
) -> tuple[list[dict], str]:
    """Append a new workout with tiebreaker deduplication logic.

    Returns ``(new_workouts_list, action)`` where action is one of:
    - ``'appended'``                  — no conflict, workout added
    - ``'skipped_dup'``               — same source_activity_id already present
    - ``'skipped_lower_priority'``    — same date already has a workout from preferred_source
    - ``'replaced_lower_priority'``   — incoming is preferred; displaces an entry from another source

    Rules:
    1. If ``is_duplicate(...)`` for ``new_workout``'s source+id → ``skipped_dup``, return unchanged.
    2. Find existing workouts on the same date.
    3. If incoming ``source == preferred_source`` AND there's an existing entry from a different source
       on that date: mark existing entry as superseded (add ``superseded_by: new_workout["id"]``) —
       keep it in the list — and append new. Action = ``'replaced_lower_priority'``.
    4. If incoming ``source != preferred_source`` AND there's an existing entry from ``preferred_source``
       on that date: do not append; action = ``'skipped_lower_priority'``.
    5. Otherwise append; action = ``'appended'``.

    Never deletes data. Never mutates input lists in place — returns a new list.
    """
    # Work on a shallow copy of the list; individual dict objects shared until mutated
    result = list(workouts)

    incoming_source = new_workout.get("source", "manual")
    incoming_date = new_workout.get("date")
    incoming_id = new_workout.get("id")

    # Rule 1: duplicate check
    id_field = f"{incoming_source}_activity_id"
    # Get the source-specific id from the actual sub-record or top-level
    actual = new_workout.get("actual") or {}
    source_activity_id = actual.get(id_field) or new_workout.get(id_field)

    if source_activity_id is not None and is_duplicate(workouts, incoming_source, source_activity_id):
        return list(workouts), "skipped_dup"

    # Rule 2: find existing workouts on the same date
    same_date_workouts = [w for w in result if w.get("date") == incoming_date]

    if incoming_source == preferred_source:
        # Rule 3: incoming is preferred source — check for lower-priority entries on same date
        lower_priority = [
            w for w in same_date_workouts
            if w.get("source") != preferred_source and "superseded_by" not in w
        ]
        if lower_priority:
            # Mark them as superseded (copy to avoid mutating originals)
            new_result = []
            for w in result:
                if w in lower_priority:
                    superseded = dict(w)
                    superseded["superseded_by"] = incoming_id
                    new_result.append(superseded)
                else:
                    new_result.append(w)
            new_result.append(new_workout)
            return new_result, "replaced_lower_priority"
    else:
        # Rule 4: incoming is not preferred source — skip if preferred already present
        preferred_on_date = [
            w for w in same_date_workouts
            if w.get("source") == preferred_source and "superseded_by" not in w
        ]
        if preferred_on_date:
            return list(workouts), "skipped_lower_priority"

    # Rule 5: no conflict — just append
    result.append(new_workout)
    return result, "appended"
