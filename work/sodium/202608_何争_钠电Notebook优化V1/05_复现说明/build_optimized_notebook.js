const fs = require("fs");
const path = require("path");

const taskRoot = path.resolve(__dirname, "..");
const notebookPath = path.join(taskRoot, "02_模型", "钠电_多温度倍率对标_优化版.ipynb");

let cellNumber = 0;

function nextCellId(prefix) {
  cellNumber += 1;
  return `${prefix}-${String(cellNumber).padStart(2, "0")}`;
}

function markdown(source) {
  return { cell_type: "markdown", id: nextCellId("markdown"), metadata: {}, source };
}

function code(source) {
  return { cell_type: "code", id: nextCellId("code"), execution_count: null, metadata: {}, outputs: [], source };
}

const cells = [
  markdown(`# 钠离子 164 Ah 电芯多温度倍率对标

本 Notebook 对实验倍率充电与倍率放电数据执行可复现的 PyBaMM DFN 对标。

- 倍率充电：0、10、15、20、25、35、45 ℃，每个温度 0.1/0.3/0.5/0.8/1.0/1.5C。
- 倍率放电：25、−20 ℃，每个温度 0.1/0.3/0.5/0.8/1.0/1.5C。
- 实验工况从文件名解析，不再依赖文件排序和列表位置。
- 每个 case 独立创建 ParameterValues，避免温度或参数污染。
- 原始运行结果写入 BatteryProject/output/runs/sodium_rate_benchmark/<run_id>/。

建议先执行烟雾单元确认环境，再执行完整矩阵。`),

  markdown(`## 1. 环境与配置

本单元只包含显式路径、导入、绘图样式和运行参数。若迁移机器，只需修改 PROJECT_ROOT 与 DATA_ROOT。`),

  code(`from pathlib import Path
import json
import sys
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display

PROJECT_ROOT = Path(r"D:\\Users\\hez\\Desktop\\hithium")
TASK_ROOT = PROJECT_ROOT / "work" / "sodium" / "202608_何争_钠电Notebook优化V1"
DATA_ROOT = TASK_ROOT / "03_输入数据" / "04-钠电电芯数据_csv"
RUN_ID = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S_notebook")
RUN_DIR = PROJECT_ROOT / "BatteryProject" / "output" / "runs" / "sodium_rate_benchmark" / RUN_ID
PLOTS_DIR = RUN_DIR / "plots"
RUN_DIR.mkdir(parents=True, exist_ok=False)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import scienceplots  # noqa: F401
    plt.style.use("science")
except (ImportError, OSError):
    warnings.warn("scienceplots 不可用，回退到 matplotlib default 样式。")
    plt.style.use("default")

plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 120

from params import load_cell_params
from BatteryProject.src.workflows.sodium_rate_benchmark import (
    SodiumBenchmarkSpec,
    discover_sodium_rate_cases,
    run_sodium_rate_benchmark,
    sodium_curve_frame,
    sodium_metrics_frame,
)

get_hithium_params = load_cell_params("Na", reload_module=True)
SPEC = SodiumBenchmarkSpec(
    charge_cutoff_v=3.3,
    discharge_cutoff_v=1.5,
    charge_initial_soc=0.0,
    discharge_initial_soc=1.0,
)
print(f"PyBaMM workflow ready. RUN_DIR={RUN_DIR}")`),

  markdown(`## 2. 实验数据发现与覆盖检查

覆盖检查必须得到 42 个 charge case 和 12 个 discharge case。倍率和温度直接来自路径元数据。`),

  code(`all_cases = discover_sodium_rate_cases(DATA_ROOT)
case_table = pd.DataFrame([
    {
        "mode": case.mode,
        "temperature_C": case.temperature_c,
        "rate_C": case.rate_c,
        "file": str(case.data_path),
        "size_bytes": case.data_path.stat().st_size,
    }
    for case in all_cases
])

coverage = (
    case_table.groupby(["mode", "temperature_C"])["rate_C"]
    .agg(["count", lambda values: ", ".join(f"{value:g}" for value in sorted(values))])
    .rename(columns={"<lambda_0>": "rates_C"})
    .reset_index()
)
assert (case_table["mode"] == "charge").sum() == 42, "倍充 case 应为 42 个"
assert (case_table["mode"] == "discharge").sum() == 12, "倍放 case 应为 12 个"
assert not case_table.duplicated(["mode", "temperature_C", "rate_C"]).any(), "存在重复工况"
display(coverage)
case_table.to_csv(RUN_DIR / "case_coverage.csv", index=False, encoding="utf-8-sig")`),

  markdown(`## 3. OCP 参数曲线检查

直接读取参数表并显示正、负极 OCP 随 stoichiometry 的变化。这里不把电极 stoichiometry 误标为整电芯 SOC。`),

  code(`def load_ocp_profile(file_name):
    raw = pd.read_csv(PROJECT_ROOT / "params" / file_name, header=None, names=["stoichiometry", "ocp_V"])
    return raw.sort_values("stoichiometry").drop_duplicates("stoichiometry")

positive_ocp = load_ocp_profile("Na_revise.csv")
negative_ocp = load_ocp_profile("HardC.csv")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
axes[0].plot(positive_ocp["stoichiometry"], positive_ocp["ocp_V"], color="#0068b5", lw=1.8)
axes[0].set(title="NFPP positive-electrode OCP", xlabel="Stoichiometry", ylabel="OCP (V)")
axes[1].plot(negative_ocp["stoichiometry"], negative_ocp["ocp_V"], color="#d64541", lw=1.8)
axes[1].set(title="Hard-carbon negative-electrode OCP", xlabel="Stoichiometry", ylabel="OCP (V)")
for ax in axes:
    ax.grid(alpha=0.25)
fig.savefig(PLOTS_DIR / "ocp_parameter_profiles.png", bbox_inches="tight")
plt.show()`),

  markdown(`## 4. 最小烟雾测试

先运行 25 ℃、0.1C 充电 case。必须状态为 ok，才进入完整矩阵。`),

  code(`smoke_case = next(case for case in all_cases if case.key == ("charge", 25.0, 0.1))
smoke_results = run_sodium_rate_benchmark(
    [smoke_case],
    get_hithium_params,
    spec=SPEC,
    showprogress=False,
    stop_on_error=True,
)
smoke_metrics = sodium_metrics_frame(smoke_results)
assert smoke_metrics.loc[0, "status"] == "ok"
display(smoke_metrics)`),

  markdown(`## 5. 完整 54-case 仿真

各 case 相互独立。失败 case 会保留为结构化记录，不会污染或中断其他工况。`),

  code(`results = run_sodium_rate_benchmark(
    all_cases,
    get_hithium_params,
    spec=SPEC,
    showprogress=False,
    stop_on_error=False,
)
metrics = sodium_metrics_frame(results)
curves = sodium_curve_frame(results, max_points_per_curve=500)

status_summary = metrics.groupby(["mode", "status"]).size().rename("cases").reset_index()
display(status_summary)
display(metrics.round(4))

metrics.to_csv(RUN_DIR / "benchmark_metrics.csv", index=False, encoding="utf-8-sig")
curves.to_csv(RUN_DIR / "benchmark_curves.csv", index=False, encoding="utf-8-sig")`),

  markdown(`## 6. Sim–Exp 曲线对比

实验曲线使用虚线，模型曲线使用实线；相同倍率保持相同颜色。充电与放电分别按温度输出。`),

  code(`RATE_COLORS = {
    0.1: "#111111",
    0.3: "#d64541",
    0.5: "#0099cc",
    0.8: "#f28e2b",
    1.0: "#2ca02c",
    1.5: "#8e5ea2",
}

def plot_temperature_comparison(mode, temperature_c):
    selected = [
        result for key, result in results.items()
        if key[0] == mode and key[1] == temperature_c and result.status == "ok"
    ]
    selected.sort(key=lambda result: result.case.rate_c)
    fig, ax = plt.subplots(figsize=(8.2, 5.2), constrained_layout=True)
    for result in selected:
        rate = result.case.rate_c
        color = RATE_COLORS[rate]
        ax.plot(
            result.experiment["capacity_ah"],
            result.experiment["voltage_v"],
            ls="--",
            lw=1.2,
            color=color,
            label=f"{rate:g}C Exp",
        )
        ax.plot(
            result.simulation["capacity_ah"],
            result.simulation["voltage_v"],
            ls="-",
            lw=1.5,
            color=color,
            label=f"{rate:g}C Sim",
        )
    direction = "Charge" if mode == "charge" else "Discharge"
    ax.set(
        xlabel="Capacity (Ah)",
        ylabel="Voltage (V)",
        title=f"{direction}: {temperature_c:+g} °C — Sim vs Exp",
    )
    ax.grid(alpha=0.25)
    ax.legend(ncol=2, fontsize=8)
    file_name = f"{mode}_{temperature_c:+g}C_sim_exp.png".replace("+", "p").replace("-", "m")
    fig.savefig(PLOTS_DIR / file_name, bbox_inches="tight")
    plt.show()

for temperature_c in sorted(case_table.loc[case_table["mode"] == "charge", "temperature_C"].unique()):
    plot_temperature_comparison("charge", temperature_c)

for temperature_c in sorted(case_table.loc[case_table["mode"] == "discharge", "temperature_C"].unique()):
    plot_temperature_comparison("discharge", temperature_c)`),

  markdown(`## 7. 误差与容量偏差汇总

RMSE/RRMSE 单独输出，不把数值堆叠到曲线图中。容量误差为 Sim − Exp。`),

  code(`successful = metrics.loc[metrics["status"] == "ok"].copy()

def plot_metric_heatmap(mode, metric, title, colorbar_label, cmap="viridis"):
    table = successful.loc[successful["mode"] == mode].pivot(
        index="temperature_c", columns="rate_c", values=metric
    ).sort_index().sort_index(axis=1)
    fig, ax = plt.subplots(figsize=(7.5, 3.8), constrained_layout=True)
    image = ax.imshow(table.to_numpy(), aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(table.columns)), [f"{rate:g}C" for rate in table.columns])
    ax.set_yticks(range(len(table.index)), [f"{temp:+g} °C" for temp in table.index])
    ax.set(xlabel="Rate", ylabel="Temperature", title=title)
    for row in range(table.shape[0]):
        for col in range(table.shape[1]):
            value = table.iloc[row, col]
            if np.isfinite(value):
                ax.text(col, row, f"{value:.3f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label=colorbar_label)
    fig.savefig(PLOTS_DIR / f"{mode}_{metric}_heatmap.png", bbox_inches="tight")
    plt.show()

plot_metric_heatmap("charge", "voltage_rmse_v", "Charge voltage RMSE", "RMSE (V)", "Blues")
plot_metric_heatmap("discharge", "voltage_rmse_v", "Discharge voltage RMSE", "RMSE (V)", "Blues")
plot_metric_heatmap("charge", "capacity_error_pct", "Charge capacity error", "Error (%)", "coolwarm")
plot_metric_heatmap("discharge", "capacity_error_pct", "Discharge capacity error", "Error (%)", "coolwarm")

summary_columns = [
    "mode", "temperature_c", "rate_c", "voltage_rmse_v", "voltage_rrmse_pct",
    "capacity_error_ah", "capacity_error_pct", "solve_seconds", "termination",
]
display(successful[summary_columns].round(4))`),

  markdown(`## 8. 单 case 内部状态诊断

默认展示 25 ℃、1C 充电。该单元只读取已经完成的 result，不依赖最后一次循环残留的 sim 变量。`),

  code(`DIAGNOSTIC_KEY = ("charge", 25.0, 1.0)
diagnostic = results[DIAGNOSTIC_KEY]
assert diagnostic.status == "ok", diagnostic.error
solution = diagnostic.solution
capacity = solution["Throughput capacity [A.h]"].entries

diagnostic_variables = [
    ("Voltage [V]", "Voltage (V)"),
    ("Battery open-circuit voltage [V]", "OCV (V)"),
    ("Average positive particle stoichiometry", "Positive stoichiometry"),
    ("Average negative particle stoichiometry", "Negative stoichiometry"),
]
fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
for ax, (variable, ylabel) in zip(axes.flat, diagnostic_variables):
    values = np.asarray(solution[variable].entries).squeeze()
    ax.plot(capacity, values, lw=1.5)
    ax.set(xlabel="Throughput capacity (Ah)", ylabel=ylabel, title=variable)
    ax.grid(alpha=0.25)
fig.savefig(PLOTS_DIR / "diagnostic_charge_25C_1C.png", bbox_inches="tight")
plt.show()`),

  markdown(`## 9. 运行清单与验收

最终单元写入机器可读 manifest，并检查 54 个 case 是否全部成功。若存在失败，保留结果并明确报错。`),

  code(`failed = metrics.loc[metrics["status"] != "ok", ["mode", "temperature_c", "rate_c", "error"]]
manifest = {
    "run_id": RUN_ID,
    "data_root": str(DATA_ROOT),
    "case_count": int(len(metrics)),
    "success_count": int((metrics["status"] == "ok").sum()),
    "failure_count": int((metrics["status"] != "ok").sum()),
    "charge_count": int((metrics["mode"] == "charge").sum()),
    "discharge_count": int((metrics["mode"] == "discharge").sum()),
    "outputs": [
        "case_coverage.csv",
        "benchmark_metrics.csv",
        "benchmark_curves.csv",
        "plots/",
    ],
}
(RUN_DIR / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
display(pd.DataFrame([manifest]))
if not failed.empty:
    display(failed)
assert len(metrics) == 54, f"应输出 54 个 case，实际 {len(metrics)}"
assert failed.empty, f"仍有 {len(failed)} 个仿真失败，请查看失败表格"
print(f"验收通过：54/54 cases 成功。结果目录：{RUN_DIR}")`),
];

const notebook = {
  cells,
  metadata: {
    kernelspec: { display_name: "Python 3", language: "python", name: "python3" },
    language_info: { name: "python", version: "3.11" },
  },
  nbformat: 4,
  nbformat_minor: 5,
};

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
console.log(notebookPath);
