"""
test_vdot.py — Unit tests for vdot.py.

Data-dependent assertions are skipped when data/vdot-table.json is absent.
"""
import unittest
import sys
from pathlib import Path

# Allow importing vdot without installing as a package.
sys.path.insert(0, str(Path(__file__).parent))

import vdot as vdot_mod


class TestVdotAPIContract(unittest.TestCase):
    """Tests that don't require the data file."""

    def test_vdot_from_race_exists(self):
        self.assertTrue(callable(vdot_mod.vdot_from_race))

    def test_paces_for_vdot_exists(self):
        self.assertTrue(callable(vdot_mod.paces_for_vdot))

    def test_predict_race_time_exists(self):
        self.assertTrue(callable(vdot_mod.predict_race_time))

    def test_vdot_from_race_unsupported_distance_raises(self):
        with self.assertRaises(ValueError):
            vdot_mod.vdot_from_race(1000, 240)

    def test_predict_race_time_unsupported_distance_raises(self):
        with self.assertRaises(ValueError):
            vdot_mod.predict_race_time(47.0, 1000)

    def test_vdot_from_race_all_supported_distances_are_accepted(self):
        """Accepted distances do not raise ValueError (FileNotFoundError is OK if no data)."""
        supported = [5000, 10000, 21097, 42195]
        for dist in supported:
            try:
                vdot_mod.vdot_from_race(dist, 3600)
            except ValueError:
                self.fail(f"vdot_from_race raised ValueError for supported distance {dist}")
            except FileNotFoundError:
                pass  # Data absent — acceptable in this test.

    def test_predict_race_time_all_supported_distances_accepted(self):
        supported = [5000, 10000, 21097, 42195]
        for dist in supported:
            try:
                vdot_mod.predict_race_time(47.0, dist)
            except ValueError:
                self.fail(f"predict_race_time raised ValueError for supported distance {dist}")
            except FileNotFoundError:
                pass


class TestVdotDataDependent(unittest.TestCase):
    """Tests that require data/vdot-table.json.  Skipped if absent."""

    @classmethod
    def setUpClass(cls):
        # Clear cached table so each test suite gets a fresh load.
        vdot_mod._table = None
        plugin_root = Path(__file__).resolve().parents[3]
        cls.data_available = (plugin_root / "data" / "vdot-table.json").exists()

    def setUp(self):
        if not self.data_available:
            self.skipTest("data/vdot-table.json not yet populated — skipping data-dependent tests")

    def test_vdot_from_race_5k_sub24(self):
        # 5K in 24:00 (1440 s) → approximately VDOT 40 per Daniels' table
        # (anchor: VDOT 40 predicts 5K = 1448s = 24:08; VDOT 41 predicts 1416s = 23:36).
        # Original comment "≈ VDOT 47" was incorrect — corrected against filled table.
        result = vdot_mod.vdot_from_race(5000, 1440)
        self.assertAlmostEqual(result, 40, delta=1.5)

    def test_paces_for_vdot_returns_expected_keys(self):
        paces = vdot_mod.paces_for_vdot(47.0)
        for key in ("easy_per_km_s", "marathon_per_km_s", "threshold_per_km_s",
                    "interval_per_km_s", "repetition_per_km_s"):
            self.assertIn(key, paces)

    def test_paces_for_vdot_ordering(self):
        # Easy pace (slowest) > marathon > threshold > interval > repetition (fastest).
        paces = vdot_mod.paces_for_vdot(47.0)
        self.assertGreater(paces["easy_per_km_s"], paces["marathon_per_km_s"])
        self.assertGreater(paces["marathon_per_km_s"], paces["threshold_per_km_s"])
        self.assertGreater(paces["threshold_per_km_s"], paces["interval_per_km_s"])
        self.assertGreater(paces["interval_per_km_s"], paces["repetition_per_km_s"])

    def test_paces_for_vdot_returns_ints(self):
        paces = vdot_mod.paces_for_vdot(47.0)
        for key, val in paces.items():
            self.assertIsInstance(val, int, f"{key} should be int")

    def test_predict_race_time_5k(self):
        # VDOT 47 → predicted 5K around 21:02 (1262s) per Daniels' table.
        # Original comment "around 24:00" was incorrect — 24:00 maps to ~VDOT 40.
        result = vdot_mod.predict_race_time(47.0, 5000)
        self.assertAlmostEqual(result, 1262, delta=60)

    def test_predict_race_time_returns_int(self):
        result = vdot_mod.predict_race_time(47.0, 5000)
        self.assertIsInstance(result, int)

    def test_vdot_from_race_roundtrip(self):
        # vdot_from_race(dist, predict_race_time(v, dist)) ≈ v.
        v = 50.0
        for dist in [5000, 10000, 21097, 42195]:
            predicted_time = vdot_mod.predict_race_time(v, dist)
            recovered_vdot = vdot_mod.vdot_from_race(dist, predicted_time)
            self.assertAlmostEqual(recovered_vdot, v, delta=0.5,
                                   msg=f"Roundtrip failed for distance {dist}")


if __name__ == "__main__":
    unittest.main()
