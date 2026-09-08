from pathlib import Path

import nbformat as nbf


OUTPUT = Path("work/CW368_DFN模型对标及产热功率仿真.ipynb")
nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
nb.metadata["language_info"] = {"name": "python", "version": "3.11"}

cells = []
cells.append(
    nbf.v4.new_markdown_cell(
        """# LDS CW368 DFN 模型对标及 0.125P / 0.167P / 0.25P 产热功率仿真

本 Notebook 使用 **开启接触阻抗** 的 PyBaMM DFN：

- 设计容量：1362.4 Ah，几何与极片结构来自文件夹内设计参数表 `LDS CW368` 列。
- 对标温度：25℃。
- 实测工况：0.125P（约 627.91 W）与 0.25P（约 1255.81 W），两只电芯、每倍率各两个完整循环。
- 预测工况：0.167P（约 838.88 W），文件夹中没有直接实测曲线，因此仅作为模型预测。
- 电压窗口：充电 3.65 V，放电 2.5 V。
- 结果输出周期：30 s，与实测曲线采样周期一致。
- 产热口径：25℃等温 DFN 电化学热源 + 显式接触阻抗热 `I²R_contact`。

参数文件保留设计宽度。**电压曲线对标**使用显式有效面积系数 `0.937`
对齐实测约 1214 Ah 的可用容量；**产热计算**关闭该校准，使用原始设计面积
（面积系数 `1.0`）。接触阻抗在两套计算中都开启。

负极 OCP 使用 25℃ 0.125P/0.25P 曲线辨识得到的平滑局部 stoichiometry
warp，使石墨分级嵌锂平台在容量轴上的位置与实测一致；这属于 CW368 专属
OCP 校准，不修改设计几何。"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """%load_ext autoreload
%autoreload 2
%matplotlib inline

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

TASK_ROOT = Path(r"D:\\Users\\hez\\Desktop\\hithium\\work\\MIC_LDS\\202607_何争_LDS CW368模型对标及0.125-0.167-0.25P产热功率仿真")
MODEL_DIR = TASK_ROOT / "02_模型"
OUTPUT_DIR = TASK_ROOT / "04_输出结果" / "CW368_DFN对标及产热"
PARAMS_ROOT = Path(r"D:\\Users\\hez\\Desktop\\hithium\\params")

for path in [MODEL_DIR, PARAMS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import paramsLDSCW368 as params_module
import cw368_dfn_benchmark as benchmark_module
importlib.reload(params_module)
importlib.reload(benchmark_module)

get_hithium_params = params_module.get_hithium_params
run_benchmark = benchmark_module.run_benchmark
load_results = benchmark_module.load_results

print(f"PyBaMM: {pybamm.__version__}")
print(f"science style enabled: {'science' in plt.style.available}")
print(f"Output: {OUTPUT_DIR}")"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 1. 设计参数与模型固化检查"))
cells.append(
    nbf.v4.new_code_cell(
        """params_25c = get_hithium_params(1, 298.15)
parameter_audit = pd.DataFrame(
    [
        ["设计容量", 1362.4, params_25c["Nominal cell capacity [A.h]"], "Ah", "设计表"],
        ["JR个数", 2, 2, "-", "设计表"],
        ["阴极层数/单JR", 83, 83, "层", "设计表"],
        ["正极厚度", 96.5125, params_25c["Positive electrode thickness [m]"] * 1e6, "μm", "反弹后单面"],
        ["负极厚度", 80.45, params_25c["Negative electrode thickness [m]"] * 1e6, "μm", "反弹后单面"],
        ["隔膜厚度", 11.0, params_25c["Separator thickness [m]"] * 1e6, "μm", "设计表0.011按mm口径换算"],
        ["正极粒径半径", 0.45, params_25c["Positive particle radius [m]"] * 1e6, "μm", "Dv50/2"],
        ["负极粒径半径", 5.5, params_25c["Negative particle radius [m]"] * 1e6, "μm", "Dv50/2"],
        ["设计电极宽度", params_module.DESIGN_ELECTRODE_WIDTH_M, params_module.DESIGN_ELECTRODE_WIDTH_M, "m", "213.5mm×83×双面×2JR"],
        ["电压对标面积系数", np.nan, benchmark_module.BENCHMARK_AREA_FACTOR, "-", "实测容量校准项"],
        ["产热面积系数", 1.0, benchmark_module.HEAT_AREA_FACTOR, "-", "原始设计面积"],
        ["接触阻抗", np.nan, params_25c["Contact resistance [Ohm]"], "Ω", "开启并参与端电压/产热"],
        ["负极OCP中段warp幅值", np.nan, params_module.NEGATIVE_OCP_STO_WARP_DELTA, "-", "CW368曲线辨识"],
        ["负极OCP电压偏置", np.nan, params_module.NEGATIVE_OCP_VOLTAGE_OFFSET_V * 1e3, "mV", "CW368曲线辨识"],
    ],
    columns=["参数", "设计表/推导值", "模型固化值", "单位", "说明"],
)
display(parameter_audit)

model_check = pd.DataFrame(
    {
        "检查项": ["模型", "接触阻抗", "热源", "温度", "输出周期", "网格"],
        "设置": [
            "DFN",
            "开启",
            "等温电化学热源 + I²R_contact",
            "25℃",
            "30 s",
            str(benchmark_module.VAR_PTS),
        ],
    }
)
display(model_check)"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 2. 实测数据覆盖范围"))
cells.append(
    nbf.v4.new_code_cell(
        """experiment_curves = benchmark_module.load_experiment_curves()
power_targets = benchmark_module.measured_power_targets(experiment_curves)
coverage_rows = []
for (p_rate, direction), curves in sorted(experiment_curves.items()):
    coverage_rows.append(
        {
            "P倍率": p_rate,
            "方向": direction,
            "完整实测曲线数": len(curves),
            "平均终止容量(Ah)": np.mean([curve["capacity_ah"].iloc[-1] for curve in curves]),
            "平均功率(W)": np.mean([curve["power_w"].median() for curve in curves]),
        }
    )
coverage = pd.DataFrame(coverage_rows)
display(coverage.style.format({"平均终止容量(Ah)": "{:.2f}", "平均功率(W)": "{:.2f}"}))
display(pd.DataFrame(
    [
        [rate, power_targets[rate], "实测对标" if rate in benchmark_module.MEASURED_RATES else "仅模型预测"]
        for rate in benchmark_module.RATES
    ],
    columns=["P倍率", "目标功率(W)", "数据状态"],
).style.format({"P倍率": "{:.3f}", "目标功率(W)": "{:.2f}"}))"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 3. 一键运行或加载完整结果"))
cells.append(
    nbf.v4.new_code_cell(
        """FORCE_RERUN = False
required_files = [
    OUTPUT_DIR / "curves.csv",
    OUTPUT_DIR / "metrics.csv",
    OUTPUT_DIR / "heat_summary.csv",
    OUTPUT_DIR / "efficiency_summary.csv",
]

if FORCE_RERUN or not all(path.exists() for path in required_files):
    results = run_benchmark(OUTPUT_DIR, period_s=30)
else:
    results = load_results(OUTPUT_DIR)
    print("已加载现有完整结果；如需重算，将 FORCE_RERUN 改为 True。")

curves = results["curves"]
metrics = results["metrics"]
heat_summary = results["heat_summary"]
efficiency_summary = results["efficiency_summary"]
print({name: len(frame) for name, frame in results.items()})"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 4. 模型—实测充放电曲线对标"))
cells.append(
    nbf.v4.new_code_cell(
        """plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

plot_dir = OUTPUT_DIR / "plots"
plot_dir.mkdir(parents=True, exist_ok=True)
fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0), squeeze=False)

for row, direction in enumerate(["充电", "放电"]):
    for col, p_rate in enumerate([0.125, 0.25]):
        ax = axes[row, col]
        subset = curves[
            (curves["p_rate"] == p_rate)
            & (curves["direction"] == direction)
            & (curves["series"] != "dfn_heat_design")
        ]
        for series, series_frame in subset.groupby("series"):
            if series == "dfn_sim":
                ax.plot(
                    series_frame["capacity_ah"],
                    series_frame["voltage_v"],
                    color="#111111",
                    lw=2.0,
                    label="DFN model",
                    zorder=5,
                )
            else:
                ax.plot(
                    series_frame["capacity_ah"],
                    series_frame["voltage_v"],
                    ls="--",
                    lw=1.0,
                    alpha=0.65,
                    label=series.replace("exp_", ""),
                )
        ax.set_title(f"25℃ {p_rate:.3f}P {'Charge' if direction == '充电' else 'Discharge'}")
        ax.set_xlabel("Capacity [Ah]")
        ax.set_ylabel("Voltage [V]")
        ax.legend(frameon=False, fontsize=7)

fig.tight_layout()
comparison_path = plot_dir / "cw368_voltage_benchmark.png"
fig.savefig(comparison_path, dpi=220, bbox_inches="tight")
plt.show()
print(comparison_path)"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 5. 电压误差、容量误差与能效"))
cells.append(
    nbf.v4.new_code_cell(
        """mean_metrics = metrics[(metrics["series"] == "mean") & (metrics["status"] == "ok")].copy()
voltage_metrics = mean_metrics[
    ["p_rate", "direction", "rmse_v", "rrmse_pct", "mae_v", "max_abs_error_v"]
]
capacity_metrics = mean_metrics[
    ["p_rate", "direction", "exp_end_capacity_ah", "sim_end_capacity_ah", "end_capacity_error_pct"]
]

print("电压误差：")
display(voltage_metrics.style.format({
    "p_rate": "{:.3f}",
    "rmse_v": "{:.4f}",
    "rrmse_pct": "{:.3f}",
    "mae_v": "{:.4f}",
    "max_abs_error_v": "{:.4f}",
}))
print("容量误差：")
display(capacity_metrics.style.format({
    "p_rate": "{:.3f}",
    "exp_end_capacity_ah": "{:.2f}",
    "sim_end_capacity_ah": "{:.2f}",
    "end_capacity_error_pct": "{:.3f}",
}))
print("能量效率：")
display(efficiency_summary.style.format({
    "p_rate": "{:.3f}",
    "exp_energy_efficiency_pct": "{:.3f}",
    "sim_energy_efficiency_pct": "{:.3f}",
    "efficiency_error_pct_point": "{:.3f}",
    "sim_charge_energy_wh": "{:.1f}",
    "sim_discharge_energy_wh": "{:.1f}",
}))"""
    )
)
cells.append(
    nbf.v4.new_markdown_cell(
        """## 6. 0.125P / 0.167P / 0.25P 产热功率

以下产热曲线全部使用 **原始设计面积（有效面积系数 1.0）**，不使用电压
对标中的 0.937 容量校准。"""
    )
)
cells.append(
    nbf.v4.new_code_cell(
        """plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

fig, axes = plt.subplots(2, 3, figsize=(15.0, 7.6), squeeze=False)
for row, direction in enumerate(["充电", "放电"]):
    for col, p_rate in enumerate(benchmark_module.RATES):
        ax = axes[row, col]
        sim = curves[
            (curves["p_rate"] == p_rate)
            & (curves["direction"] == direction)
            & (curves["series"] == "dfn_heat_design")
        ]
        ax.plot(sim["capacity_ah"], sim["net_total_heat_w"], lw=1.8, label="Net total")
        ax.plot(sim["capacity_ah"], sim["gross_total_heat_w"], lw=1.2, ls="--", label="Gross heat")
        ax.plot(sim["capacity_ah"], sim["contact_heat_w"], lw=1.0, label="Contact I²R")
        ax.set_title(f"{p_rate:.3f}P {'Charge' if direction == '充电' else 'Discharge'}")
        ax.set_xlabel("Capacity [Ah]")
        ax.set_ylabel("Heat power [W]")
        ax.legend(frameon=False, fontsize=7)

fig.tight_layout()
heat_path = plot_dir / "cw368_heat_power.png"
fig.savefig(heat_path, dpi=220, bbox_inches="tight")
plt.show()
print(heat_path)"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 7. 产热组分与积分热量"))
cells.append(
    nbf.v4.new_code_cell(
        """heat_display_columns = [
    "p_rate",
    "direction",
    "end_capacity_ah",
    "duration_h",
    "net_total_heat_w_mean",
    "net_total_heat_w_max",
    "net_total_heat_w_integral_wh",
    "gross_total_heat_w_mean",
    "gross_total_heat_w_max",
    "gross_total_heat_w_integral_wh",
    "contact_heat_w_mean",
    "contact_heat_w_integral_wh",
]
display(heat_summary[heat_display_columns].style.format({
    "p_rate": "{:.3f}",
    "end_capacity_ah": "{:.2f}",
    "duration_h": "{:.3f}",
    "net_total_heat_w_mean": "{:.2f}",
    "net_total_heat_w_max": "{:.2f}",
    "net_total_heat_w_integral_wh": "{:.2f}",
    "gross_total_heat_w_mean": "{:.2f}",
    "gross_total_heat_w_max": "{:.2f}",
    "gross_total_heat_w_integral_wh": "{:.2f}",
    "contact_heat_w_mean": "{:.2f}",
    "contact_heat_w_integral_wh": "{:.2f}",
}))

component_columns = [
    "p_rate", "direction",
    "ohmic_heat_w_integral_wh",
    "irreversible_heat_w_integral_wh",
    "reversible_heat_w_integral_wh",
    "hysteresis_heat_w_integral_wh",
    "contact_heat_w_integral_wh",
]
display(heat_summary[component_columns].style.format({
    "p_rate": "{:.3f}",
    **{column: "{:.2f}" for column in component_columns[2:]},
}))"""
    )
)
cells.append(nbf.v4.new_markdown_cell("## 8. 关键结论自动汇总"))
cells.append(
    nbf.v4.new_code_cell(
        """benchmark_mean = mean_metrics.groupby("p_rate").agg(
    rmse_v=("rmse_v", "mean"),
    rrmse_pct=("rrmse_pct", "mean"),
    capacity_error_pct=("end_capacity_error_pct", "mean"),
)
display(benchmark_mean.style.format("{:.3f}"))

for p_rate in [0.125, 0.25]:
    row = benchmark_mean.loc[p_rate]
    eff = efficiency_summary[np.isclose(efficiency_summary["p_rate"], p_rate)].iloc[0]
    print(
        f"{p_rate:.3f}P：平均电压 RMSE={row.rmse_v:.4f} V，"
        f"RRMSE={row.rrmse_pct:.3f}%，平均容量误差={row.capacity_error_pct:.3f}%；"
        f"模型能效={eff.sim_energy_efficiency_pct:.3f}%，"
        f"实测能效={eff.exp_energy_efficiency_pct:.3f}%。"
    )

prediction = heat_summary[np.isclose(heat_summary["p_rate"], 0.167)]
print("0.167P 为模型预测，无直接实测曲线：")
display(prediction[heat_display_columns].style.format({
    "p_rate": "{:.3f}",
    "end_capacity_ah": "{:.2f}",
    "duration_h": "{:.3f}",
    "net_total_heat_w_mean": "{:.2f}",
    "net_total_heat_w_max": "{:.2f}",
    "net_total_heat_w_integral_wh": "{:.2f}",
    "gross_total_heat_w_mean": "{:.2f}",
    "gross_total_heat_w_max": "{:.2f}",
    "gross_total_heat_w_integral_wh": "{:.2f}",
    "contact_heat_w_mean": "{:.2f}",
    "contact_heat_w_integral_wh": "{:.2f}",
}))"""
    )
)

nb["cells"] = cells
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
