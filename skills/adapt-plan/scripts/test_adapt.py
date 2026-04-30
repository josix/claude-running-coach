"""
test_adapt.py — Unit tests for adapt.py.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adapt import adapt, insert_recovery_week


def _make_plan(weeks=None):
    """Return a minimal plan fixture."""
    if weeks is None:
        weeks = [
            {
                "week_number": 1,
                "phase": "build",
                "target_volume_min": 200,
                "target_long_run_min": 80,
                "days": [
                    {"date": "2026-05-04", "dow": "Mon", "type": "E", "duration_min": 40},
                    {"date": "2026-05-05", "dow": "Tue", "type": "T", "duration_min": 40},
                    {"date": "2026-05-07", "dow": "Thu", "type": "I", "duration_min": 50},
                    {"date": "2026-05-09", "dow": "Sat", "type": "L", "duration_min": 70},
                ],
            },
            {
                "week_number": 2,
                "phase": "build",
                "target_volume_min": 220,
                "target_long_run_min": 85,
                "days": [
                    {"date": "2026-05-11", "dow": "Mon", "type": "E", "duration_min": 40},
                    {"date": "2026-05-12", "dow": "Tue", "type": "T", "duration_min": 45},
                    {"date": "2026-05-14", "dow": "Thu", "type": "I", "duration_min": 55},
                    {"date": "2026-05-16", "dow": "Sat", "type": "L", "duration_min": 85},
                ],
            },
        ]
    return {"weeks": weeks}


def _make_state(misses=0, ahead=0, red_flags=None):
    return {
        "consecutive_misses": misses,
        "consecutive_ahead": ahead,
        "carry_forward": {"recurring_red_flags": red_flags or []},
    }


def _delta(verdict, hr_drift=None, rpe_delta=None):
    return {"verdict": verdict, "hr_drift_bpm": hr_drift, "rpe_delta": rpe_delta}


TODAY = "2026-05-06"  # Mid-week 1 (week 1 runs Mon 2026-05-04 – Sat 2026-05-09).


class TestInputImmutability(unittest.TestCase):

    def test_original_plan_not_mutated(self):
        plan = _make_plan()
        state = _make_state()
        original_vol = plan["weeks"][1]["target_volume_min"]
        adapt(plan, state, _delta("under"), TODAY)
        adapt(plan, state, _delta("under"), TODAY)
        adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(plan["weeks"][1]["target_volume_min"], original_vol)

    def test_original_state_not_mutated(self):
        plan = _make_plan()
        state = _make_state(misses=0)
        adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(state["consecutive_misses"], 0)


class TestMonitorAction(unittest.TestCase):

    def test_first_miss_is_monitor(self):
        plan = _make_plan()
        state = _make_state(misses=0)
        _, new_state, action = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(action, "monitor")
        self.assertEqual(new_state["consecutive_misses"], 1)

    def test_monitor_does_not_change_plan(self):
        plan = _make_plan()
        state = _make_state(misses=0)
        new_plan, _, _ = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(new_plan["weeks"][0]["days"][1]["type"], "T")  # unchanged


class TestReduceNextQuality(unittest.TestCase):

    def test_second_miss_is_reduce_next_quality(self):
        plan = _make_plan()
        state = _make_state(misses=1)
        _, _, action = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(action, "reduce_next_quality")

    def test_second_miss_downgrades_quality_session(self):
        plan = _make_plan()
        state = _make_state(misses=1)
        new_plan, _, _ = adapt(plan, state, _delta("under"), TODAY)
        # TODAY=2026-05-06; first quality day after today is 2026-05-07 (I) → should downgrade to T.
        day_05_07 = next(
            d for w in new_plan["weeks"] for d in w["days"] if d["date"] == "2026-05-07"
        )
        self.assertEqual(day_05_07["type"], "T")

    def test_second_miss_counter_increments(self):
        plan = _make_plan()
        state = _make_state(misses=1)
        _, new_state, _ = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(new_state["consecutive_misses"], 2)

    def test_second_miss_resets_ahead(self):
        plan = _make_plan()
        state = _make_state(misses=1, ahead=2)
        _, new_state, _ = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(new_state["consecutive_ahead"], 0)


class TestRecoveryWeek(unittest.TestCase):

    def test_third_miss_is_recovery_week(self):
        plan = _make_plan()
        state = _make_state(misses=2)
        _, _, action = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(action, "recovery_week")

    def test_third_miss_resets_misses(self):
        plan = _make_plan()
        state = _make_state(misses=2)
        _, new_state, _ = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(new_state["consecutive_misses"], 0)

    def test_recovery_week_cuts_volume(self):
        plan = _make_plan()
        state = _make_state(misses=2)
        original_vol = plan["weeks"][1]["target_volume_min"]
        new_plan, _, _ = adapt(plan, state, _delta("under"), TODAY)
        new_vol = new_plan["weeks"][1]["target_volume_min"]
        self.assertAlmostEqual(new_vol, original_vol * 0.70, delta=2)

    def test_recovery_week_marks_flag(self):
        plan = _make_plan()
        state = _make_state(misses=2)
        new_plan, _, _ = adapt(plan, state, _delta("under"), TODAY)
        week2 = next(w for w in new_plan["weeks"] if w["week_number"] == 2)
        self.assertTrue(week2.get("recovery"))

    def test_fourth_miss_also_recovery_week(self):
        plan = _make_plan()
        state = _make_state(misses=3)
        _, _, action = adapt(plan, state, _delta("under"), TODAY)
        self.assertEqual(action, "recovery_week")


class TestVdotBump(unittest.TestCase):

    def test_first_over_no_bump(self):
        plan = _make_plan()
        state = _make_state(ahead=0)
        _, new_state, action = adapt(plan, state, _delta("over"), TODAY)
        self.assertNotEqual(action, "vdot_bump")
        self.assertEqual(new_state["consecutive_ahead"], 1)

    def test_second_over_no_bump(self):
        plan = _make_plan()
        state = _make_state(ahead=1)
        _, _, action = adapt(plan, state, _delta("over"), TODAY)
        self.assertNotEqual(action, "vdot_bump")

    def test_third_over_is_vdot_bump(self):
        plan = _make_plan()
        state = _make_state(ahead=2)
        _, new_state, action = adapt(plan, state, _delta("over"), TODAY)
        self.assertEqual(action, "vdot_bump")
        self.assertEqual(new_state["consecutive_ahead"], 0)

    def test_over_resets_misses(self):
        plan = _make_plan()
        state = _make_state(misses=2, ahead=0)
        _, new_state, _ = adapt(plan, state, _delta("over"), TODAY)
        self.assertEqual(new_state["consecutive_misses"], 0)


class TestOnTarget(unittest.TestCase):

    def test_on_target_resets_both_counters(self):
        plan = _make_plan()
        state = _make_state(misses=2, ahead=1)
        _, new_state, action = adapt(plan, state, _delta("on-target"), TODAY)
        self.assertEqual(action, "no_change")
        self.assertEqual(new_state["consecutive_misses"], 0)
        self.assertEqual(new_state["consecutive_ahead"], 0)


class TestAbortedVerdict(unittest.TestCase):

    def test_aborted_increments_misses(self):
        plan = _make_plan()
        state = _make_state(misses=0)
        _, new_state, _ = adapt(plan, state, _delta("aborted"), TODAY)
        self.assertEqual(new_state["consecutive_misses"], 1)

    def test_aborted_no_red_flag_when_drift_low(self):
        plan = _make_plan()
        state = _make_state()
        _, new_state, action = adapt(plan, state, _delta("aborted", hr_drift=3.0, rpe_delta=1), TODAY)
        flags = new_state.get("carry_forward", {}).get("recurring_red_flags", [])
        self.assertEqual(len(flags), 0)
        self.assertEqual(action, "monitor")

    def test_aborted_adds_red_flag_when_drift_high_and_rpe_high(self):
        plan = _make_plan()
        state = _make_state()
        _, new_state, action = adapt(plan, state, _delta("aborted", hr_drift=9.0, rpe_delta=2), TODAY)
        flags = new_state.get("carry_forward", {}).get("recurring_red_flags", [])
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["signal"], "high_drift_high_rpe")

    def test_aborted_two_red_flags_within_14d_triggers_recovery(self):
        plan = _make_plan()
        # Pre-seed one red flag from 7 days ago.
        state = _make_state(
            red_flags=[{"date": "2026-04-26", "signal": "high_drift_high_rpe"}]
        )
        _, _, action = adapt(plan, state, _delta("aborted", hr_drift=9.0, rpe_delta=3), TODAY)
        self.assertEqual(action, "red_flag_recovery")

    def test_aborted_old_red_flag_beyond_14d_no_recovery(self):
        plan = _make_plan()
        state = _make_state(
            red_flags=[{"date": "2026-04-01", "signal": "high_drift_high_rpe"}]
        )
        _, _, action = adapt(plan, state, _delta("aborted", hr_drift=9.0, rpe_delta=3), TODAY)
        self.assertNotEqual(action, "red_flag_recovery")


class TestAbortedDispatchesMisses(unittest.TestCase):

    def test_aborted_resets_ahead_and_dispatches_misses(self):
        # 3 consecutive aborted should trigger recovery_week
        plan = _make_plan()
        state = {"consecutive_misses": 2, "consecutive_ahead": 5, "carry_forward": {"recurring_red_flags": []}}
        delta = {"verdict": "aborted", "completion_pct": 30, "pace_delta_pct": 0, "rpe_delta": 0, "hr_drift_bpm": 0}
        new_plan, new_state, action = adapt(plan, state, delta, "2026-04-30")
        self.assertEqual(action, "recovery_week")
        self.assertEqual(new_state["consecutive_ahead"], 0)
        self.assertEqual(new_state["consecutive_misses"], 0)  # reset after intervention


class TestRecoveryWeekStubUpdatesMacrocycleTotalWeeks(unittest.TestCase):

    def test_recovery_week_stub_updates_macrocycle_total_weeks(self):
        plan = {
            "macrocycle": {"total_weeks": 1, "phases": []},
            "weeks": [{"week_number": 1, "phase": "base", "target_volume_min": 240, "target_long_run_min": 80, "days": []}],
        }
        state = {"consecutive_misses": 2, "consecutive_ahead": 0, "carry_forward": {"recurring_red_flags": []}}
        delta = {"verdict": "under", "completion_pct": 70, "pace_delta_pct": 7, "rpe_delta": 3, "hr_drift_bpm": 2}
        new_plan, _, action = adapt(plan, state, delta, "2027-01-01")  # date past plan
        self.assertEqual(action, "recovery_week")
        self.assertEqual(new_plan["macrocycle"]["total_weeks"], len(new_plan["weeks"]))


class TestInsertRecoveryWeekPublicHelper(unittest.TestCase):

    def test_insert_recovery_week_public_helper(self):
        plan = {
            "macrocycle": {"total_weeks": 4, "phases": []},
            "weeks": [
                {
                    "week_number": i,
                    "phase": "base",
                    "target_volume_min": 240,
                    "target_long_run_min": 60,
                    "days": [{"date": f"2026-05-{10+i*7:02d}", "dow": "Mon", "type": "Rest", "duration_min": 0, "target_pace": None, "notes": ""}],
                }
                for i in range(1, 5)
            ],
        }
        new_plan = insert_recovery_week(plan, "2026-05-10")
        self.assertIsNot(new_plan, plan)  # immutability: returns a new object
        self.assertNotEqual(new_plan, plan)  # the plan has been modified


if __name__ == "__main__":
    unittest.main()
