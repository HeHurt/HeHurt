"""Tests for the headless canonical lifecycle heat workflow."""

from pathlib import Path
import os
import subprocess

import numpy as np
import pandas as pd
import pytest

from src.lifecycle_heat_reporting import append_unconstrained_trend_extrapolation
from src.workflows import lifecycle_heat as lifecycle_heat_module
from src.workflows.lifecycle_heat import (
    LifecycleHeatWorkflowSpec,
    build_feature_parity_table,
    run_lifecycle_heat_workflow,
)


def _config(run_mode="smoke"):
    return {
        "cell": "587Ah",
        "run_mode": run_mode,
        "conditions": [
            {
                "temperature_c": 25,
                "aging_p_rate": 0.5,
                "diagnostic_p_rates": [0.25, 0.5],
            }
        ],
        "contact_resistances": [{"label": "R_low", "resistance_mohm": 0.056276}],
        "soh_targets_pct": [100, 95, 90],
        "entropy": {
            "query": {
                "cell": "AI_virtual_cell",
                "kind": "raw",
                "format": "csv",
                "path_contains": "entropy_coefficient_fits_by_branch.csv",
            },
            "sample_label": "SOH95%",
            "equilibrium_charge_weight": 0.31,
            "source_note": "test entropy",
        },
        "modes": {
            "smoke": {"total_cycles": 1, "aging_t_factor": 1, "cycles_per_block": 1},
            "study": {"total_cycles": 20000, "aging_t_factor": 50, "cycles_per_block": 1},
        },
    }


def test_lifecycle_heat_spec_uses_selected_mode():
    smoke = LifecycleHeatWorkflowSpec.from_mapping(_config("smoke"))
    study = LifecycleHeatWorkflowSpec.from_mapping(_config("study"))
    assert smoke.total_cycles == 1
    assert smoke.aging_t_factor == 1
    assert study.total_cycles == 20000
    assert study.aging_t_factor == 50


def test_lifecycle_heat_spec_rejects_unsorted_soh_targets():
    config = _config()
    config["soh_targets_pct"] = [95, 100]
    with pytest.raises(ValueError, match="sorted descending"):
        LifecycleHeatWorkflowSpec.from_mapping(config)


def test_feature_parity_table_keeps_required_capabilities():
    table = build_feature_parity_table()
    combined = "\n".join(table["功能"].astype(str).tolist() + table["canonical实现"].astype(str).tolist())
    for required in ("多电芯", "多温度", "多倍率", "多接触电阻", "SOH 诊断", "entropy", "checkpoint", "趋势外推", "中文 Excel"):
        assert required in combined


def test_trend_extrapolation_marks_missing_lower_soh():
    actual = pd.DataFrame(
        {
            "target_soh_pct": [100.0, 95.0],
            "actual_soh_pct": [100.0, 95.0],
            "real_cycle": [1.0, 100.0],
            "diagnostic_p_rate": [0.5, 0.5],
            "temperature_c": [25.0, 25.0],
            "aging_p_rate": [0.5, 0.5],
            "contact_resistance_mohm": [0.05, 0.05],
            "data_source": ["仿真实际点", "仿真实际点"],
            "calibrated_total_charge_w": [10.0, 12.0],
            "calibrated_total_discharge_w": [11.0, 13.0],
        }
    )
    completed = append_unconstrained_trend_extrapolation(actual, [100, 95, 90], [0.5])
    extrapolated = completed.loc[completed["target_soh_pct"].eq(90.0)].iloc[0]
    assert extrapolated["data_source"] == "趋势外推"
    assert np.isfinite(extrapolated["calibrated_total_charge_w"])


def test_run_lifecycle_heat_workflow_writes_standard_artifacts(tmp_path, monkeypatch):
    spec = LifecycleHeatWorkflowSpec.from_mapping(_config())
    entropy_file = tmp_path / "entropy.csv"
    entropy_file.write_text(
        "sample_label,branch,soc_target,dudt_v_per_k\n"
        "SOH95%,充电支路,0,0.0\n"
        "SOH95%,充电支路,100,0.0\n"
        "SOH95%,放电支路,0,0.0\n"
        "SOH95%,放电支路,100,0.0\n",
        encoding="utf-8",
    )

    def fake_load_params(_cell):
        return lambda _factor, temperature=298.15: {
            "Nominal cell capacity [A.h]": 587.0,
            "Negative electrode lithiation OCP [V]": lambda x: x,
            "Negative electrode delithiation OCP [V]": lambda x: x,
            "Positive electrode lithiation OCP [V]": lambda x: x,
            "Positive electrode delithiation OCP [V]": lambda x: x,
        }

    def fake_run(*_args, **_kwargs):
        diagnostic_df = pd.DataFrame(
            {
                "target_soh_pct": [100.0],
                "actual_soh_pct": [100.0],
                "real_cycle": [1.0],
                "diagnostic_p_rate": [0.5],
                "diagnostic_status": ["simulated"],
                "diagnostic_error": [""],
                "q_sei_ah": [0.1],
                "q_sei_on_cracks_ah": [0.0],
                "q_plating_ah": [0.0],
                "lam_neg_ah": [0.0],
            }
        )
        return {
            "results": {
                "lifecycle_heat": {
                    "diagnostic_df": diagnostic_df,
                    "diagnostic_solutions": [],
                    "run_status": "completed",
                    "last_valid_soh_pct": 100.0,
                    "pending_diagnostic_soh_targets_pct": [],
                    "failure_message": "",
                    "solutions": [],
                    "solution_real_cycles": [],
                }
            },
            "summary_df": pd.DataFrame(),
        }

    monkeypatch.setattr(lifecycle_heat_module, "load_params", fake_load_params)
    monkeypatch.setattr(lifecycle_heat_module, "resolve_entropy_file", lambda *_args, **_kwargs: entropy_file)
    monkeypatch.setattr(lifecycle_heat_module, "run_pulse_lifecycle_scenarios", fake_run)
    result = run_lifecycle_heat_workflow(
        spec,
        project_root=tmp_path / "BatteryProject",
        workspace_root=tmp_path,
        run_id="test_run",
    )
    assert result["metrics_path"].is_file()
    assert result["artifact_manifest"].is_file()
    assert (result["context"].run_dir / "config.json").is_file()
    assert list(Path(result["context"].artifacts_dir).glob("**/*.xlsx"))


def test_lifecycle_heat_canonical_notebook_contract():
    import json

    notebook_path = Path(__file__).parents[1] / "examples" / "workflows" / "全生命周期产热.ipynb"
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
    for heading in ("Feature parity", "SOH诊断", "趋势外推", "中文Excel", "绘图"):
        assert heading in combined
    assert "DatasetQuery" in combined
    assert "def " not in "\n".join(
        source for source, cell in zip(sources, notebook["cells"]) if cell["cell_type"] == "code"
    )
