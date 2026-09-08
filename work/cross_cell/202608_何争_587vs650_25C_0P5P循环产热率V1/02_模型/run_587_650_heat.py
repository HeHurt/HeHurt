# -*- coding: utf-8 -*-
"""587 vs 650 电芯 25°C 0.5P 循环全生命周期产热率仿真。

计算��式完全对齐参考任务：
  work/587Ah/202607_何争_587电池全生命周期产热率及1C-30sDCR/notebooks/587Ah_0p5P_lifecycle_heat_generation.ipynb

要点：
- 等温模型 + calculate heat source for isothermal models = true
- FULL_PULSE_LIFECYCLE_MODEL_OPTIONS（SEI + plating + particle mechanics + SEI on cracks + LAM）
- 老化加速因子 50，block 续算，容量检查间隔 1000 等效圈
- 产热链：PyBaMM 欧姆/反应/混合/滞回热 + I*T*dU/dT(SOH95 先验) 可逆热 + I^2*R_contact 接触热
- 650 沿用 587 的滞后校准权重与熵热先验（同一 LFP 体系，无 650 专属标定，作为临时先验）

运行：
  python run_587_650_heat.py --mode smoke   # 快速验证
  python run_587_650_heat.py --mode study   # 正式：跑到 65% SOH 以下
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm

pybamm.settings.max_y_value = 1.0e9

WORKSPACE_ROOT = Path(r"C:\HithiumSSD\hithium")
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
TASK_ROOT = WORKSPACE_ROOT / "work" / "cross_cell" / "202608_何争_587vs650_25C_0P5P循环产热率V1"

for path in (PROJECT_ROOT, PARAMS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import src.analysis as analysis_module
import src.heat_calibration as heat_calibration_module
import src.plotting as plotting_module
import src.simulation as simulation_module

get_all_heat_components = analysis_module.get_all_heat_components
build_calibrated_parameter_loader = heat_calibration_module.build_calibrated_parameter_loader
compute_cycle_calibrated_heat = heat_calibration_module.compute_cycle_calibrated_heat
load_branch_entropy_curves = heat_calibration_module.load_branch_entropy_curves
FULL_PULSE_LIFECYCLE_MODEL_OPTIONS = simulation_module.FULL_PULSE_LIFECYCLE_MODEL_OPTIONS
p_rate_to_power_w = simulation_module.p_rate_to_power_w
run_pulse_lifecycle_scenarios = simulation_module.run_pulse_lifecycle_scenarios
snapshot_degradation_variables = simulation_module.snapshot_degradation_variables

plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"
plt.rcParams["font.sans-serif"] = ["Calibri", "Microsoft YaHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------------------------
# 工况配置（两电芯共用，容量/功率随电芯变化）
# ---------------------------------------------------------------------------
TEMPERATURE_K = 298.15
TEMPERATURE_LABEL = "25°C"
P_RATE = 0.5
NOMINAL_VOLTAGE_V = 3.2
CHARGE_CUTOFF_V = 3.65
DISCHARGE_CUTOFF_V = 2.50
REST_MINUTES = 10.0
PERIOD_MINUTES = 0.5

# 外接接触电阻（单位 Ohm；按电芯独立配置，来自客户提供的 650 不同SOH发热功率仿真需求收集信息）
# 587 → 0.07513 mΩ；650 → 0.07147 mΩ
CELL_CONTACT_RESISTANCE_OHM = {
    "587": 0.07513e-3,
    "650": 0.07147e-3,
}
CONTACT_RESISTANCE_OHM = CELL_CONTACT_RESISTANCE_OHM["587"]  # 兼容旧引用（run_one_cell 内逐电芯覆盖）
HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT = 0.310139  # 587 校准值，650 沿用（临时先验）

ENTROPY_CURVE_FILE = (
    WORKSPACE_ROOT / "data_raw" / "AI_virtual_cell" / "Exp" / "熵热系数测试数据"
    / "analysis_output" / "entropy_coefficient_fits_by_branch.csv"
)
ENTROPY_SAMPLE_LABEL = "SOH95%"
ENTROPY_SOURCE_SCOPE = "转用314Ah SOH95%全电芯充放电支路dU/dT，作为587/650临时先验并全生命周期固定使用"

MODE_PRESETS = {
    "smoke": {"total_real_cycles": 150, "aging_t_factor": 50, "cycles_per_block": 3, "capacity_check_interval_cycles": 150},
    "study": {"total_real_cycles": 16_000, "aging_t_factor": 50, "cycles_per_block": 20, "capacity_check_interval_cycles": 250},
}

CELLS = [
    {
        "key": "587",
        "module_name": "params587",
        "display_name": "587Ah",
        "nominal_capacity_ah": 587.0,
    },
    {
        "key": "650",
        "module_name": "params650",
        "display_name": "650Ah",
        "nominal_capacity_ah": 650.0,
    },
]

SOLVER_RTOL = 1e-6
SOLVER_ATOL = 1e-6
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 35, "r_p": 25}
TARGET_SOH_PCT = 65.0
SOH_STEP_PCT = 5.0
# 0.5P 主循环老化路径；在每个 5% SOH 点位跑一次 0.25P 诊断循环并记录产热率
DIAGNOSTIC_P_RATE = 0.25
DIAGNOSTIC_SOH_TARGETS_PCT = [100, 95, 90, 85, 80, 75, 70, 65]


def build_cell_runner(cell_cfg, mode_preset):
    """为单个电芯构建参数加载器 + 场景 + 运行配置。"""
    params_module = importlib.import_module(cell_cfg["module_name"])
    get_hithium_params = params_module.get_hithium_params

    power_w = p_rate_to_power_w(P_RATE, cell_cfg["nominal_capacity_ah"], NOMINAL_VOLTAGE_V)
    contact_resistance_ohm = CELL_CONTACT_RESISTANCE_OHM[cell_cfg["key"]]
    total_real_cycles = int(mode_preset["total_real_cycles"])
    aging_t_factor = int(mode_preset["aging_t_factor"])
    cycles_per_block = int(mode_preset["cycles_per_block"])
    capacity_check_interval_cycles = int(mode_preset["capacity_check_interval_cycles"])

    calibrated_get_hithium_params = build_calibrated_parameter_loader(
        get_hithium_params, HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT
    )

    def lifecycle_get_hithium_params(*args, **kwargs):
        cell_params = calibrated_get_hithium_params(*args, **kwargs)
        cell_params["Contact resistance [Ohm]"] = contact_resistance_ohm
        return cell_params

    param_check = lifecycle_get_hithium_params(1, temperature=TEMPERATURE_K)
    assert "Nominal cell capacity [A.h]" in param_check

    model_options = dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)
    model_options["calculate heat source for isothermal models"] = "true"

    scenarios = [
        {
            "name": "baseline_0p5p_10min_rest",
            "display_name": f"{cell_cfg['display_name']} 0.5P充放电，静置10min",
            "pulse_p_rate": None,
            "enabled": True,
        }
    ]
    runtime_config = {
        "total_cycles": total_real_cycles,
        "use_block_acceleration": True,
        "cycles_per_block": cycles_per_block,
        "aging_t_factor": aging_t_factor,
        "conditioning_t_factor": 1,
        "capacity_check_interval_cycles": capacity_check_interval_cycles,
        "capacity_check_p_rate": P_RATE,
        "capacity_check_at_start": True,
        "solver_root_method": "casadi",
        "solver_root_tol": 1e-4,
        "return_partial_on_error": True,
        "diagnostic_soh_targets_pct": DIAGNOSTIC_SOH_TARGETS_PCT,
        "diagnostic_p_rates": [DIAGNOSTIC_P_RATE],
        "stop_at_lowest_diagnostic_soh": True,
        "showprogress": False,
    }
    config = {
        "run_mode": "study_unified",
        "cell": cell_cfg["display_name"],
        "temperature_c": TEMPERATURE_K - 273.15,
        "p_rate": P_RATE,
        "power_w": power_w,
        "nominal_capacity_ah": cell_cfg["nominal_capacity_ah"],
        "nominal_voltage_v": NOMINAL_VOLTAGE_V,
        "charge_cutoff_v": CHARGE_CUTOFF_V,
        "discharge_cutoff_v": DISCHARGE_CUTOFF_V,
        "rest_minutes": REST_MINUTES,
        "period_minutes": PERIOD_MINUTES,
        "total_real_cycles": total_real_cycles,
        "aging_t_factor": aging_t_factor,
        "cycles_per_block": cycles_per_block,
        "capacity_check_interval_cycles": capacity_check_interval_cycles,
        "model_options": "完整老化模型 + 等温产热源计算",
        "enabled_aging_mechanisms": ["SEI", "lithium plating", "particle mechanics", "SEI on cracks", "LAM"],
        "heat_x_axis_mode": "soh",
        "heat_value_mode": "calibrated",
        "contact_resistance_ohm": contact_resistance_ohm,
        "entropy_sample_label": ENTROPY_SAMPLE_LABEL,
        "entropy_source_scope": ENTROPY_SOURCE_SCOPE,
        "entropy_reference_policy": "全生命周期固定SOH95",
        "equilibrium_charge_weight": HYSTERESIS_EQUILIBRIUM_CHARGE_WEIGHT,
        "thermal_model": "未启用；仅在等温模型中计算产热源",
        "pybamm_version": pybamm.__version__,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return {
        "cell_cfg": cell_cfg,
        "get_hithium_params": lifecycle_get_hithium_params,
        "model_options": model_options,
        "scenarios": scenarios,
        "runtime_config": runtime_config,
        "config": config,
        "power_w": power_w,
        "contact_resistance_ohm": contact_resistance_ohm,
        "total_real_cycles": total_real_cycles,
        "aging_t_factor": aging_t_factor,
        "cycles_per_block": cycles_per_block,
    }


def run_one_cell(runner, output_dir: Path):
    """运行单个电芯生命周期仿真并提取产热/老化数据。"""
    t0 = time.time()
    run_output = run_pulse_lifecycle_scenarios(
        runner["scenarios"],
        runner["runtime_config"],
        model_options=runner["model_options"],
        var_pts=VAR_PTS,
        nominal_capacity_ah=runner["cell_cfg"]["nominal_capacity_ah"],
        temperature_k=TEMPERATURE_K,
        get_hithium_params=runner["get_hithium_params"],
        base_p_rate=P_RATE,
        nominal_voltage_v=NOMINAL_VOLTAGE_V,
        charge_cutoff_v=CHARGE_CUTOFF_V,
        discharge_cutoff_v=DISCHARGE_CUTOFF_V,
        rest_minutes=REST_MINUTES,
        period_minutes=PERIOD_MINUTES,
        solver_rtol=SOLVER_RTOL,
        solver_atol=SOLVER_ATOL,
        keep_only_last_cycle_solution=False,
        keep_only_last_capacity_check_solution=False,  # 保留完整诊断 solution，供 0.25P 产热率计算
        return_solutions=True,
    )
    elapsed_s = time.time() - t0

    scenario_name = runner["scenarios"][0]["name"]
    bundle = run_output["results"][scenario_name]
    capacity_check_df = bundle["capacity_check_df"].copy()
    if not capacity_check_df.empty:
        capacity_check_df = capacity_check_df.sort_values("real_cycle").reset_index(drop=True)
        capacity_check_df["capacity_retention_pct"] = capacity_check_df["capacity_retention"] * 100.0

    entropy_curves = load_branch_entropy_curves(ENTROPY_CURVE_FILE, sample_label=ENTROPY_SAMPLE_LABEL)

    heat_rows = []
    for block_index, (block_end_cycle, sol) in enumerate(
        zip(bundle["solution_real_cycles"], bundle["solutions"])
    ):
        all_cycles = list(getattr(sol, "cycles", []))
        if not all_cycles:
            raise ValueError(f"等效循环{block_end_cycle:g}对应的solution不包含cycle")
        # 过滤占位 rest cycle（单 step、仅 1 个时间点，无充放活动），
        # 只保留含充/放活动的真实 cycle，避免 compute_cycle_calibrated_heat 报错
        active_cycles = [
            cyc for cyc in all_cycles
            if len(list(getattr(cyc, "steps", []))) >= 2
        ]
        if not active_cycles:
            raise ValueError(f"等效循环{block_end_cycle:g}对应的solution不含活动cycle")
        if block_index == 0:
            real_cycles = np.array([1.0])
        else:
            real_cycles = float(block_end_cycle) - np.arange(len(active_cycles) - 1, -1, -1) * runner["aging_t_factor"]

        for real_cycle, cycle in zip(real_cycles, active_cycles):
            cycle_sol = SimpleNamespace(cycles=[cycle])
            native_heat = get_all_heat_components(
                cycle_sol,
                label_for_temp=f"{TEMPERATURE_LABEL} {P_RATE:g}P",
            )
            capacity = analysis_module.get_discharge_capacity(cycle_sol)["discharge_capacity"]
            row = {
                "real_cycle": int(round(float(real_cycle))),
                "discharge_capacity_ah": float(capacity[0]) if len(capacity) else np.nan,
                "temperature_k": TEMPERATURE_K,
                "p_rate": P_RATE,
                "power_w": runner["power_w"],
            }
            for key, values in native_heat.items():
                values = np.asarray(values, dtype=float)
                row[f"{key}_w"] = float(values[0]) if values.size else np.nan
            try:
                row.update(
                    compute_cycle_calibrated_heat(
                        cycle,
                        entropy_curves,
                        contact_resistance_ohm=runner["contact_resistance_ohm"],
                    )
                )
            except Exception as exc:
                # 低 SOH 区个别 cycle 数值边缘（step 时间/电流数组异常）→ 该点产热记为 NaN，不中断整体
                for _k in ("ohmic", "reaction", "mixing", "hysteresis"):
                    row[f"{_k}_charge_w"] = np.nan
                    row[f"{_k}_discharge_w"] = np.nan
                row["reversible_reference_charge_w"] = np.nan
                row["reversible_reference_discharge_w"] = np.nan
                row["internal_irreversible_charge_w"] = np.nan
                row["internal_irreversible_discharge_w"] = np.nan
                row["calibrated_total_charge_w"] = np.nan
                row["calibrated_total_discharge_w"] = np.nan
                row["active_duration_charge_s"] = np.nan
                row["active_duration_discharge_s"] = np.nan
                print(f"  [warn] 等效循环{real_cycle:g} 产热分项计算失败({type(exc).__name__}: {exc})，该点置 NaN", flush=True)
            row.update(snapshot_degradation_variables(cycle))
            heat_rows.append(row)

    heat_df = pd.DataFrame(heat_rows).sort_values("real_cycle").drop_duplicates("real_cycle").reset_index(drop=True)
    if not np.isfinite(heat_df["discharge_capacity_ah"].iloc[0]):
        raise ValueError("首个产热仿真点缺少放电容量")
    heat_df["capacity_retention_pct"] = (
        heat_df["discharge_capacity_ah"] / heat_df["discharge_capacity_ah"].iloc[0] * 100.0
    )

    heat_df = heat_df.rename(
        columns={
            "irrev_chg_w": "irrev_heat_charge_w",
            "rev_chg_w": "rev_heat_charge_w",
            "total_chg_w": "total_heat_charge_w",
            "irrev_dchg_w": "irrev_heat_discharge_w",
            "rev_dchg_w": "rev_heat_discharge_w",
            "total_dchg_w": "total_heat_discharge_w",
            "ohmic_charge_w": "ohmic_heat_charge_w",
            "reaction_charge_w": "reaction_heat_charge_w",
            "mixing_charge_w": "mixing_heat_charge_w",
            "hysteresis_charge_w": "hysteresis_heat_charge_w",
            "contact_charge_w": "contact_heat_charge_w",
            "reversible_reference_charge_w": "rev_heat_charge_reference_w",
            "internal_irreversible_charge_w": "irrev_heat_charge_calibrated_w",
            "calibrated_total_charge_w": "total_heat_charge_calibrated_w",
            "active_duration_charge_s": "active_duration_charge_s",
            "ohmic_discharge_w": "ohmic_heat_discharge_w",
            "reaction_discharge_w": "reaction_heat_discharge_w",
            "mixing_discharge_w": "mixing_heat_discharge_w",
            "hysteresis_discharge_w": "hysteresis_heat_discharge_w",
            "contact_discharge_w": "contact_heat_discharge_w",
            "reversible_reference_discharge_w": "rev_heat_discharge_reference_w",
            "internal_irreversible_discharge_w": "irrev_heat_discharge_calibrated_w",
            "calibrated_total_discharge_w": "total_heat_discharge_calibrated_w",
            "active_duration_discharge_s": "active_duration_discharge_s",
        }
    )
    for col in [
        "irrev_heat_charge_w",
        "rev_heat_charge_w",
        "total_heat_charge_w",
        "irrev_heat_discharge_w",
        "rev_heat_discharge_w",
        "total_heat_discharge_w",
    ]:
        heat_df[col.replace("_w", "_raw_w")] = heat_df[col]
    heat_df["total_heat_charge_calibrated_w"] = heat_df["total_heat_charge_calibrated_w"].fillna(
        heat_df["total_heat_charge_raw_w"]
    )
    heat_df["total_heat_discharge_calibrated_w"] = heat_df["total_heat_discharge_calibrated_w"].fillna(
        heat_df["total_heat_discharge_raw_w"]
    )
    heat_df["plot_total_heat_charge_w"] = heat_df["total_heat_charge_calibrated_w"]
    heat_df["plot_total_heat_discharge_w"] = heat_df["total_heat_discharge_calibrated_w"]

    # 每 5% SOH 采样（100% -> TARGET_SOH_PCT，线性插值）
    soh_points = []
    soh_target = 100.0
    while soh_target >= TARGET_SOH_PCT - 1e-9:
        soh_points.append(soh_target)
        soh_target -= SOH_STEP_PCT
    sample_rows = []
    for target in soh_points:
        if heat_df["capacity_retention_pct"].max() < target:
            continue
        interp_cols = {
            "total_heat_charge_calibrated_w": "充电总产热功率(W)",
            "total_heat_discharge_calibrated_w": "放电总产热功率(W)",
            "irrev_heat_charge_calibrated_w": "充电不可逆热功率(W)",
            "rev_heat_charge_reference_w": "充电可逆热功率(W)",
            "irrev_heat_discharge_calibrated_w": "放电不可逆热功率(W)",
            "rev_heat_discharge_reference_w": "放电可逆热功率(W)",
            "ohmic_heat_charge_w": "充电欧姆热功率(W)",
            "reaction_heat_charge_w": "充电反应热功率(W)",
            "hysteresis_heat_charge_w": "充电滞后热功率(W)",
            "contact_heat_charge_w": "充电接触热功率(W)",
            "ohmic_heat_discharge_w": "放电欧姆热功率(W)",
            "reaction_heat_discharge_w": "放电反应热功率(W)",
            "hysteresis_heat_discharge_w": "放电滞后热功率(W)",
            "contact_heat_discharge_w": "放电接触热功率(W)",
        }
        row = {"目标SOH(%)": target}
        soh_arr = heat_df["capacity_retention_pct"].to_numpy(dtype=float)
        for col, cn in interp_cols.items():
            if col in heat_df.columns:
                vals = heat_df[col].to_numpy(dtype=float)
                row[cn] = float(np.interp(target, soh_arr[::-1], vals[::-1]))
        sample_rows.append(row)
    soh_sample_df = pd.DataFrame(sample_rows)

    # ------------------------------------------------------------------
    # 0.25P 诊断产热率提取：每个 5% SOH 点位跑过的一次 0.25P 循环
    # ------------------------------------------------------------------
    diag_heat_rows = []
    for item in bundle.get("diagnostic_solutions", []):
        meta = dict(item)
        sol = meta.pop("solution", None)
        if sol is None:
            continue
        target_soh = float(meta.get("target_soh_pct", np.nan))
        diag_p_rate = float(meta.get("diagnostic_p_rate", DIAGNOSTIC_P_RATE))
        if abs(diag_p_rate - DIAGNOSTIC_P_RATE) > 1e-9:
            continue  # 只处理 0.25P 诊断分支
        all_cycles = list(getattr(sol, "cycles", []))
        if not all_cycles:
            print(f"  [warn] 诊断 SOH={target_soh:g}% 的 solution 无 cycle，跳过", flush=True)
            continue
        # 过滤占位 rest cycle（单 step），取最后一个含充/放活动的 cycle
        active_cycles = [
            cyc for cyc in all_cycles
            if len(list(getattr(cyc, "steps", []))) >= 2
        ]
        if not active_cycles:
            print(f"  [warn] 诊断 SOH={target_soh:g}% 的 solution 无活动 cycle，跳过", flush=True)
            continue
        cycle = active_cycles[-1]
        cycle_sol = SimpleNamespace(cycles=[cycle])
        native_heat = get_all_heat_components(
            cycle_sol,
            label_for_temp=f"{TEMPERATURE_LABEL} {DIAGNOSTIC_P_RATE:g}P",
        )
        capacity = analysis_module.get_discharge_capacity(cycle_sol)["discharge_capacity"]
        row = {
            "target_soh_pct": target_soh,
            "actual_soh_pct": float(meta.get("actual_soh_pct", np.nan)),
            "real_cycle": float(meta.get("real_cycle", np.nan)),
            "diagnostic_p_rate": diag_p_rate,
            "discharge_capacity_ah": float(capacity[0]) if len(capacity) else np.nan,
            "power_w": p_rate_to_power_w(diag_p_rate, runner["cell_cfg"]["nominal_capacity_ah"], NOMINAL_VOLTAGE_V),
        }
        for key, values in native_heat.items():
            values = np.asarray(values, dtype=float)
            row[f"{key}_w"] = float(values[0]) if values.size else np.nan
        try:
            row.update(
                compute_cycle_calibrated_heat(
                    cycle,
                    entropy_curves,
                    contact_resistance_ohm=runner["contact_resistance_ohm"],
                )
            )
        except Exception as exc:
            print(f"  [warn] 诊断 SOH={target_soh:g}% 产热分项计算失败({type(exc).__name__}: {exc})，该点置 NaN", flush=True)
            for _k in ("ohmic", "reaction", "mixing", "hysteresis"):
                row[f"{_k}_charge_w"] = np.nan
                row[f"{_k}_discharge_w"] = np.nan
            row["reversible_reference_charge_w"] = np.nan
            row["reversible_reference_discharge_w"] = np.nan
            row["internal_irreversible_charge_w"] = np.nan
            row["internal_irreversible_discharge_w"] = np.nan
            row["calibrated_total_charge_w"] = np.nan
            row["calibrated_total_discharge_w"] = np.nan
            row["active_duration_charge_s"] = np.nan
            row["active_duration_discharge_s"] = np.nan
        diag_heat_rows.append(row)

    diag_heat_df = pd.DataFrame(diag_heat_rows).sort_values("target_soh_pct", ascending=False).reset_index(drop=True)
    if not diag_heat_df.empty:
        diag_heat_df = diag_heat_df.rename(
            columns={
                "irrev_chg_w": "irrev_heat_charge_w",
                "rev_chg_w": "rev_heat_charge_w",
                "total_chg_w": "total_heat_charge_w",
                "irrev_dchg_w": "irrev_heat_discharge_w",
                "rev_dchg_w": "rev_heat_discharge_w",
                "total_dchg_w": "total_heat_discharge_w",
                "ohmic_charge_w": "ohmic_heat_charge_w",
                "reaction_charge_w": "reaction_heat_charge_w",
                "hysteresis_charge_w": "hysteresis_heat_charge_w",
                "contact_charge_w": "contact_heat_charge_w",
                "reversible_reference_charge_w": "rev_heat_charge_reference_w",
                "internal_irreversible_charge_w": "irrev_heat_charge_calibrated_w",
                "calibrated_total_charge_w": "total_heat_charge_calibrated_w",
                "ohmic_discharge_w": "ohmic_heat_discharge_w",
                "reaction_discharge_w": "reaction_heat_discharge_w",
                "hysteresis_discharge_w": "hysteresis_heat_discharge_w",
                "contact_discharge_w": "contact_heat_discharge_w",
                "reversible_reference_discharge_w": "rev_heat_discharge_reference_w",
                "internal_irreversible_discharge_w": "irrev_heat_discharge_calibrated_w",
                "calibrated_total_discharge_w": "total_heat_discharge_calibrated_w",
            }
        )
        for col in ["total_heat_charge_calibrated_w", "total_heat_discharge_calibrated_w"]:
            if col in diag_heat_df.columns:
                diag_heat_df[col] = diag_heat_df[col].fillna(
                    diag_heat_df[col.replace("calibrated_", "")].where(
                        diag_heat_df[col].isna() & diag_heat_df[col.replace("calibrated_", "")].notna()
                    )
                )

    result = {
        "heat_df": heat_df,
        "capacity_check_df": capacity_check_df,
        "soh_sample_df": soh_sample_df,
        "diag_heat_df": diag_heat_df,
        "elapsed_s": elapsed_s,
        "config": runner["config"],
        "bundle": bundle,
        "final_solution": bundle["solutions"][-1] if bundle["solutions"] else None,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["smoke", "study"], default="study")
    parser.add_argument("--cells", default="587,650", help="逗号分隔，如 587,650")
    args = parser.parse_args()

    mode_preset = MODE_PRESETS[args.mode]
    cells = [c for c in args.cells.split(",") if c.strip()]
    output_dir = TASK_ROOT / "04_输出结果" / (f"run_{args.mode}_{datetime.now():%Y%m%d_%H%M%S}")
    plots_dir = output_dir / "图表"
    for folder in (output_dir, plots_dir):
        folder.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for cell_cfg in CELLS:
        if cell_cfg["key"] not in cells:
            continue
        print(f"\n===== 运行 {cell_cfg['display_name']} ({args.mode}) =====", flush=True)
        runner = build_cell_runner(cell_cfg, mode_preset)
        result = run_one_cell(runner, output_dir)
        all_results[cell_cfg["key"]] = result
        heat_df = result["heat_df"]
        diag_heat_df = result["diag_heat_df"]
        print(f"  完成 {cell_cfg['display_name']}：{len(heat_df)} 个仿真点，"
              f"最终SOH={heat_df['capacity_retention_pct'].iloc[-1]:.2f}%，"
              f"0.25P诊断点={len(diag_heat_df)}，耗时 {result['elapsed_s']:.1f}s", flush=True)
        # 保存每点明细 csv
        heat_df.to_csv(output_dir / f"{cell_cfg['key']}_heat_lifecycle.csv", index=False, encoding="utf-8-sig")
        result["soh_sample_df"].to_csv(
            output_dir / f"{cell_cfg['key']}_soh_5pct_sample.csv", index=False, encoding="utf-8-sig"
        )
        if not diag_heat_df.empty:
            diag_heat_df.to_csv(
                output_dir / f"{cell_cfg['key']}_diag_0p25P_heat.csv", index=False, encoding="utf-8-sig"
            )
        with open(output_dir / f"{cell_cfg['key']}_config.json", "w", encoding="utf-8") as f:
            json.dump(result["config"], f, ensure_ascii=False, indent=2, default=str)

    # ------------------------------------------------------------------
    # 后处理：产热率 vs SOH 图（587 vs 650 对比）
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for key, result in all_results.items():
        df = result["heat_df"]
        label = f"{key}Ah"
        color = "#111111" if key == "587" else "#e53935"
        axes[0, 0].plot(df["real_cycle"], df["capacity_retention_pct"], color=color, lw=1.8, label=label)
        axes[0, 1].plot(df["real_cycle"], df["plot_total_heat_charge_w"], color=color, lw=1.8, label=f"{label} 充电")
        axes[0, 1].plot(df["real_cycle"], df["plot_total_heat_discharge_w"], color=color, lw=1.8, ls="--", label=f"{label} 放电")
    axes[0, 0].set_xlabel("等效循环圈数")
    axes[0, 0].set_ylabel("SOH (%)")
    axes[0, 0].set_title("容量保持率")
    axes[0, 0].grid(True, ls="--", alpha=0.35)
    axes[0, 0].legend()
    axes[0, 1].set_xlabel("等效循环圈数")
    axes[0, 1].set_ylabel("平均产热功率 (W)")
    axes[0, 1].set_title("全生命周期总产热功率")
    axes[0, 1].grid(True, ls="--", alpha=0.35)
    axes[0, 1].legend()

    # 产热率 vs SOH（每 5% SOH 采样）
    for ax, direction, title in zip(axes[1], ["charge", "discharge"], ["充电平均产热功率 vs SOH", "放电平均产热功率 vs SOH"]):
        for key, result in all_results.items():
            df = result["heat_df"]
            color = "#111111" if key == "587" else "#e53935"
            ax.plot(
                df["capacity_retention_pct"], df[f"plot_total_heat_{direction}_w"],
                color=color, lw=1.8, label=f"{key}Ah",
            )
        ax.set_xlabel("SOH (%)")
        ax.set_ylabel("平均产热功率 (W)")
        ax.set_title(title)
        ax.invert_xaxis()
        ax.grid(True, ls="--", alpha=0.35)
        ax.legend()
    fig.suptitle("587 vs 650 电芯 25°C 0.5P 全生命周期产热率", fontsize=16, y=1.01)
    fig.tight_layout()
    compare_plot_path = plots_dir / "587vs650_全生命周期产热对比.png"
    fig.savefig(compare_plot_path, dpi=220, bbox_inches="tight")
    print("对比图：", compare_plot_path)
    plt.close(fig)

    # ------------------------------------------------------------------
    # 0.25P 诊断产热率 vs SOH（每 5% SOH 点位跑一次 0.25P 循环）
    # ------------------------------------------------------------------
    fig2, axes2 = plt.subplots(1, 2, figsize=(13, 5))
    for ax, direction, title in zip(axes2, ["charge", "discharge"], ["0.25P 充电平均产热功率 vs SOH", "0.25P 放电平均产热功率 vs SOH"]):
        for key, result in all_results.items():
            diag = result["diag_heat_df"]
            if diag.empty:
                continue
            color = "#111111" if key == "587" else "#e53935"
            marker = "o" if key == "587" else "s"
            ax.plot(
                diag["target_soh_pct"], diag[f"total_heat_{direction}_calibrated_w"],
                color=color, lw=1.8, marker=marker, ms=6, label=f"{key}Ah",
            )
        ax.set_xlabel("SOH (%)")
        ax.set_ylabel("平均产热功率 (W)")
        ax.set_title(title)
        ax.invert_xaxis()
        ax.grid(True, ls="--", alpha=0.35)
        ax.legend()
    fig2.suptitle("0.5P 循环老化路径下各 SOH 点位的 0.25P 产热率（每 5% SOH 测量一次）", fontsize=13, y=1.03)
    fig2.tight_layout()
    diag_plot_path = plots_dir / "587vs650_0P25P产热率vsSOH.png"
    fig2.savefig(diag_plot_path, dpi=220, bbox_inches="tight")
    print("0.25P 诊断对比图：", diag_plot_path)
    plt.close(fig2)

    # 每 5% SOH 采样对比表
    print("\n===== 每 5% SOH 产热率对比（0.5P 主循环）=====")
    sample_keys = ["充电总产热功率(W)", "放电总产热功率(W)", "充电不可逆热功率(W)", "放电不可逆热功率(W)",
                   "充电可逆热功率(W)", "放电可逆热功率(W)"]
    with pd.ExcelWriter(output_dir / "587vs650_每5pctSOH产热率.xlsx", engine="openpyxl") as writer:
        for key in ["587", "650"]:
            if key in all_results:
                df = all_results[key]["soh_sample_df"].copy()
                df.insert(0, "电芯", f"{key}Ah")
                df.to_excel(writer, sheet_name=f"{key}Ah_每5pctSOH", index=False)
        # 汇总对比 sheet
        rows = []
        if "587" in all_results and "650" in all_results:
            for _, r587 in all_results["587"]["soh_sample_df"].iterrows():
                target = r587["目标SOH(%)"]
                r650 = all_results["650"]["soh_sample_df"]
                r650m = r650[r650["目标SOH(%)"] == target]
                if r650m.empty:
                    continue
                r650r = r650m.iloc[0]
                row = {"目标SOH(%)": target}
                for col in sample_keys:
                    row[f"587_{col}"] = r587.get(col, np.nan)
                    row[f"650_{col}"] = r650r.get(col, np.nan)
                    row[f"差值650-587_{col}"] = row[f"650_{col}"] - row[f"587_{col}"]
                rows.append(row)
        if rows:
            compare_df = pd.DataFrame(rows)
            compare_df.to_excel(writer, sheet_name="587vs650对比", index=False)
            print(compare_df.to_string(index=False))

        # 0.25P 诊断产热率 sheet（每 5% SOH 点位跑 0.25P 循环）
        diag_cols = [
            "total_heat_charge_calibrated_w", "total_heat_discharge_calibrated_w",
            "irrev_heat_charge_calibrated_w", "irrev_heat_discharge_calibrated_w",
            "rev_heat_charge_reference_w", "rev_heat_discharge_reference_w",
        ]
        diag_cols_cn = {
            "total_heat_charge_calibrated_w": "充电总产热功率(W)",
            "total_heat_discharge_calibrated_w": "放电总产热功率(W)",
            "irrev_heat_charge_calibrated_w": "充电不可逆热功率(W)",
            "irrev_heat_discharge_calibrated_w": "放电不可逆热功率(W)",
            "rev_heat_charge_reference_w": "充电可逆热功率(W)",
            "rev_heat_discharge_reference_w": "放电可逆热功率(W)",
        }
        if "587" in all_results and "650" in all_results:
            diag_rows = []
            for _, r587 in all_results["587"]["diag_heat_df"].iterrows():
                target = r587["target_soh_pct"]
                r650m = all_results["650"]["diag_heat_df"]
                r650m = r650m[r650m["target_soh_pct"] == target]
                if r650m.empty:
                    continue
                r650r = r650m.iloc[0]
                row = {"目标SOH(%)": target}
                row["587_实际SOH(%)"] = r587.get("actual_soh_pct", np.nan)
                row["650_实际SOH(%)"] = r650r.get("actual_soh_pct", np.nan)
                for col in diag_cols:
                    v587 = r587.get(col, np.nan)
                    v650 = r650r.get(col, np.nan)
                    row[f"587_{diag_cols_cn[col]}"] = v587
                    row[f"650_{diag_cols_cn[col]}"] = v650
                    row[f"差值650-587_{diag_cols_cn[col]}"] = v650 - v587
                diag_rows.append(row)
            if diag_rows:
                diag_compare_df = pd.DataFrame(diag_rows)
                diag_compare_df.to_excel(writer, sheet_name="0P25P诊断vsSOH", index=False)
                print("\n===== 0.25P 诊断产热率对比（0.5P 老化路径上每 5% SOH 测一次）=====")
                print(diag_compare_df.to_string(index=False))

    print("\n输出目录：", output_dir)
    return output_dir


if __name__ == "__main__":
    main()
