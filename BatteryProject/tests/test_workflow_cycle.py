"""Tests for the headless canonical cycle-aging workflow."""

import pandas as pd
import pytest

from src.workflows import cycle as cycle_module
from src.workflows.cycle import CycleWorkflowSpec, run_cycle_workflow


def _config(run_mode="smoke"):
    return {
        "cell": "587Ah",
        "conditions": [{"temperature_c": 25, "rate_p": 0.25}],
        "run_mode": run_mode,
        "modes": {
            "smoke": {"total_cycles": 1, "aging_t_factor": 1},
            "study": {"total_cycles": 1400, "aging_t_factor": 50, "cycles_per_block": 20},
        },
    }


def test_cycle_spec_uses_selected_mode():
    smoke = CycleWorkflowSpec.from_mapping(_config("smoke"))
    study = CycleWorkflowSpec.from_mapping(_config("study"))
    assert smoke.total_cycles == 1
    assert smoke.aging_t_factor == 1
    assert study.total_cycles == 1400
    assert study.cycles_per_block == 20


def test_cycle_spec_rejects_empty_conditions():
    config = _config()
    config["conditions"] = []
    with pytest.raises(ValueError, match="at least one"):
        CycleWorkflowSpec.from_mapping(config)


def test_run_cycle_workflow_writes_standard_artifacts(tmp_path, monkeypatch):
    spec = CycleWorkflowSpec.from_mapping(_config())

    def fake_load_params(_cell):
        return lambda _factor, _temperature: {"Nominal cell capacity [A.h]": 587.0}

    def fake_run(*_args, **_kwargs):
        frame = pd.DataFrame({
            "real_cycle": [1],
            "discharge_capacity_ah": [586.0],
            "capacity_retention": [1.0],
        })
        return {"results": {"base_cycle": {"main_df": frame}}}

    monkeypatch.setattr(cycle_module, "load_params", fake_load_params)
    monkeypatch.setattr(cycle_module, "run_pulse_lifecycle_scenarios", fake_run)
    result = run_cycle_workflow(
        spec,
        project_root=tmp_path / "BatteryProject",
        workspace_root=tmp_path,
        run_id="test_run",
    )
    assert result["metrics_path"].is_file()
    assert (result["context"].run_dir / "config.json").is_file()
    assert result["metrics"].iloc[0]["label"] == "25°C 0.25P"
    assert result["analysis_solutions"] == []
    assert result["analysis_labels"] == []
    assert result["reference_params"] is None



def test_prepare_cycle_experiment_reads_registered_dat(tmp_path, monkeypatch):
    config = _config()
    config["experiment"] = {
        "loader": "lifecycle_dat",
        "query": {"cell": "587Ah", "format": "dat", "require_unique": True},
    }
    spec = CycleWorkflowSpec.from_mapping(config)
    source = tmp_path / "registered.dat"
    source.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(
        cycle_module.DatasetQuery,
        "resolve",
        lambda _self, _root: [{"absolute_path": str(source)}],
    )
    expected = [{"label": "587Ah 25°C 0.25P"}]
    monkeypatch.setattr(cycle_module, "load_lifecycle_dat", lambda *_args, **_kwargs: expected)
    data, resolved = cycle_module.prepare_cycle_experiment(spec, workspace_root=tmp_path)
    assert data == expected
    assert resolved == source


def test_prepare_cycle_experiment_reads_registered_cycling_folder(tmp_path, monkeypatch):
    config = _config()
    config["experiment"] = {
        "loader": "cycling_folder",
        "query": {"cell": "587Ah", "format": "csv", "require_unique": False},
    }
    spec = CycleWorkflowSpec.from_mapping(config)
    folder = tmp_path / "cycling"
    folder.mkdir()
    sources = [folder / "a.csv", folder / "b.csv"]
    monkeypatch.setattr(
        cycle_module.DatasetQuery,
        "resolve",
        lambda _self, _root: [{"absolute_path": str(source)} for source in sources],
    )
    monkeypatch.setattr(
        cycle_module,
        "load_cycling_folder",
        lambda resolved_folder: [{"source_file": resolved_folder}],
    )
    data, processed = cycle_module.prepare_cycle_experiment(spec, workspace_root=tmp_path)
    assert data == [{"source_file": str(folder)}]
    assert processed is None
