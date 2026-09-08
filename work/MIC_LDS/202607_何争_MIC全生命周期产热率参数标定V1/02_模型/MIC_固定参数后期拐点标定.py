from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pybamm


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
RUNS_ROOT = PROJECT_ROOT / "output" / "runs" / "mic_fixed_parameter_knee_calibration"

for path in (PROJECT_ROOT, PARAMS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from paramsMIC import get_hithium_params as base_get_hithium_params  # noqa: E402
from src.runtime import apply_pybamm_runtime_limits  # noqa: E402
from src.simulation import (  # noqa: E402
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    run_pulse_lifecycle_scenarios,
)


apply_pybamm_runtime_limits()

EXPERIMENT_CAPACITY_RETENTION = {
    200: 0.9745491214,
    400: 0.9615100362,
    600: 0.9510080075,
}
BASE_PARIS_M = 2.2
NOMINAL_CAPACITY_AH = 1175.0
TEMPERATURE_K = 298.15
AGING_P_RATE = 0.25
CONTACT_RESISTANCE_OHM = 0.07018e-3
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate a single fixed Paris-law parameter set for the MIC late-life knee."
    )
    parser.add_argument("--paris-m", type=float, required=True)
    parser.add_argument("--reference-dk", type=float, default=14_000.0)
    parser.add_argument("--cracking-rate-scale", type=float, default=1.0)
    parser.add_argument("--lam-scale", type=float, default=1.0)
    parser.add_argument("--sei-scale", type=float, default=1.0)
    parser.add_argument("--total-real-cycles", type=int, default=600)
    parser.add_argument("--acceleration-factor", type=float, default=50.0)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--showprogress", action="store_true")
    return parser.parse_args()


def build_parameter_loader(
    paris_m: float,
    reference_dk: float,
    cracking_rate_scale: float,
    lam_scale: float,
    sei_scale: float,
):
    if min(paris_m, reference_dk, cracking_rate_scale, lam_scale, sei_scale) <= 0:
        raise ValueError("All calibration parameters must be positive")
    normalization = reference_dk ** (BASE_PARIS_M - paris_m)

    def load_params(t_factor=1, temperature=298.15):
        values = base_get_hithium_params(t_factor, temperature=temperature)
        base_cracking_rate = values["Negative electrode cracking rate"]

        def calibrated_cracking_rate(cell_temperature):
            return base_cracking_rate(cell_temperature) * normalization * cracking_rate_scale

        values["Negative electrode Paris' law constant m"] = paris_m
        values["Negative electrode cracking rate"] = calibrated_cracking_rate
        values["Negative electrode LAM constant proportional term [s-1]"] *= lam_scale
        values["SEI kinetic rate constant [m.s-1]"] *= sei_scale
        values["EC diffusivity [m2.s-1]"] *= sei_scale
        values["Contact resistance [Ohm]"] = CONTACT_RESISTANCE_OHM
        return values

    return load_params, normalization


def interpolate_at_cycles(main_df: pd.DataFrame, cycles: list[int]) -> pd.DataFrame:
    x = main_df["real_cycle"].to_numpy(dtype=float)
    rows = []
    for cycle in cycles:
        row = {"real_cycle": cycle}
        for column in [
            "capacity_retention",
            "discharge_capacity_ah",
            "q_sei_ah",
            "q_sei_on_cracks_ah",
            "negative_porosity_avg",
            "lli_ah",
            "lam_neg_ah",
        ]:
            row[column] = float(np.interp(cycle, x, main_df[column].to_numpy(dtype=float)))
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RUNS_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    parameter_loader, normalization = build_parameter_loader(
        args.paris_m,
        args.reference_dk,
        args.cracking_rate_scale,
        args.lam_scale,
        args.sei_scale,
    )
    runtime_config = {
        "total_cycles": args.total_real_cycles,
        "use_block_acceleration": True,
        "cycles_per_block": 1,
        "aging_t_factor": args.acceleration_factor,
        "conditioning_t_factor": 1,
        "capacity_check_interval_cycles": None,
        "capacity_check_at_start": False,
        "diagnostic_soh_targets_pct": (),
        "diagnostic_p_rates": (0.25,),
        "stop_at_lowest_diagnostic_soh": False,
        "return_partial_on_error": True,
        "showprogress": args.showprogress,
    }
    model_options = dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)
    scenarios = [{
        "name": "mic_fixed_parameter_knee",
        "display_name": "MIC 25C 0.25P fixed-parameter late-life knee calibration",
        "pulse_p_rate": None,
        "enabled": True,
    }]
    config = {
        "paris_m": args.paris_m,
        "base_paris_m": BASE_PARIS_M,
        "reference_dk": args.reference_dk,
        "cracking_rate_scale": args.cracking_rate_scale,
        "lam_scale": args.lam_scale,
        "sei_scale": args.sei_scale,
        "normalization": normalization,
        "total_real_cycles": args.total_real_cycles,
        "acceleration_factor": args.acceleration_factor,
        "temperature_k": TEMPERATURE_K,
        "aging_p_rate": AGING_P_RATE,
        "contact_resistance_ohm": CONTACT_RESISTANCE_OHM,
        "var_pts": VAR_PTS,
        "pybamm_version": pybamm.__version__,
    }
    (output_dir / "运行配置.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    started = time.time()
    result = run_pulse_lifecycle_scenarios(
        scenarios,
        runtime_config,
        model_options=model_options,
        var_pts=VAR_PTS,
        nominal_capacity_ah=NOMINAL_CAPACITY_AH,
        temperature_k=TEMPERATURE_K,
        get_hithium_params=parameter_loader,
        base_p_rate=AGING_P_RATE,
        nominal_voltage_v=3.2,
        charge_cutoff_v=3.65,
        discharge_cutoff_v=2.5,
        rest_minutes=10.0,
        period_minutes=0.5,
        solver_rtol=1e-6,
        solver_atol=1e-6,
        keep_only_last_cycle_solution=True,
        keep_only_last_capacity_check_solution=True,
        return_solutions=False,
    )
    bundle = result["results"]["mic_fixed_parameter_knee"]
    main_df = bundle["main_df"].copy()
    main_df.to_csv(output_dir / "全生命周期主线.csv", index=False, encoding="utf-8-sig")

    requested_cycles = [200, 400, 600]
    if args.total_real_cycles >= 10_000:
        requested_cycles.extend([10_000, 15_000])
    requested_cycles = [cycle for cycle in requested_cycles if cycle <= args.total_real_cycles]
    checkpoints = interpolate_at_cycles(main_df, requested_cycles)
    checkpoints["experiment_capacity_retention"] = checkpoints["real_cycle"].map(
        EXPERIMENT_CAPACITY_RETENTION
    )
    checkpoints["capacity_error_pct_point"] = (
        checkpoints["capacity_retention"] - checkpoints["experiment_capacity_retention"]
    ) * 100.0
    checkpoints.to_csv(output_dir / "目标圈数汇总.csv", index=False, encoding="utf-8-sig")

    early = checkpoints.dropna(subset=["experiment_capacity_retention"])
    early_rmse = float(np.sqrt(np.mean(early["capacity_error_pct_point"] ** 2)))
    row_15000 = checkpoints.loc[checkpoints["real_cycle"].eq(15_000)]
    soh_15000 = float(row_15000["capacity_retention"].iloc[0]) if not row_15000.empty else np.nan
    summary = {
        **config,
        "run_status": bundle["run_status"],
        "real_cycles_covered": bundle["real_cycles_covered"],
        "last_valid_soh_pct": bundle["last_valid_soh_pct"],
        "early_capacity_rmse_pct_point": early_rmse,
        "soh_15000_pct": soh_15000 * 100.0 if np.isfinite(soh_15000) else None,
        "target_error_15000_pct_point": (
            (soh_15000 - 0.65) * 100.0 if np.isfinite(soh_15000) else None
        ),
        "elapsed_s": time.time() - started,
        "failure_message": bundle["failure_message"],
    }
    (output_dir / "结果摘要.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(checkpoints.to_string(index=False))
    print(f"Saved to: {output_dir}")


if __name__ == "__main__":
    main()
