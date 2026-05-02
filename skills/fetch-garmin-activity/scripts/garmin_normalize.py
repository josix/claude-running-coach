"""
garmin_normalize.py — Pure helper functions for Garmin Connect activity normalization.

No I/O. All functions are deterministic and side-effect-free.

Field-name truth source: nrvim/garmin-givemydata MCP server
(https://github.com/nrvim/garmin-givemydata)

The upstream MCP server reads from a local SQLite database and returns
snake_case fields with units already applied (duration_min, distance_km, etc.).
This is a different shape from the legacy Taxuspt/garmin_mcp camelCase
output — see docstring examples below.

Expected input shapes:

normalize_activity expects a `garmin_activity_detail` response, which is a dict:
    {
      "activity": { activity_id, activity_type, start_time_local,
                    duration_min, distance_km, avg_hr, max_hr, ... },
      "splits": [{ split_number, distance_m, duration_sec,
                   avg_speed, avg_hr, ... }, ...],
      "hr_zones": {...},
      "weather": {...},
      "exercise_sets": [...],
      "running_dynamics": {...}
    }

is_duplicate / upsert_workout are source-agnostic and unchanged.
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ACTIVITY_TYPES = frozenset({
    "running",
    "track_running",
    "trail_running",
    "treadmill_running",
    "virtual_run",
    "indoor_running",
})
MIN_MOVING_TIME_MIN = 5.0  # 5 minutes


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _looks_like_uuid(value: object) -> bool:
    return isinstance(value, str) and bool(_UUID_RE.match(value))


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def normalize_activity(detail: dict) -> Optional[dict]:
    """Convert a `garmin_activity_detail` response to an internal ``actual`` workout sub-record.

    `detail` is the dict returned by `mcp__garmin__garmin_activity_detail` —
    its top-level keys are `activity`, `splits`, `hr_zones`, `weather`,
    `exercise_sets`, and (for runs) `running_dynamics`.

    Returns ``None`` to skip the activity if any of:
    - ``activity.activity_type`` is not in ``VALID_ACTIVITY_TYPES``
    - ``activity.duration_min`` < 5 or missing
    - ``activity.distance_km`` == 0 or missing

    Returns a dict with keys matching the workouts-schema.md ``actual`` sub-record:
    - ``duration_min``         : int   — round(duration_min)
    - ``distance_km``          : float — round(distance_km, 2)
    - ``avg_pace_per_km_s``    : int | None — derived from duration_min and distance_km
    - ``avg_hr``               : int | None
    - ``max_hr``               : int | None
    - ``rpe``                  : None — Garmin activities have no RPE field
    - ``splits``               : list[{km, pace_per_km_s}] — from detail.splits
    - ``notes``                : str — always empty (no description field)
    - ``garmin_activity_id``   : str — coerced from activity.activity_id
    """
    activity = (detail or {}).get("activity") or {}

    activity_type = activity.get("activity_type") or ""
    if activity_type not in VALID_ACTIVITY_TYPES:
        return None

    duration_min = activity.get("duration_min")
    if duration_min is None or duration_min < MIN_MOVING_TIME_MIN:
        return None

    distance_km = activity.get("distance_km")
    if not distance_km:
        return None

    if distance_km > 0:
        avg_pace_per_km_s: Optional[int] = round(duration_min * 60.0 / distance_km)
    else:
        avg_pace_per_km_s = None

    raw_avg_hr = activity.get("avg_hr")
    avg_hr: Optional[int] = round(raw_avg_hr) if raw_avg_hr is not None else None

    raw_max_hr = activity.get("max_hr")
    max_hr: Optional[int] = round(raw_max_hr) if raw_max_hr is not None else None

    raw_splits = (detail or {}).get("splits") or []
    splits: list[dict] = []
    for split in raw_splits:
        split_num = split.get("split_number")
        split_dist_m = split.get("distance_m") or 0
        split_dur_sec = split.get("duration_sec") or 0
        # Skip the trailing partial-km split (typically ~5 m of overshoot).
        # Garmin frequently emits a final split of distance_m < 100 with
        # duration_sec ≈ 1 — keeping it would produce nonsense paces.
        if split_dist_m < 100:
            continue
        if split_dur_sec > 0 and split_dist_m > 0:
            pace_s: Optional[int] = round(split_dur_sec * 1000.0 / split_dist_m)
        else:
            pace_s = None
        splits.append({"km": split_num, "pace_per_km_s": pace_s})

    activity_id = activity.get("activity_id")
    if activity_id is None:
        # Required for dedup — refuse to normalize without one.
        return None

    return {
        "duration_min": round(duration_min),
        "distance_km": round(distance_km, 2),
        "avg_pace_per_km_s": avg_pace_per_km_s,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "rpe": None,
        "splits": splits,
        "notes": "",
        "garmin_activity_id": str(activity_id),
    }


def extract_display_name(user_profile: dict) -> Optional[str]:
    """Pick a human-readable display name from a `garmin_user_profile` response.

    Order of preference: social_profile.fullName, social_profile.userProfileFullName,
    user_profile_base.firstName (+lastName), social_profile.displayName (rejected if UUID),
    social_profile.userName.

    Returns ``None`` if nothing usable is found.
    """
    social = (user_profile or {}).get("social_profile") or {}
    base = (user_profile or {}).get("user_profile_base") or {}

    full_name = social.get("fullName")
    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()

    user_profile_full = social.get("userProfileFullName")
    if isinstance(user_profile_full, str) and user_profile_full.strip():
        return user_profile_full.strip()

    first = base.get("firstName")
    last = base.get("lastName")
    if isinstance(first, str) and first.strip():
        if isinstance(last, str) and last.strip():
            return f"{first.strip()} {last.strip()}"
        return first.strip()

    display = social.get("displayName")
    if isinstance(display, str) and display.strip() and not _looks_like_uuid(display):
        return display.strip()

    user_name = social.get("userName")
    if isinstance(user_name, str) and user_name.strip():
        return user_name.strip()

    return None


def is_duplicate(workouts: list[dict], source: str, source_activity_id: str) -> bool:
    """Return ``True`` iff any existing workout has a matching (source, id) pair.

    Kept in sync with skills/fetch-strava-activity/scripts/strava_normalize.py.
    The id-field key is dynamically ``f'{source}_activity_id'``, so this function
    works for any source value (manual / strava / garmin).
    """
    id_field = f"{source}_activity_id"
    for workout in workouts:
        actual = workout.get("actual") or {}
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

    Kept in sync with skills/fetch-strava-activity/scripts/strava_normalize.py.
    The id-field key is dynamically ``f'{source}_activity_id'``, so this function
    works for any source value (manual / strava / garmin).

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
    result = list(workouts)

    incoming_source = new_workout.get("source", "manual")
    incoming_date = new_workout.get("date")
    incoming_id = new_workout.get("id")

    id_field = f"{incoming_source}_activity_id"
    actual = new_workout.get("actual") or {}
    source_activity_id = actual.get(id_field) or new_workout.get(id_field)

    if source_activity_id is not None and is_duplicate(workouts, incoming_source, source_activity_id):
        return list(workouts), "skipped_dup"

    same_date_workouts = [w for w in result if w.get("date") == incoming_date]

    if incoming_source == preferred_source:
        lower_priority = [
            w for w in same_date_workouts
            if w.get("source") != preferred_source and "superseded_by" not in w
        ]
        if lower_priority:
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
        preferred_on_date = [
            w for w in same_date_workouts
            if w.get("source") == preferred_source and "superseded_by" not in w
        ]
        if preferred_on_date:
            return list(workouts), "skipped_lower_priority"

    result.append(new_workout)
    return result, "appended"
