"""
test_macrocycle.py — Unit tests for macrocycle.py.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from macrocycle import build_macrocycle


_DAYS = ["Tue", "Thu", "Sat", "Sun"]


class TestBuildMacrocycle24Week(unittest.TestCase):
    """24-week marathon plan (the canonical case)."""

    @classmethod
    def setUpClass(cls):
        cls.result = build_macrocycle("2026-04-30", "2026-10-15", _DAYS)

    def test_total_weeks(self):
        # 2026-04-30 → 2026-10-15 = 168 days = 24 weeks exactly.
        self.assertEqual(self.result["total_weeks"], 24)

    def test_phases_sum_to_total(self):
        total = sum(p["end_week"] - p["start_week"] + 1 for p in self.result["phases"])
        self.assertEqual(total, self.result["total_weeks"])

    def test_taper_is_2_or_3_weeks(self):
        taper = next(p for p in self.result["phases"] if p["name"] == "taper")
        taper_weeks = taper["end_week"] - taper["start_week"] + 1
        self.assertIn(taper_weeks, (2, 3))

    def test_taper_ends_at_last_week(self):
        taper = next(p for p in self.result["phases"] if p["name"] == "taper")
        self.assertEqual(taper["end_week"], self.result["total_weeks"])

    def test_correct_number_of_weeks(self):
        self.assertEqual(len(self.result["weeks"]), 24)

    def test_phases_order(self):
        order = [p["name"] for p in self.result["phases"]]
        self.assertEqual(order, ["base", "build", "peak", "taper"])

    def test_start_date_preserved(self):
        self.assertEqual(self.result["start_date"], "2026-04-30")

    def test_end_date_preserved(self):
        self.assertEqual(self.result["end_date"], "2026-10-15")


class TestBuildMacrocycle12Week(unittest.TestCase):
    """12-week shorter plan."""

    @classmethod
    def setUpClass(cls):
        # 12 weeks from 2026-05-01 → 2026-07-24 (84 days).
        cls.result = build_macrocycle("2026-05-01", "2026-07-24", _DAYS)

    def test_total_weeks(self):
        self.assertEqual(self.result["total_weeks"], 12)

    def test_phases_sum_to_total(self):
        total = sum(p["end_week"] - p["start_week"] + 1 for p in self.result["phases"])
        self.assertEqual(total, 12)

    def test_taper_at_least_2_weeks(self):
        taper = next(p for p in self.result["phases"] if p["name"] == "taper")
        taper_weeks = taper["end_week"] - taper["start_week"] + 1
        self.assertGreaterEqual(taper_weeks, 2)

    def test_week_count_matches(self):
        self.assertEqual(len(self.result["weeks"]), 12)

    def test_base_comes_before_build(self):
        base = next(p for p in self.result["phases"] if p["name"] == "base")
        build = next(p for p in self.result["phases"] if p["name"] == "build")
        self.assertLess(base["start_week"], build["start_week"])

    def test_build_comes_before_peak(self):
        build = next(p for p in self.result["phases"] if p["name"] == "build")
        peak = next(p for p in self.result["phases"] if p["name"] == "peak")
        self.assertLess(build["start_week"], peak["start_week"])


class TestBuildMacrocycleErrors(unittest.TestCase):

    def test_7_week_raises(self):
        with self.assertRaises(ValueError):
            # 7 weeks = 49 days
            from datetime import date, timedelta
            start = date(2026, 5, 1)
            race = start + timedelta(days=49)
            build_macrocycle(start.isoformat(), race.isoformat(), _DAYS)

    def test_race_before_start_raises(self):
        with self.assertRaises(ValueError):
            build_macrocycle("2026-10-15", "2026-04-30", _DAYS)

    def test_race_same_day_raises(self):
        with self.assertRaises(ValueError):
            build_macrocycle("2026-05-01", "2026-05-01", _DAYS)


class TestPhaseOrdering(unittest.TestCase):
    """Phase boundaries must be monotonically increasing (base → build → peak → taper)."""

    def _get_result(self, weeks: int):
        from datetime import date, timedelta
        start = date(2026, 1, 1)
        race = start + timedelta(weeks=weeks)
        return build_macrocycle(start.isoformat(), race.isoformat(), _DAYS)

    def test_monotonic_start_weeks_24(self):
        result = self._get_result(24)
        starts = [p["start_week"] for p in result["phases"]]
        self.assertEqual(starts, sorted(starts))

    def test_monotonic_start_weeks_16(self):
        result = self._get_result(16)
        starts = [p["start_week"] for p in result["phases"]]
        self.assertEqual(starts, sorted(starts))

    def test_no_gap_between_phases(self):
        """Phases must be contiguous — no skipped week numbers."""
        result = self._get_result(20)
        phases = result["phases"]
        for i in range(len(phases) - 1):
            self.assertEqual(phases[i]["end_week"] + 1, phases[i + 1]["start_week"],
                             f"Gap between {phases[i]['name']} and {phases[i+1]['name']}")

    def test_weeks_have_correct_phase_labels(self):
        result = self._get_result(24)
        phases = result["phases"]
        for week in result["weeks"]:
            wn = week["week_number"]
            expected_phase = next(
                p["name"] for p in phases if p["start_week"] <= wn <= p["end_week"]
            )
            self.assertEqual(week["phase"], expected_phase)

    def test_week_skeleton_structure(self):
        result = self._get_result(24)
        for week in result["weeks"]:
            self.assertIn("week_number", week)
            self.assertIn("phase", week)
            self.assertEqual(week["target_volume_min"], 0)
            self.assertEqual(week["target_long_run_min"], 0)
            self.assertEqual(week["days"], [])


if __name__ == "__main__":
    unittest.main()
