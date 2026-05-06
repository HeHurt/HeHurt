from __future__ import annotations

import importlib
import os
import sys
import tempfile
import time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = Path(tempfile.gettempdir()) / "batteryproject_streamlit"
RUNTIME_HOME = RUNTIME_ROOT / "home"
MPL_CONFIG_DIR = RUNTIME_ROOT / "mpl"
RUNTIME_ROOT.mkdir(exist_ok=True)
RUNTIME_HOME.mkdir(exist_ok=True)
MPL_CONFIG_DIR.mkdir(exist_ok=True)
os.environ.setdefault("PYBAMM_DISABLE_TELEMETRY", "true")
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
os.environ.setdefault("HOME", str(RUNTIME_HOME))
os.environ.setdefault("USERPROFILE", str(RUNTIME_HOME))
os.environ.setdefault("HOMEDRIVE", RUNTIME_HOME.drive)
os.environ.setdefault("HOMEPATH", "\\" + "\\".join(RUNTIME_HOME.parts[1:]) if len(RUNTIME_HOME.parts) > 1 else "\\")
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.analysis import compute_cycle_energies, get_discharge_capacity
from src.compare import compare_all
from src.exp_loader import load_cycling_folder
from src.simulation import run_peak_current
from src.utils import BatteryDataLoader


st.set_page_config(
    page_title="BatteryProject Sim Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)


VAR_PTS_STANDARD = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
PARAMETER_SET_OPTIONS = {
    "314Ah 默认参数（BatteryProject）": ("src.config", "get_hithium_params"),
    "MIC 1175Ah 参数": ("params.paramsMIC", "get_hithium_params"),
    "587Ah 参数": ("params.params587", "get_hithium_params"),
    "280Ah 参数": ("params.params280", "get_hithium_params"),
}


def apply_page_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1.5rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.35rem;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.9rem;
        }
        .small-note {
            color: #5b6470;
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("exp_data_list", [])
    st.session_state.setdefault("excel_preview_df", None)
    st.session_state.setdefault("saved_request", None)
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("last_error", None)


def format_temperature_label(temp_c: float) -> str:
    rounded = round(temp_c)
    if abs(temp_c - rounded) < 1e-6:
        return f"{rounded}°C"
    return f"{temp_c:.1f}°C"


def parse_float_list(raw_text: str) -> list[float]:
    values: list[float] = []
    for token in raw_text.replace("，", ",").replace(" ", ",").split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    if not values:
        raise ValueError("请至少输入一个数值。")
    return values


def load_parameter_getter(option_name: str):
    module_name, func_name = PARAMETER_SET_OPTIONS.get(
        option_name,
        ("src.config", "get_hithium_params"),
    )
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def build_cycle_model() -> pybamm.BaseModel:
    options = {
        "calculate discharge energy": "true",
        "contact resistance": "true",
        "open-circuit potential": ("current sigmoid", "current sigmoid"),
    }
    return pybamm.lithium_ion.DFN(options)


def build_cycle_experiment(
    c_rate: float,
    cycles: int,
    temperature_k: float,
    charge_cutoff_v: float,
    discharge_cutoff_v: float,
    rest_minutes: int,
    period_minutes: int,
) -> pybamm.Experiment:
    step = (
        f"Charge at {c_rate}C until {charge_cutoff_v} V ({period_minutes} minute period)",
        f"Rest for {rest_minutes} minutes ({period_minutes} minute period)",
        f"Discharge at {c_rate}C until {discharge_cutoff_v} V ({period_minutes} minute period)",
        f"Rest for {rest_minutes} minutes ({period_minutes} minute period)",
    )
    return pybamm.Experiment([step] * cycles, temperature=temperature_k)


def build_solver():
    try:
        return pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6), "IDAKLUSolver"
    except Exception:
        return pybamm.CasadiSolver(mode="safe", rtol=1e-6, atol=1e-6), "CasadiSolver"


def get_solution_entries(sol, candidates: list[str]) -> np.ndarray:
    for candidate in candidates:
        try:
            return np.asarray(sol[candidate].entries, dtype=float)
        except Exception:
            continue
    return np.array([])


def make_cycle_label(request: dict) -> str:
    return f"{format_temperature_label(request['temperature_c'])} {request['c_rate']}P"


def summarize_cycle_result(cycle_df: pd.DataFrame) -> dict[str, float | int | None]:
    if cycle_df.empty:
        return {
            "cycle_count": 0,
            "initial_capacity_ah": np.nan,
            "final_capacity_ah": np.nan,
            "retention_pct": np.nan,
            "mean_efficiency_pct": np.nan,
            "soh80_cycle": None,
        }

    initial_capacity = float(cycle_df["discharge_capacity_ah"].iloc[0])
    final_capacity = float(cycle_df["discharge_capacity_ah"].iloc[-1])
    retention = np.nan
    if initial_capacity and np.isfinite(initial_capacity):
        retention = final_capacity / initial_capacity * 100.0

    mean_efficiency = float(cycle_df["efficiency_pct"].mean()) if not cycle_df["efficiency_pct"].empty else np.nan
    soh80_threshold = initial_capacity * 0.8 if np.isfinite(initial_capacity) else np.nan
    if np.isfinite(soh80_threshold):
        below_threshold = cycle_df.loc[cycle_df["discharge_capacity_ah"] <= soh80_threshold, "cycle"]
        soh80_cycle = int(below_threshold.iloc[0]) if not below_threshold.empty else None
    else:
        soh80_cycle = None

    return {
        "cycle_count": int(cycle_df["cycle"].max()),
        "initial_capacity_ah": initial_capacity,
        "final_capacity_ah": final_capacity,
        "retention_pct": retention,
        "mean_efficiency_pct": mean_efficiency,
        "soh80_cycle": soh80_cycle,
    }


def run_cycle_simulation(request: dict, status_box) -> dict:
    getter = load_parameter_getter(request["parameter_set"])
    logs: list[str] = []
    start = time.perf_counter()

    status_box.info("正在创建 DFN 模型...")
    logs.append("DFN model created.")
    model = build_cycle_model()

    status_box.info("正在加载参数...")
    logs.append(f"Parameter set: {request['parameter_set']}")
    params = pybamm.ParameterValues("OKane2022")
    params.update(getter(1, temperature=request["temperature_k"]), check_already_exists=False)

    status_box.info("正在准备求解器与 Experiment...")
    logs.append(f"Temperature: {request['temperature_c']} °C, rate: {request['c_rate']} C")
    solver, solver_name = build_solver()
    experiment = build_cycle_experiment(
        c_rate=request["c_rate"],
        cycles=request["cycles"],
        temperature_k=request["temperature_k"],
        charge_cutoff_v=request["charge_cutoff_v"],
        discharge_cutoff_v=request["discharge_cutoff_v"],
        rest_minutes=request["rest_minutes"],
        period_minutes=request["period_minutes"],
    )

    status_box.info("正在执行仿真...")
    sim = pybamm.Simulation(
        model,
        parameter_values=params,
        experiment=experiment,
        solver=solver,
        var_pts=VAR_PTS_STANDARD,
    )
    sol = sim.solve(calc_esoh=False)
    elapsed_s = time.perf_counter() - start
    logs.append(f"Simulation finished in {elapsed_s:.1f} s.")

    capacities = get_discharge_capacity(sol)["discharge_capacity"]
    energies = compute_cycle_energies(sol)
    common_len = min(
        len(capacities),
        len(energies["e_charge"]),
        len(energies["e_discharge"]),
        len(energies["efficiency"]),
    )
    cycle_df = pd.DataFrame(
        {
            "cycle": np.arange(1, common_len + 1),
            "discharge_capacity_ah": capacities[:common_len],
            "charge_energy_wh": energies["e_charge"][:common_len],
            "discharge_energy_wh": energies["e_discharge"][:common_len],
            "efficiency_pct": energies["efficiency"][:common_len] * 100.0,
        }
    )
    if not cycle_df.empty and np.isfinite(cycle_df["discharge_capacity_ah"].iloc[0]):
        cycle_df["retention_pct"] = (
            cycle_df["discharge_capacity_ah"] / cycle_df["discharge_capacity_ah"].iloc[0] * 100.0
        )
    else:
        cycle_df["retention_pct"] = np.nan

    trace_df = pd.DataFrame(
        {
            "time_h": get_solution_entries(sol, ["Time [h]"]),
            "voltage_v": get_solution_entries(sol, ["Voltage [V]", "Terminal voltage [V]"]),
            "current_a": get_solution_entries(sol, ["Current [A]"]),
        }
    )
    if not trace_df.empty:
        trace_df = trace_df.dropna(how="all")

    summary = summarize_cycle_result(cycle_df)
    return {
        "kind": "cycle",
        "label": make_cycle_label(request),
        "parameter_set": request["parameter_set"],
        "solver_name": solver_name,
        "elapsed_s": elapsed_s,
        "cycle_df": cycle_df,
        "trace_df": trace_df,
        "summary": summary,
        "logs": logs,
        "request": request,
        "solution": sol,
        "params": params,
    }


def run_peak_current_simulation(request: dict, status_box) -> dict:
    getter = load_parameter_getter(request["parameter_set"])
    logs: list[str] = []
    start = time.perf_counter()

    status_box.info("正在创建峰值电流模型...")
    model = build_cycle_model()
    params = pybamm.ParameterValues("OKane2022")
    params.update(getter(1, temperature=request["temperature_k"]), check_already_exists=False)
    logs.append(f"Parameter set: {request['parameter_set']}")

    status_box.info("正在执行峰值电流扫描...")
    result = run_peak_current(
        model,
        params,
        VAR_PTS_STANDARD,
        temperature=request["temperature_k"],
        nominal=request["nominal_current"],
        t_period=request["pulse_seconds"],
        x0=request["initial_soc"],
        charge_soc_list=request["charge_soc_list"],
        discharge_soc_list=request["discharge_soc_list"],
        search_ratios=request["search_ratios"],
        mode=request["mode"],
    )
    elapsed_s = time.perf_counter() - start
    logs.append(f"Peak current scan finished in {elapsed_s:.1f} s.")

    charge_df = pd.DataFrame(
        {
            "soc": result.get("charge_soc", []),
            "peak_current_a": result.get("charge_peak_current", []),
            "peak_power_w": result.get("charge_peak_power", []),
            "initial_voltage_v": result.get("charge_first_voltage", []),
        }
    )
    discharge_df = pd.DataFrame(
        {
            "soc": result.get("discharge_soc", []),
            "peak_current_a": result.get("discharge_peak_current", []),
            "peak_power_w": result.get("discharge_peak_power", []),
            "initial_voltage_v": result.get("discharge_first_voltage", []),
        }
    )

    return {
        "kind": "peak",
        "label": f"{format_temperature_label(request['temperature_c'])} 峰值电流",
        "parameter_set": request["parameter_set"],
        "elapsed_s": elapsed_s,
        "charge_df": charge_df,
        "discharge_df": discharge_df,
        "logs": logs,
        "request": request,
    }


def plot_experiment_preview(exp_data: dict):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    axes[0].plot(exp_data.get("cycle", []), exp_data.get("retention", []) * 100.0, color="#2563eb", linewidth=1.8)
    axes[0].set_title("容量保持率")
    axes[0].set_xlabel("循环")
    axes[0].set_ylabel("Retention (%)")
    axes[0].grid(alpha=0.25)

    axes[1].plot(exp_data.get("cycle", []), exp_data.get("efficiency", []) * 100.0, color="#0f766e", linewidth=1.8)
    axes[1].set_title("能量效率")
    axes[1].set_xlabel("循环")
    axes[1].set_ylabel("Efficiency (%)")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    return fig


def plot_cycle_trace(trace_df: pd.DataFrame):
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True)
    axes[0].plot(trace_df["time_h"], trace_df["voltage_v"], color="#2563eb", linewidth=1.6)
    axes[0].set_ylabel("电压 (V)")
    axes[0].grid(alpha=0.25)
    axes[0].set_title("仿真过程曲线")

    axes[1].plot(trace_df["time_h"], trace_df["current_a"], color="#dc2626", linewidth=1.4)
    axes[1].set_xlabel("时间 (h)")
    axes[1].set_ylabel("电流 (A)")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    return fig


def plot_cycle_summary(cycle_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].plot(cycle_df["cycle"], cycle_df["retention_pct"], color="#2563eb", linewidth=1.8)
    axes[0].set_title("容量保持率")
    axes[0].set_xlabel("循环")
    axes[0].set_ylabel("Retention (%)")
    axes[0].grid(alpha=0.25)

    axes[1].plot(cycle_df["cycle"], cycle_df["efficiency_pct"], color="#0f766e", linewidth=1.8)
    axes[1].set_title("能量效率")
    axes[1].set_xlabel("循环")
    axes[1].set_ylabel("Efficiency (%)")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    return fig


def plot_peak_summary(charge_df: pd.DataFrame, discharge_df: pd.DataFrame, mode: str):
    metric_name = "峰值功率 (W)" if mode == "W" else "峰值电流 (A)"
    value_column = "peak_power_w" if mode == "W" else "peak_current_a"

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].plot(charge_df["soc"], charge_df[value_column], marker="o", color="#2563eb", linewidth=1.7)
    axes[0].set_title("充电方向")
    axes[0].set_xlabel("SOC")
    axes[0].set_ylabel(metric_name)
    axes[0].grid(alpha=0.25)

    axes[1].plot(discharge_df["soc"], discharge_df[value_column], marker="o", color="#dc2626", linewidth=1.7)
    axes[1].set_title("放电方向")
    axes[1].set_xlabel("SOC")
    axes[1].set_ylabel(metric_name)
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    return fig


def render_sidebar() -> None:
    st.sidebar.title("BatteryProject")
    st.sidebar.caption("PyBaMM 前端 MVP")
    st.sidebar.markdown("当前阶段先打通数据导入、工况配置、仿真运行和结果分析。")

    exp_data_list = st.session_state.get("exp_data_list", [])
    request = st.session_state.get("saved_request")
    result = st.session_state.get("last_result")

    st.sidebar.subheader("当前状态")
    st.sidebar.write(f"实验条件数: {len(exp_data_list)}")
    st.sidebar.write(f"当前工况: {request['kind'] if request else '未保存'}")
    st.sidebar.write(f"最近结果: {result['kind'] if result else '无'}")

    if request:
        st.sidebar.subheader("工况摘要")
        st.sidebar.write(f"参数集: {request['parameter_set']}")
        st.sidebar.write(f"温度: {request['temperature_c']} °C")
        if request["kind"] == "cycle":
            st.sidebar.write(f"倍率: {request['c_rate']} C")
            st.sidebar.write(f"循环数: {request['cycles']}")
        else:
            st.sidebar.write(f"脉冲时长: {request['pulse_seconds']} s")
            st.sidebar.write(f"模式: {request['mode']}")

    if result and "summary" in result:
        summary = result["summary"]
        st.sidebar.subheader("结果摘要")
        st.sidebar.write(f"容量保持率: {summary['retention_pct']:.2f} %")
        st.sidebar.write(f"平均效率: {summary['mean_efficiency_pct']:.2f} %")


def render_data_tab() -> None:
    st.subheader("1. 数据导入与预览")
    st.caption("优先支持循环 CSV 文件夹导入；Excel 预览用于快速核对表头与数据格式。")

    col_left, col_right = st.columns([1.15, 0.85])

    with col_left:
        with st.form("load_csv_folder_form"):
            default_csv_folder = str(PROJECT_ROOT / "data")
            csv_folder = st.text_input("循环 CSV 文件夹路径", value=default_csv_folder)
            csv_channel = st.number_input("通道索引", min_value=0, max_value=4, value=0, step=1)
            load_csv = st.form_submit_button("加载循环 CSV")

        if load_csv:
            try:
                exp_data_list = load_cycling_folder(csv_folder, channel=int(csv_channel))
                st.session_state["exp_data_list"] = exp_data_list
                st.success(f"已加载 {len(exp_data_list)} 个实验条件。")
            except Exception as exc:
                st.session_state["exp_data_list"] = []
                st.error(f"加载循环 CSV 失败: {exc}")

        exp_data_list = st.session_state.get("exp_data_list", [])
        if exp_data_list:
            summary_rows = []
            for item in exp_data_list:
                cycle = item.get("cycle", np.array([]))
                retention = item.get("retention", np.array([]))
                efficiency = item.get("efficiency", np.array([]))
                summary_rows.append(
                    {
                        "label": item.get("label", ""),
                        "cycle_points": int(cycle.size),
                        "final_retention_pct": float(retention[-1] * 100.0) if retention.size else np.nan,
                        "mean_efficiency_pct": float(np.nanmean(efficiency) * 100.0) if efficiency.size else np.nan,
                    }
                )
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

            label_options = [item["label"] for item in exp_data_list]
            selected_label = st.selectbox("预览实验条件", label_options, key="exp_preview_label")
            selected_data = next(item for item in exp_data_list if item["label"] == selected_label)
            preview_fig = plot_experiment_preview(selected_data)
            st.pyplot(preview_fig, use_container_width=True)
            plt.close(preview_fig)
        else:
            st.info("还没有加载循环 CSV 数据。")

    with col_right:
        with st.form("excel_preview_form"):
            default_excel = str(PROJECT_ROOT / "data" / "587Ah-cell performance.xlsx")
            excel_path = st.text_input("Excel 文件路径（可选）", value=default_excel)
            sheet_name = st.text_input("Sheet 名称或索引", value="0")
            load_excel = st.form_submit_button("预览 Excel")

        if load_excel:
            try:
                loader = BatteryDataLoader()
                sheet_value = int(sheet_name) if sheet_name.isdigit() else sheet_name
                preview_df = loader.load_data(excel_path, sheet_name=sheet_value)
                st.session_state["excel_preview_df"] = preview_df
                st.success("Excel 预览完成。")
            except Exception as exc:
                st.session_state["excel_preview_df"] = None
                st.error(f"预览 Excel 失败: {exc}")

        preview_df = st.session_state.get("excel_preview_df")
        if isinstance(preview_df, pd.DataFrame):
            st.dataframe(preview_df.head(20), use_container_width=True)
        else:
            st.info("可选：加载 Excel，用于快速检查实验数据表结构。")


def render_config_tab() -> None:
    st.subheader("2. 工况设置")
    simulation_mode = st.radio(
        "仿真类型",
        options=["循环性能（推荐）", "峰值电流扫描"],
        horizontal=True,
    )

    if simulation_mode == "循环性能（推荐）":
        with st.form("cycle_request_form"):
            col1, col2, col3 = st.columns(3)
            parameter_set = col1.selectbox("参数集", list(PARAMETER_SET_OPTIONS.keys()), index=0)
            temperature_c = col2.number_input("环境温度 (°C)", min_value=-30.0, max_value=80.0, value=25.0, step=5.0)
            c_rate = col3.number_input("充放电倍率 (C)", min_value=0.05, max_value=5.0, value=0.5, step=0.05)

            col4, col5, col6 = st.columns(3)
            cycles = col4.number_input("循环数", min_value=1, max_value=2000, value=20, step=1)
            charge_cutoff_v = col5.number_input("充电截止电压 (V)", min_value=2.5, max_value=4.5, value=3.65, step=0.01)
            discharge_cutoff_v = col6.number_input("放电截止电压 (V)", min_value=1.5, max_value=4.0, value=2.50, step=0.01)

            col7, col8 = st.columns(2)
            rest_minutes = col7.number_input("静置时长 (min)", min_value=0, max_value=180, value=10, step=5)
            period_minutes = col8.number_input("采样周期 (min)", min_value=1, max_value=60, value=5, step=1)
            submitted = st.form_submit_button("保存循环工况")

        if submitted:
            request = {
                "kind": "cycle",
                "parameter_set": parameter_set,
                "temperature_c": float(temperature_c),
                "temperature_k": float(temperature_c) + 273.15,
                "c_rate": float(c_rate),
                "cycles": int(cycles),
                "charge_cutoff_v": float(charge_cutoff_v),
                "discharge_cutoff_v": float(discharge_cutoff_v),
                "rest_minutes": int(rest_minutes),
                "period_minutes": int(period_minutes),
            }
            st.session_state["saved_request"] = request
            st.success("循环工况已保存。")
            st.json(request)

    else:
        with st.form("peak_request_form"):
            col1, col2, col3 = st.columns(3)
            parameter_set = col1.selectbox("参数集", list(PARAMETER_SET_OPTIONS.keys()), index=1)
            temperature_c = col2.number_input("环境温度 (°C)", min_value=-30.0, max_value=80.0, value=0.0, step=5.0)
            mode = col3.selectbox("扫描模式", ["A", "W"], index=0)

            col4, col5, col6 = st.columns(3)
            nominal_current = col4.number_input("标称电流 / 功率基准", min_value=1.0, max_value=5000.0, value=1175.0, step=25.0)
            pulse_seconds = col5.number_input("脉冲时长 (s)", min_value=1, max_value=300, value=3, step=1)
            initial_soc = col6.number_input("初始 SOC", min_value=0.0, max_value=1.0, value=1.0, step=0.05)

            charge_soc_text = st.text_input("充电侧 SOC 列表", value="0.95")
            discharge_soc_text = st.text_input("放电侧 SOC 列表", value="1.0")
            ratios_text = st.text_input("搜索倍率列表", value="0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5")
            submitted = st.form_submit_button("保存峰值电流工况")

        if submitted:
            try:
                request = {
                    "kind": "peak",
                    "parameter_set": parameter_set,
                    "temperature_c": float(temperature_c),
                    "temperature_k": float(temperature_c) + 273.15,
                    "mode": mode,
                    "nominal_current": float(nominal_current),
                    "pulse_seconds": int(pulse_seconds),
                    "initial_soc": float(initial_soc),
                    "charge_soc_list": parse_float_list(charge_soc_text),
                    "discharge_soc_list": parse_float_list(discharge_soc_text),
                    "search_ratios": parse_float_list(ratios_text),
                }
                st.session_state["saved_request"] = request
                st.success("峰值电流工况已保存。")
                st.json(request)
            except Exception as exc:
                st.error(f"工况保存失败: {exc}")


def render_run_tab() -> None:
    st.subheader("3. 运行仿真")
    request = st.session_state.get("saved_request")
    if not request:
        st.info("请先在“工况设置”里保存一个仿真工况。")
        return

    st.caption("当前工况")
    st.json(request)

    status_box = st.empty()
    if st.button("开始运行", type="primary", use_container_width=False):
        st.session_state["last_error"] = None
        try:
            with st.spinner("仿真执行中，请稍候..."):
                if request["kind"] == "cycle":
                    result = run_cycle_simulation(request, status_box)
                else:
                    result = run_peak_current_simulation(request, status_box)
            st.session_state["last_result"] = result
            status_box.success("仿真完成。可以前往“结果分析”查看输出。")
        except Exception as exc:
            st.session_state["last_result"] = None
            st.session_state["last_error"] = str(exc)
            status_box.error(f"仿真失败: {exc}")

    last_error = st.session_state.get("last_error")
    if last_error:
        st.error(last_error)


def render_cycle_comparison(result: dict) -> None:
    exp_data_list = st.session_state.get("exp_data_list", [])
    if not exp_data_list:
        st.info("尚未加载实验 CSV，暂不显示 Sim-Exp 对比。")
        return

    try:
        axes = compare_all(
            [result["solution"]],
            [result["label"]],
            exp_data_list=exp_data_list,
            params=None,
            acceleration_factor=1,
            metrics=["retention", "efficiency"],
        )
    except Exception as exc:
        st.warning(f"自动对比失败: {exc}")
        return

    if not axes:
        st.info("没有生成可展示的对比图。")
        return

    for metric_name, ax in axes.items():
        st.markdown(f"**{metric_name} 对比**")
        st.pyplot(ax.figure, use_container_width=True)
        plt.close(ax.figure)


def render_results_tab() -> None:
    st.subheader("4. 结果分析")
    last_error = st.session_state.get("last_error")
    result = st.session_state.get("last_result")

    if last_error and not result:
        st.error(last_error)
        return
    if not result:
        st.info("还没有可展示的仿真结果。")
        return

    st.caption(f"结果类型: {result['kind']} | 参数集: {result['parameter_set']}")

    if result["kind"] == "cycle":
        summary = result["summary"]
        metric_cols = st.columns(5)
        metric_cols[0].metric("循环数", summary["cycle_count"])
        metric_cols[1].metric("初始容量", f"{summary['initial_capacity_ah']:.3f} Ah")
        metric_cols[2].metric("最终容量", f"{summary['final_capacity_ah']:.3f} Ah")
        metric_cols[3].metric("容量保持率", f"{summary['retention_pct']:.2f} %")
        metric_cols[4].metric("平均效率", f"{summary['mean_efficiency_pct']:.2f} %")

        chart_col_left, chart_col_right = st.columns(2)
        with chart_col_left:
            trace_fig = plot_cycle_trace(result["trace_df"])
            st.pyplot(trace_fig, use_container_width=True)
            plt.close(trace_fig)
        with chart_col_right:
            summary_fig = plot_cycle_summary(result["cycle_df"])
            st.pyplot(summary_fig, use_container_width=True)
            plt.close(summary_fig)

        st.markdown("**循环指标表**")
        st.dataframe(result["cycle_df"], use_container_width=True, hide_index=True)

        metrics_csv = result["cycle_df"].to_csv(index=False).encode("utf-8-sig")
        trace_csv = result["trace_df"].to_csv(index=False).encode("utf-8-sig")
        download_col1, download_col2 = st.columns(2)
        download_col1.download_button(
            "下载循环指标 CSV",
            data=metrics_csv,
            file_name="cycle_metrics.csv",
            mime="text/csv",
        )
        download_col2.download_button(
            "下载时序曲线 CSV",
            data=trace_csv,
            file_name="cycle_trace.csv",
            mime="text/csv",
        )

        st.markdown("**实验对比**")
        render_cycle_comparison(result)

    else:
        charge_df = result["charge_df"]
        discharge_df = result["discharge_df"]

        metric_cols = st.columns(4)
        metric_cols[0].metric("运行耗时", f"{result['elapsed_s']:.1f} s")
        metric_cols[1].metric("最大充电峰值", f"{charge_df['peak_current_a'].max():.2f} A")
        metric_cols[2].metric("最大放电峰值", f"{discharge_df['peak_current_a'].max():.2f} A")
        metric_cols[3].metric("工况数", len(charge_df) + len(discharge_df))

        peak_fig = plot_peak_summary(charge_df, discharge_df, result["request"]["mode"])
        st.pyplot(peak_fig, use_container_width=True)
        plt.close(peak_fig)

        st.markdown("**充电侧结果**")
        st.dataframe(charge_df, use_container_width=True, hide_index=True)
        st.markdown("**放电侧结果**")
        st.dataframe(discharge_df, use_container_width=True, hide_index=True)

        merged = pd.concat(
            [
                charge_df.assign(direction="charge"),
                discharge_df.assign(direction="discharge"),
            ],
            ignore_index=True,
        )
        st.download_button(
            "下载峰值电流结果 CSV",
            data=merged.to_csv(index=False).encode("utf-8-sig"),
            file_name="peak_current_scan.csv",
            mime="text/csv",
        )

    st.markdown("**运行日志**")
    for log_line in result.get("logs", []):
        st.code(log_line, language="text")


def main() -> None:
    apply_page_style()
    init_state()
    render_sidebar()

    st.title("BatteryProject Sim Studio")
    st.caption("MVP 版本：先打通 BatteryProject 的数据导入、工况配置、仿真执行与结果分析。")

    tabs = st.tabs(
        [
            "数据导入",
            "工况设置",
            "运行仿真",
            "结果分析",
        ]
    )

    with tabs[0]:
        render_data_tab()
    with tabs[1]:
        render_config_tab()
    with tabs[2]:
        render_run_tab()
    with tabs[3]:
        render_results_tab()


if __name__ == "__main__":
    main()
