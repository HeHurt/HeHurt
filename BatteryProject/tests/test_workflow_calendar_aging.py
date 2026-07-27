from __future__ import annotations

import pandas as pd
import pytest

from src.workflows import calendar_aging as calendar_module
from src.workflows.calendar_aging import CalendarAgingSpec


def _config(mode: str = "activated", run_mode: str = "smoke") -> dict:
    return {
        "cell": "MIC",
        "aging_mode": mode,
        "run_mode": run_mode,
        "modes": {
            "smoke": {
                "activated_months": 1,
                "unactivated_target_days": [1, 2],
            },
            "study": {
                "activated_months": 240,
                "max_storage_years": 20,
                "storage_interval_years": 1,
            },
        },
    }


def test_spec_builds_twenty_independent_year_targets():
    spec = CalendarAgingSpec.from_mapping(_config("unactivated", "study"))
    assert len(spec.unactivated_target_days) == 20
    assert spec.unactivated_target_days[0] == 365
    assert spec.unactivated_target_days[-1] == 20 * 365


def test_activated_protocol_has_one_reference_and_monthly_cycles():
    spec = CalendarAgingSpec.from_mapping(_config())
    cycles = calendar_module.build_activated_cycles(spec)
    assert len(cycles) == 2
    assert len(cycles[0]) == 3
    assert len(cycles[1]) == 5
    assert "Rest for 720 hour" in cycles[1][0]


def test_unactivated_protocol_is_endpoint_only():
    spec = CalendarAgingSpec.from_mapping(_config("unactivated"))
    cycles = calendar_module.build_unactivated_cycles(spec, 365)
    assert len(cycles) == 2
    assert len(cycles[1]) == 4
    assert "Rest for 8760 hour" in cycles[1][0]
    assert sum("Rest for" in step for cycle in cycles for step in cycle) == 1


def test_spec_rejects_unknown_mode():
    config = _config()
    config["aging_mode"] = "monthly"
    with pytest.raises(ValueError, match="aging_mode"):
        CalendarAgingSpec.from_mapping(config)


def test_workflow_runs_each_unactivated_horizon_independently(
    tmp_path,
    monkeypatch,
):
    spec = CalendarAgingSpec.from_mapping(_config("unactivated"))
    solved_targets = []

    def fake_solve(_spec, cycles):
        solved_targets.append(cycles[1][0])
        return object()

    def fake_extract(_solution, _spec, target_days):
        row = {
            "case": f"{target_days:g}_day",
            "storage_days": target_days,
            "storage_years": target_days / 365,
            "reference_capacity_ah": 100,
            "retained_capacity_ah": 99,
            "recovered_capacity_ah": 99.5,
            "retention_rate": 0.99,
            "recovery_rate": 0.995,
            "reversible_self_discharge_rate": 1 - 99 / 99.5,
            "irreversible_capacity_loss_rate": 0.005,
        }
        profile = pd.DataFrame({
            "case": [row["case"]],
            "storage_days": [target_days],
            "rest_time_h": [target_days * 24],
            "voltage_v": [3.4],
        })
        return row, profile

    monkeypatch.setattr(calendar_module, "_solve_case", fake_solve)
    monkeypatch.setattr(
        calendar_module,
        "extract_unactivated_result",
        fake_extract,
    )
    result = calendar_module.run_calendar_aging_workflow(
        spec,
        project_root=tmp_path / "BatteryProject",
        run_id="calendar_test",
    )
    assert len(solved_targets) == 2
    assert solved_targets[0] != solved_targets[1]
    assert result["metrics"]["storage_days"].tolist() == [1.0, 2.0]
    assert result["metrics_path"].is_file()
    assert result["rest_profiles_path"].is_file()


def test_unactivated_protocol_supports_half_p_diagnostics():
    config = _config("unactivated")
    config.update({
        "diagnostic_rate_p": 0.5,
        "nominal_capacity_ah": 587,
        "nominal_voltage_v": 3.2,
    })
    spec = CalendarAgingSpec.from_mapping(config)
    cycles = calendar_module.build_unactivated_cycles(spec, 30)
    assert "939.20W" in cycles[0][0]
    assert "939.20W" in cycles[0][1]
