import sys
import unittest
from pathlib import Path

import numpy as np


BATTERY_PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BATTERY_PROJECT_ROOT.parent
PARAMS_ROOT = WORKSPACE_ROOT / "params"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

import src.simulation_rpt as simulation_rpt_module  # noqa: E402


class SafeLastScalarTests(unittest.TestCase):
    def test_safe_last_scalar_prefers_final_time_evaluation(self):
        class FakeProcessedVariable:
            def __init__(self):
                self.called_with = None

            def __call__(self, t):
                self.called_with = t
                return np.array([[3.14]])

            @property
            def entries(self):
                raise AssertionError("entries should not be accessed when final-time eval works")

        class FakeSolution(dict):
            def __init__(self):
                super().__init__()
                self.t = np.array([0.0, 1.0, 2.0])

        sol = FakeSolution()
        sol["test_variable"] = FakeProcessedVariable()

        value = simulation_rpt_module.safe_last_scalar(sol, "test_variable")

        self.assertAlmostEqual(value, 3.14)
        self.assertEqual(sol["test_variable"].called_with, 2.0)

    def test_safe_last_scalar_falls_back_to_entries(self):
        class FakeProcessedVariable:
            def __call__(self, t):
                raise RuntimeError("final-time evaluation unavailable")

            @property
            def entries(self):
                return np.array([1.0, 2.0, 4.2])

        class FakeSolution(dict):
            def __init__(self):
                super().__init__()
                self.t = np.array([0.0, 1.0, 2.0])

        sol = FakeSolution()
        sol["test_variable"] = FakeProcessedVariable()

        value = simulation_rpt_module.safe_last_scalar(sol, "test_variable")

        self.assertAlmostEqual(value, 4.2)


class ValidateRptSummaryTests(unittest.TestCase):
    def test_validate_rpt_summary_rejects_partial_results(self):
        with self.assertRaisesRegex(ValueError, "Invalid RPT summary"):
            simulation_rpt_module.validate_rpt_summary(
                {
                    "rpt_charge_capacity_ah": np.nan,
                    "rpt_discharge_capacity_ah": 0.0,
                    "rpt_charge_energy_wh": np.nan,
                    "rpt_discharge_energy_wh": 0.0,
                    "rpt_efficiency": np.nan,
                }
            )

    def test_validate_rpt_summary_can_require_discharge_only(self):
        summary = {
            "rpt_charge_capacity_ah": np.nan,
            "rpt_discharge_capacity_ah": 100.0,
            "rpt_charge_energy_wh": np.nan,
            "rpt_discharge_energy_wh": 320.0,
            "rpt_efficiency": np.nan,
        }
        result = simulation_rpt_module.validate_rpt_summary(
            summary,
            required_finite_fields=(
                "rpt_discharge_capacity_ah",
                "rpt_discharge_energy_wh",
            ),
        )
        self.assertIs(result, summary)


if __name__ == "__main__":
    unittest.main()