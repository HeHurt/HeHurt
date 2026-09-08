from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.workflows import calendar_aging_half_soc as half_soc_module
from src.workflows.calendar_aging import CalendarAgingSpec
from src.workflows.calendar_aging_half_soc import (
    AGING_T_FACTOR,
    HalfSocBaseline,
    build_final_test_steps,
    build_half_soc_metric_row,
)


def _spec() -> CalendarAgingSpec:
    return CalendarAgingSpec.from_mapping({
        "cell": "587",
        "aging_mode": "unactivated",
        "temperature_c": 0,
        "diagnostic_rate_p": 0.5,
        "nominal_capacity_ah": 587,
        "nominal_voltage_v": 3.2,
        "unactivated_target_days": [30],
        "return_solutions": False,
    })


def _baseline() -> HalfSocBaseline:
    return HalfSocBaseline(
        solution=object(),
        c0_ah=600.0,
        target_half_c0_ah=300.0,
        charged_to_storage_ah=300.0,
        test_temperature_c=25.0,
    )


def test_aging_factor_is_one():
    assert AGING_T_FACTOR == 1.0


def test_final_test_is_fixed_at_25c_with_one_hour_relaxation():
    steps = build_final_test_steps(_spec(), test_temperature_c=25, relaxation_hours=1)
    assert len(steps) == 4
    assert all(step.temperature == 298.15 for step in steps)
    assert steps[0].duration == 3600


def test_half_soc_metrics_use_separate_denominators():
    row = build_half_soc_metric_row(
        storage_temperature_c=50,
        storage_days=420,
        baseline=_baseline(),
        retained_capacity_ah=285,
        recovered_capacity_ah=570,
        days_per_year=365,
        relaxation_hours=1,
    )
    assert row["retention_rate"] == 0.95
    assert row["retained_capacity_vs_c0_rate"] == 0.475
    assert row["recovery_rate"] == 0.95
    assert row["aging_t_factor"] == 1.0


def test_case_workflow_writes_metrics(tmp_path, monkeypatch):
    expected = build_half_soc_metric_row(
        storage_temperature_c=0,
        storage_days=30,
        baseline=_baseline(),
        retained_capacity_ah=299,
        recovered_capacity_ah=598,
        days_per_year=365,
        relaxation_hours=1,
    )
    monkeypatch.setattr(
        half_soc_module,
        "run_half_soc_storage_case",
        lambda *_args, **_kwargs: (expected, object()),
    )
    result = half_soc_module.run_half_soc_case_workflow(
        _spec(),
        storage_days=30,
        baseline=_baseline(),
        project_root=tmp_path / "BatteryProject",
        run_id="half_soc_test",
    )
    assert result["metrics_path"].is_file()
    saved = pd.read_csv(result["metrics_path"])
    assert saved.iloc[0]["retention_rate"] == pytest.approx(
        expected["retention_rate"]
    )
    assert result["solution"] is None
    assert (Path(result["context"].run_dir) / "config.json").is_file()
