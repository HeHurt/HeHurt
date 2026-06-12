"""Smoke tests for src/utils.py — no PyBaMM needed."""

import unittest
import logging

import numpy as np
import pandas as pd

from src.utils import (
    BatteryDataLoader,
    process_sol_list_with_custom_extractor,
    safe_var_access,
)


class _StubStep:
    """Minimal stand-in for a PyBaMM step object that supports ``step[name].entries``."""

    def __init__(self, vars_dict):
        self._vars = vars_dict

    def __getitem__(self, key):
        if key not in self._vars:
            raise KeyError(key)
        return type("_E", (), {"entries": np.asarray(self._vars[key])})()


class SafeVarAccessTests(unittest.TestCase):
    def test_returns_first_available(self):
        step = _StubStep({"Voltage [V]": [3.2, 3.3]})
        out = safe_var_access(step, ["Current [A]", "Voltage [V]"])
        np.testing.assert_array_equal(out, [3.2, 3.3])

    def test_raises_when_none_available(self):
        step = _StubStep({"Other": [1]})
        with self.assertRaises(KeyError):
            safe_var_access(step, ["Voltage [V]", "Current [A]"])


class BatteryDataLoaderTests(unittest.TestCase):
    def test_standardize_columns_maps_aliases(self):
        # _standardize_columns currently uses naive case-insensitive substring
        # matching, and its alias lists contain very short tokens ("t", "V",
        # "Ah") that pollute longer column names. We therefore only smoke-test
        # the simplest case: a single unique column gets renamed. See
        # docs/proposed_easy_imports.py / AGENTS.md for the broader fix.
        loader = BatteryDataLoader()
        # "xyz_999" is chosen to avoid every single-letter alias ('t','v','i')
        # and every multi-char alias ('ah','wh','cyc#'…). It must survive unchanged.
        df = pd.DataFrame({"Cycle Index": [1, 2], "xyz_999": [0, 0]})
        out = loader._standardize_columns(df)
        self.assertIn("cycle", out.columns)
        self.assertIn("xyz_999", out.columns)


class ProcessSolListTests(unittest.TestCase):
    def test_empty_sol_list_no_error(self):
        # Just verify it doesn't raise on the empty fast-path.
        class _DummyPlotter:
            def __init__(self):
                self.calls = []
            def add_sim_data(self, label, x, cap, ret):
                self.calls.append((label, x, cap, ret))

        plotter = _DummyPlotter()
        process_sol_list_with_custom_extractor(plotter, [], [], t_factor=50)
        self.assertEqual(plotter.calls, [])

    def test_none_sol_does_not_inject(self):
        class _DummyPlotter:
            def __init__(self):
                self.calls = []
            def add_sim_data(self, label, x, cap, ret):
                self.calls.append(label)

        plotter = _DummyPlotter()
        # get_discharge_capacity(None) returns empty → branch should skip add_sim_data
        # but log an error; we silence to keep test output clean.
        logging.getLogger("src.utils").setLevel(logging.CRITICAL)
        process_sol_list_with_custom_extractor(plotter, [None], ["x"], t_factor=50)
        self.assertEqual(plotter.calls, [])


class _FakeVar:
    def __init__(self, entries):
        self.entries = np.asarray(entries, dtype=float)


class _FakeCapStep:
    def __init__(self, current, throughput):
        self._d = {
            "Current [A]": _FakeVar(current),
            "Throughput capacity [A.h]": _FakeVar(throughput),
        }

    def __getitem__(self, key):
        return self._d[key]


class _FakeCapCycle:
    def __init__(self, steps):
        self.steps = steps


class _FakeCapSol:
    def __init__(self, cycles):
        self.cycles = cycles


class RetentionUnitTests(unittest.TestCase):
    """process_sol_list_with_custom_extractor 注入 0–1 小数保持率。"""

    def test_injects_fraction_with_second_cycle_baseline(self):
        sol = _FakeCapSol([
            _FakeCapCycle([_FakeCapStep([1.0, 1.0], [0.0, 0.5])]),
            _FakeCapCycle([_FakeCapStep([1.0, 1.0], [0.0, 0.4])]),
        ])

        calls = []

        class _DummyPlotter:
            def add_sim_data(self, label, x, cap, ret):
                calls.append((label, x, cap, ret))

        process_sol_list_with_custom_extractor(_DummyPlotter(), [sol], ["c"], t_factor=50)
        self.assertEqual(len(calls), 1)
        _, _, cap, ret = calls[0]
        # 基线为第 2 圈（conditioning 跳过约定），且为 0–1 小数（非百分制）
        np.testing.assert_allclose(cap, [0.5, 0.4])
        np.testing.assert_allclose(ret, [1.25, 1.0])


if __name__ == "__main__":
    unittest.main()
