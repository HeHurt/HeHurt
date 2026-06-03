from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
NOTEBOOK_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

from params587 import get_hithium_params


CANONICAL_PERFORMANCE_PATH = WORKSPACE_ROOT / "data_raw" / "587Ah" / "587Ah-cell performance.xlsx"
LEGACY_PERFORMANCE_PATH = NOTEBOOK_ROOT / "Exp" / "欧盟电池法仿真数据" / "587Ah-cell performance.xlsx"
PERFORMANCE_PATH = CANONICAL_PERFORMANCE_PATH if CANONICAL_PERFORMANCE_PATH.exists() else LEGACY_PERFORMANCE_PATH
OCV_RAW_FILES = [
    NOTEBOOK_ROOT / "Exp" / "欧盟电池法仿真数据" / "实验OCV曲线" / "5100001531_3_0IJCB903671131F7M0000107.xlsx",
    NOTEBOOK_ROOT / "Exp" / "欧盟电池法仿真数据" / "实验OCV曲线" / "5100001531_5_0IJCB903091131F850000314.xlsx",
]
OUTPUT_DIR = NOTEBOOK_ROOT / "output"
SUMMARY_PATH = OUTPUT_DIR / "eu_rate_summary_25C.csv"
CURVES_PATH = OUTPUT_DIR / "eu_rate_curves_25C_long.csv"
PLOT_PATH = OUTPUT_DIR / "eu_rate_compare_25C.png"
OCV_SUMMARY_PATH = OUTPUT_DIR / "eu_ocv_summary.csv"
OCV_CURVES_PATH = OUTPUT_DIR / "eu_ocv_curves_long.csv"
OCV_PLOT_PATH = OUTPUT_DIR / "eu_ocv_compare.png"


def format_rate_label(rate: float) -> str:
    return f"{float(rate):g}P"


def extract_contiguous_xy(df: pd.DataFrame, start_row: int, x_col: int, y_col: int) -> tuple[np.ndarray, np.ndarray]:
    x_values: list[float] = []
    y_values: list[float] = []
    started = False
    for row in range(start_row, len(df)):
        x = df.iat[row, x_col] if x_col < df.shape[1] else np.nan
        y = df.iat[row, y_col] if y_col < df.shape[1] else np.nan
        if pd.notna(x) and pd.notna(y):
            x_values.append(float(x))
            y_values.append(float(y))
            started = True
        elif started:
            break
    return np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float)


def load_rate_curves_from_performance(path: Path) -> tuple[dict[str, dict[str, np.ndarray]], pd.DataFrame]:
    rate_df = pd.read_excel(path, sheet_name="Rate", header=None)

    block_row = None
    for idx in range(len(rate_df)):
        row_values = [value.strip() for value in rate_df.iloc[idx].dropna() if isinstance(value, str)]
        if "Charge" in row_values and "Discharge" in row_values and any(value.endswith("P") for value in row_values):
            block_row = idx
            break

    if block_row is None:
        raise ValueError("未在 Rate sheet 中找到倍率块起始行")

    block_starts: dict[str, int] = {}
    for col, value in rate_df.iloc[block_row].items():
        if isinstance(value, str) and value.endswith("P"):
            block_starts[value.strip()] = col

    curves: dict[str, dict[str, np.ndarray]] = {}
    summary_rows: list[dict[str, float | int | str]] = []
    curve_rows: list[dict[str, float | str]] = []

    for rate_label, start_col in sorted(block_starts.items(), key=lambda item: float(item[0].rstrip("P"))):
        charge_capacity, charge_voltage = extract_contiguous_xy(rate_df, block_row + 3, start_col + 2, start_col + 1)
        discharge_capacity, discharge_voltage = extract_contiguous_xy(rate_df, block_row + 3, start_col + 9, start_col + 8)

        if charge_capacity.size == 0 and discharge_capacity.size == 0:
            continue

        discharge_capacity = np.abs(discharge_capacity)
        curves[rate_label] = {
            "charge_capacity": charge_capacity,
            "charge_voltage": charge_voltage,
            "discharge_capacity": discharge_capacity,
            "discharge_voltage": discharge_voltage,
        }

        charge_capacity_summary = rate_df.iat[block_row + 1, start_col + 2]
        discharge_capacity_summary = rate_df.iat[block_row + 1, start_col + 9]
        summary_rows.append(
            {
                "rate_label": rate_label,
                "exp_charge_capacity_ah": float(charge_capacity_summary) if pd.notna(charge_capacity_summary) else np.nan,
                "exp_discharge_capacity_ah": float(discharge_capacity_summary) if pd.notna(discharge_capacity_summary) else np.nan,
                "exp_charge_points": int(charge_capacity.size),
                "exp_discharge_points": int(discharge_capacity.size),
            }
        )

        for capacity, voltage in zip(charge_capacity, charge_voltage):
            curve_rows.append(
                {
                    "rate_label": rate_label,
                    "direction": "charge",
                    "capacity_ah": float(capacity),
                    "voltage_v": float(voltage),
                }
            )
        for capacity, voltage in zip(discharge_capacity, discharge_voltage):
            curve_rows.append(
                {
                    "rate_label": rate_label,
                    "direction": "discharge",
                    "capacity_ah": float(capacity),
                    "voltage_v": float(voltage),
                }
            )

    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary = summary.sort_values("rate_label", key=lambda s: s.str.rstrip("P").astype(float)).reset_index(drop=True)

    curves_long = pd.DataFrame(curve_rows)
    return curves, summary, curves_long


def curve_rmse(exp_capacity: np.ndarray, exp_voltage: np.ndarray, sim_capacity: np.ndarray, sim_voltage: np.ndarray) -> float:
    if exp_capacity.size == 0 or sim_capacity.size == 0:
        return np.nan

    shared_end = min(float(exp_capacity.max()), float(sim_capacity.max()))
    if shared_end <= 0:
        return np.nan

    sample_capacity = np.linspace(0, shared_end, 200)
    exp_interp = np.interp(sample_capacity, exp_capacity, exp_voltage)
    sim_interp = np.interp(sample_capacity, sim_capacity, sim_voltage)
    return float(np.sqrt(np.mean((sim_interp - exp_interp) ** 2)))


def load_ocv_cycle_curves(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    steps = pd.read_excel(path, sheet_name="工步层", engine="calamine")
    records = pd.read_excel(
        path,
        sheet_name="记录层",
        usecols=["工步序号", "工步状态", "实际电压(V)", "实际电流(A)", "容量(Ah)", "相对时间(h:min:s.ms)"],
        engine="calamine",
    )

    target_steps = steps.loc[
        steps["工步状态"].isin(["充电CC", "放电DC"])
        & (steps["持续时间(h:min:s.ms)"].astype(str).str.contains(":", na=False)),
        ["工步序号", "循环序号", "工步状态", "起始电流(A)", "结束电流(A)", "单工步充电容量(Ah)", "单工步放电容量(Ah)", "持续时间(h:min:s.ms)"],
    ].copy()

    target_steps["current_abs_mean_a"] = (
        target_steps[["起始电流(A)", "结束电流(A)"]].abs().mean(axis=1)
    )

    cycle_map = {
        4: "near_ocv_0.05C",
        5: "near_ocv_0.005C",
    }
    target_steps = target_steps[target_steps["循环序号"].isin(cycle_map)].copy()
    target_steps["curve_label"] = target_steps["循环序号"].map(cycle_map)

    curve_rows: list[dict[str, float | str | int]] = []
    summary_rows: list[dict[str, float | str | int]] = []

    for _, step_row in target_steps.iterrows():
        step_no = int(step_row["工步序号"])
        step_records = records[records["工步序号"] == step_no].copy()
        if step_records.empty:
            continue

        step_records["capacity_abs_ah"] = step_records["容量(Ah)"].abs().astype(float)
        step_records["voltage_v"] = step_records["实际电压(V)"].astype(float)
        step_records["current_a"] = step_records["实际电流(A)"].astype(float)

        file_label = path.stem.split("_")[1]
        direction = "charge" if step_row["工步状态"] == "充电CC" else "discharge"
        curve_name = f"{step_row['curve_label']}_{direction}"

        for _, record in step_records.iterrows():
            curve_rows.append(
                {
                    "file_label": file_label,
                    "curve_name": curve_name,
                    "cycle_index": int(step_row["循环序号"]),
                    "step_no": step_no,
                    "direction": direction,
                    "capacity_ah": float(record["capacity_abs_ah"]),
                    "voltage_v": float(record["voltage_v"]),
                    "current_a": float(record["current_a"]),
                }
            )

        summary_rows.append(
            {
                "file_label": file_label,
                "cycle_index": int(step_row["循环序号"]),
                "curve_name": curve_name,
                "direction": direction,
                "step_no": step_no,
                "current_abs_mean_a": float(step_row["current_abs_mean_a"]),
                "capacity_ah": float(step_records["capacity_abs_ah"].max()),
                "voltage_min_v": float(step_records["voltage_v"].min()),
                "voltage_max_v": float(step_records["voltage_v"].max()),
                "points": int(len(step_records)),
                "duration_hms": str(step_row["持续时间(h:min:s.ms)"]),
            }
        )

    return pd.DataFrame(summary_rows), pd.DataFrame(curve_rows)


def run_ocv_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_frames: list[pd.DataFrame] = []
    curve_frames: list[pd.DataFrame] = []
    for path in OCV_RAW_FILES:
        if not path.exists():
            continue
        summary_df, curves_df = load_ocv_cycle_curves(path)
        summary_frames.append(summary_df)
        curve_frames.append(curves_df)

    summary = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    curves = pd.concat(curve_frames, ignore_index=True) if curve_frames else pd.DataFrame()

    if not summary.empty:
        summary = summary.sort_values(["cycle_index", "file_label", "direction"]).reset_index(drop=True)
        summary.to_csv(OCV_SUMMARY_PATH, index=False, encoding="utf-8-sig")
    if not curves.empty:
        curves.to_csv(OCV_CURVES_PATH, index=False, encoding="utf-8-sig")

        palette = {
            "near_ocv_0.05C_charge": "tab:blue",
            "near_ocv_0.05C_discharge": "tab:orange",
            "near_ocv_0.005C_charge": "tab:green",
            "near_ocv_0.005C_discharge": "tab:red",
        }
        fig, ax = plt.subplots(figsize=(10, 6))
        for curve_name, group in curves.groupby("curve_name"):
            group_sorted = group.sort_values("capacity_ah")
            ax.plot(
                group_sorted["capacity_ah"],
                group_sorted["voltage_v"],
                lw=1.8,
                alpha=0.75,
                color=palette.get(curve_name, "gray"),
                label=curve_name,
            )
        ax.set_xlabel("Capacity (Ah)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Raw near-OCV / depolarized curves from EU test")
        ax.grid(True)
        ax.legend()
        plt.tight_layout()
        fig.savefig(OCV_PLOT_PATH, dpi=200, bbox_inches="tight")

    return summary, curves


def simulate_rate(rate: float) -> dict[str, np.ndarray]:
    temperature = 298.15
    nominal_current = 587
    nominal_voltage = 3.2

    model = pybamm.lithium_ion.DFN(
        {
            "calculate discharge energy": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )
    experiment = pybamm.Experiment(
        [
            (
                f"Charge at {rate * nominal_current * nominal_voltage:.0f}W until 3.65 V (0.5 minute period)",
                "Rest for 60 minute",
                f"Discharge at {rate * nominal_current * nominal_voltage:.0f}W until 2.5 V (0.5 minute period)",
            )
        ],
        temperature=temperature,
    )
    params = pybamm.ParameterValues("OKane2022")
    params.update(get_hithium_params(1, temperature), check_already_exists=False)

    sim = pybamm.Simulation(
        model,
        parameter_values=params,
        experiment=experiment,
        var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 15, "r_p": 15},
        solver=pybamm.IDAKLUSolver(),
    )
    sol = sim.solve(showprogress=False)

    voltage = sol["Voltage [V]"].entries
    capacity = sol["Throughput capacity [A.h]"].entries
    idx_max = int(voltage.argmax())
    charge_capacity = capacity[: idx_max + 1]
    charge_voltage = voltage[: idx_max + 1]
    discharge_capacity = capacity[idx_max + 1 :]
    if discharge_capacity.size:
        discharge_capacity = discharge_capacity - discharge_capacity[0]
    discharge_voltage = voltage[idx_max + 1 :]

    return {
        "charge_capacity": charge_capacity,
        "charge_voltage": charge_voltage,
        "discharge_capacity": discharge_capacity,
        "discharge_voltage": discharge_voltage,
    }


def main() -> None:
    if not PERFORMANCE_PATH.exists():
        raise FileNotFoundError(f"未找到实验文件: {PERFORMANCE_PATH}")

    try:
        plt.style.use("science")
    except OSError:
        pass
    plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exp_curves, summary_df, curves_long_df = load_rate_curves_from_performance(PERFORMANCE_PATH)
    curves_long_df.to_csv(CURVES_PATH, index=False, encoding="utf-8-sig")

    sim_curves: dict[str, dict[str, np.ndarray]] = {}
    sim_errors: dict[str, str] = {}

    for rate_label in summary_df["rate_label"].tolist():
        rate = float(rate_label.rstrip("P"))
        try:
            print(f"Running 25℃ simulation for {rate_label} ...")
            sim_curves[rate_label] = simulate_rate(rate)
        except Exception as exc:
            sim_errors[rate_label] = str(exc)
            print(f"Simulation failed for {rate_label}: {exc}")

    summary_df["sim_charge_capacity_ah"] = np.nan
    summary_df["sim_discharge_capacity_ah"] = np.nan
    summary_df["charge_voltage_rmse_v"] = np.nan
    summary_df["discharge_voltage_rmse_v"] = np.nan
    summary_df["sim_status"] = "missing"

    for idx, row in summary_df.iterrows():
        rate_label = row["rate_label"]
        if rate_label not in sim_curves:
            if rate_label in sim_errors:
                summary_df.at[idx, "sim_status"] = f"failed: {sim_errors[rate_label]}"
            continue

        sim_curve = sim_curves[rate_label]
        exp_curve = exp_curves[rate_label]
        summary_df.at[idx, "sim_charge_capacity_ah"] = float(sim_curve["charge_capacity"].max()) if sim_curve["charge_capacity"].size else np.nan
        summary_df.at[idx, "sim_discharge_capacity_ah"] = float(sim_curve["discharge_capacity"].max()) if sim_curve["discharge_capacity"].size else np.nan
        summary_df.at[idx, "charge_voltage_rmse_v"] = curve_rmse(
            exp_curve["charge_capacity"],
            exp_curve["charge_voltage"],
            sim_curve["charge_capacity"],
            sim_curve["charge_voltage"],
        )
        summary_df.at[idx, "discharge_voltage_rmse_v"] = curve_rmse(
            exp_curve["discharge_capacity"],
            exp_curve["discharge_voltage"],
            sim_curve["discharge_capacity"],
            sim_curve["discharge_voltage"],
        )
        summary_df.at[idx, "sim_status"] = "ok"

    summary_df.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    palette = ["black", "red", "deepskyblue", "orange", "green"]
    rate_labels = summary_df["rate_label"].tolist()
    color_map = {rate_label: palette[idx % len(palette)] for idx, rate_label in enumerate(rate_labels)}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    for rate_label in rate_labels:
        exp_curve = exp_curves[rate_label]
        color = color_map[rate_label]

        ax1.plot(
            exp_curve["charge_capacity"],
            exp_curve["charge_voltage"],
            ls="--",
            lw=2,
            color=color,
            label=f"25℃ {rate_label} Exp",
        )
        ax2.plot(
            exp_curve["discharge_capacity"],
            exp_curve["discharge_voltage"],
            ls="--",
            lw=2,
            color=color,
            label=f"25℃ {rate_label} Exp",
        )

        if rate_label not in sim_curves:
            continue

        sim_curve = sim_curves[rate_label]
        ax1.plot(
            sim_curve["charge_capacity"],
            sim_curve["charge_voltage"],
            ls="-",
            lw=2.5,
            color=color,
            label=f"25℃ {rate_label} Sim",
        )
        ax2.plot(
            sim_curve["discharge_capacity"],
            sim_curve["discharge_voltage"],
            ls="-",
            lw=2.5,
            color=color,
            label=f"25℃ {rate_label} Sim",
        )

    ax1.set_xlabel("Capacity (Ah)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title("25℃ Charge Curve: Sim vs Exp")
    ax1.grid(True)
    ax1.legend(fontsize=10)

    ax2.set_xlabel("Capacity (Ah)")
    ax2.set_ylabel("Voltage (V)")
    ax2.set_title("25℃ Discharge Curve: Sim vs Exp")
    ax2.grid(True)
    ax2.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig(PLOT_PATH, dpi=200, bbox_inches="tight")

    rounded = summary_df.copy()
    numeric_cols = rounded.select_dtypes(include=[np.number]).columns
    rounded[numeric_cols] = rounded[numeric_cols].round(4)
    print("\n=== Available benchmark rates from performance workbook ===")
    print(rounded.to_string(index=False))
    print(f"\nSaved summary: {SUMMARY_PATH}")
    print(f"Saved curves: {CURVES_PATH}")
    print(f"Saved plot: {PLOT_PATH}")

    ocv_summary, _ = run_ocv_analysis()
    if not ocv_summary.empty:
        ocv_rounded = ocv_summary.copy()
        numeric_cols = ocv_rounded.select_dtypes(include=[np.number]).columns
        ocv_rounded[numeric_cols] = ocv_rounded[numeric_cols].round(4)
        print("\n=== Near-OCV / depolarized curve summary ===")
        print(ocv_rounded.to_string(index=False))
        print(f"\nSaved OCV summary: {OCV_SUMMARY_PATH}")
        print(f"Saved OCV curves: {OCV_CURVES_PATH}")
        print(f"Saved OCV plot: {OCV_PLOT_PATH}")


if __name__ == "__main__":
    main()