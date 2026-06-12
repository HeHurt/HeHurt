import sys
import unittest
from pathlib import Path

import numpy as np
import pybamm


BATTERY_PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BATTERY_PROJECT_ROOT.parent
PARAMS_ROOT = WORKSPACE_ROOT / "params"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

from paramsMIC import get_hithium_params
from src.simulation import run_peak_current


class PeakCurrentRegressionTests(unittest.TestCase):
    def test_current_sigmoid_model_returns_finite_peak_currents(self):
        model = pybamm.lithium_ion.DFN(
            {
                "calculate discharge energy": "true",
                "contact resistance": "true",
                "open-circuit potential": ("current sigmoid", "current sigmoid"),
            }
        )
        params = pybamm.ParameterValues("OKane2022")
        params.update(get_hithium_params(1, 273.15))
        var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}

        result = run_peak_current(
            model,
            params,
            var_pts,
            temperature=273.15,
            nominal=1175,
            t_period=3,
            x0=1,
            charge_soc_list=[0.95],
            discharge_soc_list=[1.0],
            search_ratios=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5],
        )

        self.assertTrue(np.isfinite(result["charge_peak_current"][0]))
        self.assertTrue(np.isfinite(result["discharge_peak_current"][0]))
        self.assertGreater(result["charge_peak_current"][0], 0)
        self.assertGreater(result["discharge_peak_current"][0], 0)

    def test_current_sigmoid_model_returns_finite_peak_powers_in_w_mode(self):
        model = pybamm.lithium_ion.DFN(
            {
                "calculate discharge energy": "true",
                "contact resistance": "true",
                "open-circuit potential": ("current sigmoid", "current sigmoid"),
            }
        )
        params = pybamm.ParameterValues("OKane2022")
        params.update(get_hithium_params(1, 273.15))
        var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}

        result = run_peak_current(
            model,
            params,
            var_pts,
            temperature=273.15,
            nominal=1175,
            t_period=3,
            x0=1,
            charge_soc_list=[0.95],
            discharge_soc_list=[1.0],
            search_ratios=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5],
            mode="W",
        )

        self.assertTrue(np.isfinite(result["charge_peak_power"][0]))
        self.assertTrue(np.isfinite(result["discharge_peak_power"][0]))
        self.assertGreater(result["charge_peak_power"][0], 0)
        self.assertGreater(result["discharge_peak_power"][0], 0)
        self.assertAlmostEqual(
            result["charge_peak_current"][0],
            result["charge_peak_power"][0] / 3.2,
            places=6,
        )
        self.assertAlmostEqual(
            result["discharge_peak_current"][0],
            result["discharge_peak_power"][0] / 3.2,
            places=6,
        )


class FindPeakBracketTests(unittest.TestCase):
    """_find_peak_current_bracket 自适应扩展（纯函数，无需求解器）。"""

    def test_root_inside_grid_unchanged(self):
        from src.simulation_peak import _find_peak_current_bracket

        left, right, _ = _find_peak_current_bracket(lambda r: 3 - r, [1, 2, 5])
        self.assertEqual((left, right), (2, 5))

    def test_root_above_grid_extends_upward(self):
        from src.simulation_peak import _find_peak_current_bracket

        # 根在 7，网格最大 5——复现 0°C 峰值倍率刚超出采样网格的回归场景
        left, right, sampled = _find_peak_current_bracket(lambda r: 7 - r, [1, 2, 5])
        self.assertEqual((left, right), (5, 10))
        self.assertGreater(len(sampled), 3)

    def test_root_below_grid_extends_downward(self):
        from src.simulation_peak import _find_peak_current_bracket

        left, right, _ = _find_peak_current_bracket(
            lambda r: 0.3 - r, [1, 2, 5], max_extensions=4
        )
        self.assertIsNotNone(left)
        self.assertLessEqual(left, 0.3)
        self.assertGreaterEqual(right, 0.3)

    def test_no_root_returns_none(self):
        from src.simulation_peak import _find_peak_current_bracket

        left, right, _ = _find_peak_current_bracket(
            lambda r: 1.0, [1, 2], max_extensions=2
        )
        self.assertIsNone(left)
        self.assertIsNone(right)


if __name__ == "__main__":
    unittest.main()