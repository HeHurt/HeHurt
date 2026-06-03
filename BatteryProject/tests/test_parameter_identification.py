"""Smoke tests for src/parameter_identification.py.

No PyBaMM solver needed — only pure logic + scipy optimizer.
"""

import unittest

import numpy as np

from src.parameter_identification import (
    ParamSpec,
    compute_loss,
    extract_aging_output,
    params_to_model_input,
    run_parameter_optimization,
)


class ParamSpecAndMappingTests(unittest.TestCase):
    def test_paramspec_log_roundtrip(self):
        change_params = {"K_sei": ParamSpec("user", "log", 1e-16, 1e-13)}
        # Search-space mid-point in log10 space is -14.5; physical value 10**-14.5
        out = params_to_model_input({"K_sei": -14.5}, change_params)
        self.assertAlmostEqual(out["user"]["K_sei"], 10**-14.5, places=20)
        self.assertEqual(out["model"], {})

    def test_paramspec_line_passthrough(self):
        change_params = {"alpha": ParamSpec("model", "line", 0.1, 0.9)}
        out = params_to_model_input({"alpha": 0.5}, change_params)
        self.assertAlmostEqual(out["model"]["alpha"], 0.5)
        self.assertEqual(out["user"], {})

    def test_list_form_change_params_accepted(self):
        change_params = {"K_sei": ["user", "log", 1e-16, 1e-13]}
        out = params_to_model_input({"K_sei": -15.0}, change_params)
        self.assertAlmostEqual(out["user"]["K_sei"], 1e-15)

    def test_fixed_input_params_merged(self):
        change_params = {"K_sei": ParamSpec("user", "log", 1e-16, 1e-13)}
        fixed = {"user": {"frozen": 1.23}, "model": {"flag": True}}
        out = params_to_model_input({"K_sei": -14.0}, change_params, fixed_input_params=fixed)
        self.assertEqual(out["user"]["frozen"], 1.23)
        self.assertEqual(out["model"]["flag"], True)
        self.assertAlmostEqual(out["user"]["K_sei"], 1e-14)

    def test_invalid_bounds_raise(self):
        # Bound check is performed inside run_parameter_optimization (via
        # _to_search_space), not in params_to_model_input.
        change_params = {"bad": ParamSpec("user", "log", 1.0, 1.0)}  # low == high
        with self.assertRaises(ValueError):
            run_parameter_optimization(lambda p: 1.0, change_params, method="MO")

    def test_unsupported_scope_raises(self):
        change_params = {"x": ParamSpec("invalid_scope", "line", 0.0, 1.0)}
        with self.assertRaises(ValueError):
            params_to_model_input({"x": 0.5}, change_params)


class ExtractAgingOutputTests(unittest.TestCase):
    def test_none_sol_returns_empty(self):
        out = extract_aging_output(None)
        self.assertEqual(out["Measured capacity [A.h]"].size, 0)
        self.assertEqual(out["Simulation Record data"], [])


class ComputeLossTests(unittest.TestCase):
    def test_unknown_loss_type_raises(self):
        with self.assertRaises(ValueError):
            compute_loss("nonsense", [np.array([]), np.array([])], {})

    def test_cycle_line_empty_sim_returns_penalty(self):
        # sim_output 缺 "Measured capacity [A.h]" → loss_cycle_line 直接返 100.0
        loss = compute_loss(
            "cycle_line",
            [np.array([1, 50, 100]), np.array([1.0, 0.95, 0.9])],
            {"Measured capacity [A.h]": np.array([])},
            t_factor=50,
        )
        self.assertAlmostEqual(loss, 100.0)

    def test_hybrid_requires_dict_exp_data(self):
        with self.assertRaises(ValueError):
            compute_loss(["cycle_line"], [np.array([])], {})


class RunParameterOptimizationTests(unittest.TestCase):
    """Use MO (scipy SLSQP) backend — no optional deps needed."""

    def test_mo_recovers_optimum_of_quadratic(self):
        change_params = {"x": ParamSpec("user", "line", -2.0, 2.0)}

        def objective(search_params):
            # fitness = 1 / (0.1 + (x - 0.5)^2)  → maximum at x=0.5
            x = float(search_params["x"])
            return 1.0 / (0.1 + (x - 0.5) ** 2)

        result = run_parameter_optimization(
            objective, change_params, method="MO", init={"x": 0.0}
        )
        self.assertEqual(result["method"], "MO")
        self.assertIn("best_params", result)
        self.assertAlmostEqual(result["best_params"]["x"], 0.5, places=3)

    def test_invalid_method_raises(self):
        change_params = {"x": ParamSpec("user", "line", 0.0, 1.0)}
        with self.assertRaises(ValueError):
            run_parameter_optimization(lambda p: 1.0, change_params, method="XX")

    def test_bo_missing_dependency_friendly_error(self):
        """If bayes_opt is missing, the ImportError must be informative."""
        try:
            import bayes_opt  # noqa: F401
            self.skipTest("bayes_opt installed; cannot test missing-dep branch")
        except ImportError:
            pass
        change_params = {"x": ParamSpec("user", "line", 0.0, 1.0)}
        with self.assertRaises(ImportError) as ctx:
            run_parameter_optimization(lambda p: 1.0, change_params, method="BO")
        # Must mention the package name so the user knows what to install
        self.assertIn("bayesian-optimization", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
