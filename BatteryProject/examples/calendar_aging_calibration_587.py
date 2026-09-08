"""End-to-end sensitivity and calibration case for 587 Ah calendar aging.

Examples
--------
Package the already accepted result without rerunning simulations:
    python BatteryProject/examples/calendar_aging_calibration_587.py --mode accepted

Run OAT screening, automatic parameter selection, optimization, and validation:
    python BatteryProject/examples/calendar_aging_calibration_587.py --mode full
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tomllib
from typing import Any

import pandas as pd


HITHIUM_ROOT = Path(__file__).resolve().parents[2]
PARAMS_ROOT = HITHIUM_ROOT / "params"
for import_path in (HITHIUM_ROOT, PARAMS_ROOT):
    import_text = str(import_path)
    if import_text not in sys.path:
        sys.path.insert(0, import_text)

from BatteryProject.src.tabular_calibration import (  # noqa: E402
    CalibrationParameter,
    TabularCalibrationSpec,
    run_tabular_calibration,
)


DEFAULT_CONFIG = Path(__file__).with_suffix(".toml")


def _read_config(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _load_activated_runner(path: Path):
    module_spec = importlib.util.spec_from_file_location(
        "calendar_aging_587_activated_case",
        path,
    )
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"cannot load activated runner: {path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def _build_experiment(config: dict[str, Any]) -> pd.DataFrame:
    source = pd.read_csv(HITHIUM_ROOT / config["experiment_csv"])
    temperatures = set(config["temperatures_c"])
    checkpoints = set(config["checkpoint_days"])
    selected = source.loc[
        source["temperature_c"].isin(temperatures)
        & source["storage_days"].isin(checkpoints)
    ].copy()
    experiment = (
        selected.groupby(
            ["temperature_c", "storage_days"],
            as_index=False,
        )["recovery_rate"]
        .mean()
        .rename(columns={"recovery_rate": "observed_recovery_rate"})
    )
    experiment["storage_soc_pct"] = config["protocol"]["storage_soc_pct"]
    experiment["aging_mode"] = config["protocol"]["aging_mode"]
    experiment["split"] = experiment["storage_days"].map(
        lambda day: (
            "train"
            if day <= config["training_max_days"]
            else "validation"
        )
    )
    return experiment


def _build_simulation_function(config: dict[str, Any]):
    runner = _load_activated_runner(HITHIUM_ROOT / config["activated_runner"])
    checkpoints = tuple(int(day) for day in config["checkpoint_days"])

    def simulate(parameters: dict[str, float]) -> pd.DataFrame:
        candidate = runner.CalibrationParameters(**parameters)
        frames = []
        for temperature_c in config["temperatures_c"]:
            result = runner.run_activated_case(
                float(temperature_c),
                candidate,
                checkpoint_days=checkpoints,
            )
            frames.append(
                result[
                    ["temperature_c", "storage_days", "recovery_rate"]
                ].rename(columns={"recovery_rate": "predicted_recovery_rate"})
            )
        return pd.concat(frames, ignore_index=True)

    return simulate


def _calibration_spec(config: dict[str, Any]) -> TabularCalibrationSpec:
    rules = config["decision_rules"]
    return TabularCalibrationSpec(
        case_columns=("temperature_c", "storage_days"),
        observed_column="observed_recovery_rate",
        prediction_column="predicted_recovery_rate",
        required_constants={
            "storage_soc_pct": config["protocol"]["storage_soc_pct"],
            "aging_mode": config["protocol"]["aging_mode"],
        },
        sensitivity_threshold=rules["sensitivity_threshold"],
        response_correlation_threshold=rules[
            "response_correlation_threshold"
        ],
        max_selected_parameters=rules["max_selected_parameters"],
    )


def _parameters(config: dict[str, Any]) -> list[CalibrationParameter]:
    return [
        CalibrationParameter(**parameter)
        for parameter in config["parameters"]
    ]


def package_accepted_case(
    config: dict[str, Any],
    output_dir: Path,
) -> Path:
    """Package the accepted manual-screening result as a reusable baseline."""
    source_dir = HITHIUM_ROOT / config["accepted_results_dir"]
    required = [
        "calibration_comparison.csv",
        "sensitivity_summary.csv",
        "calibration_config.json",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in required:
        source = source_dir / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, output_dir / name)
    experiment = _build_experiment(config)
    experiment.to_csv(
        output_dir / "experiment_train_validation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    manifest = {
        "case_name": config["case_name"],
        "status": "accepted",
        "source_results": str(source_dir),
        "training_rule": (
            f"storage_days <= {config['training_max_days']}"
        ),
        "validation_rule": (
            f"storage_days > {config['training_max_days']}"
        ),
        "rerun_command": (
            "python BatteryProject/examples/"
            "calendar_aging_calibration_587.py --mode full"
        ),
    }
    (output_dir / "case_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("accepted", "full"),
        default="accepted",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    config = _read_config(args.config)
    output_dir = args.output_dir or (
        HITHIUM_ROOT
        / "BatteryProject"
        / "output"
        / "runs"
        / "tabular_calibration"
        / (
            "20260727_587_calendar_accepted_case"
            if args.mode == "accepted"
            else "20260727_587_calendar_automatic_v1"
        )
    )
    if args.mode == "accepted":
        result_dir = package_accepted_case(config, output_dir)
    else:
        optimizer = config["optimizer"]
        result = run_tabular_calibration(
            _build_experiment(config),
            _calibration_spec(config),
            _parameters(config),
            _build_simulation_function(config),
            output_dir=output_dir,
            cache_namespace=config["case_name"],
            method=optimizer["method"],
            method_params={
                key: value
                for key, value in optimizer.items()
                if key != "method"
            },
        )
        result_dir = result["output_dir"]
    print(f"Calibration case output: {result_dir}")


if __name__ == "__main__":
    main()
