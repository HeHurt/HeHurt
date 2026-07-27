"""Tests for the headless canonical PSD workflow."""

import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.workflows import psd as psd_module
from src.workflows.psd import (
    PsdWorkflowSpec,
    fit_dv_to_comsol_histogram,
    raw_psd_to_comsol_histogram,
    run_psd_workflow,
)


def _config(run_mode="smoke"):
    return {
        "cell": "MIC",
        "run_mode": run_mode,
        "default_diameters_um": [0.243, 0.276, 0.314, 0.357, 0.405, 0.460, 0.523, 0.594, 0.675],
        "materials": {
            "Demo": {
                "Dv50_um": 0.872,
                "vol_pct": [0.51, 1.74, 3.43, 5.09, 6.28, 6.81, 6.70, 6.19, 5.56],
            }
        },
        "rate_list": [0.5],
        "modes": {
            "smoke": {"run_simulation": False, "run_comsol_conversion": True},
            "study": {"run_simulation": True, "run_comsol_conversion": True, "cycles": 2},
        },
        "comsol_dv": [
            {
                "name": "LFP",
                "dv_percentiles_um": {10: 0.432, 50: 1.262, 90: 3.843, 99: 6.742},
                "n_bins": 5,
                "rp_min_um": 0.1,
                "rp_max_um": 3.5,
                "weighting": "surface",
            }
        ],
        "comsol_raw": [
            {
                "name": "YA15",
                "diameters_um": [0.243, 0.276, 0.314, 0.357, 0.405, 0.460],
                "vol_pct": [0.51, 1.74, 3.43, 5.09, 6.28, 6.81],
                "n_bins": 4,
                "total_count": 50,
            }
        ],
    }


def test_psd_spec_uses_selected_mode():
    smoke = PsdWorkflowSpec.from_mapping(_config("smoke"))
    study = PsdWorkflowSpec.from_mapping(_config("study"))
    assert smoke.run_simulation is False
    assert smoke.run_comsol_conversion is True
    assert study.run_simulation is True
    assert study.cycles == 2


def test_psd_spec_rejects_ambiguous_operation_inputs():
    config = _config()
    config["power_w_list"] = [500]
    with pytest.raises(ValueError, match="only one"):
        PsdWorkflowSpec.from_mapping(config)


def test_comsol_histogram_converters_return_java_ready_tables():
    spec = PsdWorkflowSpec.from_mapping(_config())
    dv_result = fit_dv_to_comsol_histogram(spec.comsol_dv[0])
    raw_result = raw_psd_to_comsol_histogram(spec.comsol_raw[0])
    assert len(dv_result["histogram"]) == 5
    assert len(raw_result["histogram"]) == 4
    assert dv_result["rp_min_um"] == 0.1
    assert raw_result["total_count"] > 0
    assert "model.param().set" in psd_module.comsol_histogram_to_java(dv_result)


def test_load_psd_materials_from_registry_reads_registered_csv(tmp_path, monkeypatch):
    source = tmp_path / "psd.csv"
    source.write_text(
        "material,diameter_um,vol_pct\nA,0.2,1\nA,0.3,2\nB,0.2,3\nB,0.3,4\n",
        encoding="utf-8",
    )
    config = _config()
    config["materials"] = {}
    config["datasets"] = [
        {"query": {"cell": "MIC", "format": "csv", "require_unique": True}, "loader": "psd_csv"}
    ]
    spec = PsdWorkflowSpec.from_mapping(config)
    monkeypatch.setattr(
        psd_module.DatasetQuery,
        "resolve",
        lambda _self, _root: [{"absolute_path": str(source)}],
    )
    materials, entries = psd_module.load_psd_materials_from_registry(spec.datasets, workspace_root=tmp_path)
    assert set(materials) == {"A", "B"}
    assert len(entries) == 1
    assert materials["A"]["vol_pct"].tolist() == [1.0, 2.0]


def test_run_psd_workflow_writes_standard_artifacts(tmp_path, monkeypatch):
    spec = PsdWorkflowSpec.from_mapping(_config())
    monkeypatch.setattr(psd_module, "load_psd_materials_from_registry", lambda *_args, **_kwargs: ({}, []))
    result = run_psd_workflow(
        spec,
        project_root=tmp_path / "BatteryProject",
        workspace_root=tmp_path,
        run_id="test_run",
    )
    assert result["metrics_path"].is_file()
    assert (result["context"].run_dir / "config.json").is_file()
    assert (result["context"].run_dir / "artifacts.json").is_file()
    assert (result["context"].run_dir / "status.json").is_file()
    assert result["artifact_paths"]["material_summary"].is_file()
    assert result["artifact_paths"]["summary_workbook"].is_file()
    assert result["metrics"].set_index("section").loc["materials", "rows"] == 1
    assert isinstance(result["comsol_histograms"], pd.DataFrame)


def test_psd_canonical_keeps_full_analysis_sections():
    notebook_path = Path(__file__).parents[1] / "examples" / "workflows" / "粒径分布.ipynb"
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
        env={**os.environ, "ELECTRON_RUN_AS_NODE": "1"},
    )
    notebook = json.loads(completed.stdout.decode("utf-8"))
    sources = ["".join(cell.get("source", [])) for cell in notebook["cells"]]
    combined = "\n".join(sources)
    tagged_cells = [cell for cell in notebook["cells"] if cell.get("metadata", {}).get("tags") == ["parameters"]]
    assert len(tagged_cells) == 1
    assert notebook["cells"][1]["metadata"]["tags"] == ["parameters"]
    for heading in (
        "Feature Parity",
        "PSD 拟合",
        "材料对比",
        "仿真",
        "离散与 COMSOL 转换",
        "电压曲线",
        "导出",
    ):
        assert heading in combined
    code = "\n".join(source for source, cell in zip(sources, notebook["cells"]) if cell["cell_type"] == "code")
    assert "def " not in code
    assert "CONFIG" in sources[1]
    assert "DatasetQuery" in combined
