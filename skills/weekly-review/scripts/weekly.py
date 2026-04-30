"""
weekly.py — Weekly training review aggregation and verdict logic.
"""
from __future__ import annotations


def weekly_review(workouts: list[dict], plan: dict, week_number: int) -> dict:
    """
    Aggregate workouts for a plan week and produce a review verdict.

    Args:
        workouts: list of completed workout dicts (from workouts.json).
        plan: macrocycle plan dict with weeks[].days[].
        week_number: 1-indexed week number to review.

    Returns:
        Dict with completed_volume_min, prescribed_volume_min, completion_ratio,
        quality_completed, quality_prescribed, fatigue_indicators, verdict, notes.
    """
    target_week = _find_week(plan, week_number)
    if target_week is None:
        raise ValueError(f"Week {week_number} not found in plan.")

    prescribed_days = target_week.get("days", [])
    week_dates = {d["date"] for d in prescribed_days if d.get("date")}

    # Aggregate actual workouts that fall in this week's date range.
    week_workouts = [w for w in workouts if w.get("date") in week_dates]

    # Prescribed volume and quality sessions.
    quality_types = {"T", "I", "R", "M"}
    prescribed_volume_min = sum(d.get("duration_min", 0) for d in prescribed_days)
    quality_prescribed = sum(1 for d in prescribed_days if d.get("type") in quality_types)

    # Actual volume and quality sessions.
    completed_volume_min = sum(w.get("actual", {}).get("duration_min", 0) for w in week_workouts)
    quality_completed = sum(
        1 for w in week_workouts
        if w.get("prescribed", {}).get("type") in quality_types
        and w.get("analysis", {}).get("verdict") not in ("aborted",)
    )

    completion_ratio = (
        completed_volume_min / prescribed_volume_min if prescribed_volume_min > 0 else 1.0
    )

    # Fatigue indicators.
    rpe_values = [
        w.get("actual", {}).get("rpe")
        for w in week_workouts
        if w.get("actual", {}).get("rpe") is not None
    ]
    avg_rpe = sum(rpe_values) / len(rpe_values) if rpe_values else 0.0

    rpe_creep = _compute_rpe_creep(workouts, week_number, plan)

    hr_drifts = [
        w.get("analysis", {}).get("hr_drift_bpm")
        for w in week_workouts
        if w.get("analysis", {}).get("hr_drift_bpm") is not None
    ]
    hr_drift_avg = sum(hr_drifts) / len(hr_drifts) if hr_drifts else 0.0

    verdict = _compute_verdict(completion_ratio, rpe_creep, quality_completed, quality_prescribed)
    notes = _build_notes(verdict, completion_ratio, quality_completed, quality_prescribed, avg_rpe)

    return {
        "week_number": week_number,
        "completed_volume_min": completed_volume_min,
        "prescribed_volume_min": prescribed_volume_min,
        "completion_ratio": round(completion_ratio, 4),
        "quality_completed": quality_completed,
        "quality_prescribed": quality_prescribed,
        "fatigue_indicators": {
            "avg_rpe": round(avg_rpe, 2),
            "rpe_creep": rpe_creep,
            "hr_drift_avg": round(hr_drift_avg, 2),
        },
        "verdict": verdict,
        "notes": notes,
    }


def _find_week(plan: dict, week_number: int) -> dict | None:
    for w in plan.get("weeks", []):
        if w.get("week_number") == week_number:
            return w
    return None


def _compute_rpe_creep(workouts: list[dict], week_number: int, plan: dict) -> float | None:
    """
    RPE this week minus RPE last week.  Returns None if this is week 1.
    """
    if week_number <= 1:
        return None

    prev_week = _find_week(plan, week_number - 1)
    if prev_week is None:
        return None

    prev_dates = {d["date"] for d in prev_week.get("days", []) if d.get("date")}
    current_week = _find_week(plan, week_number)
    if current_week is None:
        return None
    current_dates = {d["date"] for d in current_week.get("days", []) if d.get("date")}

    def avg_rpe_for_dates(dates):
        vals = [
            w.get("actual", {}).get("rpe")
            for w in workouts
            if w.get("date") in dates and w.get("actual", {}).get("rpe") is not None
        ]
        return sum(vals) / len(vals) if vals else None

    current_avg = avg_rpe_for_dates(current_dates)
    prev_avg = avg_rpe_for_dates(prev_dates)

    if current_avg is None or prev_avg is None:
        return None
    return round(current_avg - prev_avg, 2)


def _compute_verdict(
    completion_ratio: float,
    rpe_creep: float | None,
    quality_completed: int,
    quality_prescribed: int,
) -> str:
    """
    Verdict logic per spec:
      'recovery' if completion_ratio < 0.7 OR (rpe_creep >= 1 AND quality_completed < quality_prescribed)
      'advance'  if completion_ratio >= 0.95 AND quality_completed == quality_prescribed AND rpe_creep <= 0.3
      'hold'     otherwise
    """
    if completion_ratio < 0.7:
        return "recovery"
    if rpe_creep is not None and rpe_creep >= 1 and quality_completed < quality_prescribed:
        return "recovery"
    if (
        completion_ratio >= 0.95
        and quality_completed == quality_prescribed
        and (rpe_creep is None or rpe_creep <= 0.3)
    ):
        return "advance"
    return "hold"


def _build_notes(
    verdict: str,
    completion_ratio: float,
    quality_completed: int,
    quality_prescribed: int,
    avg_rpe: float,
) -> str:
    pct = int(completion_ratio * 100)
    q_str = f"{quality_completed}/{quality_prescribed} quality sessions"
    rpe_str = f"avg RPE {avg_rpe:.1f}"
    if verdict == "advance":
        return f"Strong week: {pct}% volume completion, {q_str} completed, {rpe_str}. Advance as planned."
    if verdict == "recovery":
        return f"Recovery needed: {pct}% volume completion, {q_str}, {rpe_str}. Insert recovery week."
    return f"Hold steady: {pct}% volume completion, {q_str}, {rpe_str}. Continue plan as-is."
