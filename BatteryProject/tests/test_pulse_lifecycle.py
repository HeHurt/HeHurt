import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pandas as pd


BATTERY_PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BATTERY_PROJECT_ROOT.parent
PARAMS_ROOT = WORKSPACE_ROOT / "params"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

from src import simulation_pulse_lifecycle as spl
from src.simulation_frequency import build_frequency_current_profile, trim_current_profile
from src.simulation_pulse_lifecycle import (
    build_pulse_lifecycle_capacity_check_steps,
    build_pulse_lifecycle_cycle_steps,
    extract_cycle_voltage_curve,
    p_rate_to_power_w,
    prepare_pulse_lifecycle_scenarios,
    summarize_pulse_lifecycle_results,
)

MIC_SCENARIOS = [
    {
        "name": "baseline_0p25p",
        "display_name": "0.25P 基础充放循环",
        "pulse_p_rate": None,
        "pulse_seconds": None,
        "charge_interval_minutes": None,
        "discharge_interval_minutes": None,
        "charge_soc_window": (0.10, 0.90),
        "discharge_soc_window": (0.10, 0.90),
        "enabled": True,
    },
    {
        "name": "pulse_0p3p",
        "display_name": "0.3P 插入脉冲 2 min",
        "pulse_p_rate": 0.3,
        "pulse_seconds": 120.0,
        "charge_interval_minutes": 5.0,
        "discharge_interval_minutes": 5.0,
        "charge_soc_window": (0.10, 0.90),
        "discharge_soc_window": (0.10, 0.90),
        "enabled": True,
    },
    {
        "name": "pulse_0p375p",
        "display_name": "0.375P 插入脉冲 60 s",
        "pulse_p_rate": 0.375,
        "pulse_seconds": 60.0,
        "charge_interval_minutes": 30.0,
        "discharge_interval_minutes": 20.0,
        "charge_soc_window": (0.10, 0.70),
        "discharge_soc_window": (0.30, 1.00),
        "enabled": True,
    },
    {
        "name": "pulse_0p75p",
        "display_name": "0.75P 插入脉冲 13 s",
        "pulse_p_rate": 0.75,
        "pulse_seconds": 13.0,
        "charge_interval_minutes": 30.0,
        "discharge_interval_minutes": 20.0,
        "charge_soc_window": (0.10, 0.70),
        "discharge_soc_window": (0.30, 1.00),
        "enabled": True,
    },
]


class PulseLifecycleBuilderTests(unittest.TestCase):
    def test_p_rate_to_power_w_uses_nominal_lfp_voltage(self):
        self.assertAlmostEqual(p_rate_to_power_w(0.25, 1175, 3.2), 940.0)

    def test_default_mic_scenarios_are_four_enabled_cases(self):
        prepared = prepare_pulse_lifecycle_scenarios(
            MIC_SCENARIOS,
            nominal_capacity_ah=1175,
        )

        self.assertEqual(len(prepared["scenarios"]), 4)
        self.assertTrue(prepared["scenario_table"]["enabled"].all())
        self.assertIn("baseline_0p25p", [case["name"] for case in prepared["scenarios"]])


    def test_capacity_check_steps_are_normal_full_charge_discharge(self):
        steps = build_pulse_lifecycle_capacity_check_steps(nominal_capacity_ah=1175)

        self.assertEqual(steps[0], "Rest for 30 minutes (0.5 minute period)")
        self.assertEqual(steps[1], "Charge at 940.00W until 3.65 V (0.5 minute period)")
        self.assertEqual(steps[3], "Discharge at 940.00W until 2.50 V (0.5 minute period)")
        self.assertFalse(any("seconds" in step for step in steps))

    def test_summary_prefers_capacity_check_capacity_over_pulse_discharge_capacity(self):
        results = {
            "pulse_0p3p": {
                "scenario": {"name": "pulse_0p3p", "display_name": "0.3P 插入脉冲 2 min"},
                "main_df": pd.DataFrame(
                    {
                        "discharge_capacity_ah": [120.0],
                        "capacity_retention": [1.0],
                        "q_sei_ah": [2.0],
                        "q_plating_ah": [0.1],
                    }
                ),
                "capacity_check_df": pd.DataFrame(
                    {
                        "capacity_check_discharge_capacity_ah": [1175.0, 1116.25],
                        "capacity_retention": [1.0, 0.95],
                    }
                ),
                "real_cycles_covered": 500.0,
            }
        }

        summary = summarize_pulse_lifecycle_results(results)

        self.assertAlmostEqual(summary["final_capacity_ah"].iloc[0], 1116.25)
        self.assertAlmostEqual(summary["final_capacity_retention_pct"].iloc[0], 95.0)
        self.assertEqual(summary["final_capacity_source"].iloc[0], "capacity_check")



    def test_adaptive_window_capacity_shortens_soc_window_without_changing_power(self):
        scenario = dict(MIC_SCENARIOS[1])
        scenario["charge_soc_window"] = (0.10, 0.90)
        scenario["discharge_soc_window"] = (0.10, 0.90)

        nominal_steps = build_pulse_lifecycle_cycle_steps(
            scenario,
            nominal_capacity_ah=100,
            nominal_voltage_v=4.0,
        )
        faded_steps = build_pulse_lifecycle_cycle_steps(
            scenario,
            nominal_capacity_ah=100,
            nominal_voltage_v=4.0,
            window_capacity_ah=50,
        )

        self.assertIn("Charge at 100.00W for 0.4 hours", nominal_steps[0])
        self.assertIn("Charge at 100.00W for 0.2 hours", faded_steps[0])
        self.assertEqual(nominal_steps[1], "Charge at 120.00W for 120 seconds (0.5 minute period)")
        self.assertEqual(faded_steps[1], "Charge at 120.00W for 120 seconds (0.5 minute period)")

    def test_direct_mode_keeps_first_unaccelerated_cycle_without_cycles_per_block(self):
        class FakeSimulation:
            instances = []

            def __init__(self, model, parameter_values, experiment, var_pts, solver):
                self.experiment = experiment
                FakeSimulation.instances.append(self)

            def solve(self, **kwargs):
                return object()

        first_cycle_df = pd.DataFrame(
            {
                "sim_cycle": [1],
                "discharge_capacity_ah": [10.0],
                "capacity_retention": [1.0],
            }
        )
        accelerated_cycle_df = pd.DataFrame(
            {
                "sim_cycle": [1, 2],
                "discharge_capacity_ah": [9.5, 9.0],
                "capacity_retention": [0.95, 0.9],
            }
        )
        runtime_config = {
            "total_cycles": 100,
            "aging_t_factor": 50,
            "use_block_acceleration": False,
            "showprogress": False,
        }
        scenario = {"name": "baseline", "display_name": "baseline", "pulse_p_rate": None}

        with patch.object(spl.pybamm.lithium_ion, "DFN", return_value=object()), \
             patch.object(spl.pybamm, "IDAKLUSolver", return_value=object()), \
             patch.object(spl.pybamm, "Experiment", side_effect=lambda steps, temperature: list(steps)), \
             patch.object(spl.pybamm, "Simulation", FakeSimulation), \
             patch.object(spl, "_make_parameter_values", return_value={}), \
             patch.object(spl, "_build_cycle_dataframe", side_effect=[first_cycle_df, accelerated_cycle_df]), \
             patch.object(spl, "snapshot_degradation_variables", return_value={}):
            result = spl._run_single_pulse_lifecycle_scenario(
                scenario,
                runtime_config,
                model_options={},
                var_pts={},
                nominal_capacity_ah=100.0,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                get_discharge_capacity_func=lambda sol: {},
            )

        self.assertEqual(len(FakeSimulation.instances), 2)
        self.assertEqual(len(FakeSimulation.instances[0].experiment), 1)
        self.assertEqual(len(FakeSimulation.instances[1].experiment), 2)
        self.assertEqual(result["main_df"]["real_cycle"].tolist(), [1.0, 50.5, 100.0])
        self.assertEqual(result["real_cycles_covered"], 100.0)

    def test_inserted_pulse_charge_tail_runs_until_voltage_cutoff(self):
        scenario = MIC_SCENARIOS[1]
        steps = build_pulse_lifecycle_cycle_steps(scenario, nominal_capacity_ah=1175)
        first_rest_index = steps.index("Rest for 30 minutes (0.5 minute period)")

        self.assertEqual(steps[first_rest_index - 1], "Charge at 940.00W until 3.65 V (0.5 minute period)")

    def test_inserted_pulse_discharge_tail_runs_until_voltage_cutoff(self):
        scenario = MIC_SCENARIOS[1]
        steps = build_pulse_lifecycle_cycle_steps(scenario, nominal_capacity_ah=1175)

        self.assertEqual(steps[-2], "Discharge at 940.00W until 2.50 V (0.5 minute period)")

    def test_discharge_window_30_to_100_starts_with_pulse(self):
        scenario = MIC_SCENARIOS[2]
        steps = build_pulse_lifecycle_cycle_steps(scenario, nominal_capacity_ah=1175)
        rest_index = steps.index("Rest for 30 minutes (0.5 minute period)")

        self.assertTrue(steps[rest_index + 1].startswith("Discharge at 1410.00W for 60 seconds"))


class FrequencyProfileTests(unittest.TestCase):
    def test_build_and_trim_frequency_current_profile(self):
        time_s, current_a = build_frequency_current_profile(10, 2, 293.5)

        np.testing.assert_allclose(time_s[:4], [0.0, 10.0, 10.0, 20.0])
        np.testing.assert_allclose(current_a[:4], [293.5, 293.5, -293.5, -293.5])

        trimmed_time, trimmed_current = trim_current_profile(time_s, current_a, 15)
        self.assertEqual(trimmed_time.shape, trimmed_current.shape)
        self.assertGreaterEqual(trimmed_time.size, 2)
        self.assertLessEqual(trimmed_time[-1], 20.0)


class ExtractVoltageCurveTests(unittest.TestCase):
    def test_extract_cycle_voltage_curve_masks_charge_and_discharge(self):
        class Variable:
            def __init__(self, values):
                self.entries = np.asarray(values, dtype=float)

        class Cycle:
            def __getitem__(self, name):
                return {
                    "Current [A]": Variable([-1, -1, 0, 1, 1]),
                    "Voltage [V]": Variable([3.2, 3.3, 3.31, 3.2, 3.1]),
                    "Throughput capacity [A.h]": Variable([0, 1, 1, 2, 3]),
                    "Time [s]": Variable([0, 10, 20, 30, 40]),
                }[name]

        charge = extract_cycle_voltage_curve(Cycle(), direction="charge", x_axis="capacity")
        discharge = extract_cycle_voltage_curve(Cycle(), direction="discharge", x_axis="time")

        np.testing.assert_allclose(charge["x"], [0, 1])
        np.testing.assert_allclose(charge["voltage"], [3.2, 3.3])
        np.testing.assert_allclose(discharge["x"], [0, 10])
        np.testing.assert_allclose(discharge["voltage"], [3.2, 3.1])


if __name__ == "__main__":
    unittest.main()
