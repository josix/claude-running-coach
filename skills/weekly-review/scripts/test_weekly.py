"""
test_weekly.py — Unit tests for weekly.py.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from weekly import weekly_review


def _make_plan(week1_days=None, week2_days=None):
    if week1_days is None:
        week1_days = [
            {"date": "2026-05-05", "dow": "Tue", "type": "T", "duration_min": 40},
            {"date": "2026-05-07", "dow": "Thu", "type": "I", "duration_min": 50},
            {"date": "2026-05-09", "dow": "Sat", "type": "L", "duration_min": 75},
            {"date": "2026-05-10", "dow": "Sun", "type": "E", "duration_min": 35},
        ]
    if week2_days is None:
        week2_days = [
            {"date": "2026-05-12", "dow": "Tue", "type": "T", "duration_min": 45},
            {"date": "2026-05-14", "dow": "Thu", "type": "I", "duration_min": 55},
            {"date": "2026-05-16", "dow": "Sat", "type": "L", "duration_min": 80},
            {"date": "2026-05-17", "dow": "Sun", "type": "E", "duration_min": 40},
        ]
    return {
        "weeks": [
            {
                "week_number": 1,
                "phase": "build",
                "target_volume_min": 200,
                "target_long_run_min": 75,
                "days": week1_days,
            },
            {
                "week_number": 2,
                "phase": "build",
                "target_volume_min": 220,
                "target_long_run_min": 80,
                "days": week2_days,
            },
        ]
    }


def _make_workout(date_str, workout_type, duration_min, rpe, hr_drift=None, verdict="on-target"):
    return {
        "date": date_str,
        "prescribed": {"type": workout_type, "duration_min": duration_min},
        "actual": {"duration_min": duration_min, "rpe": rpe},
        "analysis": {"hr_drift_bpm": hr_drift, "verdict": verdict},
    }


class TestVerdictAdvance(unittest.TestCase):
    """completion >= 95%, all quality done, rpe_creep <= 0.3."""

    def test_advance_verdict(self):
        plan = _make_plan()
        # Perfect week 1.
        workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=7),
            _make_workout("2026-05-07", "I", 50, rpe=8),
            _make_workout("2026-05-09", "L", 75, rpe=5),
            _make_workout("2026-05-10", "E", 35, rpe=4),
        ]
        result = weekly_review(workouts, plan, 1)
        self.assertEqual(result["verdict"], "advance")

    def test_advance_all_fields_present(self):
        plan = _make_plan()
        workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=7),
            _make_workout("2026-05-07", "I", 50, rpe=8),
            _make_workout("2026-05-09", "L", 75, rpe=5),
            _make_workout("2026-05-10", "E", 35, rpe=4),
        ]
        result = weekly_review(workouts, plan, 1)
        for key in ("week_number", "completed_volume_min", "prescribed_volume_min",
                    "completion_ratio", "quality_completed", "quality_prescribed",
                    "fatigue_indicators", "verdict", "notes"):
            self.assertIn(key, result)

    def test_advance_completion_ratio_correct(self):
        plan = _make_plan()
        workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=7),
            _make_workout("2026-05-07", "I", 50, rpe=8),
            _make_workout("2026-05-09", "L", 75, rpe=5),
            _make_workout("2026-05-10", "E", 35, rpe=4),
        ]
        result = weekly_review(workouts, plan, 1)
        self.assertAlmostEqual(result["completion_ratio"], 1.0, places=2)


class TestVerdictHold(unittest.TestCase):

    def test_hold_partial_completion(self):
        plan = _make_plan()
        # ~85% completion, both quality done, low rpe creep.
        workouts = [
            _make_workout("2026-05-05", "T", 38, rpe=7),
            _make_workout("2026-05-07", "I", 42, rpe=8),
            _make_workout("2026-05-09", "L", 60, rpe=5),
            _make_workout("2026-05-10", "E", 30, rpe=4),
        ]
        result = weekly_review(workouts, plan, 1)
        # 170/200 = 85% → not advance (< 95%) but not recovery (>= 70%).
        self.assertEqual(result["verdict"], "hold")

    def test_hold_missing_quality_but_high_completion(self):
        plan = _make_plan()
        # High completion but missed quality — check rpe_creep path.
        workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=7, verdict="aborted"),
            _make_workout("2026-05-07", "I", 50, rpe=8),
            _make_workout("2026-05-09", "L", 75, rpe=5),
            _make_workout("2026-05-10", "E", 35, rpe=4),
        ]
        result = weekly_review(workouts, plan, 1)
        # quality_completed < quality_prescribed; rpe_creep None (week 1 → no prev week).
        # completion >= 95%, but quality_completed != quality_prescribed → not advance.
        self.assertIn(result["verdict"], ("hold", "recovery"))


class TestVerdictRecovery(unittest.TestCase):

    def test_recovery_low_completion(self):
        plan = _make_plan()
        # 60% completion.
        workouts = [
            _make_workout("2026-05-05", "T", 20, rpe=7),
            _make_workout("2026-05-07", "I", 25, rpe=8),
        ]
        result = weekly_review(workouts, plan, 1)
        self.assertEqual(result["verdict"], "recovery")

    def test_recovery_high_rpe_creep_with_missed_quality(self):
        plan = _make_plan()
        # Week 1 workouts (lower RPE).
        week1_workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=6),
            _make_workout("2026-05-07", "I", 50, rpe=6),
            _make_workout("2026-05-09", "L", 75, rpe=5),
            _make_workout("2026-05-10", "E", 35, rpe=4),
        ]
        # Week 2 workouts: high RPE, missed one quality.
        week2_workouts = [
            _make_workout("2026-05-12", "T", 45, rpe=9),
            # I session skipped
            _make_workout("2026-05-16", "L", 80, rpe=8),
            _make_workout("2026-05-17", "E", 40, rpe=7),
        ]
        all_workouts = week1_workouts + week2_workouts
        result = weekly_review(all_workouts, plan, 2)
        # rpe_creep = (9+8+7)/3 - (6+6+5+4)/4 = 8.0 - 5.25 = 2.75 >= 1
        # quality_completed for week 2: only T done (I skipped).
        self.assertEqual(result["verdict"], "recovery")

    def test_recovery_at_exactly_70_pct_boundary(self):
        plan = _make_plan()
        # Exactly 70% completion (140/200 min).
        workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=7),
            _make_workout("2026-05-07", "I", 50, rpe=8),
            _make_workout("2026-05-09", "L", 50, rpe=5),
        ]
        # 40+50+50 = 140 / 200 = 70% → NOT < 70 → not recovery from completion alone.
        result = weekly_review(workouts, plan, 1)
        self.assertNotEqual(result["verdict"], "recovery")

    def test_recovery_below_70_pct(self):
        plan = _make_plan()
        # 139/200 = 69.5% < 70% → recovery.
        workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=7),
            _make_workout("2026-05-07", "I", 50, rpe=8),
            _make_workout("2026-05-09", "L", 49, rpe=5),
        ]
        result = weekly_review(workouts, plan, 1)
        self.assertEqual(result["verdict"], "recovery")


class TestRpeCreep(unittest.TestCase):

    def test_rpe_creep_none_for_week1(self):
        plan = _make_plan()
        workouts = [_make_workout("2026-05-05", "T", 40, rpe=7)]
        result = weekly_review(workouts, plan, 1)
        self.assertIsNone(result["fatigue_indicators"]["rpe_creep"])

    def test_rpe_creep_computed_for_week2(self):
        plan = _make_plan()
        week1_workouts = [
            _make_workout("2026-05-05", "T", 40, rpe=6),
            _make_workout("2026-05-09", "L", 75, rpe=5),
        ]
        week2_workouts = [
            _make_workout("2026-05-12", "T", 45, rpe=8),
            _make_workout("2026-05-16", "L", 80, rpe=7),
        ]
        result = weekly_review(week1_workouts + week2_workouts, plan, 2)
        # week2 avg = (8+7)/2 = 7.5, week1 avg = (6+5)/2 = 5.5 → creep = 2.0
        self.assertAlmostEqual(result["fatigue_indicators"]["rpe_creep"], 2.0, places=1)


class TestOutputStructure(unittest.TestCase):

    def test_week_number_matches(self):
        plan = _make_plan()
        result = weekly_review([], plan, 1)
        self.assertEqual(result["week_number"], 1)

    def test_zero_workouts_does_not_crash(self):
        plan = _make_plan()
        result = weekly_review([], plan, 1)
        self.assertEqual(result["completed_volume_min"], 0)
        self.assertEqual(result["quality_completed"], 0)

    def test_invalid_week_raises(self):
        plan = _make_plan()
        with self.assertRaises(ValueError):
            weekly_review([], plan, 99)

    def test_hr_drift_avg_present(self):
        plan = _make_plan()
        workouts = [
            {
                "date": "2026-05-05",
                "prescribed": {"type": "T", "duration_min": 40},
                "actual": {"duration_min": 40, "rpe": 7},
                "analysis": {"hr_drift_bpm": 4.0, "verdict": "on-target"},
            }
        ]
        result = weekly_review(workouts, plan, 1)
        self.assertAlmostEqual(result["fatigue_indicators"]["hr_drift_avg"], 4.0, places=1)


if __name__ == "__main__":
    unittest.main()
