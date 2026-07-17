"""Smoke tests for src/electrolyte_dryout.py — initialization & state plumbing.

The ``update()`` path needs a real PyBaMM solution and is left for integration
tests. Here we cover the constructor: parameter ingestion, history seeding,
and the ``enabled`` flag.
"""

import contextlib
import io
import unittest

import numpy as np

from src.electrolyte_dryout import DryoutTracker, _apply_porosity_factors_to_state


def _make_stub_params(**overrides):
    """Minimal ParameterValues-compatible dict (supports __getitem__, update, get)."""
    base = {
        "Negative electrode thickness [m]": 85e-6,
        "Positive electrode thickness [m]": 75e-6,
        "Separator thickness [m]": 20e-6,
        "Electrode width [m]": 0.5,
        "Electrode height [m]": 0.3,
        "Negative electrode porosity": 0.3,
        "Positive electrode porosity": 0.3,
        "Separator porosity": 0.5,
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,
        # EC initial / Bulk solvent are optional — leave one out to exercise .get fallback
        "Bulk solvent concentration [mol.m-3]": 4541.0,
    }
    base.update(overrides)
    return base


def _silent_init(params, **kwargs):
    """Suppress DryoutTracker's print() during construction."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return DryoutTracker(params, **kwargs)


class DryoutTrackerInitTests(unittest.TestCase):
    def test_enabled_when_excess_ratio_ge_one(self):
        params = _make_stub_params()
        tracker = _silent_init(params, excess_ratio=1.2)
        self.assertTrue(tracker.enabled)

    def test_disabled_when_excess_ratio_below_one(self):
        params = _make_stub_params()
        tracker = _silent_init(params, excess_ratio=0.9)
        self.assertFalse(tracker.enabled)

    def test_history_seeded_with_expected_keys(self):
        params = _make_stub_params()
        tracker = _silent_init(params)
        for key in (
            "Vol_Elely_Tot", "Vol_Elely_JR", "Vol_Pore_tot",
            "Ratio_Dryout", "Ratio_CeEC", "Ratio_CeLi",
            "Width", "Vol_EC_consumed", "Vol_Elely_need",
            "Vol_Elely_add", "Vol_Pore_decrease",
            "c_e_reservoir", "c_EC_reservoir",
        ):
            self.assertIn(key, tracker.history)
            self.assertEqual(len(tracker.history[key]), 1, f"{key} should be seeded with one entry")

    def test_initial_volumes_match_geometry(self):
        params = _make_stub_params()
        tracker = _silent_init(params, excess_ratio=1.5)
        # pore_vol = (L_n*eps_n + L_p*eps_p + L_s*eps_s) * L_y * L_z
        expected_pore = (85e-6 * 0.3 + 75e-6 * 0.3 + 20e-6 * 0.5) * 0.5 * 0.3
        self.assertAlmostEqual(tracker._vol_jr, expected_pore)
        self.assertAlmostEqual(tracker._vol_tot, expected_pore * 1.5)

    def test_params_get_injected_after_init(self):
        params = _make_stub_params()
        _silent_init(params)
        # Constructor side-effect: dry-out tracking keys should be present
        for key in (
            "Current total electrolyte volume in whole cell [m3]",
            "Current total electrolyte volume in jelly roll [m3]",
            "Current solvent concentration in the reservoir [mol.m-3]",
            "Current electrolyte concentration in the reservoir [mol.m-3]",
            "Ratio of electrolyte dry out in jelly roll",
            "Initial Electrode width [m]",
        ):
            self.assertIn(key, params)

    def test_ec_initial_falls_back_to_bulk_solvent(self):
        # No "EC initial concentration" provided → falls back to Bulk solvent
        params = _make_stub_params()
        tracker = _silent_init(params)
        self.assertAlmostEqual(tracker.history["c_EC_reservoir"][0], 4541.0)


class ApplyPorosityFactorsTests(unittest.TestCase):
    def test_scales_porosity_times_concentration_states(self):
        state = {
            "Negative electrode porosity times concentration [mol.m-3]": np.array([1000.0, 1000.0]),
            "Separator porosity times concentration [mol.m-3]": np.array([1000.0]),
            "Negative electrolyte potential [V]": np.array([0.1]),
        }

        _apply_porosity_factors_to_state(
            state,
            {"negative electrode": 0.9, "separator": 0.8, "positive electrode": 0.7},
        )

        np.testing.assert_allclose(
            state["Negative electrode porosity times concentration [mol.m-3]"],
            [900.0, 900.0],
        )
        np.testing.assert_allclose(
            state["Separator porosity times concentration [mol.m-3]"], [800.0]
        )
        # 不在状态里的正极键被跳过；无关键不受影响
        np.testing.assert_allclose(state["Negative electrolyte potential [V]"], [0.1])


if __name__ == "__main__":
    unittest.main()
