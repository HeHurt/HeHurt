"""Final-OCV-smoothed CW363 charge/discharge static SOC-OCV calibration.

The calibration fits a full-cell OCV correction around the unmodified PyBaMM
baseline, while regularizing the curvature of the final OCV rather than the
correction alone. Endpoint voltages are high-weight soft observations, not hard
equalities. Endpoint stoichiometries remain those from the unmodified 940 W
charge/discharge protocol; this script does not identify an electrode OCP.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm
from scipy.interpolate import PchipInterpolator
from scipy.optimize import Bounds, LinearConstraint, minimize


TASK_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = Path(__file__).resolve().parent
RUNS_ROOT = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "cw363_soc_ocv"
PREVIOUS_RUN = TASK_ROOT / "04_输出结果" / "20260901_143404_full_charge_discharge"
TEMPERATURES = (25.0, 45.0)
DIRECTIONS = ("charge", "discharge")
REGULARIZATION_CANDIDATES = np.asarray([0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0])
MODEL_PRIOR_WEIGHT = 0.001
ENDPOINT_DATA_WEIGHT = 25.0


def load_legacy_module():
    path = SCRIPT_DIR / "cw363_full_soc_ocv_validation.py"
    spec = importlib.util.spec_from_file_location("cw363_full_validation", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


legacy = load_legacy_module()


def baseline_values(temperature_c, endpoints, direction, soc_values):
    parameters = legacy.fresh_parameters(temperature_c + 273.15)
    values = []
    for soc in np.asarray(soc_values, dtype=float):
        ocv, _, _ = legacy.branch_ocv(
            parameters, endpoints, float(soc), temperature_c + 273.15, direction
        )
        values.append(ocv)
    return np.asarray(values)


def anchor_matrix():
    matrix = np.zeros((21, 101))
    matrix[np.arange(21), np.arange(0, 101, 5)] = 1
    return matrix


def fit_regularized_correction(residual_v, baseline_dense_v, matrix, regularization, train_mask=None):
    dense_count = len(baseline_dense_v)
    weights = np.ones(len(residual_v)) if train_mask is None else np.asarray(train_mask, dtype=float)
    weights[[0, -1]] *= ENDPOINT_DATA_WEIGHT
    first_difference = np.diff(np.eye(dense_count), axis=0)
    second_difference = np.diff(np.eye(dense_count), n=2, axis=0)
    weighted_matrix = weights[:, None] * matrix
    hessian = (
        matrix.T @ weighted_matrix
        + regularization * second_difference.T @ second_difference
        + MODEL_PRIOR_WEIGHT * np.eye(dense_count)
    )
    baseline_roughness = second_difference @ baseline_dense_v
    rhs = (
        matrix.T @ (weights * residual_v)
        - regularization * second_difference.T @ baseline_roughness
    )
    initial = np.linalg.solve(hessian, rhs)
    constraint_lower = -(first_difference @ baseline_dense_v)
    def objective(correction):
        data_error = np.sqrt(weights) * (matrix @ correction - residual_v)
        roughness = second_difference @ (baseline_dense_v + correction)
        return float(
            data_error @ data_error
            + regularization * (roughness @ roughness)
            + MODEL_PRIOR_WEIGHT * (correction @ correction)
        )

    def gradient(correction):
        return 2 * (hessian @ correction - rhs)

    result = minimize(
        objective,
        initial,
        jac=gradient,
        method="SLSQP",
        bounds=Bounds(-0.30, 0.30),
        constraints=[LinearConstraint(first_difference, constraint_lower, np.inf)],
        options={"ftol": 1e-13, "maxiter": 800},
    )
    if not result.success:
        raise RuntimeError(f"Constrained correction fit failed: {result.message}")
    correction_dense = np.asarray(result.x)
    return matrix @ correction_dense, correction_dense


def fit_unconstrained_correction(
    residual_v, baseline_dense_v, matrix, regularization, train_mask=None
):
    dense_count = matrix.shape[1]
    weights = np.ones(len(residual_v)) if train_mask is None else np.asarray(train_mask, dtype=float)
    weights[[0, -1]] *= ENDPOINT_DATA_WEIGHT
    second_difference = np.diff(np.eye(dense_count), n=2, axis=0)
    weighted_matrix = weights[:, None] * matrix
    hessian = (
        matrix.T @ weighted_matrix
        + regularization * second_difference.T @ second_difference
        + MODEL_PRIOR_WEIGHT * np.eye(dense_count)
    )
    rhs = (
        matrix.T @ (weights * residual_v)
        - regularization
        * second_difference.T
        @ (second_difference @ baseline_dense_v)
    )
    correction = np.linalg.solve(hessian, rhs)
    return matrix @ correction, correction


def select_regularization(x, measured_mean_v, baseline_anchor_v, baseline_dense_v, dense_soc):
    del x, dense_soc
    residual = measured_mean_v - baseline_anchor_v
    matrix = anchor_matrix()
    rows = []
    for regularization in REGULARIZATION_CANDIDATES:
        squared_errors = []
        for index in range(1, len(residual) - 1):
            train_mask = np.ones(len(residual))
            train_mask[index] = 0
            correction_anchor, _ = fit_unconstrained_correction(
                residual, baseline_dense_v, matrix, regularization, train_mask
            )
            prediction = baseline_anchor_v[index] + correction_anchor[index]
            squared_errors.append((prediction - measured_mean_v[index]) ** 2)
        correction_anchor, correction_dense = fit_regularized_correction(
            residual, baseline_dense_v, matrix, regularization
        )
        calibrated_dense = baseline_dense_v + correction_dense
        mse = float(np.mean(squared_errors))
        rows.append(
            {
                "regularization_lambda": float(regularization),
                "soc_loo_rmse_mv": float(np.sqrt(mse) * 1000),
                "anchor_rmse_mv": float(
                    np.sqrt(np.mean((baseline_anchor_v + correction_anchor - measured_mean_v) ** 2))
                    * 1000
                ),
                "min_slope_mv_per_pct": float(np.min(np.diff(calibrated_dense)) * 1000),
                "monotonic_non_decreasing": bool(np.min(np.diff(calibrated_dense)) >= -1e-10),
            }
        )
    candidates = pd.DataFrame(rows)
    cv_minimum = float(candidates["soc_loo_rmse_mv"].min())
    eligible = candidates[candidates["soc_loo_rmse_mv"] <= cv_minimum + 0.5]
    selected_index = eligible["regularization_lambda"].idxmin()
    selected = candidates.loc[selected_index].to_dict()
    selected["cv_minimum_rmse_mv"] = cv_minimum
    selected["cv_selection_tolerance_mv"] = 0.5
    correction_anchor, correction_dense = fit_regularized_correction(
        residual, baseline_dense_v, matrix, selected["regularization_lambda"]
    )
    return correction_anchor, correction_dense, selected, candidates, matrix


def calibration_inputs(raw, temperature_c, direction):
    subset = raw[
        (raw["temperature_c"] == temperature_c)
        & (raw["rate_p"] == 0.25)
        & (raw["direction"] == direction)
    ].copy()
    pivot = subset.pivot(index="soc_pct", columns="cell_id", values="rested_voltage_v").sort_index()
    x = pivot.index.to_numpy(dtype=float) / 100
    return x, pivot.mean(axis=1).to_numpy(), pivot


def calibrate_temperature(raw, temperature_c):
    parameters, endpoints, timeseries = legacy.run_endpoint_protocol(temperature_c)
    fits = {}
    for direction in DIRECTIONS:
        x, measured_mean, pivot = calibration_inputs(raw, temperature_c, direction)
        dense_soc = np.linspace(0, 1, 101)
        baseline_anchor = baseline_values(temperature_c, endpoints, direction, x)
        baseline_dense = baseline_values(temperature_c, endpoints, direction, dense_soc)
        correction_anchor, correction_dense, selected, candidates, matrix = select_regularization(
            x, measured_mean, baseline_anchor, baseline_dense, dense_soc
        )
        fits[direction] = {
            "x": x,
            "measured_mean": measured_mean,
            "pivot": pivot,
            "correction_anchor_v": correction_anchor,
            "correction_dense_v": correction_dense,
            "matrix": matrix,
            "baseline_dense_v": baseline_dense,
            "selected": selected,
            "candidates": candidates,
        }
    return {
        "parameters": parameters,
        "endpoints": endpoints,
        "timeseries": timeseries,
        "fits": fits,
    }


def cell_holdout_rmse(temperature_c, endpoints, direction, x, pivot, regularization, matrix):
    dense_soc = np.linspace(0, 1, 101)
    baseline_anchor = baseline_values(temperature_c, endpoints, direction, x)
    baseline_dense = baseline_values(temperature_c, endpoints, direction, dense_soc)
    errors = []
    for train_cell, test_cell in ((1, 2), (2, 1)):
        residual = pivot[train_cell].to_numpy() - baseline_anchor
        correction_anchor, _ = fit_regularized_correction(
            residual, baseline_dense, matrix, regularization
        )
        prediction = baseline_anchor + correction_anchor
        errors.extend(prediction - pivot[test_cell].to_numpy())
    errors = np.asarray(errors)
    return float(np.sqrt(np.mean(errors**2)) * 1000), float(np.max(np.abs(errors)) * 1000)


def build_outputs(raw, calibrations):
    curve_rows = []
    point_rows = []
    metric_rows = []
    cv_rows = []
    previous = pd.read_csv(PREVIOUS_RUN / "charge_discharge_soc_ocv_1pct.csv")
    for temperature_c, calibration in calibrations.items():
        endpoints = calibration["endpoints"]
        parameters = calibration["parameters"]
        for direction in DIRECTIONS:
            fit = calibration["fits"][direction]
            x = fit["x"]
            pivot = fit["pivot"]
            selected = fit["selected"]
            holdout_rmse, holdout_max = cell_holdout_rmse(
                temperature_c,
                endpoints,
                direction,
                x,
                pivot,
                selected["regularization_lambda"],
                fit["matrix"],
            )
            pchip = PchipInterpolator(x, fit["measured_mean"])
            dense_pct = np.arange(101)
            for soc_pct in dense_pct:
                soc = soc_pct / 100
                base_parameters = legacy.fresh_parameters(temperature_c + 273.15)
                baseline_ocv, xn, xp = legacy.branch_ocv(
                    base_parameters, endpoints, soc, temperature_c + 273.15, direction
                )
                smooth_ocv = baseline_ocv + float(fit["correction_dense_v"][soc_pct])
                curve_rows.append(
                    {
                        "temperature_c": temperature_c,
                        "direction": direction,
                        "soc_pct": soc_pct,
                        "xn": xn,
                        "xp": xp,
                        "baseline_pybamm_ocv_v": baseline_ocv,
                        "smooth_calibrated_ocv_v": smooth_ocv,
                        "empirical_pchip_ocv_v": float(pchip(soc)),
                        "smooth_full_cell_correction_mv": (smooth_ocv - baseline_ocv) * 1000,
                    }
                )
            for soc, cell_1, cell_2 in zip(x, pivot[1], pivot[2]):
                baseline_ocv = baseline_values(
                    temperature_c, endpoints, direction, [soc]
                )[0]
                anchor_index = int(round(soc * 20))
                smooth_ocv = baseline_ocv + float(fit["correction_anchor_v"][anchor_index])
                mean_ocv = (cell_1 + cell_2) / 2
                point_rows.append(
                    {
                        "temperature_c": temperature_c,
                        "direction": direction,
                        "soc_pct": soc * 100,
                        "cell_1_ocv_v": cell_1,
                        "cell_2_ocv_v": cell_2,
                        "measured_mean_ocv_v": mean_ocv,
                        "smooth_calibrated_ocv_v": smooth_ocv,
                        "smooth_minus_mean_mv": (smooth_ocv - mean_ocv) * 1000,
                    }
                )
            points = [row for row in point_rows if row["temperature_c"] == temperature_c and row["direction"] == direction]
            errors = np.asarray([row["smooth_minus_mean_mv"] for row in points])
            curve = [row for row in curve_rows if row["temperature_c"] == temperature_c and row["direction"] == direction]
            slopes = np.diff([row["smooth_calibrated_ocv_v"] for row in curve]) * 1000
            metric_rows.append(
                {
                    "temperature_c": temperature_c,
                    "direction": direction,
                    "anchor_rmse_mv": float(np.sqrt(np.mean(errors**2))),
                    "anchor_max_abs_error_mv": float(np.max(np.abs(errors))),
                    "soc_loo_rmse_mv": selected["soc_loo_rmse_mv"],
                    "cell_holdout_rmse_mv": holdout_rmse,
                    "cell_holdout_max_abs_error_mv": holdout_max,
                    "selected_regularization_lambda": selected["regularization_lambda"],
                    "min_1pct_slope_mv_per_pct": float(np.min(slopes)),
                    "endpoint_basis": "unmodified PyBaMM 940W protocol",
                }
            )
            candidates = fit["candidates"].copy()
            candidates.insert(0, "direction", direction)
            candidates.insert(0, "temperature_c", temperature_c)
            candidates["selected"] = np.isclose(
                candidates["regularization_lambda"], selected["regularization_lambda"]
            )
            cv_rows.append(candidates)
    curves = pd.DataFrame(curve_rows)
    prior_columns = previous[
        ["temperature_c", "direction", "soc_pct", "calibrated_ocv_v"]
    ].rename(columns={"calibrated_ocv_v": "previous_forced_pchip_ocv_v"})
    curves = curves.merge(prior_columns, on=["temperature_c", "direction", "soc_pct"], how="left")
    return curves, pd.DataFrame(point_rows), pd.DataFrame(metric_rows), pd.concat(cv_rows, ignore_index=True)


def plot_comparison(curves, points, output_path):
    plt.style.use("science")
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.4), sharex=True, sharey=True)
    colors = {"baseline": "#777777", "smooth": "#005BAC", "pchip": "#D1495B"}
    for row, temperature_c in enumerate(TEMPERATURES):
        for column, direction in enumerate(DIRECTIONS):
            ax = axes[row, column]
            c = curves[(curves["temperature_c"] == temperature_c) & (curves["direction"] == direction)]
            p = points[(points["temperature_c"] == temperature_c) & (points["direction"] == direction)]
            ax.plot(c["soc_pct"], c["baseline_pybamm_ocv_v"], color=colors["baseline"], linewidth=1.1, label="Original PyBaMM")
            ax.plot(c["soc_pct"], c["smooth_calibrated_ocv_v"], color=colors["smooth"], linewidth=1.8, label="Smooth calibrated")
            ax.plot(c["soc_pct"], c["previous_forced_pchip_ocv_v"], color=colors["pchip"], linestyle="--", linewidth=1.1, label="Previous forced PCHIP")
            ax.scatter(p["soc_pct"], p["cell_1_ocv_v"], facecolors="none", edgecolors="#111111", marker="o", s=18, label="Cell 1 Exp")
            ax.scatter(p["soc_pct"], p["cell_2_ocv_v"], facecolors="none", edgecolors="#777777", marker="s", s=18, label="Cell 2 Exp")
            ax.set_title(f"{temperature_c:.0f}°C {direction.title()} Static SOC-OCV")
            ax.set_xlabel("SOC (%)")
            ax.set_ylabel("OCV (V)")
            ax.grid(alpha=0.22)
            if row == 0 and column == 0:
                ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=260)
    plt.close(fig)


def plot_diagnostics(curves, points, output_path):
    plt.style.use("science")
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.6), sharex=True)
    direction_colors = {"charge": "#005BAC", "discharge": "#D1495B"}
    for column, temperature_c in enumerate(TEMPERATURES):
        for direction in DIRECTIONS:
            c = curves[(curves["temperature_c"] == temperature_c) & (curves["direction"] == direction)]
            p = points[(points["temperature_c"] == temperature_c) & (points["direction"] == direction)]
            axes[0, column].plot(c["soc_pct"], c["smooth_full_cell_correction_mv"], color=direction_colors[direction], label=direction.title())
            axes[1, column].plot(p["soc_pct"], p["smooth_minus_mean_mv"], color=direction_colors[direction], marker="o", markersize=3, label=direction.title())
        axes[0, column].axhline(0, color="#555555", linewidth=0.7)
        axes[0, column].set_title(f"{temperature_c:.0f}°C Smooth Full-cell OCV Correction")
        axes[0, column].set_ylabel("Correction (mV)")
        axes[0, column].grid(alpha=0.22)
        axes[0, column].legend(fontsize=8)
        axes[1, column].axhline(0, color="#555555", linewidth=0.7)
        axes[1, column].set_title(f"{temperature_c:.0f}°C Anchor Residual")
        axes[1, column].set_xlabel("SOC (%)")
        axes[1, column].set_ylabel("Smooth Sim - mean Exp (mV)")
        axes[1, column].grid(alpha=0.22)
    fig.tight_layout()
    fig.savefig(output_path, dpi=260)
    plt.close(fig)


def main():
    raw, _ = legacy.load_source_measurements()
    calibrations = {
        temperature_c: calibrate_temperature(raw, temperature_c)
        for temperature_c in TEMPERATURES
    }
    curves, points, metrics, cv = build_outputs(raw, calibrations)
    run_dir = RUNS_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S_final_ocv_smooth")
    run_dir.mkdir(parents=True, exist_ok=False)
    curves.to_csv(run_dir / "smooth_soc_ocv_1pct.csv", index=False, encoding="utf-8-sig")
    points.to_csv(run_dir / "smooth_validation_points.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(run_dir / "smooth_validation_metrics.csv", index=False, encoding="utf-8-sig")
    cv.to_csv(run_dir / "smoothing_cross_validation.csv", index=False, encoding="utf-8-sig")
    endpoint_rows = []
    for temperature_c, calibration in calibrations.items():
        endpoint_rows.append(calibration["endpoints"])
    pd.DataFrame(endpoint_rows).to_csv(
        run_dir / "protocol_endpoint_stoichiometry.csv", index=False, encoding="utf-8-sig"
    )
    plot_comparison(curves, points, run_dir / "smooth_vs_pchip_comparison.png")
    plot_diagnostics(curves, points, run_dir / "smooth_correction_diagnostics.png")
    manifest = {
        "method": "PyBaMM baseline plus constrained correction with final-OCV curvature and model-prior penalties",
        "not_direct_target_interpolation": True,
        "smoothing_selection": "weakest regularization within 0.5 mV of minimum internal-SOC leave-one-out RMSE; endpoint voltages are 25x weighted soft observations; final 1% curve constrained non-decreasing and final OCV curvature is regularized",
        "cell_validation": "cell 1 to cell 2 and cell 2 to cell 1 holdout at measured SOC anchors",
        "power_w": legacy.POWER_W,
        "rest_hours": legacy.REST_HOURS,
        "endpoint_basis": "unmodified CW363 940 W charge/discharge cutoff protocol with 3 h rest",
        "dynamic_model_parameter_replacement": False,
        "pybamm_version": pybamm.__version__,
        "metrics": metrics.to_dict(orient="records"),
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(run_dir)
    print("\nMetrics:\n", metrics.to_string(index=False))
    print("\nEndpoints:\n", pd.DataFrame(endpoint_rows).to_string(index=False))


if __name__ == "__main__":
    main()
