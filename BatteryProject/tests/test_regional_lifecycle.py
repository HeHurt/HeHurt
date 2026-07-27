from types import SimpleNamespace

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from BatteryProject.src import simulation_regional_lifecycle as lifecycle
from BatteryProject.src.simulation import (
    RegionalPowerCycleResult,
    run_homogeneous_dfn_power_cycles,
    run_regional_dfn_power_cycles,
    solve_parallel_power_split,
)
from BatteryProject.src.plotting import plot_regional_negative_potential_analysis
from BatteryProject.src.simulation_regional_parallel import RegionalCellState, RegionalDFNConfig


def test_solve_parallel_power_split_discharge_charge_and_rest():
    identical = [
        RegionalCellState("a", 3.3, 0.002, 0.5),
        RegionalCellState("b", 3.3, 0.002, 0.5),
    ]
    discharge = solve_parallel_power_split(identical, 100.0)
    charge = solve_parallel_power_split(identical, -100.0)

    assert discharge.terminal_voltage_v * discharge.total_current_a == pytest.approx(100.0)
    assert charge.terminal_voltage_v * charge.total_current_a == pytest.approx(-100.0)
    assert discharge.region_currents_a["a"] == pytest.approx(discharge.region_currents_a["b"])
    assert charge.region_currents_a["a"] == pytest.approx(charge.region_currents_a["b"])

    mismatched = [
        RegionalCellState("a", 3.31, 0.002, 0.5),
        RegionalCellState("b", 3.29, 0.002, 0.5),
    ]
    rest = solve_parallel_power_split(mismatched, 0.0)
    assert rest.total_current_a == pytest.approx(0.0, abs=1e-12)
    assert sum(rest.region_currents_a.values()) == pytest.approx(0.0, abs=1e-12)
    assert rest.region_currents_a["a"] == pytest.approx(-rest.region_currents_a["b"])


def test_run_regional_power_cycles_smoke(monkeypatch):
    config = RegionalDFNConfig("whole", 1.0)
    runtime = SimpleNamespace(config=config, accepted_solution=object())
    monkeypatch.setattr(lifecycle, "_build_runtimes", lambda *args, **kwargs: {"whole": runtime})
    monkeypatch.setattr(lifecycle, "_snapshot_region_degradation", lambda *args, **kwargs: [])

    segment_calls = []

    def fake_advance(*args, **kwargs):
        segment_calls.append(kwargs["segment"])
        is_discharge = kwargs["segment"] == "discharge"
        is_charge = kwargs["segment"] == "charge"
        cycle = kwargs["cycle"]
        capacity_ah = (300.0 - 3.0 * (cycle - 1)) if is_discharge else (299.0 if is_charge else 0.0)
        return {
            "elapsed_s": 100.0,
            "global_time_s": kwargs["global_time_s"] + 100.0,
            "capacity_ah": capacity_ah,
            "energy_wh": capacity_ah * 3.2,
            "terminal_voltage_v": 2.5 if is_discharge else 3.65,
            "max_voltage_spread_v": 0.0,
            "max_abs_power_error_w": 0.0,
        }

    monkeypatch.setattr(lifecycle, "_advance_segment", fake_advance)
    result = run_regional_dfn_power_cycles(
        {"whole": object()},
        [config],
        discharge_power_w=502.4,
        cycles=2,
        equivalent_cycle_factor=50,
    )

    assert isinstance(result, RegionalPowerCycleResult)
    assert segment_calls == [
        "discharge",
        "rest_after_discharge",
        "charge",
        "rest_after_charge",
    ] * 2
    assert result.cycles()[1]["equivalent_cycle"] == pytest.approx(100.0)
    assert result.cycles()[1]["capacity_retention_pct"] == pytest.approx(99.0)


def test_run_regional_power_cycles_rejects_invalid_area_sum():
    with pytest.raises(ValueError, match="area fractions must sum to 1.0"):
        run_regional_dfn_power_cycles(
            {"a": object(), "b": object()},
            [RegionalDFNConfig("a", 0.4), RegionalDFNConfig("b", 0.5)],
            discharge_power_w=100.0,
            cycles=1,
        )

def test_solution_min_scalar_uses_full_spatial_time_field():
    variable = SimpleNamespace(entries=[[0.2, -0.03], [0.1, 0.0]])
    solution = {lifecycle.NEGATIVE_PLATING_OVERPOTENTIAL: variable}

    assert lifecycle._solution_min_scalar(
        solution, lifecycle.NEGATIVE_PLATING_OVERPOTENTIAL
    ) == pytest.approx(-0.03)
    assert lifecycle._solution_min_scalar(solution, "missing") != lifecycle._solution_min_scalar(
        solution, "missing"
    )


def test_plot_regional_negative_potential_analysis_uses_cycle_minimum():
    frame = pd.DataFrame(
        [
            {"segment": "charge", "sim_cycle": 1, "equivalent_cycle": 50, "region": "corner", "negative_surface_potential_difference_min_v": -0.02},
            {"segment": "charge", "sim_cycle": 1, "equivalent_cycle": 50, "region": "corner", "negative_surface_potential_difference_min_v": -0.03},
            {"segment": "charge", "sim_cycle": 1, "equivalent_cycle": 50, "region": "middle", "negative_surface_potential_difference_min_v": -0.01},
            {"segment": "discharge", "sim_cycle": 1, "equivalent_cycle": 50, "region": "top", "negative_surface_potential_difference_min_v": -0.50},
        ]
    )

    fig, _, regional, overall = plot_regional_negative_potential_analysis(frame)
    try:
        corner = regional.loc[regional["region"].eq("corner"), "negative_surface_potential_difference_min_v"].iloc[0]
        assert corner == pytest.approx(-0.03)
        assert overall["region"].iloc[0] == "corner"
        assert overall["negative_surface_potential_difference_min_v"].iloc[0] == pytest.approx(-0.03)
    finally:
        plt.close(fig)




def test_run_homogeneous_power_cycles_uses_native_experiment(monkeypatch):
    captured = {}

    class FakeParameters(dict):
        def copy(self):
            return FakeParameters(self)

        def update(self, values, check_already_exists=True):
            captured["parameter_update"] = dict(values)
            super().update(values)

    class FakeSimulation:
        def __init__(self, model, parameter_values, experiment, solver, var_pts):
            captured.update(
                model=model,
                parameter_values=parameter_values,
                experiment=experiment,
                solver=solver,
                var_pts=var_pts,
            )

        def solve(self, **kwargs):
            captured["solve_kwargs"] = kwargs
            return "native-solution"

    expected = RegionalPowerCycleResult((), (), (), (), (), {})
    monkeypatch.setattr(lifecycle.pybamm, "Experiment", lambda cycles, period: (cycles, period))
    monkeypatch.setattr(lifecycle.pybamm.lithium_ion, "DFN", lambda options: ("dfn", options))
    monkeypatch.setattr(lifecycle.pybamm, "IDAKLUSolver", lambda **kwargs: ("solver", kwargs))
    monkeypatch.setattr(lifecycle.pybamm, "Simulation", FakeSimulation)
    monkeypatch.setattr(lifecycle, "_convert_homogeneous_solution", lambda *args, **kwargs: expected)

    params = FakeParameters({"Nominal cell capacity [A.h]": 314.0})
    result = run_homogeneous_dfn_power_cycles(
        params,
        discharge_power_w=502.4,
        cycles=2,
        output_period_s=60,
    )

    assert result is expected
    assert captured["experiment"][1] == "60 seconds"
    assert len(captured["experiment"][0]) == 2
    assert "Discharge at 502.4 W until 2.5 V" in captured["experiment"][0][0]
    assert captured["solve_kwargs"] == {"initial_soc": 1.0, "showprogress": False}
    assert params == {"Nominal cell capacity [A.h]": 314.0}


def test_select_macro_step_uses_large_steps_away_from_cutoff():
    kwargs = {
        "segment": "discharge",
        "cutoff_v": 2.5,
        "minimum_step_s": 120.0,
        "maximum_step_s": 600.0,
        "adaptive_voltage_window_v": 0.15,
    }
    assert lifecycle._select_macro_step_s(terminal_voltage_v=3.2, **kwargs) == 600.0
    assert lifecycle._select_macro_step_s(terminal_voltage_v=2.60, **kwargs) == 240.0
    assert lifecycle._select_macro_step_s(terminal_voltage_v=2.54, **kwargs) == 120.0
    assert lifecycle._select_macro_step_s(
        segment="rest_after_discharge",
        terminal_voltage_v=2.5,
        cutoff_v=None,
        minimum_step_s=120.0,
        maximum_step_s=600.0,
        adaptive_voltage_window_v=0.15,
    ) == 600.0
