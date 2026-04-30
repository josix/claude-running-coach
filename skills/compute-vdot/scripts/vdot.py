"""
vdot.py — VDOT lookup + interpolation helpers.

Loads data/vdot-table.json relative to plugin root (3 levels up from this script).
"""
from __future__ import annotations

import json
from pathlib import Path

_SUPPORTED_DISTANCES: dict[int, str] = {
    5000: "predicted_5k_s",
    10000: "predicted_10k_s",
    21097: "predicted_half_s",
    42195: "predicted_marathon_s",
}

_PACE_KEYS = (
    "easy_per_km_s",
    "marathon_per_km_s",
    "threshold_per_km_s",
    "interval_per_km_s",
    "repetition_per_km_s",
)

_table: list[dict] | None = None


def _load_table() -> list[dict]:
    global _table
    if _table is not None:
        return _table
    # Script lives at skills/compute-vdot/scripts/vdot.py → plugin root is 3 parents up.
    plugin_root = Path(__file__).resolve().parents[3]
    table_path = plugin_root / "data" / "vdot-table.json"
    if not table_path.exists():
        raise FileNotFoundError(
            "VDOT table not yet populated; run /run-init or contact maintainer."
        )
    with table_path.open() as f:
        data = json.load(f)
    rows: list[dict] = data["rows"]
    # Sort ascending by vdot to ensure binary-search invariant.
    rows.sort(key=lambda r: r["vdot"])
    _table = rows
    return _table


def _interpolate(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """Linear interpolation: find y at x given (x0, y0) and (x1, y1)."""
    if x1 == x0:
        return float(y0)
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _find_bracket(rows: list[dict], key: str, target: float, ascending: bool) -> tuple[int, int]:
    """
    Find adjacent row indices such that rows[lo][key] and rows[hi][key] bracket target.
    ascending=True: rows[lo][key] <= target <= rows[hi][key].
    ascending=False (paces decrease as vdot increases): reverse logic.
    """
    if ascending:
        for i in range(len(rows) - 1):
            if rows[i][key] <= target <= rows[i + 1][key]:
                return i, i + 1
        # Out of range — clamp.
        if target < rows[0][key]:
            return 0, 1
        return len(rows) - 2, len(rows) - 1
    else:
        # descending: rows[0][key] is largest (slowest time), rows[-1][key] is smallest (fastest).
        for i in range(len(rows) - 1):
            if rows[i][key] >= target >= rows[i + 1][key]:
                return i, i + 1
        if target > rows[0][key]:
            return 0, 1
        return len(rows) - 2, len(rows) - 1


def vdot_from_race(distance_m: int, time_s: int) -> float:
    """
    Given a race result, return the VDOT score (linear interpolation between table rows).

    Args:
        distance_m: race distance in metres; supported: 5000, 10000, 21097, 42195.
        time_s: finish time in seconds.

    Raises:
        ValueError: if distance_m is not a supported distance.
        FileNotFoundError: if VDOT table data file is missing.
    """
    if distance_m not in _SUPPORTED_DISTANCES:
        raise ValueError(
            f"Unsupported distance {distance_m} m. "
            f"Supported: {sorted(_SUPPORTED_DISTANCES.keys())}"
        )
    col = _SUPPORTED_DISTANCES[distance_m]
    rows = _load_table()
    # Predicted times decrease as VDOT increases → descending values in col.
    lo, hi = _find_bracket(rows, col, time_s, ascending=False)
    vdot = _interpolate(
        time_s,
        rows[lo][col], rows[hi][col],
        rows[lo]["vdot"], rows[hi]["vdot"],
    )
    return round(vdot, 2)


def paces_for_vdot(vdot: float) -> dict:
    """
    Return training paces for a given VDOT, linearly interpolated between table rows.

    Args:
        vdot: VDOT score (float).

    Returns:
        Dict with keys: easy_per_km_s, marathon_per_km_s, threshold_per_km_s,
        interval_per_km_s, repetition_per_km_s (all int seconds/km).

    Raises:
        FileNotFoundError: if VDOT table data file is missing.
    """
    rows = _load_table()
    lo, hi = _find_bracket(rows, "vdot", vdot, ascending=True)
    result = {}
    for key in _PACE_KEYS:
        pace = _interpolate(vdot, rows[lo]["vdot"], rows[hi]["vdot"], rows[lo][key], rows[hi][key])
        result[key] = int(round(pace))
    return result


def predict_race_time(vdot: float, distance_m: int) -> int:
    """
    Return predicted finish time in seconds for the given distance, interpolated from table.

    Args:
        vdot: VDOT score (float).
        distance_m: race distance in metres; supported: 5000, 10000, 21097, 42195.

    Raises:
        ValueError: if distance_m is not a supported distance.
        FileNotFoundError: if VDOT table data file is missing.
    """
    if distance_m not in _SUPPORTED_DISTANCES:
        raise ValueError(
            f"Unsupported distance {distance_m} m. "
            f"Supported: {sorted(_SUPPORTED_DISTANCES.keys())}"
        )
    col = _SUPPORTED_DISTANCES[distance_m]
    rows = _load_table()
    lo, hi = _find_bracket(rows, "vdot", vdot, ascending=True)
    time = _interpolate(vdot, rows[lo]["vdot"], rows[hi]["vdot"], rows[lo][col], rows[hi][col])
    return int(round(time))
