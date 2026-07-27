"""Tests for the canonical regional coupled-aging workflow."""

from pathlib import Path
import json
import os
import subprocess
from types import SimpleNamespace

import src.workflows.regional_coupled_aging as regional


def _config(run_mode="smoke"):
    return {
        "cell": "314Ah",
        "run_mode": run_mode,
        "area_fractions": {"A_corner": 0.1, "B_middle": 0.7, "C_top": 0.2},
        "nominal_capacity_ah": 314.0,
        "reduced_network": {
            "base_ocv_v": 3.3,
            "base_resistance_ohm": 0.001,
            "current_c_rate": 1.0,
            "sweep_multipliers": [1, 20],
        },
        "modes": {
            "smoke": {
                "transient_dfn": {"enabled": False},
                "lifecycle": {"enabled": False},
            },
            "study": {
                "transient_dfn": {"enabled": True, "duration_s": 60, "macro_step_s": 60},
                "lifecycle": {"enabled": True, "cycles": 1},
            },
        },
    }


def test_spec_uses_mode_overrides_and_keeps_independent_workflow_id():
    smoke = regional.RegionalCoupledAgingWorkflowSpec.from_mapping(_config("smoke"))
    study = regional.RegionalCoupledAgingWorkflowSpec.from_mapping(_config("study"))

    assert regional.WORKFLOW_ID == "regional_coupled_aging"
    assert smoke.transient_dfn.enabled is False
    assert smoke.lifecycle.enabled is False
    assert study.transient_dfn.enabled is True
    assert study.lifecycle.enabled is True


def test_feature_parity_keeps_required_regional_capabilities():
    table = regional.build_feature_parity_table()
    combined = "\n".join(table["功能"].astype(str).tolist() + table["canonical实现"].astype(str).tolist())
    for required in ("OCV+R", "局部堵塞", "区域DFN", "区域电流", "生命周期", "孔隙率", "DatasetQuery", "PSD独立"):
        assert required in combined


def test_reduced_network_smoke_writes_standard_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(regional, "load_params", lambda _cell: lambda *_args, **_kwargs: {"Nominal cell capacity [A.h]": 314.0})

    spec = regional.RegionalCoupledAgingWorkflowSpec.from_mapping(_config("smoke"))
    result = regional.run_regional_coupled_aging_workflow(
        spec,
        project_root=tmp_path,
        workspace_root=tmp_path,
        run_id="smoke",
    )

    assert result["context"].run_dir == tmp_path / "output" / "runs" / "regional_coupled_aging" / "smoke"
    assert (result["context"].run_dir / "config.json").is_file()
    assert result["metrics_path"].is_file()
    assert result["artifact_paths"]["reduced_network_cases"].is_file()
    assert result["artifact_paths"]["excel"].is_file()
    cases = result["reduced_network"]["case_df"]
    healthy_a = cases.query("case == 'healthy' and region == 'A_corner'")["current_a"].iloc[0]
    blocked_a = cases.query("case == 'A_blocked_x20' and region == 'A_corner'")["current_a"].iloc[0]
    assert blocked_a < healthy_a


def test_transient_and_lifecycle_sections_call_existing_runners(tmp_path, monkeypatch):
    calls = {"transient": 0, "regional_lifecycle": 0, "homogeneous": 0}

    monkeypatch.setattr(regional, "load_params", lambda _cell: lambda *_args, **_kwargs: {"Nominal cell capacity [A.h]": 314.0})
    monkeypatch.setattr(regional, "_fresh_parameter_values", lambda *_args, **_kwargs: {"Nominal cell capacity [A.h]": 314.0})

    def fake_transient(*_args, **_kwargs):
        calls["transient"] += 1
        return SimpleNamespace(
            steps=lambda: [{"region": "A_corner", "current_a": 1.0, "voltage_spread_v": 0.0}],
            iterations=lambda: [{"region": "A_corner", "iteration": 1, "converged": True}],
        )

    def fake_regional_lifecycle(*_args, **_kwargs):
        calls["regional_lifecycle"] += 1
        return SimpleNamespace(
            steps=lambda: [{"region": "A_corner", "segment": "discharge"}],
            cycles=lambda: [{"sim_cycle": 1, "capacity_retention_pct": 100.0}],
            degradation=lambda: [{"region": "A_corner", "stage": "discharge_end"}],
            iterations=lambda: [{"iteration": 1, "converged": True}],
        )

    def fake_homogeneous(*_args, **_kwargs):
        calls["homogeneous"] += 1
        return SimpleNamespace(cycles=lambda: [{"sim_cycle": 1, "capacity_retention_pct": 100.0}])

    monkeypatch.setattr(regional, "run_regional_dfn_coupling", fake_transient)
    monkeypatch.setattr(regional, "run_regional_dfn_power_cycles", fake_regional_lifecycle)
    monkeypatch.setattr(regional, "run_homogeneous_dfn_power_cycles", fake_homogeneous)

    spec = regional.RegionalCoupledAgingWorkflowSpec.from_mapping(_config("study"))
    result = regional.run_regional_coupled_aging_workflow(
        spec,
        project_root=tmp_path,
        workspace_root=tmp_path,
        run_id="study",
    )

    assert calls == {"transient": 2, "regional_lifecycle": 2, "homogeneous": 1}
    assert not result["transient_dfn"]["steps_df"].empty
    assert not result["lifecycle"]["cycles_df"].empty
    assert result["artifact_paths"]["lifecycle_cycles"].is_file()


def test_dataset_query_config_is_preserved():
    config = _config()
    config["datasets"] = [
        {
            "temperature_c": 25,
            "test_type": "区域并联",
            "kind": "processed",
            "format": ".csv",
            "path_contains": "regional",
            "require_unique": False,
        }
    ]
    spec = regional.RegionalCoupledAgingWorkflowSpec.from_mapping(config)

    assert len(spec.datasets) == 1
    assert spec.datasets[0].cell == "314Ah"
    assert spec.datasets[0].test_type == "区域并联"
    assert spec.datasets[0].require_unique is False


def test_regional_coupled_aging_canonical_notebook_contract():
    notebook_path = Path(__file__).parents[1] / "examples" / "workflows" / "区域并联耦合老化.ipynb"
    code_exe = Path("D:/软件安装/Microsoft VS Code/Code.exe")
    env = {**os.environ, "ELECTRON_RUN_AS_NODE": "1"}
    raw = subprocess.check_output(
        [str(code_exe), "-e", f"console.log(require('fs').readFileSync({str(notebook_path)!r}, 'utf8'))"],
        text=True,
        encoding="utf-8",
        env=env,
    )
    notebook = json.loads(raw)
    sources = ["".join(cell.get("source", [])) for cell in notebook["cells"]]
    combined = "\n".join(sources)
    parameter_cells = [
        cell for cell in notebook["cells"]
        if cell["cell_type"] == "code" and cell.get("metadata", {}).get("tags") == ["parameters"]
    ]

    assert len(parameter_cells) == 1
    assert "CONFIG" in "".join(parameter_cells[0]["source"])
    assert "regional_coupled_aging" in combined
    for heading in ("Feature parity", "OCV+R", "区域DFN", "生命周期", "孔隙率", "负极电位", "Artifact"):
        assert heading in combined
    assert "DatasetQuery" in combined
    assert "粒径分布" not in combined
    code_sources = "\n".join(
        source for source, cell in zip(sources, notebook["cells"]) if cell["cell_type"] == "code"
    )
    assert "def " not in code_sources
