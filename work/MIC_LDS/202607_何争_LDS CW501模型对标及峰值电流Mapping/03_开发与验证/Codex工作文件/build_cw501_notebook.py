from pathlib import Path

import nbformat as nbf


task = Path(r"D:\Users\hez\Desktop\hithium\work\MIC_LDS\202607_何争_LDS CW501模型对标及峰值电流Mapping")
notebook_path = task / "02_模型" / "CW501_DFN模型对标.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata.kernelspec = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
nb.metadata.language_info = {"name": "python", "version": "3.11"}

nb.cells = [
    nbf.v4.new_markdown_cell(
        """# CW501 DFN 模型与实测充放电曲线对标

本 Notebook 提供两种使用方式：

1. 修改“单工况实时仿真设置”后逐单元运行，实时查看模型和两只实测电芯的曲线。
2. 直接加载已完成的 20 个工况结果，查看全工况指标及温度汇总图。

模型显式开启接触阻抗，工况按实测 `|V×I|` 还原为恒功率充放电。"""
    ),
    nbf.v4.new_code_cell(
        """%load_ext autoreload
%autoreload 2

import importlib
import sys
from pathlib import Path

import matplotlib.pyplot as plt
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

import numpy as np
import pandas as pd
import pybamm
from IPython.display import display

TASK_ROOT = Path(r"D:\\Users\\hez\\Desktop\\hithium\\work\\MIC_LDS\\202607_何争_LDS CW501模型对标及峰值电流Mapping")
MODEL_DIR = TASK_ROOT / "02_模型"
PARAMS_ROOT = Path(r"D:\\Users\\hez\\Desktop\\hithium\\params")
EXPERIMENT_FILE = TASK_ROOT / "1300-25℃&45℃&5℃不同倍率下充放电数据-to何争.xlsx"
FULL_RESULT_DIR = TASK_ROOT / "04_输出结果" / "20260729_093615_full_v2"

for path in [MODEL_DIR, PARAMS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cw501_dfn_benchmark as benchmark_module
import paramsLDSCW501 as params_module

importlib.reload(benchmark_module)
importlib.reload(params_module)

parse_experiment_workbook = benchmark_module.parse_experiment_workbook
run_case = benchmark_module.run_case
comparison_metrics = benchmark_module.comparison_metrics
get_hithium_params = params_module.get_hithium_params

get_ipython().run_line_magic("matplotlib", "inline")
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

print(f"PyBaMM: {pybamm.__version__}")
print(f"science style enabled: {'science' in plt.style.available}")
print(f"Result directory: {FULL_RESULT_DIR}")"""
    ),
    nbf.v4.new_markdown_cell("## 1. 参数审计结果"),
    nbf.v4.new_code_cell(
        """params_25c = get_hithium_params(t_factor=1, temperature=298.15)
parameter_audit = pd.DataFrame(
    [
        ["Nominal cell capacity [A.h]", 1361.9, params_25c["Nominal cell capacity [A.h]"], "Ah"],
        ["Electrode height [m]", 0.555, params_25c["Electrode height [m]"], "m"],
        ["Electrode width [m]", 52.094, params_25c["Electrode width [m]"], "m"],
        ["Positive electrode thickness [m]", 135.7125e-6, params_25c["Positive electrode thickness [m]"], "m"],
        ["Negative electrode thickness [m]", 113.525e-6, params_25c["Negative electrode thickness [m]"], "m"],
        ["Positive particle radius [m]", 0.45e-6, params_25c["Positive particle radius [m]"], "m"],
        ["Negative particle radius [m]", 5.5e-6, params_25c["Negative particle radius [m]"], "m"],
        ["Contact resistance [Ohm]", 9.0549e-5, params_25c["Contact resistance [Ohm]"], "Ohm"],
    ],
    columns=["Parameter", "Design / audited value", "Model value", "Unit"],
)
parameter_audit["Relative difference [%]"] = (
    (parameter_audit["Model value"] - parameter_audit["Design / audited value"])
    / parameter_audit["Design / audited value"]
    * 100
)
display(parameter_audit)"""
    ),
    nbf.v4.new_markdown_cell("## 2. 加载实测曲线"),
    nbf.v4.new_code_cell(
        """experiment_groups = parse_experiment_workbook(EXPERIMENT_FILE)
available_cases = pd.DataFrame(
    [
        {
            "Temperature [°C]": temperature,
            "Direction": direction,
            "P-rate": p_rate,
            "Cells": len(curves),
            "Mean end capacity [Ah]": np.mean([curve["capacity_ah"].iloc[-1] for curve in curves]),
        }
        for (temperature, direction, p_rate), curves in experiment_groups.items()
    ]
).sort_values(["Temperature [°C]", "Direction", "P-rate"])
display(available_cases.reset_index(drop=True))"""
    ),
    nbf.v4.new_markdown_cell(
        """## 3. 单工况实时仿真设置

修改下面三个变量后，依次运行本单元、下一仿真单元和绘图单元。可用组合以 `available_cases` 表为准。"""
    ),
    nbf.v4.new_code_cell(
        """TEMPERATURE_C = 25
P_RATE = 0.125
DIRECTION = "充电"  # "充电" 或 "放电"

selected_key = (TEMPERATURE_C, DIRECTION, P_RATE)
if selected_key not in experiment_groups:
    raise KeyError(f"实测文件中不存在工况: {selected_key}")

selected_exp_curves = experiment_groups[selected_key]
selected_power_w = float(
    np.mean(
        [
            np.median(np.abs(curve["voltage_v"] * curve["current_a"]))
            for curve in selected_exp_curves
        ]
    )
)
print(f"Selected case: {TEMPERATURE_C}°C, {P_RATE:.3f}P, {DIRECTION}")
print(f"Measured constant power: {selected_power_w:.3f} W")"""
    ),
    nbf.v4.new_code_cell(
        """selected_sim_curve = run_case(
    temperature_c=TEMPERATURE_C,
    direction=DIRECTION,
    power_w=selected_power_w,
    period_s=30,
)

selected_metrics = pd.DataFrame(
    [
        {
            "Cell": f"cell{index}",
            "Exp end capacity [Ah]": exp_curve["capacity_ah"].iloc[-1],
            "Sim end capacity [Ah]": selected_sim_curve["capacity_ah"].iloc[-1],
            "End capacity error [%]": (
                selected_sim_curve["capacity_ah"].iloc[-1] - exp_curve["capacity_ah"].iloc[-1]
            )
            / exp_curve["capacity_ah"].iloc[-1]
            * 100,
            **comparison_metrics(exp_curve, selected_sim_curve),
        }
        for index, exp_curve in enumerate(selected_exp_curves, start=1)
    ]
)
display(selected_metrics)
print(f"Mean RRMSE: {selected_metrics['rrmse_pct'].mean():.3f}%")"""
    ),
    nbf.v4.new_code_cell(
        """plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

fig, ax = plt.subplots(figsize=(7.2, 4.8))
for index, exp_curve in enumerate(selected_exp_curves, start=1):
    ax.plot(
        exp_curve["capacity_ah"],
        exp_curve["voltage_v"],
        ls="--",
        lw=1.2,
        alpha=0.75,
        label=f"{P_RATE:.3f}P {TEMPERATURE_C}°C Exp cell{index}",
    )
ax.plot(
    selected_sim_curve["capacity_ah"],
    selected_sim_curve["voltage_v"],
    ls="-",
    lw=1.8,
    color="black",
    label=f"{P_RATE:.3f}P {TEMPERATURE_C}°C DFN Sim",
)
ax.set_title(f"CW501 {TEMPERATURE_C}°C {P_RATE:.3f}P {'Charge' if DIRECTION == '充电' else 'Discharge'}")
ax.set_xlabel("Capacity [Ah]")
ax.set_ylabel("Voltage [V]")
ax.legend(frameon=False)
fig.tight_layout()
plt.show()"""
    ),
    nbf.v4.new_markdown_cell("## 4. 已完成的全工况结果"),
    nbf.v4.new_code_cell(
        """metrics_all = pd.read_csv(FULL_RESULT_DIR / "metrics.csv", encoding="utf-8-sig")
curves_all = pd.read_csv(FULL_RESULT_DIR / "curves.csv", encoding="utf-8-sig")

metrics_mean = metrics_all[metrics_all["cell"].astype(str) == "mean"].copy()
summary = (
    metrics_mean.groupby(["temperature_c", "direction"], as_index=False)
    .agg(
        mean_rmse_v=("rmse_v", "mean"),
        mean_rrmse_pct=("rrmse_pct", "mean"),
        mean_end_capacity_error_pct=("end_capacity_error_pct", "mean"),
    )
)
display(summary)
display(
    metrics_mean[
        [
            "temperature_c",
            "direction",
            "p_rate",
            "power_w",
            "rmse_v",
            "rrmse_pct",
            "end_capacity_error_pct",
            "max_abs_error_v",
        ]
    ].reset_index(drop=True)
)"""
    ),
    nbf.v4.new_markdown_cell(
        """## 5. 全工况温度汇总图

修改 `OVERVIEW_TEMPERATURE_C` 为 5、25 或 45，然后重跑本单元。"""
    ),
    nbf.v4.new_code_cell(
        """OVERVIEW_TEMPERATURE_C = 25

plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

temperature_data = curves_all[curves_all["temperature_c"] == OVERVIEW_TEMPERATURE_C]
rates = sorted(temperature_data["p_rate"].unique())
fig, axes = plt.subplots(2, len(rates), figsize=(4.4 * len(rates), 7.0), squeeze=False)

for row_index, direction in enumerate(["充电", "放电"]):
    for column_index, p_rate in enumerate(rates):
        ax = axes[row_index, column_index]
        case = temperature_data[
            (temperature_data["direction"] == direction)
            & np.isclose(temperature_data["p_rate"], p_rate)
        ]
        if case.empty:
            ax.axis("off")
            continue
        for series_name, series in case.groupby("series"):
            is_simulation = series_name == "dfn_sim"
            ax.plot(
                series["capacity_ah"],
                series["voltage_v"],
                ls="-" if is_simulation else "--",
                lw=1.8 if is_simulation else 1.0,
                alpha=1.0 if is_simulation else 0.65,
                color="black" if is_simulation else None,
                label="DFN Sim" if is_simulation else series_name.replace("_", " "),
            )
        ax.set_title(
            f"{OVERVIEW_TEMPERATURE_C}°C {p_rate:.3f}P "
            f"{'Charge' if direction == '充电' else 'Discharge'}"
        )
        ax.set_xlabel("Capacity [Ah]")
        ax.set_ylabel("Voltage [V]")
        ax.legend(frameon=False, fontsize=8)

fig.tight_layout()
plt.show()"""
    ),
    nbf.v4.new_markdown_cell(
        """## 6. 可选：重新运行全部 20 个工况

默认关闭，避免打开 Notebook 时重复计算。需要生成新的完整 run 时，将 `RUN_ALL_CASES` 改为 `True`。"""
    ),
    nbf.v4.new_code_cell(
        """RUN_ALL_CASES = False

if RUN_ALL_CASES:
    import subprocess

    command = [sys.executable, str(MODEL_DIR / "cw501_dfn_benchmark.py")]
    print("Running:", " ".join(command))
    subprocess.run(command, check=True, cwd=TASK_ROOT)
else:
    print("RUN_ALL_CASES=False：使用已发布的完整结果。")"""
    ),
]

notebook_path.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, notebook_path)
print(notebook_path)
