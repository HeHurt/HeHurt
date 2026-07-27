import pandas as pd

from src.workflows import frequency


def test_frequency_workflow_writes_frequency_run(monkeypatch, tmp_path):
    calls = {}

    def fake_load_params(cell):
        calls["cell"] = cell

        def params_fn(t_factor, temperature=298.15):
            return {"Nominal cell capacity [A.h]": 587.0}

        return params_fn

    def fake_run_frequency_scenarios(**kwargs):
        calls["runner_kwargs"] = kwargs
        main_df = pd.DataFrame({"real_day": [1], "q_sei_ah": [0.1], "q_plating_ah": [0.0]})
        rpt_df = pd.DataFrame({"real_day": [1], "capacity_retention": [0.99], "rpt_efficiency_pct": [95.0]})
        return {
            "results": {
                "pulse_10s": {
                    "scenario": {"name": "pulse_10s", "display_name": "10 s"},
                    "main_df": main_df,
                    "rpt_df": rpt_df,
                }
            },
            "summary_df": pd.DataFrame({"scenario": ["pulse_10s"], "final_capacity_retention_pct": [99.0]}),
        }

    monkeypatch.setattr(frequency, "load_params", fake_load_params)
    monkeypatch.setattr(frequency, "run_frequency_scenarios", fake_run_frequency_scenarios)

    spec = frequency.FrequencyWorkflowSpec.from_mapping(
        {
            "cell": "587Ah",
            "run_mode": "smoke",
            "current_a": 293.5,
            "nominal_capacity_ah": 587.0,
            "temperature_c": 25,
            "scenarios": [
                {
                    "name": "pulse_10s",
                    "display_name": "10 s",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 2,
                    "enabled": True,
                }
            ],
            "modes": {"smoke": {"real_days_total": 1, "day_acceleration_factor": 1, "return_solutions": False}},
        }
    )
    result = frequency.run_frequency_workflow(spec, project_root=tmp_path, workspace_root=tmp_path, run_id="smoke")

    assert calls["cell"] == "587Ah"
    assert calls["runner_kwargs"]["temperature_k"] == 298.15
    assert calls["runner_kwargs"]["runtime_config"]["real_days_total"] == 1
    assert result["context"].run_dir == tmp_path / "output" / "runs" / "frequency_regulation" / "smoke"
    assert (result["context"].run_dir / "config.json").is_file()
    assert result["artifact_paths"]["scenario_table"].is_file()
    assert result["artifact_paths"]["rpt"].is_file()
    assert result["artifact_paths"]["excel"].is_file()


def test_frequency_waveform_preview_keeps_raw_and_equivalent_views():
    spec = frequency.FrequencyWorkflowSpec.from_mapping(
        {
            "cell": "587Ah",
            "current_a": 293.5,
            "nominal_capacity_ah": 587.0,
            "scenarios": [
                {
                    "name": "pulse_10s",
                    "display_name": "10 s",
                    "pulse_seconds": 10,
                    "total_pulses_per_day": 1440,
                    "sample_period_seconds": 2,
                    "enabled": True,
                }
            ],
        }
    )
    preview = frequency.build_frequency_waveform_preview(spec)

    assert list(preview["comparison_df"]["waveform"]) == ["raw pulses", "equivalent segments"]
    assert preview["raw_time_s"].size > preview["equivalent_time_s"].size
    assert preview["raw_zoom"][0].size >= 2
