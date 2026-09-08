from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
TASK_ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = TASK_ROOT / "03_输入数据"
RUNS_ROOT = PROJECT_ROOT / "output" / "runs" / "mic_lifecycle_calibration"

for path in (PROJECT_ROOT, PARAMS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from paramsMIC import get_hithium_params as base_get_hithium_params  # noqa: E402
from src.analysis import get_discharge_capacity  # noqa: E402
from src.runtime import apply_pybamm_runtime_limits  # noqa: E402
from src.simulation import FULL_PULSE_LIFECYCLE_MODEL_OPTIONS, run_dcr_and_power_test  # noqa: E402


apply_pybamm_runtime_limits()

EXPERIMENT_CAPACITY = {
    0: 1.0,
    200: 0.9745491214,
    400: 0.9615100362,
    600: 0.9510080075,
}
EXPERIMENT_DCR_GROWTH = {
    0: 0.0,
    200: 0.024091,
    400: 0.051348,
    600: 0.065469,
}

TEMPERATURE_K = 298.15
AGING_RATE_P = 0.25
NOMINAL_CAPACITY_AH = 1175.0
NOMINAL_VOLTAGE_V = 3.2
CONTACT_RESISTANCE_OHM = 0.07018e-3
ACCELERATION_FACTOR = 50
SIMULATED_CYCLES = 12
SIMULATED_CYCLES_PER_BLOCK = 4
REAL_CYCLES_PER_BLOCK = SIMULATED_CYCLES_PER_BLOCK * ACCELERATION_FACTOR
BASE_SEI_RESISTIVITY_OHM_M = 200_000.0
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MIC 25C capacity and DCR calibration.")
    parser.add_argument("--mode", choices=("smoke", "scan"), default="scan")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--showprogress", action="store_true")
    return parser.parse_args()


def candidate_id(candidate: dict[str, float]) -> str:
    payload = json.dumps(candidate, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_model() -> pybamm.BaseModel:
    options = dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)
    options["calculate heat source for isothermal models"] = "true"
    return pybamm.lithium_ion.DFN(options)


def build_parameter_loader(candidate: dict[str, float]):
    def load_params(t_factor=1, temperature=298.15):
        values = base_get_hithium_params(t_factor, temperature=temperature)
        values["Contact resistance [Ohm]"] = CONTACT_RESISTANCE_OHM
        values["EC diffusivity [m2.s-1]"] *= candidate["sei_scale"]
        values["SEI kinetic rate constant [m.s-1]"] *= candidate["sei_scale"]
        values["Negative electrode LAM constant proportional term [s-1]"] *= candidate["lam_scale"]
        values["SEI resistivity [Ohm.m]"] = (
            BASE_SEI_RESISTIVITY_OHM_M * candidate["sei_resistivity_scale"]
        )
        return values

    return load_params


def last_positive_capacity(solution) -> float:
    capacities = np.asarray(
        get_discharge_capacity(solution)["discharge_capacity"],
        dtype=float,
    )
    valid = capacities[np.isfinite(capacities) & (capacities > 0)]
    return float(valid[-1]) if valid.size else np.nan


def run_candidate(candidate: dict[str, float], showprogress: bool) -> tuple[pd.DataFrame, dict]:
    started = time.time()
    result = run_dcr_and_power_test(
        rate_range=[AGING_RATE_P],
        model=build_model(),
        solver=pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6),
        var_pts=VAR_PTS,
        get_hithium_params=build_parameter_loader(candidate),
        total_cycles=SIMULATED_CYCLES,
        cycles_per_block=SIMULATED_CYCLES_PER_BLOCK,
        temperature=TEMPERATURE_K,
        nominal_current=NOMINAL_CAPACITY_AH,
        nominal_voltage=NOMINAL_VOLTAGE_V,
        target_soc=0.5,
        conditioning_t_factor=1,
        aging_t_factor=ACCELERATION_FACTOR,
        record_conditioning_cycle=True,
        conditioning_cycle_number=0,
        cycle_number_factor=ACCELERATION_FACTOR,
        dcr_charge_c_rate=0.25,
        dcr_pulse_c_rate=1.0,
        dcr_pulse_duration_s=30.0,
        charge_cutoff_v=3.65,
        discharge_cutoff_v=2.5,
        rest_minutes=10.0,
        period_minutes=0.5,
        use_explicit_power_steps=False,
        keep_only_last_cycle_solution=True,
        return_solutions=True,
        showprogress=showprogress,
    )
    rate_result = result["rate_results"][AGING_RATE_P]
    solutions = rate_result["sol_list"]
    cycles = [0, 200, 400, 600]
    capacities = [last_positive_capacity(solution) for solution in solutions]
    if len(capacities) != len(cycles):
        raise RuntimeError(f"Expected {len(cycles)} stored solutions, got {len(capacities)}")

    initial_capacity = capacities[0]
    dcr_values = rate_result["dcr"]
    initial_dcr = float(dcr_values[0])
    rows = []
    for cycle, capacity in zip(cycles, capacities):
        dcr = float(dcr_values[cycle])
        rows.append(
            {
                "candidate_id": candidate_id(candidate),
                "cycle": cycle,
                "capacity_ah": capacity,
                "capacity_retention": capacity / initial_capacity,
                "exp_capacity_retention": EXPERIMENT_CAPACITY[cycle],
                "dcr_ohm": dcr,
                "dcr_growth": dcr / initial_dcr - 1.0,
                "exp_dcr_growth": EXPERIMENT_DCR_GROWTH[cycle],
            }
        )
    detail = pd.DataFrame(rows)
    capacity_rmse_pct = float(
        np.sqrt(
            np.mean(
                (
                    detail.loc[detail["cycle"] > 0, "capacity_retention"]
                    - detail.loc[detail["cycle"] > 0, "exp_capacity_retention"]
                )
                ** 2
            )
        )
        * 100
    )
    dcr_rmse_pct = float(
        np.sqrt(
            np.mean(
                (
                    detail.loc[detail["cycle"] > 0, "dcr_growth"]
                    - detail.loc[detail["cycle"] > 0, "exp_dcr_growth"]
                )
                ** 2
            )
        )
        * 100
    )
    metrics = {
        "candidate_id": candidate_id(candidate),
        **candidate,
        "capacity_rmse_pct_point": capacity_rmse_pct,
        "dcr_growth_rmse_pct_point": dcr_rmse_pct,
        "objective": capacity_rmse_pct / 0.5 + dcr_rmse_pct / 1.5,
        "elapsed_s": time.time() - started,
        "status": "completed",
        "error": "",
    }
    return detail, metrics


def stage_candidates(mode: str) -> list[dict[str, float]]:
    if mode == "smoke":
        return [
            {
                "stage": 0,
                "sei_scale": 1.0,
                "lam_scale": 1.0,
                "sei_resistivity_scale": 1.0,
            }
        ]
    stage_one = [
        {
            "stage": 1,
            "sei_scale": sei_scale,
            "lam_scale": lam_scale,
            "sei_resistivity_scale": 1.0,
        }
        for sei_scale in (0.8, 1.0, 1.2)
        for lam_scale in (0.8, 1.0, 1.2)
    ]
    return stage_one


def run_stage(
    candidates: list[dict[str, float]],
    output_dir: Path,
    showprogress: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = []
    details = []
    for index, candidate in enumerate(candidates, start=1):
        cid = candidate_id(candidate)
        print(f"[{index}/{len(candidates)}] {cid}: {candidate}", flush=True)
        try:
            detail, metrics = run_candidate(candidate, showprogress)
            details.append(detail)
        except Exception as exc:
            metrics = {
                "candidate_id": cid,
                **candidate,
                "capacity_rmse_pct_point": np.nan,
                "dcr_growth_rmse_pct_point": np.nan,
                "objective": np.inf,
                "elapsed_s": np.nan,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(metrics["error"], flush=True)
        summaries.append(metrics)
        pd.DataFrame(summaries).to_csv(
            output_dir / "候选参数汇总_进行中.csv",
            index=False,
            encoding="utf-8-sig",
        )
    summary = pd.DataFrame(summaries).sort_values("objective").reset_index(drop=True)
    detail_all = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return summary, detail_all


def add_stage_two_candidates(stage_one_summary: pd.DataFrame) -> list[dict[str, float]]:
    completed = stage_one_summary.loc[stage_one_summary["status"].eq("completed")].copy()
    if completed.empty:
        return []
    best_capacity = completed.sort_values("capacity_rmse_pct_point").head(2)
    candidates = []
    for row in best_capacity.itertuples(index=False):
        for resistivity_scale in (0.8, 1.0, 1.2):
            candidates.append(
                {
                    "stage": 2,
                    "sei_scale": float(row.sei_scale),
                    "lam_scale": float(row.lam_scale),
                    "sei_resistivity_scale": resistivity_scale,
                }
            )
    return candidates


def save_outputs(
    output_dir: Path,
    summary: pd.DataFrame,
    detail: pd.DataFrame,
    config: dict,
) -> None:
    summary.to_csv(output_dir / "候选参数汇总.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(output_dir / "容量_DCR逐点对比.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(output_dir / "MIC_25C容量_DCR参数标定结果.xlsx", engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="候选参数汇总", index=False)
        detail.to_excel(writer, sheet_name="逐点对比", index=False)
        pd.DataFrame(
            [{"项目": key, "内容": json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value}
             for key, value in config.items()]
        ).to_excel(writer, sheet_name="运行配置", index=False)

    completed = summary.loc[summary["status"].eq("completed")]
    if completed.empty:
        return
    best = completed.iloc[0]
    best_detail = detail.loc[detail["candidate_id"].eq(best["candidate_id"])]
    plt.style.use("science")
    plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(
        best_detail["cycle"],
        best_detail["exp_capacity_retention"] * 100,
        "o--",
        label="Exp",
    )
    axes[0].plot(
        best_detail["cycle"],
        best_detail["capacity_retention"] * 100,
        "o-",
        label="Sim",
    )
    axes[0].set(xlabel="Cycle", ylabel="Capacity retention (%)", title="Capacity calibration")
    axes[1].plot(
        best_detail["cycle"],
        best_detail["exp_dcr_growth"] * 100,
        "o--",
        label="Exp",
    )
    axes[1].plot(
        best_detail["cycle"],
        best_detail["dcr_growth"] * 100,
        "o-",
        label="Sim",
    )
    axes[1].set(xlabel="Cycle", ylabel="DCR growth (%)", title="DCR calibration")
    for axis in axes:
        axis.grid(True, ls="--", alpha=0.35)
        axis.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "最佳参数_容量_DCR对比.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RUNS_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    config = {
        "run_id": run_id,
        "mode": args.mode,
        "temperature_k": TEMPERATURE_K,
        "aging_rate_p": AGING_RATE_P,
        "contact_resistance_ohm": CONTACT_RESISTANCE_OHM,
        "acceleration_factor": ACCELERATION_FACTOR,
        "real_cycles_per_block": REAL_CYCLES_PER_BLOCK,
        "capacity_source": str(INPUT_ROOT / "25℃ 循环(1).xlsx"),
        "capacity_source_range": "0.25P!A203:W603",
        "dcr_source": str(INPUT_ROOT / "循环过程DCR增长.xlsx"),
        "dcr_source_range": "MIC!C22:AB25",
        "pybamm_version": pybamm.__version__,
        "var_pts": VAR_PTS,
    }
    (output_dir / "运行配置.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    stage_one_summary, stage_one_detail = run_stage(
        stage_candidates(args.mode),
        output_dir,
        args.showprogress,
    )
    summaries = [stage_one_summary]
    details = [stage_one_detail]
    if args.mode == "scan":
        stage_two = add_stage_two_candidates(stage_one_summary)
        stage_two_summary, stage_two_detail = run_stage(
            stage_two,
            output_dir,
            args.showprogress,
        )
        summaries.append(stage_two_summary)
        details.append(stage_two_detail)

    summary = pd.concat(summaries, ignore_index=True).sort_values("objective").reset_index(drop=True)
    detail = pd.concat([frame for frame in details if not frame.empty], ignore_index=True)
    save_outputs(output_dir, summary, detail, config)
    print("\nBest candidate:")
    print(summary.head(1).to_string(index=False))
    print(f"\nSaved to: {output_dir}")


if __name__ == "__main__":
    main()
