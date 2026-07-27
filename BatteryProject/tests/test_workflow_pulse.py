import pandas as pd
import pytest

from src.workflows import pulse


def test_pulse_workflow_writes_inserted_pulse_run(monkeypatch, tmp_path):
    calls = {}

    def fake_load_params(cell):
        calls["cell"] = cell

        def params_fn(t_factor, temperature=298.15):
            return {"Nominal cell capacity [A.h]": 1175.0}

        return params_fn

    def fake_run_pulse_lifecycle_scenarios(**kwargs):
        calls["runner_kwargs"] = kwargs
        main_df = pd.DataFrame({"real_cycle": [1], "capacity_retention": [1.0]})
        capacity_df = pd.DataFrame(
            {
                "scenario": ["baseline"],
                "real_cycle": [1],
                "capacity_check_discharge_capacity_ah": [1175.0],
                "capacity_retention": [1.0],
            }
        )
        return {
            "results": {
                "baseline": {
                    "scenario": {"name": "baseline", "display_name": "baseline"},
                    "main_df": main_df,
                    "capacity_check_df": capacity_df,
                }
            },
            "capacity_check_df": capacity_df,
            "summary_df": pd.DataFrame({"scenario": ["baseline"], "final_capacity_retention_pct": [100.0]}),
        }

    monkeypatch.setattr(pulse, "load_params", fake_load_params)
    monkeypatch.setattr(pulse, "run_pulse_lifecycle_scenarios", fake_run_pulse_lifecycle_scenarios)

    spec = pulse.PulseWorkflowSpec.from_mapping(
        {
            "cell": "MIC",
            "run_mode": "smoke",
            "temperature_c": 25,
            "scenarios": [{"name": "baseline", "display_name": "baseline", "pulse_p_rate": None, "enabled": True}],
            "modes": {"smoke": {"total_cycles": 1, "cycles_per_block": 1, "return_solutions": False}},
        }
    )
    result = pulse.run_pulse_workflow(spec, project_root=tmp_path, workspace_root=tmp_path, run_id="smoke")

    assert calls["cell"] == "MIC"
    assert calls["runner_kwargs"]["temperature_k"] == 298.15
    assert calls["runner_kwargs"]["runtime_config"]["total_cycles"] == 1
    assert result["context"].run_dir == tmp_path / "output" / "runs" / "inserted_pulse" / "smoke"
    assert (result["context"].run_dir / "config.json").is_file()
    assert result["artifact_paths"]["scenario_table"].is_file()
    assert result["artifact_paths"]["capacity_check"].is_file()
    assert result["artifact_paths"]["excel"].is_file()


def test_pulse_dataset_query_config_is_preserved():
    spec = pulse.PulseWorkflowSpec.from_mapping(
        {
            "cell": "MIC",
            "scenarios": [{"name": "baseline", "display_name": "baseline", "pulse_p_rate": None, "enabled": True}],
            "datasets": [
                {
                    "temperature_c": 25,
                    "test_type": "脉冲",
                    "kind": "processed",
                    "format": ".csv",
                    "path_contains": "pulse",
                    "require_unique": False,
                }
            ],
        }
    )

    assert len(spec.datasets) == 1
    assert spec.datasets[0].cell == "MIC"
    assert spec.datasets[0].test_type == "脉冲"
    assert spec.datasets[0].require_unique is False


def test_build_adjusted_capacity_table_preserves_raw_columns():
    results = {
        "pulse": {
            "scenario": {"display_name": "pulse case"},
            "capacity_check_df": pd.DataFrame(
                {
                    "real_cycle": [1],
                    "capacity_check_discharge_capacity_ah": [100.0],
                    "capacity_retention": [0.95],
                }
            ),
        }
    }

    table = pulse.build_adjusted_capacity_table(
        results,
        {"pulse": {"capacity_scale": 1.1, "capacity_offset_ah": 2.0, "retention_offset": -0.01}},
    )

    assert table.loc[0, "capacity_check_discharge_capacity_ah_raw"] == 100.0
    assert table.loc[0, "capacity_check_discharge_capacity_ah_adjusted"] == pytest.approx(112.0)
    assert table.loc[0, "capacity_retention_adjusted"] == 0.94
