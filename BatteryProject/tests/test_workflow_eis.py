"""Tests for the headless canonical EIS workflow."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.workflows import eis as eis_module
from src.workflows.eis import EisWorkflowSpec, run_eis_workflow


def _config(run_mode="smoke"):
    return {
        "cell": "MIC",
        "run_mode": run_mode,
        "base_temperature_c": 25,
        "base_soc": 0.5,
        "soc_sweep": [0.2, 0.5, 0.8],
        "temperature_sweep_c": [0, 25, 45],
        "quick_frequencies_hz": [1e3, 10, 1],
        "lifecycle_frequencies_hz": [1e3, 10, 1],
        "modes": {
            "smoke": {
                "run_quick_eis": True,
                "run_soc_sweep": True,
                "run_temperature_sweep": True,
                "run_lifecycle": True,
                "lifecycle": {"aging_cycles": 1, "aging_t_factor": 1, "target_soh_levels": [100]},
            },
            "study": {
                "run_quick_eis": True,
                "run_soc_sweep": True,
                "run_temperature_sweep": True,
                "run_lifecycle": True,
                "lifecycle": {"aging_cycles": 20, "aging_t_factor": 50, "target_soh_levels": [100, 95, 90]},
            },
        },
    }


def test_eis_spec_uses_selected_mode():
    smoke = EisWorkflowSpec.from_mapping(_config("smoke"))
    study = EisWorkflowSpec.from_mapping(_config("study"))
    assert smoke.lifecycle.aging_cycles == 1
    assert smoke.lifecycle.aging_t_factor == 1
    assert study.lifecycle.aging_cycles == 20
    assert study.lifecycle.target_soh_levels == (100.0, 95.0, 90.0)


def test_eis_spec_rejects_invalid_soc():
    config = _config()
    config["base_soc"] = 1.2
    with pytest.raises(ValueError, match="soc"):
        EisWorkflowSpec.from_mapping(config)


def test_run_quick_eis_sections_rebuilds_per_temperature(monkeypatch):
    spec = EisWorkflowSpec.from_mapping(_config())
    built_temperatures = []

    class DummyEisSimulation:
        def __init__(self, temperature_k):
            self.temperature_k = temperature_k

        def solve(self, frequencies, initial_soc):
            return SimpleNamespace(
                frequencies=np.asarray(frequencies, dtype=float),
                impedance=np.asarray(frequencies, dtype=float) * 0 + (self.temperature_k / 1000) - 0.01j,
            )

    def fake_build(*_args, temperature_k, **_kwargs):
        built_temperatures.append(temperature_k)
        return DummyEisSimulation(temperature_k)

    monkeypatch.setattr(eis_module, "_build_eis_simulation", fake_build)
    frames = eis_module.run_quick_eis_sections(spec, lambda *_args, **_kwargs: {})
    assert set(frames) == {"quick", "soc_sweep", "temperature_sweep"}
    assert built_temperatures == [298.15, 273.15, 298.15, 318.15]
    assert len(frames["soc_sweep"]["soc"].unique()) == 3


def test_run_eis_workflow_writes_standard_artifacts(tmp_path, monkeypatch):
    spec = EisWorkflowSpec.from_mapping(_config())

    quick_frame = pd.DataFrame(
        {
            "section": ["quick"],
            "label": ["25°C SOC=50%"],
            "temperature_c": [25.0],
            "soc": [0.5],
            "frequency_hz": [1.0],
            "z_real_ohm": [0.01],
            "z_imag_ohm": [-0.02],
            "minus_z_im_ohm": [0.02],
            "z_magnitude_ohm": [0.02236],
            "phase_deg": [-63.4],
        }
    )
    lifecycle_result = {
        "solution": object(),
        "soh_df": pd.DataFrame({"cycle": [1], "soh_pct": [100.0]}),
        "checkpoints_df": pd.DataFrame({"cycle": [1], "soh_pct": [100.0], "label": ["SOH=100.0% | Cycle 1"]}),
        "impedance_df": pd.DataFrame(
            {
                "label": ["SOH=100.0% | Cycle 1"],
                "cycle": [1],
                "soh_pct": [100.0],
                "frequency_hz": [1.0],
                "z_real_ohm": [0.01],
                "minus_z_im_ohm": [0.02],
                "z_magnitude_ohm": [0.02236],
                "phase_deg": [-63.4],
            }
        ),
        "components_df": pd.DataFrame({"cycle": [1], "soh_pct": [100.0], "r_ohm_ohm": [0.01]}),
        "eis_solutions": {},
        "aging_power_w": 500.0,
        "measurement_state_label": "fixed SOC=50% after recharge/rest",
    }

    monkeypatch.setattr(eis_module, "load_params", lambda _cell: (lambda *_args, **_kwargs: {}))
    monkeypatch.setattr(eis_module, "prepare_eis_experiment", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(eis_module, "run_quick_eis_sections", lambda *_args, **_kwargs: {"quick": quick_frame})
    monkeypatch.setattr(eis_module, "run_lifecycle_eis_study", lambda **_kwargs: lifecycle_result)

    result = run_eis_workflow(
        spec,
        project_root=tmp_path / "BatteryProject",
        workspace_root=tmp_path,
        run_id="test_run",
    )

    assert result["metrics_path"].is_file()
    assert (result["context"].run_dir / "config.json").is_file()
    assert (result["context"].run_dir / "status.json").is_file()
    assert result["artifact_paths"]["summary_workbook"].is_file()
    assert result["metrics"].set_index("section").loc["lifecycle_components", "rows"] == 1


def test_eis_canonical_keeps_full_analysis_sections():
    notebook_path = Path(__file__).parents[1] / "examples" / "workflows" / "阻抗分析.ipynb"
    code_exe = Path("D:/软件安装/Microsoft VS Code/Code.exe")
    if not code_exe.is_file():
        pytest.skip("Code.exe bridge is required for DLP-wrapped notebooks")
    script = (
        "const fs=require('fs');"
        f"console.log(fs.readFileSync({json.dumps(str(notebook_path).replace(os.sep, '/'))},'utf8'))"
    )
    completed = subprocess.run(
        [str(code_exe), "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "ELECTRON_RUN_AS_NODE": "1"},
    )
    notebook = json.loads(completed.stdout)
    sources = ["".join(cell.get("source", [])) for cell in notebook["cells"]]
    combined = "\n".join(sources)
    tagged_cells = [cell for cell in notebook["cells"] if cell.get("metadata", {}).get("tags") == ["parameters"]]
    assert len(tagged_cells) == 1
    assert notebook["cells"][1]["metadata"]["tags"] == ["parameters"]
    for heading in ("快速 EIS 基线", "SOC 扫描", "温度扫描", "Lifecycle-EIS 联合研究", "阻抗指标拆解", "导出"):
        assert heading in combined
    code = "\n".join(source for source, cell in zip(sources, notebook["cells"]) if cell["cell_type"] == "code")
    assert "def " not in code
    assert "CONFIG" in sources[1]
