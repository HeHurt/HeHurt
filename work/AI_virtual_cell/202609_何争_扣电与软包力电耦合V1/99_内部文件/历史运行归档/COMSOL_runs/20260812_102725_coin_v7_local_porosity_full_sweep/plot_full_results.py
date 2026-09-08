import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_102725_coin_v7_local_porosity_full_sweep")
DATA = RUN / "exported_data"
PLOTS = RUN / "plots"
V6_DATA = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260811_132326_coin_v6_force_postprocess\exported_data")
FORCES = [0, 100, 250, 500]
COLORS = {0: "#6b7280", 100: "#2a6fbb", 250: "#f59e0b", 500: "#d62728"}

try:
    import scienceplots  # noqa: F401
    plt.style.use(["science", "no-latex"])
except (ImportError, OSError):
    pass
plt.rcParams.update({"font.family": ["Calibri", "Microsoft YaHei"], "axes.unicode_minus": False, "axes.grid": True, "grid.alpha": 0.22})


def save(fig, name):
    path = PLOTS / name
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


v7_voltage = pd.read_csv(DATA / "v7_voltage_soc.csv")
v7_stage = pd.read_csv(DATA / "v7_stage_summary.csv")
v7_region = pd.read_csv(DATA / "v7_local_pressure_porosity.csv")
v7_cl = pd.read_csv(DATA / "v7_electrolyte_summary.csv")
v7_theta = pd.read_csv(DATA / "v7_interface_stoichiometry_summary.csv")
v7_shell = pd.read_csv(DATA / "v7_shell_current_summary.csv")
v6_voltage = pd.read_csv(V6_DATA / "force_voltage_soc.csv")
v6_stage = pd.read_csv(V6_DATA / "force_stage_summary.csv")
v6_cl = pd.read_csv(V6_DATA / "force_electrolyte_summary.csv")
plots = []

# 1. V7 charge curves and V7-V6 voltage difference.
fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), constrained_layout=True)
grid = np.linspace(0.01, 0.995, 300)
for force in FORCES:
    v7 = v7_voltage[(v7_voltage.force_N == force) & (v7_voltage.current_Crate > 0.25)].sort_values("actual_SOC")
    v6 = v6_voltage[(v6_voltage.force_N == force) & (v6_voltage.current_Crate > 0.25)].sort_values("actual_SOC")
    axes[0].plot(v7.actual_SOC * 100, v7.loaded_voltage_V, color=COLORS[force], lw=1.7, label=f"{force} N")
    v7_i = np.interp(grid, v7.actual_SOC, v7.loaded_voltage_V)
    v6_i = np.interp(grid, v6.actual_SOC, v6.loaded_voltage_V)
    axes[1].plot(grid * 100, (v7_i - v6_i) * 1000, color=COLORS[force], lw=1.7, label=f"{force} N")
axes[0].axhline(3.65, color="crimson", ls="--", lw=1, label="3.65 V")
axes[0].set(xlabel="实际充电 SOC (%)", ylabel="加载端电压 (V)", title="V7局部孔隙率模型")
axes[1].axhline(0, color="0.35", lw=0.8)
axes[1].set(xlabel="实际充电 SOC (%)", ylabel="V7−V6 电压差 (mV)", title="相对均匀孔隙率模型的电压变化")
for ax in axes:
    ax.legend(fontsize=8)
fig.suptitle("V7完整四外力扫描：电压–SOC及模型差异", fontsize=14)
plots.append(save(fig, "01_voltage_soc_v7_vs_v6.png"))

# 2. Cutoff comparison.
v7_cut = v7_stage[v7_stage.stage == "cutoff"].sort_values("force_N")
v6_cut = v6_stage[v6_stage.stage == "cutoff"].sort_values("force_N")
fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.7), constrained_layout=True)
axes[0].plot(v6_cut.force_N, v6_cut.actual_SOC * 100, "o--", label="V6均匀孔隙率")
axes[0].plot(v7_cut.force_N, v7_cut.actual_SOC * 100, "s-", label="V7局部孔隙率")
axes[1].plot(v6_cut.force_N, v6_cut.loaded_voltage_V, "o--", label="V6均匀孔隙率")
axes[1].plot(v7_cut.force_N, v7_cut.loaded_voltage_V, "s-", label="V7局部孔隙率")
axes[0].set(xlabel="外力 (N)", ylabel="截止 SOC (%)", title="事件前最后充电点SOC")
axes[1].set(xlabel="外力 (N)", ylabel="事件前加载电压 (V)", title="事件定位点电压")
for ax in axes:
    ax.legend(fontsize=8)
fig.suptitle("V6/V7充电截止状态对比", fontsize=14)
plots.append(save(fig, "02_cutoff_v7_vs_v6.png"))

# 3. Local pressure and porosity at cutoff.
cut_region = v7_region[v7_region.stage == "cutoff"]
fig, axes = plt.subplots(1, 2, figsize=(12.3, 4.9), constrained_layout=True)
region_labels = {"negative": "负极", "separator": "隔膜", "positive": "正极"}
markers = {"negative": "o", "separator": "s", "positive": "^"}
for region in region_labels:
    group = cut_region[cut_region.region == region].sort_values("force_N")
    axes[0].plot(group.force_N, group.pressure_mean_MPa, marker=markers[region], label=region_labels[region])
    axes[0].fill_between(group.force_N, group.pressure_min_MPa, group.pressure_max_MPa, alpha=0.10)
    lower = np.maximum(0, group.porosity_mean - group.porosity_min)
    upper = np.maximum(0, group.porosity_max - group.porosity_mean)
    axes[1].errorbar(group.force_N, group.porosity_mean, yerr=np.vstack([lower, upper]), marker=markers[region], capsize=3, label=region_labels[region])
axes[0].axhline(2, color="crimson", ls="--", lw=1, label="2 MPa截断")
axes[0].set(xlabel="外力 (N)", ylabel="局部压缩压力 (MPa)", title="区域平均值及min–max范围")
axes[1].set(xlabel="外力 (N)", ylabel="局部孔隙率", title="区域平均值及min–max范围")
for ax in axes:
    ax.legend(fontsize=8)
fig.suptitle("V7截止阶段：局部压力与孔隙率分布", fontsize=14)
plots.append(save(fig, "03_local_pressure_porosity_cutoff.png"))

# 4. Electrolyte concentration polarization V7 vs V6.
def cell_span(frame):
    subset = frame[frame.stage == "cutoff"]
    return [
        subset[subset.force_N == force].cl_max_mol_m3.max() - subset[subset.force_N == force].cl_min_mol_m3.min()
        for force in FORCES
    ]

v7_span = cell_span(v7_cl)
v6_span = cell_span(v6_cl)
fig, axes = plt.subplots(1, 2, figsize=(12.3, 4.8), constrained_layout=True)
axes[0].plot(FORCES, v6_span, "o--", label="V6均匀孔隙率")
axes[0].plot(FORCES, v7_span, "s-", label="V7局部孔隙率")
axes[0].set(xlabel="外力 (N)", ylabel="全电芯浓度极差 (mol/m³)", title="截止时浓差不均匀程度")
for region in region_labels:
    group = v7_cl[(v7_cl.stage == "cutoff") & (v7_cl.region == region)].sort_values("force_N")
    axes[1].plot(group.force_N, group.cl_std_mol_m3, marker=markers[region], label=region_labels[region])
axes[1].set(xlabel="外力 (N)", ylabel="区域浓度标准差 (mol/m³)", title="V7各多孔区浓度非均匀性")
for ax in axes:
    ax.legend(fontsize=8)
fig.suptitle("局部孔隙率对电解液浓差极化的影响", fontsize=14)
plots.append(save(fig, "04_electrolyte_polarization_v7_vs_v6.png"))

# 5. Interface stoichiometry heterogeneity.
cut_theta = v7_theta[v7_theta.stage == "cutoff"]
interface_labels = {"negative_Cu": "负极–铜箔", "negative_separator": "负极–隔膜", "positive_separator": "正极–隔膜", "positive_Al": "正极–铝箔"}
fig, axes = plt.subplots(1, 2, figsize=(12.3, 4.8), constrained_layout=True)
for interface, label in interface_labels.items():
    group = cut_theta[cut_theta.interface == interface].sort_values("force_N")
    target = axes[0] if interface.startswith("negative") else axes[1]
    target.plot(group.force_N, group.stoichiometry_span, "o-", label=label)
axes[0].set(xlabel="外力 (N)", ylabel="界面嵌锂比极差", title="负极界面")
axes[1].set(xlabel="外力 (N)", ylabel="界面嵌锂比极差", title="正极界面")
for ax in axes:
    ax.legend(fontsize=8)
fig.suptitle("V7截止阶段：局部孔隙率引起的界面嵌锂不均匀", fontsize=14)
plots.append(save(fig, "05_interface_stoichiometry_heterogeneity.png"))

# 6. Shell current redistribution.
cut_shell = v7_shell[v7_shell.stage == "cutoff"].sort_values("force_N")
fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.7), constrained_layout=True)
axes[0].plot(cut_shell.force_N, cut_shell.shell_current_mean_A_m2, "o-", color="#2a6fbb")
axes[1].plot(cut_shell.force_N, cut_shell.shell_current_std_A_m2, "o-", color="#d62728", label="标准差")
axes[1].plot(cut_shell.force_N, cut_shell.shell_current_max_A_m2, "s--", color="#6b7280", label="最大值")
axes[0].set(xlabel="外力 (N)", ylabel="平均 |Js| (A/m²)", title="过流结构平均电流密度")
axes[1].set(xlabel="外力 (N)", ylabel="|Js| (A/m²)", title="电流密度离散性与峰值")
axes[1].legend(fontsize=8)
fig.suptitle("V7截止阶段：过流结构电流密度统计", fontsize=14)
plots.append(save(fig, "06_shell_current_density_summary.png"))

summary = {
    "plots": plots,
    "cutoff_v7": v7_cut.to_dict("records"),
    "concentration_span_v6_mol_m3": dict(zip(map(str, FORCES), map(float, v6_span))),
    "concentration_span_v7_mol_m3": dict(zip(map(str, FORCES), map(float, v7_span))),
    "porosity_cutoff": cut_region.to_dict("records"),
    "notes": [
        "局部压力场来自对应F_ext的静力学sol2，不随SOC变化；本版未包含材料呼吸。",
        "局部压力上限2 MPa用于限制边缘应力集中，压力与孔隙率参数仍需实验标定。",
        "事件前最后充电点可能存在3.65 V定位过冲，截止电压不宜用于毫伏级定量比较。",
    ],
}
(RUN / "postprocess_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"plots": plots, "summary": str(RUN / 'postprocess_summary.json')}, ensure_ascii=False))
