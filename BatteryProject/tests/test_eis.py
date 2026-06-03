import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

import src.simulation_eis as simulation_eis_module


class EisPostProcessingTests(unittest.TestCase):
    def test_pick_soh_checkpoints_keeps_unique_targets_and_lowest_soh(self):
        soh_table = pd.DataFrame(
            [
                {"cycle": 1, "soh_pct": 100.0, "discharge_capacity_ah": 314.0},
                {"cycle": 2, "soh_pct": 95.2, "discharge_capacity_ah": 299.0},
                {"cycle": 3, "soh_pct": 94.9, "discharge_capacity_ah": 298.0},
                {"cycle": 4, "soh_pct": 88.0, "discharge_capacity_ah": 276.0},
            ]
        )

        checkpoints = simulation_eis_module.pick_soh_checkpoints(soh_table, [95.0, 90.0])

        self.assertEqual(list(checkpoints["cycle"]), [3, 4])
        self.assertEqual(checkpoints["label"].iloc[0], "SOH=94.9% | Cycle 3")

    def test_unresolved_semicircle_sets_charge_transfer_proxy_to_zero(self):
        solution = SimpleNamespace(
            frequencies=np.array([1e4, 1e2, 1.0]),
            impedance=np.array([0.01 + 0.00j, 0.03 - 0.01j, 0.08 - 0.04j]),
        )

        summary = simulation_eis_module.summarize_impedance_components(
            solution,
            label="SOH=90%",
            soh_pct=90.0,
            cycle_number=5,
        )

        self.assertFalse(summary["semicircle_resolved"])
        self.assertEqual(summary["r_ct_proxy_ohm"], 0.0)
        self.assertAlmostEqual(summary["r_diffusion_proxy_ohm"], summary["r_polarization_ohm"])


class LifecycleEisWorkflowTests(unittest.TestCase):
    def test_run_lifecycle_eis_study_merges_measurement_metadata(self):
        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, solver=None, var_pts=None):
                self.model = model
                self.parameter_values = parameter_values
                self.experiment = experiment
                self.solver = solver
                self.var_pts = var_pts

            def solve(self, **_kwargs):
                return SimpleNamespace(cycles=[SimpleNamespace(last_state=object()), SimpleNamespace(last_state=object())])

        soh_df = pd.DataFrame(
            [
                {"cycle": 1, "soh_pct": 100.0, "discharge_capacity_ah": 314.0},
                {"cycle": 2, "soh_pct": 95.0, "discharge_capacity_ah": 298.3},
            ]
        )
        checkpoints_df = pd.DataFrame(
            [
                {"cycle": 1, "target_soh_pct": 100.0, "soh_pct": 100.0, "label": "SOH=100.0% | Cycle 1"},
                {"cycle": 2, "target_soh_pct": 95.0, "soh_pct": 95.0, "label": "SOH=95.0% | Cycle 2"},
            ]
        )

        def fake_run_eis_from_checkpoint(*_args, **_kwargs):
            solution = SimpleNamespace(
                frequencies=np.array([1e4, 1e2, 1.0]),
                impedance=np.array([0.01 + 0.00j, 0.02 - 0.02j, 0.05 - 0.01j]),
            )
            meta = {
                "eis_state": "fixed SOC=50% after recharge/rest",
                "eis_target_soc_pct": 50.0,
                "conditioning_charge_current_a": 10.0,
                "conditioning_duration_h": 1.5,
            }
            return solution, meta

        with (
            patch.object(simulation_eis_module, "_build_parameter_values", return_value={"Nominal cell capacity [A.h]": 314.0}),
            patch.object(simulation_eis_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_eis_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_eis_module, "build_lifecycle_power_experiment", return_value=object()),
            patch.object(simulation_eis_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_eis_module, "build_lifecycle_soh_table", return_value=soh_df),
            patch.object(simulation_eis_module, "pick_soh_checkpoints", return_value=checkpoints_df.copy()),
            patch.object(simulation_eis_module, "run_eis_from_checkpoint", side_effect=fake_run_eis_from_checkpoint),
        ):
            result = simulation_eis_module.run_lifecycle_eis_study(
                get_hithium_params=lambda t_factor, temperature: {},
                frequencies=np.logspace(-2, 3, 3),
                target_soh_levels=[100, 95],
                aging_cycles=2,
                aging_power_rate=0.5,
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                temperature_k=298.15,
                aging_t_factor=50,
            )

        self.assertAlmostEqual(result["aging_power_w"], 0.5 * 314.0 * 3.2)
        self.assertEqual(list(result["checkpoints_df"]["eis_target_soc_pct"]), [50.0, 50.0])
        self.assertEqual(list(result["components_df"]["cycle"]), [1, 2])
        self.assertEqual(sorted(result["eis_solutions"].keys()), ["SOH=100.0% | Cycle 1", "SOH=95.0% | Cycle 2"])


if __name__ == "__main__":
    unittest.main()