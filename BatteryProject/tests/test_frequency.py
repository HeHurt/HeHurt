import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


BATTERY_PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BATTERY_PROJECT_ROOT.parent
PARAMS_ROOT = WORKSPACE_ROOT / "params"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

import src.simulation_frequency as simulation_frequency_module  # noqa: E402


class FrequencyScenarioPreparationTests(unittest.TestCase):
    def test_prepare_frequency_scenarios_populates_derived_metrics(self):
        prepared = simulation_frequency_module.prepare_frequency_scenarios(
            scenarios=[
                {
                    "name": "s1",
                    "display_name": "Scenario 1",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 2.0,
                    "enabled": True,
                }
            ],
            current_a=293.5,
            nominal_capacity_ah=587.0,
        )

        scenario = prepared["scenarios"][0]
        self.assertEqual(scenario["pair_count_per_day"], 720)
        self.assertAlmostEqual(scenario["charge_ah_per_day"], 587.0)
        self.assertAlmostEqual(scenario["efc_per_day"], 1.0)
        self.assertAlmostEqual(scenario["soc_swing_per_half_cycle"], 10 / 7200)

        scenario_table = prepared["scenario_table"]
        self.assertEqual(list(scenario_table["scenario"]), ["Scenario 1"])
        self.assertTrue(bool(scenario_table["enabled"].iloc[0]))


class RunFrequencyScenarioTests(unittest.TestCase):
    def test_run_frequency_scenario_accepts_raw_scenario(self):
        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.model = model
                self.parameter_values = parameter_values
                self.experiment = experiment
                self.var_pts = var_pts
                self.solver = solver

            def solve(self, **kwargs):
                return DummySolution()

        rpt_summary = {
            "rpt_charge_capacity_ah": 590.0,
            "rpt_discharge_capacity_ah": 580.0,
            "rpt_charge_energy_wh": 1900.0,
            "rpt_discharge_energy_wh": 1805.0,
            "rpt_efficiency": 0.95,
            "rpt_max_force_n": 10.0,
            "rpt_min_force_n": 5.0,
        }

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                side_effect=lambda *args, **kwargs: dict(degradation_snapshot),
            ),
            patch.object(simulation_frequency_module, "run_branch_rpt", return_value=(object(), dict(rpt_summary))),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "raw_frequency",
                    "display_name": "Raw Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 2.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 1,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 1,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=293.5,
                nominal_capacity_ah=587.0,
                initial_soc=0.6,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
            )

        self.assertAlmostEqual(bundle["scenario"]["efc_per_day"], 1.0)
        self.assertEqual(bundle["main_df"]["real_day"].iloc[0], 1)
        self.assertEqual(bundle["rpt_df"]["real_day"].iloc[0], 1)
        self.assertAlmostEqual(bundle["rpt_df"]["capacity_retention"].iloc[0], 1.0)
        self.assertAlmostEqual(bundle["rpt_df"]["rpt_efficiency_pct"].iloc[0], 95.0)

    def test_run_frequency_scenario_uses_block_progress_when_enabled(self):
        progress_calls = []

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.model = model
                self.parameter_values = parameter_values
                self.experiment = experiment
                self.var_pts = var_pts
                self.solver = solver

            def solve(self, **kwargs):
                return DummySolution()

        def passthrough_progress(iterable, **kwargs):
            progress_calls.append(kwargs)
            return iterable

        rpt_summary = {
            "rpt_charge_capacity_ah": 590.0,
            "rpt_discharge_capacity_ah": 580.0,
            "rpt_charge_energy_wh": 1900.0,
            "rpt_discharge_energy_wh": 1805.0,
            "rpt_efficiency": 0.95,
            "rpt_max_force_n": 10.0,
            "rpt_min_force_n": 5.0,
        }

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                side_effect=lambda *args, **kwargs: dict(degradation_snapshot),
            ),
            patch.object(simulation_frequency_module, "run_branch_rpt", return_value=(object(), dict(rpt_summary))),
            patch.object(simulation_frequency_module, "_maybe_wrap_progress", side_effect=passthrough_progress),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "raw_frequency",
                    "display_name": "Raw Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 2.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 2,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 1,
                    "showprogress": True,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=293.5,
                nominal_capacity_ah=587.0,
                initial_soc=0.6,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
            )

        self.assertEqual(len(progress_calls), 1)
        self.assertTrue(progress_calls[0]["enabled"])
        self.assertEqual(progress_calls[0]["total"], 2)
        self.assertEqual(progress_calls[0]["unit"], "block")
        self.assertIn("Raw Frequency", progress_calls[0]["desc"])
        self.assertEqual(bundle["main_df"]["real_day"].iloc[-1], 2)

    def test_run_frequency_scenario_equivalent_mode_compresses_day_steps(self):
        captured_experiments = []

        class DummyExperiment:
            def __init__(self, steps, temperature=None):
                self.steps = steps
                self.temperature = temperature
                captured_experiments.append(self)

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.model = model
                self.parameter_values = parameter_values
                self.experiment = experiment
                self.var_pts = var_pts
                self.solver = solver

            def solve(self, **kwargs):
                return DummySolution()

        rpt_summary = {
            "rpt_charge_capacity_ah": 590.0,
            "rpt_discharge_capacity_ah": 580.0,
            "rpt_charge_energy_wh": 1900.0,
            "rpt_discharge_energy_wh": 1805.0,
            "rpt_efficiency": 0.95,
            "rpt_max_force_n": 10.0,
            "rpt_min_force_n": 5.0,
        }

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", DummyExperiment),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                side_effect=lambda *args, **kwargs: dict(degradation_snapshot),
            ),
            patch.object(simulation_frequency_module, "run_branch_rpt", return_value=(object(), dict(rpt_summary))),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "raw_frequency",
                    "display_name": "Raw Frequency",
                    "pulse_seconds": 5,
                    "total_pulses_per_day": 2880,
                    "sample_period_seconds": 1.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 1,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 1,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=293.5,
                nominal_capacity_ah=587.0,
                initial_soc=0.6,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=True,
            )

        expected_pair_count = -(
            -(2880 // 2) // simulation_frequency_module.EQUIVALENT_FREQUENCY_PAIR_GROUP_SIZE
        )
        experiment_steps = captured_experiments[0].steps[0]
        self.assertEqual(len(experiment_steps), expected_pair_count * 2)
        self.assertLess(len(experiment_steps), 2880)
        self.assertTrue(bool(bundle["main_df"]["use_equivalent_frequency"].iloc[0]))
        self.assertEqual(bundle["main_df"]["simulated_pair_count"].iloc[0], expected_pair_count)
        self.assertEqual(bundle["main_df"]["original_pulses_per_day"].iloc[0], 2880)
        self.assertEqual(bundle["main_df"]["simulated_segments_per_day"].iloc[0], expected_pair_count * 2)
        self.assertAlmostEqual(
            bundle["main_df"]["pulse_compression_ratio"].iloc[0],
            2880 / (expected_pair_count * 2),
        )


class RunFrequencyScenariosParallelTests(unittest.TestCase):
    def test_parallel_mode_uses_process_pool_and_preserves_order(self):
        executor_instances = []
        progress_calls = []

        class DummyExecutor:
            def __init__(self, max_workers=None):
                self.max_workers = max_workers
                self.tasks = None
                executor_instances.append(self)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def map(self, func, tasks):
                self.tasks = list(tasks)
                return [func(task) for task in self.tasks]

        def fake_worker(task):
            scenario = task["scenario"]
            simulated_segments = 30 if scenario["name"] == "s1" else 60
            main_df = pd.DataFrame(
                [
                    {
                        "real_day": task["runtime_config"]["real_days_total"],
                        "q_sei_ah": 0.1,
                        "q_plating_ah": 0.2,
                        "lli_ah": 0.3,
                        "lam_neg_ah": 0.4,
                        "sei_total_thickness_m": 1e-9,
                        "use_equivalent_frequency": task["use_equivalent_frequency"],
                        "original_pulses_per_day": scenario["total_pulses_per_day"],
                        "simulated_segments_per_day": simulated_segments,
                        "pulse_compression_ratio": scenario["total_pulses_per_day"] / simulated_segments,
                        "simulated_segment_seconds": 120.0,
                    }
                ]
            )
            rpt_df = pd.DataFrame(
                [
                    {
                        "real_day": task["runtime_config"]["real_days_total"],
                        "rpt_discharge_capacity_ah": 580.0,
                        "capacity_retention": 0.99,
                        "rpt_efficiency": 0.95,
                        "rpt_efficiency_pct": 95.0,
                    }
                ]
            )
            return {
                "scenario": scenario,
                "main_df": main_df,
                "rpt_df": rpt_df,
                "final_main_solution": None,
                "rpt_solutions": [],
            }

        def passthrough_progress(iterable, **kwargs):
            progress_calls.append(kwargs)
            return iterable

        scenarios = [
            {
                "name": "s1",
                "display_name": "Scenario 1",
                "pulse_seconds": 10,
                "total_pulses_per_day": 1440,
                "sample_period_seconds": 2.0,
                "enabled": True,
            },
            {
                "name": "s2",
                "display_name": "Scenario 2",
                "pulse_seconds": 10,
                "total_pulses_per_day": 2880,
                "sample_period_seconds": 2.0,
                "enabled": True,
            },
        ]

        with patch.object(simulation_frequency_module, "ProcessPoolExecutor", DummyExecutor), \
            patch.object(simulation_frequency_module, "run_frequency_scenario_from_kwargs", side_effect=fake_worker), \
            patch.object(simulation_frequency_module, "_maybe_wrap_progress", side_effect=passthrough_progress):
            bundle = simulation_frequency_module.run_frequency_scenarios(
                scenarios=scenarios,
                runtime_config={
                    "real_days_total": 10,
                    "day_acceleration_factor": 5,
                    "rpt_every_real_days": 5,
                    "showprogress": True,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=293.5,
                nominal_capacity_ah=587.0,
                initial_soc=0.6,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                parallel=True,
                max_workers=2,
                return_solutions=False,
                use_equivalent_frequency=True,
            )

        self.assertEqual(len(executor_instances), 1)
        self.assertEqual(executor_instances[0].max_workers, 2)
        self.assertEqual([task["scenario"]["name"] for task in executor_instances[0].tasks], ["s1", "s2"])
        self.assertEqual(list(bundle["results"].keys()), ["s1", "s2"])
        self.assertEqual(list(bundle["summary_df"]["scenario"]), ["Scenario 1", "Scenario 2"])
        self.assertTrue(bool(bundle["summary_df"]["use_equivalent_frequency"].iloc[0]))
        self.assertEqual(bundle["summary_df"]["original_pulses_per_day"].iloc[0], 1440)
        self.assertEqual(bundle["summary_df"]["simulated_segments_per_day"].iloc[0], 30)
        self.assertAlmostEqual(bundle["summary_df"]["pulse_compression_ratio"].iloc[0], 48.0)
        self.assertEqual(executor_instances[0].tasks[0]["runtime_config"]["showprogress"], False)
        self.assertTrue(executor_instances[0].tasks[0]["use_equivalent_frequency"])
        self.assertEqual(len(progress_calls), 1)
        self.assertTrue(progress_calls[0]["enabled"])
        self.assertEqual(progress_calls[0]["total"], 2)
        self.assertEqual(progress_calls[0]["unit"], "scenario")
        self.assertEqual(progress_calls[0]["desc"], "Frequency scenarios")


class FrequencyLongRunRecoveryTests(unittest.TestCase):
    def test_run_frequency_scenario_records_invalid_rpt_as_failed_summary(self):
        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.experiment = experiment

            def solve(self, **kwargs):
                return DummySolution()

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                side_effect=lambda *args, **kwargs: dict(degradation_snapshot),
            ),
            patch.object(
                simulation_frequency_module,
                "run_branch_rpt",
                side_effect=ValueError("Invalid RPT summary: missing finite charge/discharge metrics"),
            ),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "invalid_rpt_frequency",
                    "display_name": "Invalid RPT Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 10.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 1,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 1,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=157.0,
                nominal_capacity_ah=314.0,
                initial_soc=0.5,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=False,
            )

        self.assertFalse(bool(bundle["terminated_early"]))
        self.assertEqual(bundle["rpt_df"]["real_day"].iloc[0], 1)
        self.assertTrue(pd.isna(bundle["rpt_df"]["capacity_retention"].iloc[0]))
        self.assertEqual(bundle["rpt_df"]["rpt_failure_type"].iloc[0], "ValueError")
        self.assertIn("Invalid RPT summary", bundle["rpt_df"]["rpt_failure_message"].iloc[0])

    def test_run_frequency_scenario_retries_with_finer_equivalent_segments(self):
        attempted_segment_seconds = []

        class DummyExperiment:
            def __init__(self, steps, temperature=None):
                self.steps = steps
                self.temperature = temperature

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.experiment = experiment

            def solve(self, **kwargs):
                segment_seconds = float(self.experiment.steps[0][0].split(" for ")[1].split(" second")[0])
                attempted_segment_seconds.append(segment_seconds)
                if segment_seconds >= 500:
                    raise simulation_frequency_module.pybamm.SolverError(
                        "Events ['Minimum voltage [V]'] are non-positive at initial conditions with inputs {}"
                    )
                return DummySolution()

        rpt_summary = {
            "rpt_charge_capacity_ah": 590.0,
            "rpt_discharge_capacity_ah": 580.0,
            "rpt_charge_energy_wh": 1900.0,
            "rpt_discharge_energy_wh": 1805.0,
            "rpt_efficiency": 0.95,
            "rpt_max_force_n": 10.0,
            "rpt_min_force_n": 5.0,
        }

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", DummyExperiment),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                return_value=degradation_snapshot,
            ),
            patch.object(simulation_frequency_module, "run_branch_rpt", return_value=(object(), dict(rpt_summary))),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "adaptive_frequency",
                    "display_name": "Adaptive Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 10.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 1,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 1,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=157.0,
                nominal_capacity_ah=314.0,
                initial_soc=0.5,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=True,
            )

        self.assertEqual([round(value, 3) for value in attempted_segment_seconds], [900.0, 480.0])
        self.assertEqual(bundle["main_df"]["simulated_segments_per_day"].iloc[0], 30)
        self.assertAlmostEqual(bundle["main_df"]["simulated_segment_seconds"].iloc[0], 480.0)
        self.assertEqual(bundle["main_df"]["equivalent_pair_group_size"].iloc[0], 50)
        self.assertFalse(bool(bundle["terminated_early"]))

    def test_run_frequency_scenario_stops_gracefully_after_last_feasible_block(self):
        solve_calls = []
        solutions = []

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.experiment = experiment

            def solve(self, **kwargs):
                solve_calls.append(kwargs)
                if len(solve_calls) == 1:
                    solution = DummySolution()
                    solutions.append(solution)
                    return solution
                raise ValueError(
                    "The `all_ts` time vector must be strictly increasing across all segments of the sub-solutions."
                )

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                return_value=degradation_snapshot,
            ),
            patch.object(simulation_frequency_module, "run_branch_rpt", return_value=(object(), {})),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "graceful_frequency",
                    "display_name": "Graceful Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 10.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 3,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 10,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=157.0,
                nominal_capacity_ah=314.0,
                initial_soc=0.5,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=False,
            )

        self.assertEqual(list(bundle["main_df"]["real_day"]), [1])
        self.assertEqual(bundle["real_days_covered"], 1)
        self.assertTrue(bool(bundle["terminated_early"]))
        self.assertIn("strictly increasing", bundle["termination_reason"])
        self.assertIs(solve_calls[1]["starting_solution"], solutions[0].last_state)

    def test_run_frequency_scenarios_summary_uses_last_feasible_day(self):
        solve_calls = []

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.experiment = experiment

            def solve(self, **kwargs):
                solve_calls.append(kwargs)
                if len(solve_calls) == 1:
                    return DummySolution()
                raise ValueError(
                    "The `all_ts` time vector must be strictly increasing across all segments of the sub-solutions."
                )

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(simulation_frequency_module, "_make_parameter_values", return_value=object()),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                return_value=degradation_snapshot,
            ),
        ):
            bundle = simulation_frequency_module.run_frequency_scenarios(
                scenarios=[
                    {
                        "name": "graceful_frequency",
                        "display_name": "Graceful Frequency",
                        "pulse_seconds": 10,
                        "total_pulses_per_day": 1440,
                        "sample_period_seconds": 10.0,
                        "enabled": True,
                    }
                ],
                runtime_config={
                    "real_days_total": 3,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 10,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=157.0,
                nominal_capacity_ah=314.0,
                initial_soc=0.5,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=False,
            )

        self.assertEqual(bundle["summary_df"]["real_days_covered"].iloc[0], 1)
        self.assertTrue(bool(bundle["summary_df"]["terminated_early"].iloc[0]))
        self.assertIn("strictly increasing", bundle["summary_df"]["termination_reason"].iloc[0])

    def test_run_frequency_scenario_splits_infeasible_block_into_smaller_real_days(self):
        attempted_t_factors = []

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.parameter_values = parameter_values

            def solve(self, **kwargs):
                attempted_t_factors.append(self.parameter_values["t_factor"])
                if self.parameter_values["t_factor"] > 50:
                    raise simulation_frequency_module.pybamm.SolverError(
                        "Events ['Minimum voltage [V]'] are non-positive at initial conditions with inputs {}"
                    )
                return DummySolution()

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(
                simulation_frequency_module,
                "_make_parameter_values",
                side_effect=lambda get_hithium_params, t_factor, temperature, check_already_exists=False: {
                    "t_factor": t_factor,
                },
            ),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                side_effect=lambda *args, **kwargs: dict(degradation_snapshot),
            ),
            patch.object(
                simulation_frequency_module,
                "run_branch_rpt",
                return_value=(
                    object(),
                    {
                        "rpt_charge_capacity_ah": 590.0,
                        "rpt_discharge_capacity_ah": 580.0,
                        "rpt_charge_energy_wh": 1900.0,
                        "rpt_discharge_energy_wh": 1805.0,
                        "rpt_efficiency": 0.95,
                        "rpt_max_force_n": 10.0,
                        "rpt_min_force_n": 5.0,
                    },
                ),
            ),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "split_frequency",
                    "display_name": "Split Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 10.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 73,
                    "day_acceleration_factor": 73,
                    "rpt_every_real_days": 365,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=157.0,
                nominal_capacity_ah=314.0,
                initial_soc=0.5,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=False,
            )

        self.assertEqual(attempted_t_factors, [73.0, 36.0, 37.0])
        self.assertEqual(list(bundle["main_df"]["real_day"]), [36, 73])
        self.assertEqual(bundle["real_days_covered"], 73)
        self.assertFalse(bool(bundle["terminated_early"]))

    def test_run_frequency_scenario_relaxes_main_voltage_limits_after_initial_condition_failure(self):
        attempted_lower_cutoffs = []

        class DummySolution:
            def __init__(self):
                self.last_state = object()

        class DummySimulation:
            def __init__(self, model, parameter_values=None, experiment=None, var_pts=None, solver=None):
                self.parameter_values = parameter_values

            def solve(self, **kwargs):
                attempted_lower_cutoffs.append(self.parameter_values["Lower voltage cut-off [V]"])
                if self.parameter_values["Lower voltage cut-off [V]"] > 0:
                    raise simulation_frequency_module.pybamm.SolverError(
                        "Events ['Minimum voltage [V]'] are non-positive at initial conditions with inputs {}"
                    )
                return DummySolution()

        degradation_snapshot = {
            "throughput_ah": 1.0,
            "q_sei_ah": 0.1,
            "q_sei_on_cracks_ah": 0.0,
            "q_plating_ah": 0.2,
            "q_side_ah": 0.3,
            "sei_total_thickness_m": 1e-9,
            "negative_porosity_avg": 0.3,
            "lli_ah": 0.4,
            "lam_neg_ah": 0.5,
        }

        with (
            patch.object(simulation_frequency_module.pybamm.lithium_ion, "DFN", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "IDAKLUSolver", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Experiment", return_value=object()),
            patch.object(simulation_frequency_module.pybamm, "Simulation", DummySimulation),
            patch.object(
                simulation_frequency_module,
                "_make_parameter_values",
                return_value={
                    "Lower voltage cut-off [V]": 2.5,
                    "Upper voltage cut-off [V]": 3.65,
                },
            ),
            patch.object(
                simulation_frequency_module,
                "snapshot_degradation_variables",
                side_effect=lambda *args, **kwargs: dict(degradation_snapshot),
            ),
            patch.object(
                simulation_frequency_module,
                "run_branch_rpt",
                return_value=(
                    object(),
                    {
                        "rpt_charge_capacity_ah": 590.0,
                        "rpt_discharge_capacity_ah": 580.0,
                        "rpt_charge_energy_wh": 1900.0,
                        "rpt_discharge_energy_wh": 1805.0,
                        "rpt_efficiency": 0.95,
                        "rpt_max_force_n": 10.0,
                        "rpt_min_force_n": 5.0,
                    },
                ),
            ),
        ):
            bundle = simulation_frequency_module.run_frequency_scenario(
                scenario={
                    "name": "relaxed_voltage_frequency",
                    "display_name": "Relaxed Voltage Frequency",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 10.0,
                    "enabled": True,
                },
                runtime_config={
                    "real_days_total": 1,
                    "day_acceleration_factor": 1,
                    "rpt_every_real_days": 365,
                    "showprogress": False,
                },
                model_options={"SEI": "ec reaction limited"},
                var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
                current_a=157.0,
                nominal_capacity_ah=314.0,
                initial_soc=0.5,
                temperature_k=298.15,
                get_hithium_params=lambda t_factor, temperature: {},
                return_solutions=False,
                use_equivalent_frequency=False,
            )

        self.assertEqual(attempted_lower_cutoffs, [2.5, 0.0])
        self.assertTrue(bool(bundle["main_df"]["relaxed_voltage_limits"].iloc[0]))
        self.assertFalse(bool(bundle["terminated_early"]))


if __name__ == "__main__":
    unittest.main()
