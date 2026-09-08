from pathlib import Path

import numpy as np
import pandas as pd

from BatteryProject.src.tabular_calibration import (
    CalibrationParameter,
    CandidateEvaluator,
    TabularCalibrationSpec,
    run_oat_sensitivity,
    run_tabular_calibration,
    select_sensitive_parameters,
)


def _experiment() -> pd.DataFrame:
    x = np.arange(1.0, 7.0)
    return pd.DataFrame({
        "case": x,
        "protocol": "demo",
        "split": ["train"] * 4 + ["validation"] * 2,
        "observed": 1.0 + 2.0 * x,
    })


def _simulate(parameters: dict[str, float]) -> pd.DataFrame:
    x = np.arange(1.0, 7.0)
    prediction = (
        1.0
        + parameters["slope"] * x
        + 0.99 * parameters["correlated"] * x
        + parameters["insensitive"] * 0.0
    )
    return pd.DataFrame({"case": x, "prediction": prediction})


def _spec() -> TabularCalibrationSpec:
    return TabularCalibrationSpec(
        case_columns=("case",),
        observed_column="observed",
        required_constants={"protocol": "demo"},
        sensitivity_threshold=1e-6,
        response_correlation_threshold=0.95,
        max_selected_parameters=2,
    )


def _parameters() -> list[CalibrationParameter]:
    return [
        CalibrationParameter("slope", 2.0, 1.0, 3.0),
        CalibrationParameter("correlated", 0.0, -0.5, 0.5),
        CalibrationParameter("insensitive", 1.0, 0.5, 1.5),
    ]


def test_oat_ranking_filters_insensitive_and_correlated_response(tmp_path: Path):
    evaluator = CandidateEvaluator(
        _experiment(),
        _spec(),
        _simulate,
        cache_dir=tmp_path,
        cache_namespace="unit",
    )
    ranking, responses = run_oat_sensitivity(evaluator, _parameters())
    selected, correlation = select_sensitive_parameters(
        ranking,
        responses,
        _spec(),
    )

    assert ranking.iloc[0]["parameter"] == "slope"
    assert ranking.iloc[-1]["normalized_sensitivity"] == 0
    assert selected == ["slope"]
    assert abs(correlation.loc["slope", "correlated"]) > 0.95


def test_candidate_evaluator_reuses_cached_predictions(tmp_path: Path):
    calls = {"count": 0}

    def counted(parameters: dict[str, float]) -> pd.DataFrame:
        calls["count"] += 1
        return _simulate(parameters)

    evaluator = CandidateEvaluator(
        _experiment(),
        _spec(),
        counted,
        cache_dir=tmp_path,
        cache_namespace="cache",
    )
    parameters = {item.name: item.baseline for item in _parameters()}
    first = evaluator.evaluate(parameters, label="first")
    second = evaluator.evaluate(parameters, label="second")

    assert calls["count"] == 1
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert first["metrics"]["rmse_train"] == 0
    assert first["metrics"]["rmse_validation"] == 0


def test_protocol_mismatch_fails_before_simulation(tmp_path: Path):
    experiment = _experiment()
    experiment["protocol"] = "wrong"
    try:
        CandidateEvaluator(
            experiment,
            _spec(),
            _simulate,
            cache_dir=tmp_path,
        )
    except ValueError as exc:
        assert "protocol mismatch" in str(exc)
    else:
        raise AssertionError("protocol mismatch must fail")


def test_end_to_end_workflow_writes_machine_readable_outputs(tmp_path: Path):
    result = run_tabular_calibration(
        _experiment(),
        _spec(),
        _parameters(),
        _simulate,
        output_dir=tmp_path,
        cache_namespace="end-to-end",
        method="MO",
    )

    assert result["summary"]["selected_parameters"] == ["slope"]
    assert result["summary"]["best_metrics"]["rmse_validation"] < 1e-8
    assert (tmp_path / "calibration_summary.json").is_file()
    assert (tmp_path / "sensitivity_ranking.csv").is_file()
    assert (tmp_path / "response_correlation.csv").is_file()
    assert (tmp_path / "evaluation_log.csv").is_file()
    assert (tmp_path / "best_fit_comparison.csv").is_file()
