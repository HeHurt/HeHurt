"""Tests for regional parallel-cell current splitting."""

import unittest
from unittest.mock import patch

import pybamm

import src.simulation_regional_parallel as regional_module
from src.simulation import (
    RegionalCellState,
    RegionalDFNConfig,
    aggregate_regional_capacity_ah,
    build_area_scaled_regions,
    run_regional_dfn_coupling,
    solve_parallel_current_split,
)


class _FakeVariable:
    def __init__(self, value):
        self.entries = [value]


class _FakeSolution:
    termination = "final time"

    def __init__(
        self,
        start_s=0.0,
        end_s=0.0,
        voltage_v=3.3,
        ocv_v=3.3,
        negative_porosity=0.3,
        separator_porosity=0.4,
        positive_porosity=0.25,
    ):
        self.t = [start_s, end_s]
        self._variables = {
            "Terminal voltage [V]": _FakeVariable(voltage_v),
            "Surface open-circuit voltage [V]": _FakeVariable(ocv_v),
            "X-averaged negative electrode porosity": _FakeVariable(negative_porosity),
            "X-averaged separator porosity": _FakeVariable(separator_porosity),
            "X-averaged positive electrode porosity": _FakeVariable(positive_porosity),
        }

    def __getitem__(self, name):
        return self._variables[name]


class _FakeSimulation:
    def __init__(self, model, *, parameter_values, solver, var_pts):
        self.parameter_values = parameter_values
        self.resistance_ohm = float(parameter_values["Contact resistance [Ohm]"])
        self.negative_porosity = float(parameter_values["Negative electrode porosity"])
        self.separator_porosity = float(parameter_values["Separator porosity"])
        self.positive_porosity = float(parameter_values["Positive electrode porosity"])
        self.resistance_ohm *= 0.3 / self.negative_porosity

    def build(self, initial_soc=None, inputs=None):
        return None

    def step(self, dt, *, starting_solution, save, inputs):
        start_s = float(starting_solution.t[-1])
        current_a = float(inputs[regional_module.CURRENT_INPUT_NAME])
        ocv_v = 3.3
        voltage_v = ocv_v - current_a * self.resistance_ohm
        return _FakeSolution(
            start_s,
            start_s + dt,
            voltage_v,
            ocv_v,
            self.negative_porosity,
            self.separator_porosity,
            self.positive_porosity,
        )


class RegionalParallelTests(unittest.TestCase):
    def test_area_scaled_regions_recover_full_cell_resistance(self):
        regions = build_area_scaled_regions(
            {"corner": 0.1, "middle": 0.7, "top": 0.2},
            nominal_capacity_ah=100.0,
            base_ocv_v=3.3,
            base_resistance_ohm=0.01,
        )

        result = solve_parallel_current_split(regions, total_current_a=100.0)

        self.assertAlmostEqual(result.terminal_voltage_v, 2.3)
        self.assertAlmostEqual(result.region_currents_a["corner"], 10.0)
        self.assertAlmostEqual(result.region_currents_a["middle"], 70.0)
        self.assertAlmostEqual(result.region_currents_a["top"], 20.0)
        self.assertAlmostEqual(aggregate_regional_capacity_ah(regions), 100.0)

    def test_clogged_region_sheds_current_to_healthy_regions(self):
        regions = build_area_scaled_regions(
            {"corner": 0.1, "middle": 0.7, "top": 0.2},
            nominal_capacity_ah=100.0,
            base_ocv_v=3.3,
            base_resistance_ohm=0.01,
            resistance_multipliers={"corner": 100.0, "middle": 1.0, "top": 1.0},
        )

        result = solve_parallel_current_split(regions, total_current_a=100.0)

        self.assertLess(result.region_currents_a["corner"], 0.2)
        self.assertGreater(result.region_currents_a["middle"], 77.0)
        self.assertGreater(result.region_currents_a["top"], 22.0)
        self.assertAlmostEqual(sum(result.region_currents_a.values()), 100.0)

    def test_ocv_mismatch_creates_balancing_current_at_rest(self):
        regions = (
            RegionalCellState("high_soc", ocv_v=3.4, resistance_ohm=0.1),
            RegionalCellState("low_soc", ocv_v=3.2, resistance_ohm=0.1),
        )

        result = solve_parallel_current_split(regions, total_current_a=0.0)

        self.assertAlmostEqual(result.terminal_voltage_v, 3.3)
        self.assertAlmostEqual(result.region_currents_a["high_soc"], 1.0)
        self.assertAlmostEqual(result.region_currents_a["low_soc"], -1.0)

    def test_current_bounds_can_disconnect_failed_region(self):
        regions = (
            RegionalCellState("failed", ocv_v=3.3, resistance_ohm=0.01, lower_current_a=0.0, upper_current_a=0.0),
            RegionalCellState("healthy_a", ocv_v=3.3, resistance_ohm=0.01),
            RegionalCellState("healthy_b", ocv_v=3.3, resistance_ohm=0.01),
        )

        result = solve_parallel_current_split(regions, total_current_a=6.0)

        self.assertEqual(result.clamped_regions, ("failed",))
        self.assertAlmostEqual(result.region_currents_a["failed"], 0.0)
        self.assertAlmostEqual(result.region_currents_a["healthy_a"], 3.0)
        self.assertAlmostEqual(result.region_currents_a["healthy_b"], 3.0)

    def test_capacity_requires_region_capacity_values(self):
        regions = (
            RegionalCellState("a", ocv_v=3.3, resistance_ohm=0.01, capacity_ah=1.0),
            RegionalCellState("b", ocv_v=3.3, resistance_ohm=0.01),
        )

        with self.assertRaises(ValueError):
            aggregate_regional_capacity_ah(regions)

    def test_facade_exports_rows_for_reporting(self):
        regions = build_area_scaled_regions(
            {"corner": 0.1, "middle": 0.9},
            nominal_capacity_ah=10.0,
            base_ocv_v=3.3,
            base_resistance_ohm=0.01,
        )

        rows = solve_parallel_current_split(regions, total_current_a=10.0).rows()

        self.assertEqual(rows[0]["region"], "corner")
        self.assertAlmostEqual(rows[0]["c_rate"], 1.0)


    def test_regional_dfn_runner_scales_geometry_and_redistributes_current(self):
        base_params = pybamm.ParameterValues(
            {
                "Electrode width [m]": 1.0,
                "Nominal cell capacity [A.h]": 100.0,
                "Contact resistance [Ohm]": 0.01,
                "Negative electrode porosity": 0.3,
                "Separator porosity": 0.4,
                "Positive electrode porosity": 0.25,
            }
        )
        configs = (
            RegionalDFNConfig(
                "corner",
                0.1,
                parameter_multipliers={"Negative electrode porosity": 0.5},
            ),
            RegionalDFNConfig("middle", 0.7),
            RegionalDFNConfig("top", 0.2),
        )
        simulations = []

        def make_simulation(*args, **kwargs):
            simulation = _FakeSimulation(*args, **kwargs)
            simulations.append(simulation)
            return simulation

        with (
            patch.object(regional_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(regional_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(regional_module.pybamm, "Simulation", side_effect=make_simulation),
            patch.object(regional_module.pybamm, "EmptySolution", side_effect=_FakeSolution),
        ):
            result = run_regional_dfn_coupling(
                base_params,
                configs,
                total_current_a=100.0,
                duration_s=60.0,
                macro_step_s=60.0,
                relaxation=1.0,
                max_iterations=4,
            )

        capacities = [float(sim.parameter_values["Nominal cell capacity [A.h]"]) for sim in simulations]
        widths = [float(sim.parameter_values["Electrode width [m]"]) for sim in simulations]
        self.assertEqual(capacities, [10.0, 70.0, 20.0])
        self.assertEqual(widths, [0.1, 0.7, 0.2])

        final_rows = {row["region"]: row for row in result.steps()}
        self.assertLess(final_rows["corner"]["current_a"], 10.0)
        self.assertGreater(final_rows["middle"]["current_a"], 70.0)
        self.assertGreater(final_rows["top"]["current_a"], 20.0)
        self.assertLessEqual(final_rows["corner"]["kcl_error_a"], 1e-6)
        self.assertLessEqual(final_rows["corner"]["voltage_spread_v"], 1e-3)
        self.assertAlmostEqual(final_rows["corner"]["negative_porosity"], 0.15)
        self.assertAlmostEqual(final_rows["middle"]["separator_porosity"], 0.4)
        self.assertAlmostEqual(final_rows["top"]["positive_porosity"], 0.25)
        self.assertEqual(len(result.final_solutions), 3)

    def test_regional_dfn_runner_requires_area_sum_one(self):
        configs = (RegionalDFNConfig("a", 0.2), RegionalDFNConfig("b", 0.7))
        with self.assertRaises(ValueError):
            run_regional_dfn_coupling(
                object(),
                configs,
                total_current_a=1.0,
                duration_s=1.0,
            )


if __name__ == "__main__":
    unittest.main()
