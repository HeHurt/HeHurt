from pathlib import Path

import nbformat as nbf


task = Path(r"D:\Users\hez\Desktop\hithium\work\MIC_LDS\202607_何争_LDS CW501模型对标及峰值电流Mapping")
notebook_path = task / "02_模型" / "CW501_10s30s60s峰值电流Mapping.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata.kernelspec = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
nb.metadata.language_info = {"name": "python", "version": "3.11"}

nb.cells = [
    nbf.v4.new_markdown_cell(
        """# CW501 10s / 30s / 60s 峰值电流 Mapping

本 Notebook 使用启用接触阻抗的 DFN，按电压截止条件搜索最大恒流脉冲：

- 充电温度：0–55℃，5℃间隔。
- 放电温度：−30、−20、−10℃；0–55℃为5℃间隔。
- 脉冲时间：10 s、30 s、60 s。
- 充电 SOC：0–95%，5%间隔。
- 放电 SOC：5–100%，5%间隔。
- 电压限制：充电 3.65 V、放电 2.5 V。

全量计算按“方向×温度×脉宽”逐组保存，可中断并一键续算。"""
    ),
    nbf.v4.new_code_cell(
        """%load_ext autoreload
%autoreload 2
%matplotlib inline

import importlib
import os
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
FULL_OUTPUT_DIR = TASK_ROOT / "04_输出结果" / "峰值电流Mapping"
SMOKE_OUTPUT_DIR = TASK_ROOT / "04_输出结果" / "峰值电流Mapping_smoke"

if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

import cw501_peak_current_mapping as peak_module
importlib.reload(peak_module)

run_peak_current_mapping = peak_module.run_peak_current_mapping
load_peak_current_mapping = peak_module.load_peak_current_mapping
fresh_parameter_values = peak_module.fresh_parameter_values

print(f"PyBaMM: {pybamm.__version__}")
print(f"science style enabled: {'science' in plt.style.available}")
print(f"Full output: {FULL_OUTPUT_DIR}")"""
    ),
    nbf.v4.new_markdown_cell("## 1. 计算矩阵与模型检查"),
    nbf.v4.new_code_cell(
        """matrix_summary = pd.DataFrame(
    [
        ["Charge temperature [°C]", list(peak_module.DEFAULT_CHARGE_TEMPERATURES_C)],
        ["Discharge temperature [°C]", list(peak_module.DEFAULT_DISCHARGE_TEMPERATURES_C)],
        ["Pulse duration [s]", list(peak_module.DEFAULT_DURATIONS_S)],
        ["Charge SOC [%]", [int(x * 100) for x in peak_module.DEFAULT_CHARGE_SOC]],
        ["Discharge SOC [%]", [int(x * 100) for x in peak_module.DEFAULT_DISCHARGE_SOC]],
    ],
    columns=["Item", "Values"],
)
display(matrix_summary)

params_25c = fresh_parameter_values(25)
model_check = pd.DataFrame(
    {
        "Item": [
            "Nominal capacity [Ah]",
            "Contact resistance [Ohm]",
            "Lower cut-off [V]",
            "Upper cut-off [V]",
            "Expected groups",
            "Expected SOC results",
        ],
        "Value": [
            params_25c["Nominal cell capacity [A.h]"],
            params_25c["Contact resistance [Ohm]"],
            params_25c["Lower voltage cut-off [V]"],
            params_25c["Upper voltage cut-off [V]"],
            3 * (12 + 15),
            3 * (12 * 20 + 15 * 20),
        ],
    }
)
display(model_check)"""
    ),
    nbf.v4.new_markdown_cell(
        """## 2. 已验证的最小案例

25℃、10 s、50% SOC 的充电和放电结果用于确认模型、接触阻抗及截止事件正常。"""
    ),
    nbf.v4.new_code_cell(
        """smoke_df = load_peak_current_mapping(SMOKE_OUTPUT_DIR)
if smoke_df.empty:
    smoke_df = run_peak_current_mapping(
        output_dir=SMOKE_OUTPUT_DIR,
        durations_s=(10,),
        charge_temperatures_c=(25,),
        discharge_temperatures_c=(25,),
        charge_soc=(0.5,),
        discharge_soc=(0.5,),
        resume=True,
    )
display(smoke_df)"""
    ),
    nbf.v4.new_markdown_cell(
        """## 3. 一键运行或续算完整 Mapping

**正常打开 Notebook 时，运行下面这一个单元即可。**  
输出逐组写入 `04_输出结果/峰值电流Mapping/peak_current_map.csv`；中断后再次运行会自动跳过已完成组。

自动交付校验环境会设置 `CW501_SKIP_FULL_MAPPING=1`，仅跳过耗时的全矩阵计算，不影响你本地正常运行。"""
    ),
    nbf.v4.new_code_cell(
        """if os.getenv("CW501_SKIP_FULL_MAPPING") == "1":
    print("自动校验模式：跳过全量 Mapping，使用烟雾结果检查后处理。")
    mapping_df = smoke_df.copy()
else:
    mapping_df = run_peak_current_mapping(
        output_dir=FULL_OUTPUT_DIR,
        durations_s=peak_module.DEFAULT_DURATIONS_S,
        charge_temperatures_c=peak_module.DEFAULT_CHARGE_TEMPERATURES_C,
        discharge_temperatures_c=peak_module.DEFAULT_DISCHARGE_TEMPERATURES_C,
        charge_soc=peak_module.DEFAULT_CHARGE_SOC,
        discharge_soc=peak_module.DEFAULT_DISCHARGE_SOC,
        resume=True,
    )

print(f"Loaded rows: {len(mapping_df):,}")
display(mapping_df.tail())"""
    ),
    nbf.v4.new_markdown_cell(
        """## 4. 随时重新加载检查点

若计算在另一个窗口运行，可重复运行本单元刷新结果，不需要重启 Kernel。"""
    ),
    nbf.v4.new_code_cell(
        """latest_full_df = load_peak_current_mapping(FULL_OUTPUT_DIR)
if latest_full_df.empty:
    mapping_df = smoke_df.copy()
    active_output_dir = SMOKE_OUTPUT_DIR
    print("完整 Mapping 尚未生成，当前显示烟雾结果。")
else:
    mapping_df = latest_full_df.copy()
    active_output_dir = FULL_OUTPUT_DIR
    print("已加载完整/部分 Mapping 检查点。")

coverage = (
    mapping_df.groupby(["direction", "duration_s"], as_index=False)
    .agg(
        temperatures=("temperature_c", "nunique"),
        soc_results=("soc", "count"),
        solved=("status", lambda values: int((values == "ok").sum())),
        unsolved=("status", lambda values: int((values != "ok").sum())),
    )
)
display(coverage)
print(f"Active rows: {len(mapping_df):,}")"""
    ),
    nbf.v4.new_markdown_cell("## 5. 峰值电流热力图"),
    nbf.v4.new_code_cell(
        """plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

plot_dir = active_output_dir / "plots"
plot_dir.mkdir(parents=True, exist_ok=True)
durations = [10, 30, 60]
fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.0), squeeze=False)

for row_index, direction in enumerate(["charge", "discharge"]):
    for column_index, duration_s in enumerate(durations):
        ax = axes[row_index, column_index]
        subset = mapping_df[
            (mapping_df["direction"] == direction)
            & (mapping_df["duration_s"] == duration_s)
        ]
        if subset.empty:
            ax.axis("off")
            continue
        pivot = subset.pivot_table(
            index="temperature_c",
            columns="soc_pct",
            values="peak_current_ka",
            aggfunc="first",
        ).sort_index()
        image = ax.imshow(
            pivot.to_numpy(),
            aspect="auto",
            origin="lower",
            cmap="viridis",
            interpolation="nearest",
        )
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_xticklabels([f"{value:.0f}" for value in pivot.columns], rotation=90)
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_yticklabels([f"{value:.0f}" for value in pivot.index])
        ax.set_xlabel("SOC [%]")
        ax.set_ylabel("Temperature [°C]")
        ax.set_title(f"{direction.title()} {duration_s}s Peak Current [kA]")
        fig.colorbar(image, ax=ax, label="Peak current [kA]")

fig.tight_layout()
heatmap_path = plot_dir / "cw501_peak_current_heatmaps.png"
fig.savefig(heatmap_path, dpi=220, bbox_inches="tight")
plt.show()
print(heatmap_path)"""
    ),
    nbf.v4.new_markdown_cell("## 6. 典型 SOC 的温度切片"),
    nbf.v4.new_code_cell(
        """plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

SELECTED_SOC_PCT = [20, 50, 80]
fig, axes = plt.subplots(2, 3, figsize=(14.5, 7.5), squeeze=False)

for row_index, direction in enumerate(["charge", "discharge"]):
    for column_index, duration_s in enumerate(durations):
        ax = axes[row_index, column_index]
        subset = mapping_df[
            (mapping_df["direction"] == direction)
            & (mapping_df["duration_s"] == duration_s)
        ]
        if subset.empty:
            ax.axis("off")
            continue
        for soc_pct in SELECTED_SOC_PCT:
            series = subset[np.isclose(subset["soc_pct"], soc_pct)].sort_values("temperature_c")
            if not series.empty:
                ax.plot(
                    series["temperature_c"],
                    series["peak_current_ka"],
                    marker="o",
                    ms=3.5,
                    label=f"{soc_pct}% SOC",
                )
        ax.set_xlabel("Temperature [°C]")
        ax.set_ylabel("Peak current [kA]")
        ax.set_title(f"{direction.title()} {duration_s}s")
        ax.legend(frameon=False)

fig.tight_layout()
slice_path = plot_dir / "cw501_peak_current_temperature_slices.png"
fig.savefig(slice_path, dpi=220, bbox_inches="tight")
plt.show()
print(slice_path)"""
    ),
    nbf.v4.new_markdown_cell(
        """## 7. 单张 Mapping 表查看

修改方向和脉宽即可查看或复制对应的“温度×SOC”峰值电流表。"""
    ),
    nbf.v4.new_code_cell(
        """VIEW_DIRECTION = "charge"  # "charge" / "discharge"
VIEW_DURATION_S = 10

mapping_table_ka = (
    mapping_df[
        (mapping_df["direction"] == VIEW_DIRECTION)
        & (mapping_df["duration_s"] == VIEW_DURATION_S)
    ]
    .pivot_table(
        index="temperature_c",
        columns="soc_pct",
        values="peak_current_ka",
        aggfunc="first",
    )
    .sort_index()
)
mapping_table_ka.index.name = "Temperature [°C]"
mapping_table_ka.columns.name = "SOC [%]"
display(mapping_table_ka.style.format("{:.3f}"))

unsolved = mapping_df[mapping_df["status"] != "ok"]
print(f"Unsolved points: {len(unsolved)}")
if not unsolved.empty:
    display(unsolved)"""
    ),
]

notebook_path.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, notebook_path)
print(notebook_path)
