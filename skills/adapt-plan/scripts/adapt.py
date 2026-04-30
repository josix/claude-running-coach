"""
adapt.py — Strike-rule engine implementing DESIGN.md §4 adaptive iteration rules.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

_TYPE_DOWNGRADE: dict[str, str] = {
    "T": "E",
    "I": "T",
    "R": "I",
}


def adapt(plan: dict, state: dict, delta: dict, today: str) -> tuple[dict, dict, str]:
    """
    Apply 1/2/3-strike adaptation rules per DESIGN.md §4.

    Args:
        plan:  plan dict (macrocycle with weeks + days).
        state: daily_state dict (consecutive_misses, consecutive_ahead, carry_forward).
        delta: analysis dict (verdict, hr_drift_bpm, rpe_delta).
        today: ISO YYYY-MM-DD of the workout being evaluated.

    Returns:
        (new_plan, new_state, action) — new_plan and new_state are deep copies; inputs unmodified.

    Actions:
        'monitor', 'reduce_next_quality', 'recovery_week',
        'vdot_bump', 'red_flag_recovery', 'no_change'
    """
    new_plan = copy.deepcopy(plan)
    new_state = copy.deepcopy(state)
    verdict = delta.get("verdict", "on-target")
    action: str = "no_change"

    if verdict == "under":
        new_state["consecutive_misses"] = new_state.get("consecutive_misses", 0) + 1
        new_state["consecutive_ahead"] = 0
        misses = new_state["consecutive_misses"]

        if misses == 1:
            action = "monitor"
        elif misses == 2:
            action = "reduce_next_quality"
            _reduce_next_quality_session(new_plan, today)
        else:  # misses >= 3
            action = "recovery_week"
            _insert_recovery_week(new_plan, today)
            new_state["consecutive_misses"] = 0

    elif verdict == "over":
        new_state["consecutive_ahead"] = new_state.get("consecutive_ahead", 0) + 1
        new_state["consecutive_misses"] = 0
        ahead = new_state["consecutive_ahead"]

        if ahead >= 3:
            action = "vdot_bump"
            new_state["consecutive_ahead"] = 0
        else:
            action = "no_change"

    elif verdict == "on-target":
        new_state["consecutive_misses"] = 0
        new_state["consecutive_ahead"] = 0
        action = "no_change"

    elif verdict == "aborted":
        new_state["consecutive_misses"] = new_state.get("consecutive_misses", 0) + 1
        new_state["consecutive_ahead"] = 0  # m2 fix

        red_flag_fired = False
        hr_drift = delta.get("hr_drift_bpm")
        rpe_delta = delta.get("rpe_delta")
        if hr_drift is not None and hr_drift > 8 and rpe_delta is not None and rpe_delta >= 2:
            carry = new_state.setdefault("carry_forward", {})
            red_flags = carry.setdefault("recurring_red_flags", [])
            red_flags.append({"date": today, "signal": "high_drift_high_rpe"})

            # Count flags within last 14 days.
            today_date = date.fromisoformat(today)
            cutoff = today_date - timedelta(days=14)
            recent_count = sum(
                1 for rf in red_flags
                if date.fromisoformat(rf["date"]) >= cutoff
            )
            if recent_count >= 2:
                action = "red_flag_recovery"
                _insert_recovery_week(new_plan, today)
                red_flag_fired = True

        if not red_flag_fired:
            misses = new_state["consecutive_misses"]
            if misses == 1:
                action = "monitor"
            elif misses == 2:
                action = "reduce_next_quality"
                _reduce_next_quality_session(new_plan, today)
            else:  # misses >= 3
                action = "recovery_week"
                _insert_recovery_week(new_plan, today)
                new_state["consecutive_misses"] = 0

    return new_plan, new_state, action


def insert_recovery_week(plan: dict, today: str) -> dict:
    """Public helper: insert a recovery week into plan starting after today.
    Used by weekly-review when its verdict is 'recovery'.
    Non-destructive — returns new plan."""
    new_plan = copy.deepcopy(plan)
    _insert_recovery_week(new_plan, today)
    return new_plan


# ── Mutation helpers ──────────────────────────────────────────────────────────

def _find_next_quality_day(plan: dict, today: str) -> dict | None:
    """Return the first quality workout (T/I/R) after today across all weeks."""
    today_date = date.fromisoformat(today)
    quality_types = {"T", "I", "R"}
    for week in plan.get("weeks", []):
        for day in week.get("days", []):
            day_date_str = day.get("date")
            if not day_date_str:
                continue
            try:
                day_date = date.fromisoformat(day_date_str)
            except ValueError:
                continue
            if day_date > today_date and day.get("type") in quality_types:
                return day
    return None


def _reduce_next_quality_session(plan: dict, today: str) -> None:
    """
    Downgrade the next quality session by one step (T→E, I→T, R→I),
    or if no type mapping exists, reduce duration by 25%.
    Mutates plan in-place.
    """
    day = _find_next_quality_day(plan, today)
    if day is None:
        return
    current_type = day.get("type")
    if current_type in _TYPE_DOWNGRADE:
        day["type"] = _TYPE_DOWNGRADE[current_type]
    else:
        dur = day.get("duration_min", 0)
        day["duration_min"] = int(dur * 0.75)


def _insert_recovery_week(plan: dict, today: str) -> None:
    """
    Insert a recovery week starting the next full week after today.
    Cuts target_volume_min by 30% and drops one quality session (T/I/R → E).
    If the next week already exists in the plan, mutate it; otherwise append a stub.
    Mutates plan in-place.
    """
    today_date = date.fromisoformat(today)
    quality_types = {"T", "I", "R"}

    # Find the first week whose earliest day is strictly after today.
    # This is the "next week" that hasn't started yet.
    next_week: dict | None = None
    for week in plan.get("weeks", []):
        days = week.get("days", [])
        week_dates = []
        for d in days:
            ds = d.get("date")
            if ds:
                try:
                    week_dates.append(date.fromisoformat(ds))
                except ValueError:
                    pass
        if week_dates:
            week_start = min(week_dates)
            if week_start > today_date:
                next_week = week
                break

    if next_week is None:
        # Append a stub recovery week.
        last_week_num = max((w.get("week_number", 0) for w in plan.get("weeks", [])), default=0)
        stub = {
            "week_number": last_week_num + 1,
            "phase": "recovery",
            "target_volume_min": 0,
            "target_long_run_min": 0,
            "days": [],
            "recovery": True,
        }
        plan.setdefault("weeks", []).append(stub)
        plan.setdefault("macrocycle", {})["total_weeks"] = len(plan["weeks"])
        return

    # Mark as recovery and cut volume 30%.
    next_week["recovery"] = True
    vol = next_week.get("target_volume_min", 0)
    next_week["target_volume_min"] = int(vol * 0.70)

    # Drop one quality session (first T/I/R found → convert to E).
    downgraded = False
    for day in next_week.get("days", []):
        if not downgraded and day.get("type") in quality_types:
            day["type"] = "E"
            downgraded = True
