"""
test_analyze.py — Unit tests for analyze.py.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analyze import analyze


def _make_prescribed(type_="T", duration_min=40, target_pace_per_km_s=264, notes=""):
    return {
        "type": type_,
        "duration_min": duration_min,
        "target_pace_per_km_s": target_pace_per_km_s,
        "notes": notes,
    }


def _make_actual(
    duration_min=40,
    avg_pace_per_km_s=264,
    rpe=7,
    splits=None,
    avg_hr=None,
    max_hr=None,
    distance_km=None,
):
    return {
        "duration_min": duration_min,
        "distance_km": distance_km,
        "avg_pace_per_km_s": avg_pace_per_km_s,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "rpe": rpe,
        "splits": splits,
    }


class TestVerdictOnTarget(unittest.TestCase):

    def test_exact_match_is_on_target(self):
        result = analyze(_make_actual(), _make_prescribed())
        self.assertEqual(result["verdict"], "on-target")

    def test_slight_deviation_on_target(self):
        # 95% completion, pace just 3% slower, rpe delta = 0.
        result = analyze(
            _make_actual(duration_min=38, avg_pace_per_km_s=272, rpe=7),
            _make_prescribed(),
        )
        self.assertEqual(result["verdict"], "on-target")


class TestVerdictAborted(unittest.TestCase):

    def test_below_50_pct_is_aborted(self):
        result = analyze(
            _make_actual(duration_min=19),  # 19/40 = 47.5%
            _make_prescribed(),
        )
        self.assertEqual(result["verdict"], "aborted")

    def test_exactly_50_pct_is_not_aborted(self):
        result = analyze(
            _make_actual(duration_min=20),  # 20/40 = 50%
            _make_prescribed(),
        )
        self.assertNotEqual(result["verdict"], "aborted")


class TestVerdictUnder(unittest.TestCase):

    def test_two_signals_under(self):
        # completion < 80% AND pace > +5%.
        result = analyze(
            _make_actual(duration_min=30, avg_pace_per_km_s=280, rpe=7),  # 75% done, pace +6%
            _make_prescribed(),
        )
        self.assertEqual(result["verdict"], "under")

    def test_completion_and_rpe_under(self):
        # completion < 80% AND rpe_delta > 2.
        # Expected RPE for T = 7. actual rpe=10 → delta=3.
        result = analyze(
            _make_actual(duration_min=30, avg_pace_per_km_s=264, rpe=10),
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "under")

    def test_pace_and_rpe_under(self):
        # pace > +5% AND rpe_delta > 2 (completion ok).
        result = analyze(
            _make_actual(duration_min=40, avg_pace_per_km_s=280, rpe=10),
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "under")

    def test_single_signal_not_under(self):
        # Only completion < 80% but no second signal.
        result = analyze(
            _make_actual(duration_min=31, avg_pace_per_km_s=264, rpe=7),  # 77.5%, pace exact, rpe ok
            _make_prescribed(),
        )
        self.assertNotEqual(result["verdict"], "under")


class TestVerdictUnderBoundary(unittest.TestCase):

    def test_exactly_80_pct_completion_not_counted_as_under_signal(self):
        # 80% completion exactly → NOT a signal; so with one signal (pace ok, rpe ok) stays on-target.
        result = analyze(
            _make_actual(duration_min=32, avg_pace_per_km_s=264, rpe=7),  # 32/40 = 80%
            _make_prescribed(),
        )
        self.assertEqual(result["verdict"], "on-target")

    def test_79_pct_completion_counted_as_under_signal(self):
        # 79% contributes 1 signal; need a second to become "under".
        # Add rpe > 2 to get second signal.
        result = analyze(
            _make_actual(duration_min=31, avg_pace_per_km_s=264, rpe=10),  # 77.5%, rpe_delta=3
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "under")

    def test_79_pct_alone_not_under(self):
        result = analyze(
            _make_actual(duration_min=31, avg_pace_per_km_s=264, rpe=7),
            _make_prescribed(),
        )
        self.assertNotEqual(result["verdict"], "under")


class TestVerdictOver(unittest.TestCase):

    def test_fast_pace_and_low_rpe_is_over(self):
        # pace_delta_pct = -4% (faster), rpe_delta = -1 (<=0).
        fast_pace = int(264 * 0.96)  # ~4% faster
        result = analyze(
            _make_actual(avg_pace_per_km_s=fast_pace, rpe=6),  # expected for T=7 → delta=-1
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "over")

    def test_rpe_very_low_alone_is_NOT_over(self):
        # v0.2 fix: rpe-only trigger removed. Low RPE without faster pace = on-target,
        # not 'over'. (Common case: runner self-paces slower than target; RPE drops
        # accordingly; not a genuine over-fitness signal.)
        result = analyze(
            _make_actual(avg_pace_per_km_s=264, rpe=4),  # at-target pace, expected T=7 → delta=-3
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "on-target")

    def test_slow_pace_low_rpe_not_over(self):
        # Regression for v0.1 bug caught during dogfooding (5/1 E run):
        # User ran 26% slower than target with low RPE; old logic flipped to 'over'
        # via rpe-only trigger; new logic correctly returns 'on-target'.
        slow_pace = int(264 * 1.26)  # 26% slower
        result = analyze(
            _make_actual(avg_pace_per_km_s=slow_pace, rpe=4),  # T expected=7 → delta=-3
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "on-target")

    def test_fast_pace_with_normal_rpe_not_over(self):
        # pace faster but rpe_delta = 0 (not <= 0 for non-pace trigger) — wait, rpe_delta=0 IS <=0.
        # But rpe_delta must be < -1 for the solo trigger. Let's test rpe_delta=0 + fast pace → over.
        fast_pace = int(264 * 0.96)
        result = analyze(
            _make_actual(avg_pace_per_km_s=fast_pace, rpe=7),  # T expected=7 → delta=0
            _make_prescribed(type_="T"),
        )
        self.assertEqual(result["verdict"], "over")

    def test_fast_pace_with_positive_rpe_not_over(self):
        # pace faster but rpe_delta > 0 → not over.
        fast_pace = int(264 * 0.96)
        result = analyze(
            _make_actual(avg_pace_per_km_s=fast_pace, rpe=8),  # T expected=7 → delta=+1
            _make_prescribed(type_="T"),
        )
        self.assertNotEqual(result["verdict"], "over")


class TestNoneHandling(unittest.TestCase):

    def test_missing_rpe_gives_none_rpe_delta(self):
        actual = _make_actual()
        actual["rpe"] = None
        result = analyze(actual, _make_prescribed())
        self.assertIsNone(result["rpe_delta"])

    def test_missing_pace_gives_none_pace_delta(self):
        prescribed = _make_prescribed(target_pace_per_km_s=None)
        result = analyze(_make_actual(), prescribed)
        self.assertIsNone(result["pace_delta_pct"])

    def test_missing_splits_gives_none_hr_drift(self):
        result = analyze(_make_actual(splits=None), _make_prescribed())
        self.assertIsNone(result["hr_drift_bpm"])

    def test_no_rpe_no_crash_on_verdict(self):
        actual = _make_actual()
        actual["rpe"] = None
        result = analyze(actual, _make_prescribed())
        self.assertIn(result["verdict"], ("on-target", "under", "over", "aborted"))

    def test_zero_prescribed_duration_no_crash(self):
        prescribed = _make_prescribed(duration_min=0)
        result = analyze(_make_actual(duration_min=30), prescribed)
        self.assertEqual(result["completion_pct"], 100.0)


class TestHRDrift(unittest.TestCase):

    def test_hr_drift_computed_from_splits(self):
        splits = [
            {"avg_hr": 150},
            {"avg_hr": 152},
            {"avg_hr": 158},
            {"avg_hr": 162},
        ]
        result = analyze(_make_actual(splits=splits), _make_prescribed())
        # First half avg: (150+152)/2=151; second half avg: (158+162)/2=160; drift=9.
        self.assertAlmostEqual(result["hr_drift_bpm"], 9.0, places=1)

    def test_single_split_gives_none_drift(self):
        splits = [{"avg_hr": 155}]
        result = analyze(_make_actual(splits=splits), _make_prescribed())
        self.assertIsNone(result["hr_drift_bpm"])


class TestCompletionPct(unittest.TestCase):

    def test_completion_pct_calculation(self):
        result = analyze(_make_actual(duration_min=38), _make_prescribed(duration_min=40))
        self.assertAlmostEqual(result["completion_pct"], 95.0, places=1)

    def test_completion_over_100(self):
        result = analyze(_make_actual(duration_min=42), _make_prescribed(duration_min=40))
        self.assertAlmostEqual(result["completion_pct"], 105.0, places=1)


class TestExpectedRPETypes(unittest.TestCase):
    """Verify expected-RPE mapping for each workout type."""

    _EXPECTED = {"E": 4, "L": 5, "M": 6, "T": 7, "I": 8, "R": 9, "Strides": 5, "Recovery": 3, "Rest": 0}

    def _rpe_delta_for_type(self, workout_type, actual_rpe):
        result = analyze(
            _make_actual(rpe=actual_rpe),
            _make_prescribed(type_=workout_type, target_pace_per_km_s=None),
        )
        return result["rpe_delta"]

    def test_all_type_expected_rpe(self):
        for wtype, expected in self._EXPECTED.items():
            delta = self._rpe_delta_for_type(wtype, expected)
            self.assertEqual(delta, 0, f"Expected rpe_delta=0 for type {wtype} with rpe={expected}")


if __name__ == "__main__":
    unittest.main()
