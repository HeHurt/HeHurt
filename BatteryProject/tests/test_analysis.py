"""Unit tests for src/analysis.py (pure-logic functions, no solver needed)."""

import unittest
import numpy as np

from src.analysis import (
    calc_rrmse,
    calculate_cycle_swelling,
    compute_cycle_energies,
    get_discharge_capacity,
)


class CalcRrmseTests(unittest.TestCase):
    def test_identical_arrays_return_zero(self):
        y = np.array([3.2, 3.3, 3.4])
        rmse, rrmse = calc_rrmse(y, y)
        self.assertAlmostEqual(rmse, 0.0)
        self.assertAlmostEqual(rrmse, 0.0)

    def test_known_offset(self):
        y_true = np.array([1.0, 1.0, 1.0])
        y_pred = np.array([2.0, 2.0, 2.0])
        rmse, rrmse = calc_rrmse(y_true, y_pred)
        self.assertAlmostEqual(rmse, 1.0)
        self.assertAlmostEqual(rrmse, 1.0)  # rmse / mean(y_true) = 1/1

    def test_asymmetric_error(self):
        y_true = np.array([10.0, 10.0])
        y_pred = np.array([10.0, 12.0])
        rmse, _ = calc_rrmse(y_true, y_pred)
        expected_rmse = np.sqrt(np.mean([0.0, 4.0]))
        self.assertAlmostEqual(rmse, expected_rmse)


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


def _swelling_params():
    return {
        "Negative electrode thickness [m]": 1.0,
        "Positive electrode thickness [m]": 1.0,
        "Initial concentration in negative electrode [mol.m-3]": 0.0,
        "Initial concentration in positive electrode [mol.m-3]": 0.0,
    }


def _engineering_cycle(cn, cp=None, sei=None):
    cp = np.zeros_like(np.asarray(cn, dtype=float)) if cp is None else cp
    data = {
        "X-averaged negative particle concentration [mol.m-3]": _FakeVariable(cn),
        "X-averaged positive particle concentration [mol.m-3]": _FakeVariable(cp),
    }
    if sei is not None:
        data["X-averaged negative SEI thickness [m]"] = _FakeVariable(sei)
    return _FakeCycle(data)


class CalculateCycleSwellingTests(unittest.TestCase):
    def test_engineering_mode_preserves_tuple_result(self):
        sol = _FakeSolution([_engineering_cycle([0.0, 3.0, 6.0])])

        max_f, min_f = calculate_cycle_swelling(
            sol,
            _swelling_params(),
            omega_n=3.0,
            k_stiffness=1.0,
            preload_force=0.0,
        )

        np.testing.assert_allclose(max_f, [6.0])
        np.testing.assert_allclose(min_f, [0.0])

    def test_cycle_start_reference_zeros_each_cycle(self):
        sol = _FakeSolution([_engineering_cycle([5.0, 6.0, 7.0])])

        table = calculate_cycle_swelling(
            sol,
            _swelling_params(),
            omega_n=3.0,
            k_stiffness=1.0,
            reference="cycle_start",
            return_table=True,
        )

        self.assertAlmostEqual(table.loc[0, "max_disp_m"], 2.0)
        self.assertAlmostEqual(table.loc[0, "min_disp_m"], 0.0)
        self.assertAlmostEqual(table.loc[0, "reversible_amplitude_n"], 2.0)

    def test_solution_start_reference_uses_first_valid_solution_point(self):
        sol = _FakeSolution([
            _engineering_cycle([5.0, 6.0]),
            _engineering_cycle([7.0, 8.0]),
        ])

        table = calculate_cycle_swelling(
            sol,
            _swelling_params(),
            omega_n=3.0,
            k_stiffness=1.0,
            reference="solution_start",
            return_table=True,
        )

        np.testing.assert_allclose(table["max_force_n"].to_numpy(), [1.0, 3.0])
        np.testing.assert_allclose(table["min_force_n"].to_numpy(), [0.0, 2.0])

    def test_pybamm_thickness_mode_returns_structured_table(self):
        cycle = _engineering_cycle([0.0, 1.0])
        cycle._data["Cell thickness change [m]"] = _FakeVariable([1e-6, 3e-6])
        sol = _FakeSolution([cycle])

        table = calculate_cycle_swelling(
            sol,
            _swelling_params(),
            method="pybamm_thickness",
            k_stiffness=1.0e9,
            preload_force=10.0,
            return_table=True,
        )

        self.assertEqual(
            list(table.columns),
            [
                "cycle",
                "max_force_n",
                "min_force_n",
                "eoc_force_n",
                "reversible_amplitude_n",
                "max_disp_m",
                "min_disp_m",
                "source_method",
            ],
        )
        self.assertEqual(table.loc[0, "cycle"], 1)
        self.assertAlmostEqual(table.loc[0, "max_force_n"], 3010.0)
        self.assertAlmostEqual(table.loc[0, "min_force_n"], 1010.0)
        self.assertAlmostEqual(table.loc[0, "eoc_force_n"], 3010.0)
        self.assertAlmostEqual(table.loc[0, "reversible_amplitude_n"], 2000.0)
        self.assertAlmostEqual(table.loc[0, "max_disp_m"], 3e-6)
        self.assertAlmostEqual(table.loc[0, "min_disp_m"], 1e-6)
        self.assertEqual(table.loc[0, "source_method"], "pybamm_thickness")

    def test_invalid_method_or_reference_raises(self):
        sol = _FakeSolution([_engineering_cycle([0.0])])

        with self.assertRaises(ValueError):
            calculate_cycle_swelling(sol, _swelling_params(), method="bad")
        with self.assertRaises(ValueError):
            calculate_cycle_swelling(sol, _swelling_params(), reference="bad")

    def test_none_solution_can_return_empty_table(self):
        table = calculate_cycle_swelling(None, _swelling_params(), return_table=True)
        self.assertEqual(table.shape[0], 0)
        self.assertIn("source_method", table.columns)


class SwellingPhysicsTests(unittest.TestCase):
    def test_unilateral_contact_clamps_force_at_zero(self):
        sol = _FakeSolution([_engineering_cycle([0.0, -3.0])])

        max_f, min_f = calculate_cycle_swelling(
            sol, _swelling_params(), omega_n=3.0, k_stiffness=1.0, preload_force=1.0,
        )

        # 位移 [0, -3] -> 原始力 [1, -2]，单边接触后最小力钳到 0
        np.testing.assert_allclose(max_f, [1.0])
        np.testing.assert_allclose(min_f, [0.0])

    def test_series_stiffness_combines_fixture_and_cell(self):
        sol = _FakeSolution([_engineering_cycle([0.0, 3.0])])

        max_f, _ = calculate_cycle_swelling(
            sol, _swelling_params(), omega_n=3.0, k_stiffness=2.0, k_cell=2.0,
        )

        # k_eff = 1/(1/2 + 1/2) = 1，最大位移 3 -> 力 3
        np.testing.assert_allclose(max_f, [3.0])

    def test_irreversible_term_scaled_by_surface_area(self):
        params = _swelling_params()
        params["Negative electrode surface area to volume ratio [m-1]"] = 10.0
        sol = _FakeSolution([_engineering_cycle([0.0, 0.0], sei=[1.0, 2.0])])

        max_f, min_f = calculate_cycle_swelling(
            sol, params, omega_n=0.0, k_stiffness=1.0, beta_irreversible=0.5,
        )

        # Δδ_film = [0, 1] -> 位移 = β·a_n·L_n·Δδ = 0.5*10*1*[0, 1]
        np.testing.assert_allclose(max_f, [5.0])
        np.testing.assert_allclose(min_f, [0.0])

    def test_irreversible_term_disabled_without_surface_area(self):
        sol = _FakeSolution([_engineering_cycle([0.0, 0.0], sei=[1.0, 2.0])])

        max_f, _ = calculate_cycle_swelling(
            sol, _swelling_params(), omega_n=0.0, k_stiffness=1.0,
        )

        np.testing.assert_allclose(max_f, [0.0])

    def test_nonlinear_expansion_function_used_when_c_max_present(self):
        params = _swelling_params()
        params["Maximum concentration in negative electrode [mol.m-3]"] = 10.0
        sol = _FakeSolution([_engineering_cycle([0.0, 5.0])])

        max_f, _ = calculate_cycle_swelling(
            sol, params, k_stiffness=1.0,
            expansion_function_n=lambda sto: 2.0 * np.asarray(sto, dtype=float),
        )

        # f(sto) = 2·sto, L_n=1: ΔL = 2*(0.5 - 0) = 1
        np.testing.assert_allclose(max_f, [1.0])

    def test_builtin_expansion_functions_and_invalid_name(self):
        from src.analysis import graphite_expansion_fraction, lfp_expansion_fraction

        self.assertAlmostEqual(float(graphite_expansion_fraction(0.0)), 0.0)
        self.assertAlmostEqual(float(graphite_expansion_fraction(1.0)), 0.132)
        self.assertAlmostEqual(float(lfp_expansion_fraction(1.0)), 0.022)

        sol = _FakeSolution([_engineering_cycle([0.0])])
        with self.assertRaises(ValueError):
            calculate_cycle_swelling(sol, _swelling_params(), expansion_function_n="bogus")


class GetDischargeCapacityTests(unittest.TestCase):
    def test_none_sol_returns_empty(self):
        result = get_discharge_capacity(None)
        self.assertEqual(result["discharge_capacity"].size, 0)

    def test_sums_multiple_discharge_steps_in_one_cycle(self):
        def step(current, throughput):
            return _FakeCycle({
                "Current [A]": _FakeVariable(current),
                "Throughput capacity [A.h]": _FakeVariable(throughput),
            })

        cycle = _FakeCycle({})
        cycle.steps = [
            object(),
            step([1.0, 1.0], [0.0, 2.0]),
            step([-1.0, -1.0], [2.0, 4.0]),
            step([0.0, 0.0], [4.0, 4.0]),
            step([0.8, 0.8], [4.0, 7.5]),
        ]
        result = get_discharge_capacity(_FakeSolution([cycle]))

        np.testing.assert_allclose(result["discharge_capacity"], [5.5])


class ComputeCycleEnergiesTests(unittest.TestCase):
    def test_none_sol_returns_empty(self):
        result = compute_cycle_energies(None)
        for key in ("discharge_cap", "e_charge", "e_discharge", "efficiency"):
            self.assertEqual(result[key].size, 0)


if __name__ == "__main__":
    unittest.main()
