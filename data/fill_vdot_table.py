"""Daniels' VDOT regression filler.

Loads data/vdot-table.json (partial anchors from SD Track Mag PDF),
fills E/M paces and 10K/HM/Marathon predictions using Daniels'
published formulas (VO2 and f(t)), and interpolates odd-VDOT rows
that are entirely null. Writes back to data/vdot-table.json.

Citation: Jack Daniels, Daniels' Running Formula (Human Kinetics).
Formula reproductions:
  - https://run-things.com/calculators/jack-daniels-vdot-pace
  - https://github.com/justinphilpott/jdcalc
"""

import json
import math
from pathlib import Path


# Daniels' regression constants (well-published)
def vo2_at_velocity(v_m_per_min: float) -> float:
    return -4.60 + 0.182258 * v_m_per_min + 0.000104 * v_m_per_min ** 2


def fraction_of_vo2max(t_min: float) -> float:
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t_min) + 0.2989558 * math.exp(-0.1932605 * t_min)


def vdot_for_race(distance_m: float, time_min: float) -> float:
    v = distance_m / time_min
    return vo2_at_velocity(v) / fraction_of_vo2max(time_min)


def predict_time_min(vdot: float, distance_m: float) -> float:
    """Bisection: find time t such that vdot_for_race(distance, t) == vdot."""
    lo, hi = 1.0, 600.0  # 1 min to 10 hours
    for _ in range(100):
        mid = (lo + hi) / 2
        v = distance_m / mid
        candidate_vdot = vo2_at_velocity(v) / fraction_of_vo2max(mid)
        if candidate_vdot > vdot:
            lo = mid  # need slower (more time)
        else:
            hi = mid
        if hi - lo < 1e-4:
            break
    return (lo + hi) / 2


def velocity_at_pct_vdot(vdot: float, pct: float) -> float:
    """Solve VO2(v) = pct * vdot for v (quadratic positive root)."""
    target_vo2 = pct * vdot
    a, b, c = 0.000104, 0.182258, -4.60 - target_vo2
    discriminant = b * b - 4 * a * c
    return (-b + math.sqrt(discriminant)) / (2 * a)


def pace_per_km_s_at_pct(vdot: float, pct: float) -> int:
    v = velocity_at_pct_vdot(vdot, pct)
    return round(60000.0 / v)


def predicted_time_s(vdot: float, distance_m: int) -> int:
    return round(predict_time_min(vdot, distance_m) * 60)


# Training-zone fractions (calibrated)
E_PCT = 0.70
M_PCT = 0.84
# T, I, R from anchor table; only used for cross-validation here


def main():
    path = Path(__file__).parent / "vdot-table.json"
    data = json.loads(path.read_text())

    rows = data["rows"]
    by_vdot = {row["vdot"]: row for row in rows}

    # Pass 1: derive E, M, predicted 10K/HM/Marathon for ALL rows
    for row in rows:
        vdot = row["vdot"]
        if row["easy_per_km_s"] is None:
            row["easy_per_km_s"] = pace_per_km_s_at_pct(vdot, E_PCT)
        if row["marathon_per_km_s"] is None:
            row["marathon_per_km_s"] = pace_per_km_s_at_pct(vdot, M_PCT)
        if row["predicted_10k_s"] is None:
            row["predicted_10k_s"] = predicted_time_s(vdot, 10000)
        if row["predicted_half_s"] is None:
            row["predicted_half_s"] = predicted_time_s(vdot, 21097)
        if row["predicted_marathon_s"] is None:
            row["predicted_marathon_s"] = predicted_time_s(vdot, 42195)

    # Pass 2: fill predicted_5k_s for any null rows (odd VDOTs) using formula
    for row in rows:
        if row["predicted_5k_s"] is None:
            row["predicted_5k_s"] = predicted_time_s(row["vdot"], 5000)

    # Pass 3: interpolate T/I/R for odd-VDOT rows from adjacent integer neighbors
    for row in rows:
        vdot = row["vdot"]
        for col in ["threshold_per_km_s", "interval_per_km_s", "repetition_per_km_s"]:
            if row[col] is None:
                # Find nearest non-null neighbors
                lo_neighbor = next((by_vdot[v][col] for v in range(vdot - 1, 29, -1)
                                    if by_vdot.get(v, {}).get(col) is not None), None)
                hi_neighbor = next((by_vdot[v][col] for v in range(vdot + 1, 86)
                                    if by_vdot.get(v, {}).get(col) is not None), None)
                if lo_neighbor is not None and hi_neighbor is not None:
                    row[col] = round((lo_neighbor + hi_neighbor) / 2)
                elif lo_neighbor is not None:
                    row[col] = lo_neighbor
                elif hi_neighbor is not None:
                    row[col] = hi_neighbor

    # Cross-validation: derived 5K from formula should match anchor 5K within ±10s
    # (Print warnings, don't fail — anchor values are the published reference)
    mismatches = []
    for row in rows:
        if row["vdot"] in (30, 32, 34, 36, 38, 40, 42, 44) or 45 <= row["vdot"] <= 85:
            anchor_5k = row["predicted_5k_s"]
            # Re-compute from formula for comparison only
            formula_5k = predicted_time_s(row["vdot"], 5000)
            if abs(anchor_5k - formula_5k) > 10:
                mismatches.append((row["vdot"], anchor_5k, formula_5k))
    if mismatches:
        print(f"WARN: {len(mismatches)} rows have anchor vs formula 5K divergence > 10s:")
        for v, a, f in mismatches[:5]:
            print(f"  VDOT {v}: anchor={a}s formula={f}s diff={a-f}s")

    # Add derivation metadata
    data["derivation_notes"] = (
        "E and M paces, 10K/HM/Marathon predictions derived using Daniels' "
        "VO2 and f(t) regressions: VO2(v) = -4.60 + 0.182258v + 0.000104v^2; "
        "f(t) = 0.8 + 0.1894393·e^(-0.012778t) + 0.2989558·e^(-0.1932605t). "
        "E pace = velocity at 70%% VDOT; M pace = velocity at 84%% VDOT. "
        "Odd-VDOT T/I/R values interpolated from adjacent integer neighbors. "
        "Anchor T/I/R/5K values from SD Track Mag PDF preserved verbatim."
    )

    path.write_text(json.dumps(data, indent=2))
    null_count = sum(1 for r in rows for k, v in r.items() if v is None)
    print(f"Filled. Remaining null cells: {null_count}")


if __name__ == "__main__":
    main()
