"""587Ah EU battery regulation cycle-aging and DCR validation runner."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


WORKSPACE_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
TASK_ROOT = WORKSPACE_ROOT / "work" / "587Ah" / "202608_何争_587欧盟电池法循环DCR实测复核V1"
INPUT_DIR = TASK_ROOT / "03_输入数据"
RUNS_ROOT = PROJECT_ROOT / "output" / "runs" / "eu_battery_regulation"

for path in (WORKSPACE_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

from params587 import get_hithium_params as get_587_params  # noqa: E402
from src.analysis import compute_cycle_energies  # noqa: E402
from src.runtime import apply_pybamm_runtime_limits  # noqa: E402
from src.simulation import run_dcr_and_power_test  # noqa: E402


NOMINAL_CAPACITY_AH = 587.0
NOMINAL_VOLTAGE_V = 3.2
RATE_P = 0.5
TEMPERATURE_K = 298.15
ACCELERATION_FACTOR = 50
POWER_W = RATE_P * NOMINAL_CAPACITY_AH * NOMINAL_VOLTAGE_V
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 35, "r_p": 25}


def build_model() -> pybamm.BaseModel:
    """Return the established 587Ah DFN aging model without source edits."""
    return pybamm.lithium_ion.DFN(
        {
            "SEI": "ec reaction limited",
            "SEI porosity change": "true",
            "lithium plating": "irreversible",
            "lithium plating porosity change": "true",
            "particle mechanics": ("swelling and cracking", "swelling only"),
            "SEI on cracks": "true",
            "loss of active material": "stress-driven",
            "calculate discharge energy": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def make_parameter_getter(
    aging_scale: float,
    capacity_scale: float,
    sei_scale: float,
    sei_kinetic_scale: float,
    ec_diffusivity_scale: float,
    ec_diffusivity_schedule: tuple[float, ...],
    sei_molar_volume_scale: float,
    lam_scale: float,
    initial_sei_scale: float,
):
    """Create a task-local parameter wrapper; params587.py remains unchanged."""

    aging_block_index = 0

    def get_params(t_factor=1, temperature=TEMPERATURE_K):
        nonlocal aging_block_index
        effective_t_factor = float(t_factor)
        if effective_t_factor > 1:
            effective_t_factor *= aging_scale
        values = dict(get_587_params(effective_t_factor, temperature))
        if not math.isclose(capacity_scale, 1.0):
            values["Positive electrode active material volume fraction"] *= capacity_scale
            values["Negative electrode active material volume fraction"] *= capacity_scale
        if effective_t_factor > 1:
            current_ec_scale = (
                ec_diffusivity_schedule[aging_block_index]
                if aging_block_index < len(ec_diffusivity_schedule)
                else ec_diffusivity_scale
            )
            values["SEI kinetic rate constant [m.s-1]"] *= sei_scale * sei_kinetic_scale
            values["EC diffusivity [m2.s-1]"] *= sei_scale * current_ec_scale
            values["Negative electrode LAM constant proportional term [s-1]"] *= lam_scale
            aging_block_index += 1
        values["Initial SEI thickness [m]"] *= initial_sei_scale
        values["SEI partial molar volume [m3.mol-1]"] *= sei_molar_volume_scale
        return values

    return get_params


def latest_cycle_metrics(solution, baseline_capacity_ah=None) -> dict[str, float]:
    """Extract the latest discharge capacity, retention and energy efficiency."""
    result = compute_cycle_energies(solution)
    capacities = np.asarray(result["discharge_cap"], dtype=float)
    efficiencies = np.asarray(result["efficiency"], dtype=float)
    capacity_ah = float(capacities[-1]) if capacities.size else math.nan
    efficiency_pct = float(efficiencies[-1] * 100) if efficiencies.size else math.nan
    if baseline_capacity_ah is None or not np.isfinite(capacity_ah):
        retention_pct = math.nan
    else:
        retention_pct = capacity_ah / baseline_capacity_ah * 100
    return {
        "discharge_capacity_ah": capacity_ah,
        "capacity_retention_pct": retention_pct,
        "efficiency_pct": efficiency_pct,
    }


def build_checkpoint_table(rate_case) -> pd.DataFrame:
    """Build one row per DCR/capacity checkpoint from the packaged workflow."""
    cycles = sorted(int(value) for value in rate_case["dcr"])
    solutions = rate_case["sol_list"]
    if len(cycles) != len(solutions):
        raise RuntimeError(f"DCR/solution count mismatch: {len(cycles)} != {len(solutions)}")
    baseline = latest_cycle_metrics(solutions[0])["discharge_capacity_ah"]
    rows = []
    for cycle, solution in zip(cycles, solutions):
        metrics = latest_cycle_metrics(solution, baseline)
        rows.append(
            {
                "cycle": cycle,
                **metrics,
                "dcr_discharge_mohm": float(rate_case["dcr_discharge"][cycle]) * 1000,
                "dcr_charge_mohm": float(rate_case["dcr_charge"][cycle]) * 1000,
                "dcr_mean_mohm": float(rate_case["dcr"][cycle]) * 1000,
                "power_discharge_w": float(rate_case["power"][cycle]["power_discharge"]),
                "power_charge_w": float(rate_case["power"][cycle]["power_charge"]),
            }
        )
    return pd.DataFrame(rows)


def interpolate_row(model_df: pd.DataFrame, cycle: int) -> dict[str, float]:
    """Interpolate model checkpoint values at a requested real cycle."""
    x = model_df["cycle"].to_numpy(dtype=float)
    result = {"cycle": cycle}
    for column in (
        "discharge_capacity_ah",
        "capacity_retention_pct",
        "efficiency_pct",
        "dcr_discharge_mohm",
        "dcr_charge_mohm",
        "dcr_mean_mohm",
        "power_discharge_w",
        "power_charge_w",
    ):
        result[column] = float(np.interp(cycle, x, model_df[column].to_numpy(dtype=float)))
    return result


def compare_capacity(model_df: pd.DataFrame, exp_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Compare model and experiment in both Ah and percentage-point space."""
    measured_max = int(exp_df["cycle"].max())
    cycles = [int(c) for c in model_df["cycle"] if 100 <= c <= measured_max]
    if measured_max not in cycles and model_df["cycle"].max() >= measured_max:
        cycles.append(measured_max)
    rows = []
    exp_x = exp_df["cycle"].to_numpy(dtype=float)
    for cycle in sorted(set(cycles)):
        model_row = interpolate_row(model_df, cycle)
        exp_capacity = float(np.interp(cycle, exp_x, exp_df["mean_discharge_capacity_ah"]))
        exp_retention = float(np.interp(cycle, exp_x, exp_df["retention_vs_peak_pct"]))
        rows.append(
            {
                "cycle": cycle,
                "exp_capacity_ah": exp_capacity,
                "sim_capacity_ah": model_row["discharge_capacity_ah"],
                "capacity_error_ah": model_row["discharge_capacity_ah"] - exp_capacity,
                "capacity_relative_error_pct": (model_row["discharge_capacity_ah"] / exp_capacity - 1) * 100,
                "exp_retention_pct": exp_retention,
                "sim_retention_pct": model_row["capacity_retention_pct"],
                "retention_error_pp": model_row["capacity_retention_pct"] - exp_retention,
            }
        )
    comparison = pd.DataFrame(rows)
    rmse_ah = float(np.sqrt(np.mean(comparison["capacity_error_ah"] ** 2)))
    early = comparison[comparison["cycle"].isin([100, 200, 300])]
    metrics = {
        "retention_mae_pp": float(comparison["retention_error_pp"].abs().mean()),
        "retention_max_abs_error_pp": float(comparison["retention_error_pp"].abs().max()),
        "early_retention_mae_pp": float(early["retention_error_pp"].abs().mean()),
        "early_retention_max_abs_error_pp": float(early["retention_error_pp"].abs().max()),
        "capacity_rmse_ah": rmse_ah,
        "capacity_rrmse_pct": rmse_ah / float(comparison["exp_capacity_ah"].mean()) * 100,
        "comparison_points": int(len(comparison)),
    }
    return comparison, metrics


def compare_dcr(model_df: pd.DataFrame, exp_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Compare the protocol-matched discharge/charge/mean 50% SOC DCR branches."""
    grouped = exp_df.groupby("cycle", as_index=False).agg(
        exp_discharge_mohm=("discharge_path_discharge_dcr_mohm", "mean"),
        exp_charge_mohm=("discharge_path_charge_dcr_mohm", "mean"),
    )
    grouped["exp_mean_mohm"] = (grouped["exp_discharge_mohm"] + grouped["exp_charge_mohm"]) / 2
    rows = []
    for exp_row in grouped.itertuples(index=False):
        model_row = interpolate_row(model_df, int(exp_row.cycle))
        row = {
            "cycle": int(exp_row.cycle),
            "exp_discharge_mohm": float(exp_row.exp_discharge_mohm),
            "sim_discharge_mohm": model_row["dcr_discharge_mohm"],
            "exp_charge_mohm": float(exp_row.exp_charge_mohm),
            "sim_charge_mohm": model_row["dcr_charge_mohm"],
            "exp_mean_mohm": float(exp_row.exp_mean_mohm),
            "sim_mean_mohm": model_row["dcr_mean_mohm"],
        }
        for branch in ("discharge", "charge", "mean"):
            row[f"{branch}_relative_error_pct"] = (
                row[f"sim_{branch}_mohm"] / row[f"exp_{branch}_mohm"] - 1
            ) * 100
        rows.append(row)
    comparison = pd.DataFrame(rows)
    metrics = {
        "dcr_discharge_mape_pct": float(comparison["discharge_relative_error_pct"].abs().mean()),
        "dcr_charge_mape_pct": float(comparison["charge_relative_error_pct"].abs().mean()),
        "dcr_mean_mape_pct": float(comparison["mean_relative_error_pct"].abs().mean()),
        "dcr_discharge_max_abs_error_pct": float(comparison["discharge_relative_error_pct"].abs().max()),
        "dcr_mean_max_abs_error_pct": float(comparison["mean_relative_error_pct"].abs().max()),
    }
    return comparison, metrics


def save_plots(model_df, exp_capacity, capacity_cmp, dcr_cmp, output_dir):
    """Save report-ready scientific plots."""
    plots = output_dir / "plots"
    plots.mkdir(exist_ok=True)
    try:
        plt.style.use("science")
    except OSError:
        pass
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(exp_capacity["cycle"], exp_capacity["mean_discharge_capacity_ah"], label="实测均值", lw=1.8)
    ax.plot(model_df["cycle"], model_df["discharge_capacity_ah"], "o--", label="仿真", lw=1.5, ms=4)
    ax.set(xlabel="循环圈数", ylabel="放电容量 (Ah)")
    ax.grid(ls="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "capacity_sim_vs_exp.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(exp_capacity["cycle"], exp_capacity["retention_vs_peak_pct"], label="实测均值", lw=1.8)
    ax.plot(model_df["cycle"], model_df["capacity_retention_pct"], "o--", label="仿真", lw=1.5, ms=4)
    ax.scatter(capacity_cmp["cycle"], capacity_cmp["sim_retention_pct"], s=18)
    ax.set(xlabel="循环圈数", ylabel="容量保持率 (%)")
    ax.grid(ls="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots / "retention_sim_vs_exp.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(dcr_cmp["cycle"], dcr_cmp["exp_discharge_mohm"], "s-", label="实测放电 DCR")
    ax.plot(dcr_cmp["cycle"], dcr_cmp["sim_discharge_mohm"], "s--", label="仿真放电 DCR")
    ax.plot(dcr_cmp["cycle"], dcr_cmp["exp_mean_mohm"], "o-", label="实测充放平均 DCR")
    ax.plot(dcr_cmp["cycle"], dcr_cmp["sim_mean_mohm"], "o--", label="仿真充放平均 DCR")
    ax.set(xlabel="循环圈数", ylabel="50% SOC, 1C-30s DCR (mΩ)")
    ax.grid(ls="--", alpha=0.4)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(plots / "dcr_sim_vs_exp.png", dpi=220)
    plt.close(fig)


def run(args) -> Path:
    """Execute one validation/projection case and save machine-checkable outputs."""
    if args.total_real_cycles % ACCELERATION_FACTOR:
        raise ValueError("total-real-cycles must be divisible by 50")
    if args.interval_real_cycles % ACCELERATION_FACTOR:
        raise ValueError("interval-real-cycles must be divisible by 50")
    total_sim_cycles = args.total_real_cycles // ACCELERATION_FACTOR
    cycles_per_block = args.interval_real_cycles // ACCELERATION_FACTOR
    output_dir = RUNS_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    apply_pybamm_runtime_limits()
    model = build_model()
    solver = pybamm.IDAKLUSolver()
    ec_diffusivity_schedule = tuple(
        float(value) for value in args.early_ec_schedule.split(",") if value.strip()
    )
    parameter_getter = make_parameter_getter(
        args.aging_scale,
        args.capacity_scale,
        args.sei_scale,
        args.sei_kinetic_scale,
        args.ec_diffusivity_scale,
        ec_diffusivity_schedule,
        args.sei_molar_volume_scale,
        args.lam_scale,
        args.initial_sei_scale,
    )
    result = run_dcr_and_power_test(
        rate_range=[RATE_P],
        model=model,
        solver=solver,
        var_pts=VAR_PTS,
        get_hithium_params=parameter_getter,
        total_cycles=total_sim_cycles,
        cycles_per_block=cycles_per_block,
        temperature=TEMPERATURE_K,
        nominal_current=NOMINAL_CAPACITY_AH,
        nominal_voltage=NOMINAL_VOLTAGE_V,
        target_soc=0.5,
        conditioning_t_factor=1,
        aging_t_factor=ACCELERATION_FACTOR,
        record_conditioning_cycle=True,
        conditioning_cycle_number=0,
        cycle_number_factor=ACCELERATION_FACTOR,
        dcr_charge_c_rate=0.5,
        dcr_pulse_c_rate=1.0,
        dcr_pulse_duration_s=30.0,
        charge_cutoff_v=3.65,
        discharge_cutoff_v=2.5,
        conditioning_charge_cutoff_v=3.65,
        rest_minutes=10,
        period_minutes=0.5,
        use_explicit_power_steps=False,
        keep_only_last_cycle_solution=True,
        return_solutions=True,
        showprogress=args.show_progress,
    )
    model_df = build_checkpoint_table(result["rate_results"][RATE_P])
    exp_capacity = pd.read_csv(INPUT_DIR / "capacity_25c_0p5p_20260828.csv")
    exp_dcr = pd.read_csv(INPUT_DIR / "dcr_50soc_1c30s_20260828.csv")
    capacity_cmp, capacity_metrics = compare_capacity(model_df, exp_capacity)
    dcr_cmp, dcr_metrics = compare_dcr(model_df, exp_dcr)

    model_bol = float(model_df.loc[model_df["cycle"] == 0, "discharge_capacity_ah"].iloc[0])
    exp_bol = float(exp_capacity["mean_discharge_capacity_ah"].max())
    summary = {
        "mode": args.mode,
        "run_id": args.run_id,
        "aging_scale": args.aging_scale,
        "capacity_scale": args.capacity_scale,
        "sei_scale": args.sei_scale,
        "sei_kinetic_scale": args.sei_kinetic_scale,
        "ec_diffusivity_scale": args.ec_diffusivity_scale,
        "early_ec_schedule": list(ec_diffusivity_schedule),
        "sei_molar_volume_scale": args.sei_molar_volume_scale,
        "lam_scale": args.lam_scale,
        "initial_sei_scale": args.initial_sei_scale,
        "total_real_cycles": args.total_real_cycles,
        "interval_real_cycles": args.interval_real_cycles,
        "rated_power_w": POWER_W,
        "model_bol_capacity_ah": model_bol,
        "exp_bol_capacity_ah": exp_bol,
        "bol_capacity_bias_pct": (model_bol / exp_bol - 1) * 100,
        **capacity_metrics,
        **dcr_metrics,
    }
    summary["early_accept"] = (
        summary["early_retention_mae_pp"] <= 0.3
        and summary["early_retention_max_abs_error_pp"] <= 0.5
    )
    summary["capacity_accept"] = (
        summary["early_accept"]
        and summary["retention_mae_pp"] <= 0.5
        and summary["retention_max_abs_error_pp"] <= 1.0
        and summary["capacity_rrmse_pct"] <= 1.0
    )
    summary["dcr_accept"] = (
        summary["dcr_discharge_mape_pct"] <= 5.0 and summary["dcr_mean_mape_pct"] <= 7.0
    )
    summary["overall_accept"] = summary["capacity_accept"] and summary["dcr_accept"]

    config = vars(args) | {
        "nominal_capacity_ah": NOMINAL_CAPACITY_AH,
        "nominal_voltage_v": NOMINAL_VOLTAGE_V,
        "rate_p": RATE_P,
        "power_w": POWER_W,
        "temperature_k": TEMPERATURE_K,
        "acceleration_factor": ACCELERATION_FACTOR,
        "var_pts": VAR_PTS,
        "pybamm_version": pybamm.__version__,
    }
    model_df.to_csv(output_dir / "model_checkpoints.csv", index=False, encoding="utf-8-sig")
    capacity_cmp.to_csv(output_dir / "capacity_comparison.csv", index=False, encoding="utf-8-sig")
    dcr_cmp.to_csv(output_dir / "dcr_comparison.csv", index=False, encoding="utf-8-sig")
    (output_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_plots(model_df, exp_capacity, capacity_cmp, dcr_cmp, output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"OUTPUT_DIR={output_dir}")
    return output_dir


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=("validate", "projection"), default="validate")
    parser.add_argument("--total-real-cycles", type=int, default=1800)
    parser.add_argument("--interval-real-cycles", type=int, default=100)
    parser.add_argument("--aging-scale", type=float, default=1.0)
    parser.add_argument("--capacity-scale", type=float, default=1.0)
    parser.add_argument("--sei-scale", type=float, default=1.0)
    parser.add_argument("--sei-kinetic-scale", type=float, default=1.0)
    parser.add_argument("--ec-diffusivity-scale", type=float, default=1.0)
    parser.add_argument("--early-ec-schedule", default="")
    parser.add_argument("--sei-molar-volume-scale", type=float, default=1.0)
    parser.add_argument("--lam-scale", type=float, default=1.0)
    parser.add_argument("--initial-sei-scale", type=float, default=1.0)
    parser.add_argument("--show-progress", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
