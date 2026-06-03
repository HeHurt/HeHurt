"""Smoke tests for src/plotting.py — pure-logic helpers + BatteryPlotter state.

We avoid actually rendering figures by using matplotlib's Agg backend at import time.
"""

import matplotlib

matplotlib.use("Agg")  # headless backend, no GUI window

import unittest

import numpy as np

from src.plotting import BatteryPlotter


class LabelHelpersTests(unittest.TestCase):
    def test_normalized_key_strips_marker_suffixes(self):
        bp = BatteryPlotter()
        k1 = bp._get_normalized_key("25°C 0.5P (Sim)")
        k2 = bp._get_normalized_key("25°C 0.5P (Exp)")
        k3 = bp._get_normalized_key("25c0.5p_sim")
        # All should normalize to the same color-bucket key
        self.assertEqual(k1, k2)
        self.assertIn("0.5p", k1.lower())

    def test_charge_discharge_label_routing(self):
        self.assertTrue(BatteryPlotter._is_discharge_label("rate_dchg"))
        self.assertTrue(BatteryPlotter._is_discharge_label("Discharge heat"))
        self.assertFalse(BatteryPlotter._is_discharge_label("rate_chg"))
        self.assertTrue(BatteryPlotter._is_charge_label("rate_chg"))
        # "charge" containing "discharge" must NOT be classified as charge
        self.assertFalse(BatteryPlotter._is_charge_label("Discharge heat"))


class BatteryPlotterStateTests(unittest.TestCase):
    def test_add_and_resolve_keys(self):
        bp = BatteryPlotter()
        bp.add_exp_data("25°C 0.5P", [1, 50], [10.0, 9.9], [100.0, 99.0])
        bp.add_sim_data("25°C 0.5P", [1, 50], [10.0, 9.9], [100.0, 99.0])

        # exact key lookup
        self.assertEqual(bp._resolve_keys(bp.exp_db, "25°C 0.5P"), ["25°C 0.5P"])
        # "all"
        self.assertEqual(set(bp._resolve_keys(bp.sim_db, "all")), {"25°C 0.5P"})
        # None -> empty
        self.assertEqual(bp._resolve_keys(bp.exp_db, None), [])
        # tuple AND
        self.assertEqual(bp._resolve_keys(bp.exp_db, ("25°C", "0.5P")), ["25°C 0.5P"])
        self.assertEqual(bp._resolve_keys(bp.exp_db, ("25°C", "1.0P")), [])

    def test_color_stable_per_normalized_label(self):
        bp = BatteryPlotter()
        c1 = bp._get_color("25°C 0.5P (Sim)")
        c2 = bp._get_color("25°C 0.5P (Exp)")
        np.testing.assert_array_equal(c1, c2)

    def test_plot_does_not_crash(self):
        """Smoke: plotting should not raise on a minimal exp+sim set."""
        bp = BatteryPlotter()
        bp.add_exp_data("A", [1, 2, 3], [10, 9, 8], [100, 90, 80])
        bp.add_sim_data("A", [1, 2, 3], [10.1, 9.1, 8.1], [101, 91, 81])
        bp.plot(target_exp="all", target_sim="all")  # uses Agg, no show


if __name__ == "__main__":
    unittest.main()
