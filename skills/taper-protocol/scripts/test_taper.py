"""
test_taper.py — Unit tests for taper.py.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from taper import apply_taper


def _make_weeks(n: int, peak_vol: int = 300, race_date_str: str = "2026-10-15") -> list[dict]:
    """Build n week stubs with realistic structure."""
    from datetime import date, timedelta
    race_date = date.fromisoformat(race_date_str)
    weeks = []
    for i in range(n):
        week_num = i + 1
        # Volume ramps up to week n-3 then should be cut by taper.
        if i < n - 3:
            vol = peak_vol
        else:
            vol = peak_vol  # taper function will override
        week_start = race_date - timedelta(weeks=(n - i))
        days = [
            {
                "date": (week_start + timedelta(days=1)).isoformat(),
                "dow": "Tue", "type": "T", "duration_min": 40,
            },
            {
                "date": (week_start + timedelta(days=3)).isoformat(),
                "dow": "Thu", "type": "I", "duration_min": 50,
            },
            {
                "date": (week_start + timedelta(days=5)).isoformat(),
                "dow": "Sat", "type": "L", "duration_min": 90,
            },
            {
                "date": (week_start + timedelta(days=6)).isoformat(),
                "dow": "Sun", "type": "E", "duration_min": 40,
            },
        ]
        weeks.append({
            "week_number": week_num,
            "phase": "taper" if i >= n - 3 else "peak",
            "target_volume_min": vol,
            "target_long_run_min": 90,
            "days": days,
        })
    return weeks


class TestInputImmutability(unittest.TestCase):

    def test_original_weeks_not_mutated(self):
        weeks = _make_weeks(24, peak_vol=300)
        orig_vol = weeks[-1]["target_volume_min"]
        apply_taper(weeks, "2026-10-15")
        self.assertEqual(weeks[-1]["target_volume_min"], orig_vol)


class TestVolumeRatios(unittest.TestCase):

    def test_race_week_volume_40_pct_of_peak(self):
        peak = 300
        weeks = _make_weeks(24, peak_vol=peak)
        result = apply_taper(weeks, "2026-10-15")
        race_week_vol = result[-1]["target_volume_min"]
        expected = int(peak * 0.40)
        self.assertEqual(race_week_vol, expected)

    def test_race_week_minus_1_volume_60_pct_of_peak(self):
        peak = 300
        weeks = _make_weeks(24, peak_vol=peak)
        result = apply_taper(weeks, "2026-10-15")
        rw1_vol = result[-2]["target_volume_min"]
        expected = int(peak * 0.60)
        self.assertEqual(rw1_vol, expected)

    def test_race_week_minus_2_volume_80_pct_of_peak_for_18plus_weeks(self):
        peak = 300
        weeks = _make_weeks(18, peak_vol=peak)
        result = apply_taper(weeks, "2026-10-15")
        rw2_vol = result[-3]["target_volume_min"]
        expected = int(peak * 0.80)
        self.assertEqual(rw2_vol, expected)

    def test_race_week_minus_2_not_applied_for_short_plan(self):
        """For plans < 18 weeks, rw-2 should NOT get volume cut."""
        peak = 300
        # Use 12-week plan.
        weeks = _make_weeks(12, peak_vol=peak)
        # Pre-taper the rw-2 to peak so we can check it stays peak.
        original_rw2_vol = weeks[-3]["target_volume_min"]
        result = apply_taper(weeks, "2026-10-15")
        rw2_vol = result[-3]["target_volume_min"]
        # Should remain unchanged (taper not applied to rw-2 for 12-week plan).
        self.assertEqual(rw2_vol, original_rw2_vol)


class TestRaceDayMarking(unittest.TestCase):

    def test_race_day_marked_in_race_week(self):
        """One day in the final week must have type='Race'."""
        weeks = _make_weeks(24, peak_vol=300)
        result = apply_taper(weeks, "2026-10-15")
        race_week_days = result[-1]["days"]
        race_days = [d for d in race_week_days if d.get("type") == "Race"]
        self.assertGreaterEqual(len(race_days), 1)

    def test_no_quality_sessions_remain_in_race_week(self):
        """No T/I/R sessions should remain in race week (only E/Recovery/Race)."""
        weeks = _make_weeks(24, peak_vol=300)
        result = apply_taper(weeks, "2026-10-15")
        quality_types = {"T", "I", "R"}
        for d in result[-1]["days"]:
            self.assertNotIn(d.get("type"), quality_types,
                             f"Found quality session {d.get('type')} in race week day {d.get('date')}")


class TestRaceWeekMinus1Intensity(unittest.TestCase):

    def test_at_least_one_quality_preserved_in_rw1(self):
        """Race-week-1 should preserve at least 1 T or I session."""
        weeks = _make_weeks(24, peak_vol=300)
        result = apply_taper(weeks, "2026-10-15")
        rw1_days = result[-2]["days"]
        quality_types = {"T", "I", "R"}
        quality_count = sum(1 for d in rw1_days if d.get("type") in quality_types)
        self.assertGreaterEqual(quality_count, 1)

    def test_rw1_long_run_reduced(self):
        """Long run in race-week-1 should be shorter than original."""
        weeks = _make_weeks(24, peak_vol=300)
        original_long = next(
            d.get("duration_min", 0)
            for d in weeks[-2]["days"]
            if d.get("type") == "L"
        )
        result = apply_taper(weeks, "2026-10-15")
        new_long = next(
            (d.get("duration_min", 0) for d in result[-2]["days"] if d.get("type") == "L"),
            None,
        )
        if new_long is not None:
            self.assertLess(new_long, original_long)


class TestTaperFlag(unittest.TestCase):

    def test_taper_flag_set_on_race_week(self):
        weeks = _make_weeks(24, peak_vol=300)
        result = apply_taper(weeks, "2026-10-15")
        self.assertTrue(result[-1].get("taper"))

    def test_taper_flag_set_on_rw_minus_1(self):
        weeks = _make_weeks(24, peak_vol=300)
        result = apply_taper(weeks, "2026-10-15")
        self.assertTrue(result[-2].get("taper"))

    def test_taper_flag_set_on_rw_minus_2_for_18plus(self):
        weeks = _make_weeks(18, peak_vol=300)
        result = apply_taper(weeks, "2026-10-15")
        self.assertTrue(result[-3].get("taper"))


class TestEdgeCases(unittest.TestCase):

    def test_empty_weeks_returns_empty(self):
        result = apply_taper([], "2026-10-15")
        self.assertEqual(result, [])

    def test_single_week_does_not_crash(self):
        weeks = _make_weeks(1, peak_vol=100)
        result = apply_taper(weeks, "2026-10-15")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
