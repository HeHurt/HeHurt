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


class RetentionNormalizationTests(unittest.TestCase):
    """retention 内部统一 0–1 小数；百分制输入自动归一化。"""

    def test_percent_input_normalized_to_fraction(self):
        bp = BatteryPlotter()
        bp.add_exp_data("A", [1, 2], [10.0, 9.0], [100.0, 90.0])
        np.testing.assert_allclose(bp.exp_db["A"]["ret"], [1.0, 0.9])

    def test_fraction_input_kept_as_is(self):
        bp = BatteryPlotter()
        bp.add_sim_data("A", [1, 2], [10.0, 9.0], [1.0, 0.9])
        np.testing.assert_allclose(bp.sim_db["A"]["ret"], [1.0, 0.9])

    def test_all_nan_retention_does_not_crash(self):
        bp = BatteryPlotter()
        bp.add_exp_data("A", [1, 2], [10.0, 9.0], [np.nan, np.nan])
        self.assertTrue(np.isnan(bp.exp_db["A"]["ret"]).all())




class _FakeVariable:
    def __init__(self, entries):
        self.entries = np.asarray(entries, dtype=float)


class _FakeCycle:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


class _FakeSolution:
    def __init__(self, cycles):
        self.cycles = cycles


def _coupling_cycle(cn_end, eps_n):
    return _FakeCycle({
        "X-averaged negative particle concentration [mol.m-3]": _FakeVariable([0.0, cn_end]),
        "X-averaged positive particle concentration [mol.m-3]": _FakeVariable([0.0, 0.0]),
        "X-averaged negative electrode porosity": _FakeVariable([eps_n, eps_n]),
        "X-averaged separator porosity": _FakeVariable([0.4, 0.4]),
        "X-averaged positive electrode porosity": _FakeVariable([0.23, 0.23]),
    })


class PlotSwellingCouplingTests(unittest.TestCase):
    """plot_swelling_coupling 冒烟：力包络 + 孔隙率 + 面压，cycle 横轴。"""

    def _params(self):
        return {
            "Negative electrode thickness [m]": 1.0,
            "Positive electrode thickness [m]": 1.0,
            "Initial concentration in negative electrode [mol.m-3]": 0.0,
            "Initial concentration in positive electrode [mol.m-3]": 0.0,
        }

    def test_smoke_with_pressure_history(self):
        from src.plotting import plot_swelling_coupling

        sol = _FakeSolution([_coupling_cycle(3.0, 0.32), _coupling_cycle(4.0, 0.30)])
        result = plot_swelling_coupling(
            sol, "demo", self._params(),
            x_axis="cycle", acceleration_factor=50,
            pressure_history=[43000.0, 45000.0],
            cycles_per_block=1,
            omega_n=3.0, k_stiffness=1.0, preload_force=0.0,
            expansion_function_n=None, expansion_function_p=None,
        )
        self.assertIsNotNone(result)
        fig, (ax1, ax2) = result
        # 左图三条力线，右图三条孔隙率线
        self.assertEqual(len(ax1.get_lines()), 3)
        self.assertEqual(len(ax2.get_lines()), 3)

    def test_pressure_requires_cycles_per_block(self):
        from src.plotting import plot_swelling_coupling

        sol = _FakeSolution([_coupling_cycle(3.0, 0.32)])
        with self.assertRaises(ValueError):
            plot_swelling_coupling(
                sol, "demo", self._params(),
                pressure_history=[43000.0],
                omega_n=3.0, k_stiffness=1.0,
                expansion_function_n=None, expansion_function_p=None,
            )

    def test_none_when_empty_solution(self):
        from src.plotting import plot_swelling_coupling

        self.assertIsNone(
            plot_swelling_coupling(_FakeSolution([]), "demo", self._params())
        )


if __name__ == "__main__":
    unittest.main()
