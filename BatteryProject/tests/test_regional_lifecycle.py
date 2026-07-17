from types import SimpleNamespace

import pytest

from BatteryProject.src import simulation_regional_lifecycle as lifecycle
from BatteryProject.src.simulation import (
    RegionalPowerCycleResult,
    run_regional_dfn_power_cycles,
    solve_parallel_power_split,
)
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
