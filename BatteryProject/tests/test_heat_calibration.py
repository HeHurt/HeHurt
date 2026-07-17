from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.heat_calibration import (
    blend_ocp_functions,
    build_calibrated_parameter_loader,
    build_hysteresis_equilibrium_overrides,
    compute_cycle_calibrated_heat,
    compute_reference_reversible_heat,
    fit_hysteresis_allocation,
    load_branch_entropy_curves,
)


class _Variable:
    def __init__(self, entries):
        self.entries = np.asarray(entries, dtype=float)


class _Step(dict):
    def __getitem__(self, key):
        return _Variable(super().__getitem__(key))


class _Cycle:
    def __init__(self, steps):
        self.steps = steps


def test_load_branch_entropy_curves(tmp_path):
    path = tmp_path / "entropy.csv"
    pd.DataFrame(
        {
            "sample_label": ["SOH95%"] * 4,
            "branch": ["充电支路", "充电支路", "放电支路", "放电支路"],
            "soc_target": [0, 100, 0, 100],
            "dudt_v_per_k": [-2e-4, 1e-5, -5e-5, 8e-5],
        }
    ).to_csv(path, index=False)

    curves = load_branch_entropy_curves(path)

    assert set(curves) == {"charge", "discharge"}
    assert curves["charge"][1][0] == pytest.approx(-2e-4)


def test_build_hysteresis_equilibrium_overrides_blends_branches():
    params = {
        "Negative electrode lithiation OCP [V]": lambda sto: 0.2 + sto,
        "Negative electrode delithiation OCP [V]": lambda sto: 0.1 + sto,
        "Positive electrode lithiation OCP [V]": lambda sto: 3.2 + sto,
        "Positive electrode delithiation OCP [V]": lambda sto: 3.4 + sto,
    }

    overrides = build_hysteresis_equilibrium_overrides(params, 0.25)

    assert overrides["Negative electrode OCP [V]"](0.5) == pytest.approx(0.625)
    assert overrides["Positive electrode OCP [V]"](0.5) == pytest.approx(3.75)
    with pytest.raises(ValueError):
        blend_ocp_functions(lambda x: x, lambda x: x, 1.1)

    loader = build_calibrated_parameter_loader(lambda: params, 0.25)
    loaded = loader()
    assert loaded["Positive electrode OCP [V]"](0.5) == pytest.approx(3.75)


def test_compute_reference_reversible_heat_respects_branch_and_current_sign():
    step = _Step(
        {
            "Time [s]": [0, 1, 2],
            "Current [A]": [-10, -10, -10],
            "Volume-averaged cell temperature [K]": [300, 300, 300],
            "Throughput capacity [A.h]": [0, 0.5, 1.0],
        }
    )
    curves = {
        "charge": (np.array([0, 100]), np.array([-1e-4, -1e-4])),
        "discharge": (np.array([0, 100]), np.array([2e-4, 2e-4])),
    }

    assert compute_reference_reversible_heat(step, "charge", curves) == pytest.approx(0.3)


def test_fit_hysteresis_allocation_recovers_shared_weight():
    result = fit_hysteresis_allocation(
        {"charge": 8.0, "discharge": 10.0},
        {"charge": 10.0, "discharge": 10.0},
        {"charge": 15.0, "discharge": 13.0},
    )

    assert result["charge_weight"] == pytest.approx(0.3)
    assert result["predicted_heat_w"]["charge"] == pytest.approx(15.0)
    assert result["predicted_heat_w"]["discharge"] == pytest.approx(13.0)
    assert result["within_10pct"] is True


def test_compute_cycle_calibrated_heat_uses_internal_and_reference_terms():
    common = {
        "Time [s]": [0, 1, 2],
        "Volume-averaged cell temperature [K]": [300, 300, 300],
        "Throughput capacity [A.h]": [0, 0.5, 1.0],
        "Ohmic heating [W]": [1, 1, 1],
        "Irreversible electrochemical heating [W]": [2, 2, 2],
        "Heat of mixing [W]": [0, 0, 0],
        "Lumped contact resistance heating [W]": [0.5, 0.5, 0.5],
    }
    charge_step = _Step(
        {
            **common,
            "Current [A]": [-10, -10, -10],
            "Hysteresis electrochemical heating [W]": [3, 3, 3],
        }
    )
    discharge_step = _Step(
        {
            **common,
            "Current [A]": [10, 10, 10],
            "Hysteresis electrochemical heating [W]": [1, 1, 1],
        }
    )
    curves = {
        "charge": (np.array([0, 100]), np.array([-1e-4, -1e-4])),
        "discharge": (np.array([0, 100]), np.array([2e-4, 2e-4])),
    }

    result = compute_cycle_calibrated_heat(
        _Cycle([charge_step, discharge_step]),
        curves,
        contact_resistance_ohm=5e-3,
    )

    assert result["calibrated_total_charge_w"] == pytest.approx(6.8)
    assert result["calibrated_total_discharge_w"] == pytest.approx(5.1)
