"""Unit tests for src/swelling_coupling.py (fake solutions, no solver needed)."""

import unittest
import numpy as np

from src.swelling_coupling import (
    POROSITY_PARAM_KEYS,
    SwellingCoupler,
)


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


def _coupler_params():
    return {
        "Negative electrode thickness [m]": 1.0,
        "Positive electrode thickness [m]": 1.0,
        "Initial concentration in negative electrode [mol.m-3]": 0.0,
        "Initial concentration in positive electrode [mol.m-3]": 0.0,
        "Electrode width [m]": 2.0,
        "Electrode height [m]": 0.5,
        "Negative electrode porosity": 0.3,
        "Separator porosity": 0.5,
        "Positive electrode porosity": 0.3,
    }


def _sol(cn_end):
    cn = np.array([0.0, cn_end])
    cycle = _FakeCycle({
        "X-averaged negative particle concentration [mol.m-3]": _FakeVariable(cn),
        "X-averaged positive particle concentration [mol.m-3]": _FakeVariable(np.zeros_like(cn)),
    })
    return _FakeSolution([cycle])


class SwellingCouplerTests(unittest.TestCase):
    def _make(self, params, K=100.0):
        # omega_n=3, L_n=1 -> 位移 = c̄_n；面积 = 2*0.5 = 1 m² -> P = F
        return SwellingCoupler(
            params,
            k_stiffness=1.0,
            preload_force=0.0,
            omega_n=3.0,
            expansion_function_n=None,
            expansion_function_p=None,
            compaction_moduli={d: K for d in POROSITY_PARAM_KEYS},
            max_step_compression=0.5,
        )

    def test_update_compresses_porosity_params(self):
        params = _coupler_params()
        coupler = self._make(params, K=100.0)

        factors = coupler.update(_sol(3.0), params)

        # EOC 位移 3 -> 力 3 N -> 面压 3 Pa, ΔP = 3 -> factor = 1 - 3/100
        for domain in POROSITY_PARAM_KEYS:
            self.assertAlmostEqual(factors[domain], 0.97)
        self.assertAlmostEqual(params["Separator porosity"], 0.5 * 0.97)
        self.assertAlmostEqual(params["Negative electrode porosity"], 0.3 * 0.97)

    def test_repeat_update_with_same_force_is_identity(self):
        params = _coupler_params()
        coupler = self._make(params)
        coupler.update(_sol(3.0), params)

        factors = coupler.update(_sol(3.0), params)

        for domain in POROSITY_PARAM_KEYS:
            self.assertAlmostEqual(factors[domain], 1.0)

    def test_pressure_drop_recovers_porosity(self):
        params = _coupler_params()
        coupler = self._make(params)
        coupler.update(_sol(3.0), params)
        eps_compressed = params["Separator porosity"]

        coupler.update(_sol(0.0), params)  # 力回落到 0（单边接触钳制）

        self.assertGreater(params["Separator porosity"], eps_compressed)

    def test_step_compression_clipped(self):
        params = _coupler_params()
        coupler = self._make(params, K=1.0)  # 1 - 3/1 = -2 -> 钳到下限 0.5

        factors = coupler.update(_sol(3.0), params)

        self.assertAlmostEqual(factors["separator"], 0.5)

    def test_empty_solution_returns_no_factors(self):
        params = _coupler_params()
        coupler = self._make(params)

        factors = coupler.update(_FakeSolution([]), params)

        self.assertEqual(factors, {})
        self.assertAlmostEqual(params["Separator porosity"], 0.5)

    def test_history_tracks_force_and_porosity(self):
        params = _coupler_params()
        coupler = self._make(params)
        coupler.update(_sol(3.0), params)

        self.assertEqual(len(coupler.history["eoc_force_n"]), 2)
        self.assertAlmostEqual(coupler.history["eoc_force_n"][-1], 3.0)
        self.assertAlmostEqual(coupler.history["pressure_pa"][-1], 3.0)
        self.assertAlmostEqual(
            coupler.history["porosity_separator"][-1],
            params["Separator porosity"],
        )


if __name__ == "__main__":
    unittest.main()
