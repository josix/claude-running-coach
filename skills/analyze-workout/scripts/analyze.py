"""
analyze.py — Workout adherence analysis per DESIGN.md §4.
"""
from __future__ import annotations

# Expected RPE by workout type.
_EXPECTED_RPE: dict[str, int] = {
    "E": 4,
    "L": 5,
    "M": 6,
    "T": 7,
    "I": 8,
    "R": 9,
    "Strides": 5,
    "Recovery": 3,
    "Rest": 0,
}


def _compute_hr_drift(splits: list[dict] | None) -> float | None:
    """
    Compute intra-session HR drift: avg HR of second half minus first half.
    Returns None if splits are absent or have no HR data.
    """
    if not splits:
        return None
    hr_values = [s.get("avg_hr") for s in splits if s.get("avg_hr") is not None]
    if len(hr_values) < 2:
        return None
    mid = len(hr_values) // 2
    first_half_avg = sum(hr_values[:mid]) / mid
    second_half_avg = sum(hr_values[mid:]) / (len(hr_values) - mid)
    return round(second_half_avg - first_half_avg, 2)


def analyze(actual: dict, prescribed: dict) -> dict:
    """
    Compute adherence delta between actual and prescribed workout.

    Args:
        actual: dict with fields duration_min, distance_km, avg_pace_per_km_s,
                avg_hr, max_hr, rpe, splits.
        prescribed: dict with fields type, duration_min, target_pace_per_km_s, notes.

    Returns:
        Dict with completion_pct, pace_delta_pct, rpe_delta, hr_drift_bpm, verdict.
    """
    # ── Completion ────────────────────────────────────────────────────────────
    actual_duration = actual.get("duration_min") or 0
    prescribed_duration = prescribed.get("duration_min") or 0
    if prescribed_duration > 0:
        completion_pct = (actual_duration / prescribed_duration) * 100.0
    else:
        completion_pct = 100.0

    # ── Pace delta ────────────────────────────────────────────────────────────
    target_pace = prescribed.get("target_pace_per_km_s")
    actual_pace = actual.get("avg_pace_per_km_s")
    if target_pace and target_pace > 0 and actual_pace is not None:
        pace_delta_pct = ((actual_pace - target_pace) / target_pace) * 100.0
    else:
        pace_delta_pct = None

    # ── RPE delta ─────────────────────────────────────────────────────────────
    workout_type = prescribed.get("type", "E")
    actual_rpe = actual.get("rpe")
    if actual_rpe is not None:
        expected_rpe = _EXPECTED_RPE.get(workout_type, 5)
        rpe_delta = int(actual_rpe) - expected_rpe
    else:
        rpe_delta = None

    # ── HR drift ─────────────────────────────────────────────────────────────
    hr_drift_bpm = _compute_hr_drift(actual.get("splits"))

    # ── Verdict ───────────────────────────────────────────────────────────────
    verdict = _compute_verdict(completion_pct, pace_delta_pct, rpe_delta)

    return {
        "completion_pct": round(completion_pct, 2),
        "pace_delta_pct": round(pace_delta_pct, 2) if pace_delta_pct is not None else None,
        "rpe_delta": rpe_delta,
        "hr_drift_bpm": hr_drift_bpm,
        "verdict": verdict,
    }


def _compute_verdict(
    completion_pct: float,
    pace_delta_pct: float | None,
    rpe_delta: int | None,
) -> str:
    """
    Verdict logic per DESIGN.md §4 (v0.2 — rpe-only 'over' trigger removed).

    'aborted'    if completion_pct < 50
    'under'      if any TWO of: completion_pct < 80, pace_delta_pct > +5, rpe_delta > +2
    'over'       if BOTH pace_delta_pct < -3 AND rpe_delta <= 0
                 (rpe-only trigger removed — it falsely flagged self-paced slow runs
                 as ahead-of-fitness when the runner ran slower than prescribed AND
                 naturally reported lower RPE; the real signal of over-fitness requires
                 actual faster-than-prescribed pace.)
    'on-target'  otherwise
    """
    if completion_pct < 50:
        return "aborted"

    under_signals = 0
    if completion_pct < 80:
        under_signals += 1
    if pace_delta_pct is not None and pace_delta_pct > 5:
        under_signals += 1
    if rpe_delta is not None and rpe_delta > 2:
        under_signals += 1

    if under_signals >= 2:
        return "under"

    pace_faster = pace_delta_pct is not None and pace_delta_pct < -3
    rpe_low = rpe_delta is not None and rpe_delta <= 0
    if pace_faster and rpe_low:
        return "over"

    return "on-target"
