"""
taper.py — Taper curve generator for the final 2–3 weeks of a training plan.
"""
from __future__ import annotations

import copy
from datetime import date


def apply_taper(weeks: list[dict], race_date: str) -> list[dict]:
    """
    Modify the last 2–3 weeks of the plan into a taper curve.

    Volume schedule (measured against the highest non-taper week's target_volume_min):
      - race-week-2 (only if total weeks >= 18): -20% from peak
      - race-week-1: -40% from peak
      - race week (final): -60% from peak, 1 short opener + race day

    Intensity: preserved in race-week-1 (keep 1 T or I session).
    Returns a new weeks list (non-destructive).

    Args:
        weeks: list of week dicts with week_number, days (populated by build-training-plan).
        race_date: ISO YYYY-MM-DD of race day.
    """
    new_weeks = copy.deepcopy(weeks)
    if not new_weeks:
        return new_weeks

    total_weeks = len(new_weeks)
    race_day = date.fromisoformat(race_date)

    # Determine peak volume (highest target_volume_min across all weeks).
    peak_volume = max((w.get("target_volume_min", 0) for w in new_weeks), default=0)
    if peak_volume == 0:
        # Fallback: use the max completed duration across all days.
        peak_volume = max(
            (
                sum(d.get("duration_min", 0) for d in w.get("days", []))
                for w in new_weeks
            ),
            default=0,
        )

    # Identify taper weeks by position from the end.
    # race_week  = new_weeks[-1]
    # rw_minus_1 = new_weeks[-2] (always tapered if total >= 2)
    # rw_minus_2 = new_weeks[-3] (only if total >= 18)
    race_week = new_weeks[-1]
    _apply_race_week(race_week, peak_volume, race_day)

    if total_weeks >= 2:
        rw_minus_1 = new_weeks[-2]
        _apply_race_week_minus_1(rw_minus_1, peak_volume)

    if total_weeks >= 18:
        rw_minus_2 = new_weeks[-3]
        _apply_race_week_minus_2(rw_minus_2, peak_volume)

    return new_weeks


def _apply_race_week(week: dict, peak_volume: int, race_day: date) -> None:
    """
    Race week: volume = 40% of peak (-60%), 1 short opener + race day.
    Mutates week in-place.
    """
    week["target_volume_min"] = int(peak_volume * 0.40)
    week["taper"] = True

    days = week.get("days", [])

    # Find the day matching race_date and mark it as Race.
    for d in days:
        d_date_str = d.get("date")
        if d_date_str:
            try:
                if date.fromisoformat(d_date_str) == race_day:
                    d["type"] = "Race"
                    d["notes"] = "Race day"
                    break
            except ValueError:
                pass
    else:
        # No day matched race_day; append a race day stub.
        days.append({
            "date": race_day.isoformat(),
            "type": "Race",
            "duration_min": 0,
            "notes": "Race day",
        })

    # Convert any remaining quality sessions (T/I/R) to short E or Recovery.
    quality_types = {"T", "I", "R"}
    for d in days:
        if d.get("type") in quality_types:
            d["type"] = "E"
            d["duration_min"] = min(d.get("duration_min", 20), 20)
            d["notes"] = "Short shakeout"


def _apply_race_week_minus_1(week: dict, peak_volume: int) -> None:
    """
    Race-week-1: volume -40% (= 60% of peak), preserve 1 quality T or I.
    Mutates week in-place.
    """
    week["target_volume_min"] = int(peak_volume * 0.60)
    week["taper"] = True

    days = week.get("days", [])
    quality_types = {"T", "I", "R"}

    # Keep at most 1 quality session; convert extras to E.
    quality_count = 0
    for d in days:
        if d.get("type") in quality_types:
            if quality_count == 0:
                quality_count += 1  # preserve the first quality session
            else:
                d["type"] = "E"

    # Reduce long run duration by 40% if present.
    for d in days:
        if d.get("type") == "L":
            d["duration_min"] = int(d.get("duration_min", 0) * 0.60)


def _apply_race_week_minus_2(week: dict, peak_volume: int) -> None:
    """
    Race-week-2 (only if total weeks >= 18): volume -20% (= 80% of peak).
    Mutates week in-place.
    """
    week["target_volume_min"] = int(peak_volume * 0.80)
    week["taper"] = True
