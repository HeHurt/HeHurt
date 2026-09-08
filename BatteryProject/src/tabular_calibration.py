"""Reusable sensitivity screening and calibration for tabular experiment data."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd

from .parameter_identification import run_parameter_optimization


SimulationFunction = Callable[[dict[str, float]], pd.DataFrame]


@dataclass(frozen=True)
class CalibrationParameter:
    """One physical parameter and its admissible calibration range."""

    name: str
    baseline: float
    low: float
    high: float
    scale: str = "line"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("parameter name is required")
        if self.low >= self.high:
            raise ValueError(f"{self.name}: low must be smaller than high")
        if not self.low <= self.baseline <= self.high:
            raise ValueError(f"{self.name}: baseline must be inside bounds")
        if self.scale not in {"line", "log"}:
            raise ValueError(f"{self.name}: scale must be line or log")
        if self.scale == "log" and self.low <= 0:
            raise ValueError(f"{self.name}: log-scale bounds must be positive")


@dataclass(frozen=True)
class TabularCalibrationSpec:
    """Declarative contract for experiment alignment and automatic decisions."""

    case_columns: tuple[str, ...]
    observed_column: str
    prediction_column: str = "prediction"
    split_column: str | None = "split"
    train_label: str = "train"
    validation_label: str = "validation"
    required_constants: Mapping[str, Any] = field(default_factory=dict)
    sensitivity_threshold: float = 1e-3
    response_correlation_threshold: float = 0.95
    max_selected_parameters: int = 3
    fail_rmse: float = 100.0

    def __post_init__(self) -> None:
        if not self.case_columns:
            raise ValueError("case_columns must not be empty")
        if self.sensitivity_threshold < 0:
            raise ValueError("sensitivity_threshold must be non-negative")
        if not 0 < self.response_correlation_threshold <= 1:
            raise ValueError("response_correlation_threshold must be in (0, 1]")
        if self.max_selected_parameters <= 0:
            raise ValueError("max_selected_parameters must be positive")


def validate_experiment_table(
    experiment: pd.DataFrame,
    spec: TabularCalibrationSpec,
) -> pd.DataFrame:
    """Validate and return a deterministic copy of the experiment table."""
    required = set(spec.case_columns) | {spec.observed_column}
    if spec.split_column is not None:
        required.add(spec.split_column)
    required.update(spec.required_constants)
    missing = sorted(required.difference(experiment.columns))
    if missing:
        raise ValueError(f"experiment is missing columns: {missing}")
    if experiment.empty:
        raise ValueError("experiment must not be empty")
    if experiment[list(spec.case_columns)].duplicated().any():
        raise ValueError("experiment case columns must identify unique rows")
    observed = pd.to_numeric(experiment[spec.observed_column], errors="coerce")
    if not np.isfinite(observed).all():
        raise ValueError("observed values must be finite numbers")
    for column, expected in spec.required_constants.items():
        values = experiment[column].drop_duplicates().tolist()
        if values != [expected]:
            raise ValueError(
                f"protocol mismatch for {column}: expected {expected!r}, got {values!r}"
            )
    if spec.split_column is not None:
        labels = set(experiment[spec.split_column].astype(str))
        allowed = {spec.train_label, spec.validation_label}
        if not labels.issubset(allowed) or spec.train_label not in labels:
            raise ValueError(
                f"{spec.split_column} must use {sorted(allowed)} and include train"
            )
    return experiment.sort_values(list(spec.case_columns)).reset_index(drop=True)


def _rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(predicted - observed))))


def _parameter_key(
    namespace: str,
    parameters: Mapping[str, float],
) -> str:
    payload = {
        "namespace": namespace,
        "parameters": {key: float(parameters[key]) for key in sorted(parameters)},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()[:20]


class CandidateEvaluator:
    """Align, score, cache, and audit calls to a forward simulation."""

    def __init__(
        self,
        experiment: pd.DataFrame,
        spec: TabularCalibrationSpec,
        simulate_fn: SimulationFunction,
        *,
        cache_dir: Path | None = None,
        cache_namespace: str = "default",
    ) -> None:
        self.spec = spec
        self.experiment = validate_experiment_table(experiment, spec)
        self.simulate_fn = simulate_fn
        self.cache_dir = None if cache_dir is None else Path(cache_dir)
        self.cache_namespace = cache_namespace
        self.evaluation_rows: list[dict[str, Any]] = []
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, parameters: Mapping[str, float]) -> Path | None:
        if self.cache_dir is None:
            return None
        key = _parameter_key(self.cache_namespace, parameters)
        return self.cache_dir / f"{key}.csv"

    def _load_or_simulate(
        self,
        parameters: Mapping[str, float],
    ) -> tuple[pd.DataFrame, bool]:
        cache_path = self._cache_path(parameters)
        if cache_path is not None and cache_path.is_file():
            return pd.read_csv(cache_path), True
        prediction = self.simulate_fn(
            {key: float(value) for key, value in parameters.items()}
        )
        if not isinstance(prediction, pd.DataFrame):
            raise TypeError("simulate_fn must return a pandas DataFrame")
        required = set(self.spec.case_columns) | {self.spec.prediction_column}
        missing = sorted(required.difference(prediction.columns))
        if missing:
            raise ValueError(f"prediction is missing columns: {missing}")
        prediction = prediction[
            [*self.spec.case_columns, self.spec.prediction_column]
        ].copy()
        if prediction[list(self.spec.case_columns)].duplicated().any():
            raise ValueError("prediction case columns must identify unique rows")
        if cache_path is not None:
            prediction.to_csv(cache_path, index=False, encoding="utf-8-sig")
        return prediction, False

    def evaluate(
        self,
        parameters: Mapping[str, float],
        *,
        label: str,
    ) -> dict[str, Any]:
        """Evaluate one candidate and return aligned predictions plus metrics."""
        prediction, cache_hit = self._load_or_simulate(parameters)
        aligned = self.experiment.merge(
            prediction,
            on=list(self.spec.case_columns),
            how="left",
            validate="one_to_one",
        )
        predicted = pd.to_numeric(
            aligned[self.spec.prediction_column],
            errors="coerce",
        )
        if not np.isfinite(predicted).all():
            raise ValueError("prediction does not cover all experiment cases")
        observed = aligned[self.spec.observed_column].to_numpy(dtype=float)
        predicted_values = predicted.to_numpy(dtype=float)
        metrics = {"rmse_all": _rmse(observed, predicted_values)}
        if self.spec.split_column is None:
            metrics["rmse_train"] = metrics["rmse_all"]
            metrics["rmse_validation"] = np.nan
        else:
            split = aligned[self.spec.split_column].astype(str)
            train = split == self.spec.train_label
            validation = split == self.spec.validation_label
            metrics["rmse_train"] = _rmse(
                observed[train],
                predicted_values[train],
            )
            metrics["rmse_validation"] = (
                _rmse(observed[validation], predicted_values[validation])
                if validation.any()
                else np.nan
            )
        row = {
            "label": label,
            "cache_hit": cache_hit,
            **{f"parameter::{key}": float(value) for key, value in parameters.items()},
            **metrics,
        }
        self.evaluation_rows.append(row)
        return {
            "parameters": dict(parameters),
            "aligned": aligned,
            "metrics": metrics,
            "cache_hit": cache_hit,
        }


def run_oat_sensitivity(
    evaluator: CandidateEvaluator,
    parameters: list[CalibrationParameter],
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Evaluate each parameter at its low/high bounds and rank its response."""
    baseline = {parameter.name: parameter.baseline for parameter in parameters}
    observed_scale = float(
        np.sqrt(np.mean(np.square(
            evaluator.experiment[evaluator.spec.observed_column].to_numpy(dtype=float)
        )))
    )
    observed_scale = max(observed_scale, np.finfo(float).eps)
    rows: list[dict[str, Any]] = []
    responses: dict[str, np.ndarray] = {}
    for parameter in parameters:
        low = dict(baseline)
        high = dict(baseline)
        low[parameter.name] = parameter.low
        high[parameter.name] = parameter.high
        low_result = evaluator.evaluate(low, label=f"oat::{parameter.name}::low")
        high_result = evaluator.evaluate(high, label=f"oat::{parameter.name}::high")
        low_pred = low_result["aligned"][evaluator.spec.prediction_column].to_numpy(
            dtype=float
        )
        high_pred = high_result["aligned"][evaluator.spec.prediction_column].to_numpy(
            dtype=float
        )
        response = 0.5 * (high_pred - low_pred)
        responses[parameter.name] = response
        response_rms = float(np.sqrt(np.mean(np.square(response))))
        rows.append({
            "parameter": parameter.name,
            "baseline": parameter.baseline,
            "low": parameter.low,
            "high": parameter.high,
            "scale": parameter.scale,
            "response_rms": response_rms,
            "normalized_sensitivity": response_rms / observed_scale,
            "rmse_low": low_result["metrics"]["rmse_train"],
            "rmse_high": high_result["metrics"]["rmse_train"],
        })
    ranking = pd.DataFrame(rows).sort_values(
        "normalized_sensitivity",
        ascending=False,
    ).reset_index(drop=True)
    return ranking, responses


def select_sensitive_parameters(
    ranking: pd.DataFrame,
    responses: Mapping[str, np.ndarray],
    spec: TabularCalibrationSpec,
) -> tuple[list[str], pd.DataFrame]:
    """Greedily select sensitive, non-collinear response directions."""
    names = ranking["parameter"].tolist()
    corr = pd.DataFrame(np.eye(len(names)), index=names, columns=names)
    for i, left in enumerate(names):
        for j in range(i + 1, len(names)):
            right = names[j]
            left_response = np.asarray(responses[left], dtype=float)
            right_response = np.asarray(responses[right], dtype=float)
            if np.std(left_response) == 0 or np.std(right_response) == 0:
                value = 0.0
            else:
                value = float(np.corrcoef(left_response, right_response)[0, 1])
            corr.loc[left, right] = value
            corr.loc[right, left] = value
    selected: list[str] = []
    for row in ranking.itertuples(index=False):
        if row.normalized_sensitivity < spec.sensitivity_threshold:
            continue
        if any(
            abs(float(corr.loc[row.parameter, existing]))
            >= spec.response_correlation_threshold
            for existing in selected
        ):
            continue
        selected.append(row.parameter)
        if len(selected) >= spec.max_selected_parameters:
            break
    return selected, corr


def _physical_from_search(
    value: float,
    parameter: CalibrationParameter,
) -> float:
    return float(10 ** value) if parameter.scale == "log" else float(value)


def _search_from_physical(parameter: CalibrationParameter) -> float:
    if parameter.scale == "log":
        return float(np.log10(parameter.baseline))
    return float(parameter.baseline)


def optimize_selected_parameters(
    evaluator: CandidateEvaluator,
    parameters: list[CalibrationParameter],
    selected: list[str],
    *,
    method: str = "MO",
    method_params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit selected parameters with BatteryProject's existing optimizer."""
    if not selected:
        raise ValueError("no parameters passed sensitivity screening")
    parameter_map = {parameter.name: parameter for parameter in parameters}
    baseline = {parameter.name: parameter.baseline for parameter in parameters}
    change_params = {
        name: [
            "model",
            parameter_map[name].scale,
            parameter_map[name].low,
            parameter_map[name].high,
        ]
        for name in selected
    }

    def objective(search_params: dict[str, float]) -> float:
        candidate = dict(baseline)
        for name, value in search_params.items():
            candidate[name] = _physical_from_search(value, parameter_map[name])
        try:
            result = evaluator.evaluate(candidate, label="optimization")
            loss = result["metrics"]["rmse_train"]
        except Exception:
            loss = evaluator.spec.fail_rmse
        return 1.0 / (float(loss) + 1e-12)

    optimization = run_parameter_optimization(
        objective,
        change_params,
        method=method,
        method_params=None if method_params is None else dict(method_params),
        init={name: _search_from_physical(parameter_map[name]) for name in selected},
    )
    best = dict(baseline)
    for name, value in optimization["best_params"].items():
        best[name] = _physical_from_search(value, parameter_map[name])
    final = evaluator.evaluate(best, label="best")
    return {
        "selected_parameters": selected,
        "best_parameters": best,
        "best_fitness": optimization["best_fitness"],
        "metrics": final["metrics"],
        "aligned": final["aligned"],
        "raw_result": optimization["raw_result"],
    }


def run_tabular_calibration(
    experiment: pd.DataFrame,
    spec: TabularCalibrationSpec,
    parameters: list[CalibrationParameter],
    simulate_fn: SimulationFunction,
    *,
    output_dir: Path,
    cache_namespace: str,
    method: str = "MO",
    method_params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run baseline, OAT screening, optimization, validation, and reporting."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluator = CandidateEvaluator(
        experiment,
        spec,
        simulate_fn,
        cache_dir=output_dir / "cache",
        cache_namespace=cache_namespace,
    )
    baseline = {parameter.name: parameter.baseline for parameter in parameters}
    baseline_result = evaluator.evaluate(baseline, label="baseline")
    ranking, responses = run_oat_sensitivity(evaluator, parameters)
    selected, correlation = select_sensitive_parameters(ranking, responses, spec)
    optimized = optimize_selected_parameters(
        evaluator,
        parameters,
        selected,
        method=method,
        method_params=method_params,
    )
    ranking["selected"] = ranking["parameter"].isin(selected)
    ranking.to_csv(output_dir / "sensitivity_ranking.csv", index=False)
    correlation.to_csv(output_dir / "response_correlation.csv")
    pd.DataFrame(evaluator.evaluation_rows).to_csv(
        output_dir / "evaluation_log.csv",
        index=False,
    )
    optimized["aligned"].to_csv(
        output_dir / "best_fit_comparison.csv",
        index=False,
    )
    summary = {
        "spec": asdict(spec),
        "parameters": [asdict(parameter) for parameter in parameters],
        "selected_parameters": selected,
        "baseline_metrics": baseline_result["metrics"],
        "best_parameters": optimized["best_parameters"],
        "best_metrics": optimized["metrics"],
        "cache_namespace": cache_namespace,
    }
    (output_dir / "calibration_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "sensitivity": ranking,
        "correlation": correlation,
        "evaluation_log": pd.DataFrame(evaluator.evaluation_rows),
        "comparison": optimized["aligned"],
        "output_dir": output_dir,
    }


__all__ = [
    "CalibrationParameter",
    "CandidateEvaluator",
    "TabularCalibrationSpec",
    "optimize_selected_parameters",
    "run_oat_sensitivity",
    "run_tabular_calibration",
    "select_sensitive_parameters",
    "validate_experiment_table",
]
