"""
macrocycle.py — Date math + phase split for building a training macrocycle.
"""
from __future__ import annotations

import math
from datetime import date


def build_macrocycle(start_date: str, race_date: str, training_days: list[str]) -> dict:
    """
    Build a macrocycle skeleton from start to race day.

    Args:
        start_date: ISO YYYY-MM-DD — first day of training.
        race_date: ISO YYYY-MM-DD — race day.
        training_days: list of abbreviated day names, e.g. ["Tue","Thu","Sat","Sun"].

    Returns:
        Dict with keys: start_date, end_date, total_weeks, phases, weeks.
        Each week has: week_number, phase, target_volume_min=0, target_long_run_min=0, days=[].

    Raises:
        ValueError: if race_date <= start_date, or total weeks < 8.
    """
    start = date.fromisoformat(start_date)
    race = date.fromisoformat(race_date)

    if race <= start:
        raise ValueError(
            f"race_date ({race_date}) must be after start_date ({start_date})."
        )

    total_days = (race - start).days
    total_weeks = total_days // 7
    # If the race doesn't fall on a week boundary we still count a partial final week.
    if total_days % 7 > 0:
        total_weeks += 1

    if total_weeks < 8:
        raise ValueError(
            f"Only {total_weeks} week(s) available between {start_date} and {race_date}. "
            "Minimum is 8 weeks."
        )

    # Cap at 24 weeks; phases are anchored to the race end date.
    effective_weeks = min(total_weeks, 24)

    # Phase split — all values in whole weeks; must sum to effective_weeks exactly.
    taper_weeks = max(2, math.ceil(effective_weeks * 0.10))
    peak_weeks = math.ceil(effective_weeks * 0.15)
    build_weeks = math.ceil(effective_weeks * 0.35)
    base_weeks = effective_weeks - taper_weeks - peak_weeks - build_weeks

    # Guard against rounding eating into base (shouldn't happen but be safe).
    if base_weeks < 1:
        base_weeks = 1
        build_weeks = effective_weeks - taper_weeks - peak_weeks - base_weeks

    phases_raw = [
        ("base", base_weeks),
        ("build", build_weeks),
        ("peak", peak_weeks),
        ("taper", taper_weeks),
    ]

    # Build phase objects with start/end week numbers (1-indexed).
    phases = []
    cursor = 1
    for name, wks in phases_raw:
        phases.append({
            "name": name,
            "start_week": cursor,
            "end_week": cursor + wks - 1,
        })
        cursor += wks

    # Build empty week skeletons.
    weeks = []
    for i in range(effective_weeks):
        week_num = i + 1
        phase_name = _phase_for_week(week_num, phases)
        weeks.append({
            "week_number": week_num,
            "phase": phase_name,
            "target_volume_min": 0,
            "target_long_run_min": 0,
            "days": [],
        })

    return {
        "start_date": start_date,
        "end_date": race_date,
        "total_weeks": effective_weeks,
        "phases": phases,
        "weeks": weeks,
    }


def _phase_for_week(week_num: int, phases: list[dict]) -> str:
    for p in phases:
        if p["start_week"] <= week_num <= p["end_week"]:
            return p["name"]
    return "unknown"
