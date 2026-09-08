from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
OUTPUT_ROOT = WORKSPACE_ROOT / "work" / "587Ah" / "outputs"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.insert(0, str(PARAMS_ROOT))

from params587 import get_hithium_params  # noqa: E402
from src.analysis import compute_cycle_energies  # noqa: E402
from src.runtime import apply_pybamm_runtime_limits  # noqa: E402
from src.simulation import run_dcr_and_power_test  # noqa: E402

apply_pybamm_runtime_limits()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 587Ah EU-style lifecycle DCR simulation at 0.5P.",
    )
    parser.add_argument("--total-real-cycles", type=int, default=13000)
    parser.add_argument("--dcr-interval-real-cycles", type=int, default=1000)
    parser.add_argument("--acceleration-factor", type=int, default=50)
    parser.add_argument("--rate-p", type=float, default=0.5)
    parser.add_argument("--temperature-k", type=float, default=298.15)
    parser.add_argument("--nominal-current-a", type=float, default=587.0)
    parser.add_argument("--nominal-voltage-v", type=float, default=3.2)
    parser.add_argument("--charge-cutoff-v", type=float, default=3.65)
    parser.add_argument("--discharge-cutoff-v", type=float, default=2.5)
    parser.add_argument("--rest-minutes", type=float, default=10.0)
    parser.add_argument("--period-minutes", type=float, default=0.5)
    parser.add_argument("--dcr-target-soc", type=float, default=0.5)
    parser.add_argument("--dcr-charge-c-rate", type=float, default=0.5)
    parser.add_argument("--dcr-pulse-c-rate", type=float, default=1.0)
    parser.add_argument("--dcr-pulse-duration-s", type=float, default=30.0)
    parser.add_argument("--conditioning-t-factor", type=float, default=1.0)
    parser.add_argument("--start-dcr-cycle-number", type=int, default=0)
    parser.add_argument("--skip-start-dcr", dest="record_start_dcr", action="store_false")
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--showprogress", action="store_true")
    parser.set_defaults(record_start_dcr=True)
    return parser.parse_args()


def validate_config(args: argparse.Namespace) -> tuple[int, int]:
    if args.total_real_cycles <= 0:
        raise ValueError("--total-real-cycles must be positive")
    if args.dcr_interval_real_cycles <= 0:
        raise ValueError("--dcr-interval-real-cycles must be positive")
    if args.acceleration_factor <= 0:
        raise ValueError("--acceleration-factor must be positive")
    if not 0.0 <= args.dcr_target_soc <= 1.0:
        raise ValueError("--dcr-target-soc must be between 0 and 1")
    if args.total_real_cycles % args.acceleration_factor != 0:
        raise ValueError("--total-real-cycles must be divisible by --acceleration-factor")
    if args.dcr_interval_real_cycles % args.acceleration_factor != 0:
        raise ValueError("--dcr-interval-real-cycles must be divisible by --acceleration-factor")
    if args.total_real_cycles % args.dcr_interval_real_cycles != 0:
        raise ValueError("--total-real-cycles must be divisible by --dcr-interval-real-cycles")

    total_sim_cycles = args.total_real_cycles // args.acceleration_factor
    cycles_per_block = args.dcr_interval_real_cycles // args.acceleration_factor
    return total_sim_cycles, cycles_per_block


def make_output_dir(args: argparse.Namespace) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_name = args.output_name or (
        f"eu_lifecycle_dcr_587Ah_{args.rate_p:g}P_"
        f"{args.total_real_cycles}cycles_{timestamp}"
    )
    output_dir = OUTPUT_ROOT / case_name
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "plots").mkdir()
    return output_dir


def build_model() -> pybamm.BaseModel:
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


def extract_latest_cycle_metrics(sol, base_discharge_capacity_ah: float | None) -> dict[str, float]:
    energy_res = compute_cycle_energies(sol)
    discharge_caps = np.asarray(energy_res["discharge_cap"], dtype=float)
    efficiencies = np.asarray(energy_res["efficiency"], dtype=float)

    discharge_capacity_ah = float(discharge_caps[-1]) if discharge_caps.size else math.nan
    efficiency_pct = float(efficiencies[-1] * 100.0) if efficiencies.size else math.nan

    if (
        base_discharge_capacity_ah is None
        or not np.isfinite(base_discharge_capacity_ah)
        or base_discharge_capacity_ah <= 0
        or not np.isfinite(discharge_capacity_ah)
    ):
        capacity_retention_pct = math.nan
    else:
        capacity_retention_pct = discharge_capacity_ah / base_discharge_capacity_ah * 100.0

    return {
        "discharge_capacity_ah": discharge_capacity_ah,
        "capacity_retention_pct": capacity_retention_pct,
        "efficiency_pct": efficiency_pct,
    }


def build_dcr_dataframe(rate_case: dict, args: argparse.Namespace) -> pd.DataFrame:
    cycle_numbers = sorted(rate_case["dcr"].keys())
    stored_solutions = rate_case["sol_list"]
    if len(stored_solutions) < len(cycle_numbers):
        raise RuntimeError(
            f"Stored solution count ({len(stored_solutions)}) is smaller than DCR count ({len(cycle_numbers)})."
        )

    baseline_solution = stored_solutions[0] if stored_solutions else None
    baseline_metrics = (
        extract_latest_cycle_metrics(baseline_solution, None)
        if baseline_solution is not None
        else {"discharge_capacity_ah": math.nan}
    )
    base_capacity = baseline_metrics["discharge_capacity_ah"]
    post_block_solutions = stored_solutions[-len(cycle_numbers):]

    rows = []
    for cycle_number, snapshot_sol in zip(cycle_numbers, post_block_solutions):
        metrics = extract_latest_cycle_metrics(snapshot_sol, base_capacity)
        dcr_discharge_ohm = float(rate_case["dcr_discharge"][cycle_number])
        dcr_charge_ohm = float(rate_case["dcr_charge"][cycle_number])
        dcr_mean_ohm = float(rate_case["dcr"][cycle_number])
        rows.append(
            {
                "cycle": int(cycle_number),
                "checkpoint_label": (
                    "start_after_conditioning"
                    if args.record_start_dcr and int(cycle_number) == args.start_dcr_cycle_number
                    else f"{int(cycle_number)}cycles"
                ),
                "rate_p": args.rate_p,
                "temperature_k": args.temperature_k,
                "temperature_c": args.temperature_k - 273.15,
                "target_soc_pct": args.dcr_target_soc * 100.0,
                "dcr_pulse_current_a": args.nominal_current_a * args.dcr_pulse_c_rate,
                "dcr_pulse_duration_s": args.dcr_pulse_duration_s,
                "dcr_discharge_mohm": dcr_discharge_ohm * 1000.0,
                "dcr_charge_mohm": dcr_charge_ohm * 1000.0,
                "dcr_mean_mohm": dcr_mean_ohm * 1000.0,
                "power_discharge_w": float(rate_case["power"][cycle_number]["power_discharge"]),
                "power_charge_w": float(rate_case["power"][cycle_number]["power_charge"]),
                "charge_time_h": float(rate_case["charge_time"][cycle_number]),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def save_outputs(dcr_df: pd.DataFrame, config: dict, output_dir: Path) -> None:
    config_path = output_dir / "config.json"
    csv_path = output_dir / "dcr_lifecycle_metrics.csv"
    excel_path = output_dir / "dcr_lifecycle_metrics.xlsx"
    summary_path = output_dir / "summary.json"

    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    dcr_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        dcr_df.to_excel(writer, index=False, sheet_name="dcr_metrics")
        worksheet = writer.sheets["dcr_metrics"]
        worksheet.freeze_panes = "A2"
        for column_cells in worksheet.columns:
            max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 28)

    summary = {
        "rows": int(len(dcr_df)),
        "first_cycle": int(dcr_df["cycle"].min()) if not dcr_df.empty else None,
        "last_cycle": int(dcr_df["cycle"].max()) if not dcr_df.empty else None,
        "final_dcr_mean_mohm": float(dcr_df["dcr_mean_mohm"].iloc[-1]) if not dcr_df.empty else None,
        "final_capacity_retention_pct": (
            float(dcr_df["capacity_retention_pct"].iloc[-1]) if not dcr_df.empty else None
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_outputs(dcr_df: pd.DataFrame, output_dir: Path) -> None:
    try:
        plt.style.use("science")
    except OSError:
        pass
    plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

    plots_dir = output_dir / "plots"

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(dcr_df["cycle"], dcr_df["dcr_mean_mohm"], "o-", lw=1.8, label="Mean")
    ax.plot(dcr_df["cycle"], dcr_df["dcr_discharge_mohm"], "s--", lw=1.2, label="Discharge")
    ax.plot(dcr_df["cycle"], dcr_df["dcr_charge_mohm"], "^--", lw=1.2, label="Charge")
    ax.set_xlabel("Cycle Number")
    ax.set_ylabel("DCR (mOhm)")
    ax.set_title("587Ah 0.5P Lifecycle DCR")
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "dcr_vs_cycle.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(dcr_df["cycle"], dcr_df["capacity_retention_pct"], "o-", lw=1.8)
    ax.set_xlabel("Cycle Number")
    ax.set_ylabel("Capacity Retention (%)")
    ax.set_title("587Ah 0.5P Capacity Retention")
    ax.grid(True, ls="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(plots_dir / "capacity_retention_vs_cycle.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(dcr_df["cycle"], dcr_df["efficiency_pct"], "o-", lw=1.8)
    ax.set_xlabel("Cycle Number")
    ax.set_ylabel("Energy Efficiency (%)")
    ax.set_title("587Ah 0.5P Energy Efficiency")
    ax.grid(True, ls="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(plots_dir / "efficiency_vs_cycle.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    total_sim_cycles, cycles_per_block = validate_config(args)
    output_dir = make_output_dir(args)

    config = vars(args).copy()
    config.update(
        {
            "total_sim_cycles": total_sim_cycles,
            "cycles_per_block": cycles_per_block,
            "power_w": args.rate_p * args.nominal_current_a * args.nominal_voltage_v,
            "pybamm_version": pybamm.__version__,
            "output_dir": str(output_dir),
        }
    )

    print("=== 587Ah lifecycle DCR simulation ===")
    print(json.dumps(config, indent=2, ensure_ascii=False))

    model = build_model()
    solver = pybamm.IDAKLUSolver()
    var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 35, "r_p": 25}

    run_result = run_dcr_and_power_test(
        rate_range=[args.rate_p],
        model=model,
        solver=solver,
        var_pts=var_pts,
        get_hithium_params=get_hithium_params,
        total_cycles=total_sim_cycles,
        cycles_per_block=cycles_per_block,
        temperature=args.temperature_k,
        nominal_current=args.nominal_current_a,
        nominal_voltage=args.nominal_voltage_v,
        target_soc=args.dcr_target_soc,
        conditioning_t_factor=args.conditioning_t_factor,
        aging_t_factor=args.acceleration_factor,
        record_conditioning_cycle=args.record_start_dcr,
        conditioning_cycle_number=args.start_dcr_cycle_number,
        cycle_number_factor=args.acceleration_factor,
        dcr_charge_c_rate=args.dcr_charge_c_rate,
        dcr_pulse_c_rate=args.dcr_pulse_c_rate,
        dcr_pulse_duration_s=args.dcr_pulse_duration_s,
        charge_cutoff_v=args.charge_cutoff_v,
        discharge_cutoff_v=args.discharge_cutoff_v,
        conditioning_charge_cutoff_v=args.charge_cutoff_v,
        rest_minutes=args.rest_minutes,
        period_minutes=args.period_minutes,
        use_explicit_power_steps=False,
        keep_only_last_cycle_solution=True,
        return_solutions=True,
        showprogress=args.showprogress,
    )

    rate_case = run_result["rate_results"][args.rate_p]
    dcr_df = build_dcr_dataframe(rate_case, args)
    save_outputs(dcr_df, config, output_dir)
    plot_outputs(dcr_df, output_dir)

    print("\n=== DCR results ===")
    print(dcr_df.to_string(index=False))
    print(f"\nSaved outputs to: {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Simulation failed: {exc}", file=sys.stderr)
        raise
