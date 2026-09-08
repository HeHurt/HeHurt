import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260811_132326_coin_v6_force_postprocess")
DATA = RUN / "exported_data"
PLOTS = RUN / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)
FORCES = [0, 100, 250, 500]
COLORS = {0: "#6b7280", 100: "#2a6fbb", 250: "#f59e0b", 500: "#d62728"}
LABELS = {force: f"{force} N" for force in FORCES}

try:
    import scienceplots  # noqa: F401
    plt.style.use(["science", "no-latex"])
except (ImportError, OSError):
    pass
plt.rcParams.update({
    "font.family": ["Calibri", "Microsoft YaHei"],
    "axes.unicode_minus": False,
    "axes.grid": True,
    "grid.alpha": 0.22,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def save(fig, name):
    path = PLOTS / name
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


voltage = pd.read_csv(DATA / "force_voltage_soc.csv")
stages = pd.read_csv(DATA / "force_stage_summary.csv")
mechanics = pd.read_csv(DATA / "force_mechanical_summary.csv")
interfaces = pd.read_csv(DATA / "force_interface_stoichiometry.csv")
electrolyte = pd.read_csv(DATA / "force_electrolyte_summary.csv")
plots = []

# 1. Voltage and millivolt-scale force sensitivity.
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
soc_grid = np.linspace(0.01, 0.99, 250)
base_interp = None
for force in FORCES:
    group = voltage[(voltage.force_N == force) & (voltage.current_Crate > 0.25)].sort_values("actual_SOC")
    axes[0].plot(group.actual_SOC * 100, group.loaded_voltage_V, color=COLORS[force], lw=1.8, label=LABELS[force])
    interp = np.interp(soc_grid, group.actual_SOC, group.loaded_voltage_V)
    if force == 0:
        base_interp = interp
    axes[1].plot(soc_grid * 100, (interp - base_interp) * 1000, color=COLORS[force], lw=1.8, label=LABELS[force])
axes[0].axhline(3.65, color="crimson", ls="--", lw=1.1, label="3.65 V 设定阈值")
axes[0].set(xlabel="实际充电 SOC (%)", ylabel="加载端电压 (V)", title="充电电压–SOC")
axes[1].axhline(0, color="0.35", lw=0.8)
axes[1].set(xlabel="实际充电 SOC (%)", ylabel="相对 0 N 的电压变化 (mV)", title="外力引起的电压偏移")
for ax in axes:
    ax.legend(fontsize=8)
fig.suptitle("V6 已保存解：不同外力下的电压性能对比", fontsize=14)
plots.append(save(fig, "01_voltage_SOC_force_comparison.png"))

# 2. Coupling path and charge-end metrics.
cutoff = stages[stages.stage == "cutoff"].sort_values("force_N")
soc50 = stages[stages.stage == "SOC50"].sort_values("force_N")
fig, axes = plt.subplots(2, 2, figsize=(11.5, 8), constrained_layout=True)
axes[0, 0].plot(soc50.force_N, soc50.pressure_MPa, "o-", color="#2a6fbb")
axes[0, 0].set(xlabel="外力 (N)", ylabel="等效面压 (MPa)", title="外力 → 面压")
axes[0, 1].plot(soc50.force_N, soc50.contact_resistance_mohm, "o-", color="#d62728")
axes[0, 1].set(xlabel="外力 (N)", ylabel="等效接触电阻 (mΩ)", title="面压 → 接触电阻")
for column, label, color in [("epsl_negative", "负极", "#333333"), ("epsl_separator", "隔膜", "#2a6fbb"), ("epsl_positive", "正极", "#d62728")]:
    axes[1, 0].plot(soc50.force_N, soc50[column], "o-", label=label, color=color)
axes[1, 0].set(xlabel="外力 (N)", ylabel="液相孔隙率", title="面压 → 多孔区孔隙率")
axes[1, 0].legend(fontsize=8)
ax = axes[1, 1]
ax.plot(cutoff.force_N, cutoff.actual_SOC * 100, "o-", color="#2a6fbb", label="截止 SOC")
ax.set(xlabel="外力 (N)", ylabel="截止 SOC (%)", title="充电截止状态")
ax2 = ax.twinx()
ax2.plot(cutoff.force_N, cutoff.loaded_voltage_V, "s--", color="#d62728", label="事件前最后充电点")
ax2.set_ylabel("事件前加载电压 (V)")
lines = ax.get_lines() + ax2.get_lines()
ax.legend(lines, [line.get_label() for line in lines], fontsize=8, loc="best")
fig.suptitle("V6 单向力–电化学耦合链及截止性能", fontsize=14)
plots.append(save(fig, "02_coupling_chain_and_cutoff.png"))

# 3. Mean interface stoichiometry versus SOC.
mean_theta = interfaces.groupby(["force_N", "stage", "actual_SOC", "interface"], as_index=False).stoichiometry.mean()
interface_order = ["negative_Cu", "negative_separator", "positive_separator", "positive_Al"]
titles = {"negative_Cu": "负极–铜箔", "negative_separator": "负极–隔膜", "positive_separator": "正极–隔膜", "positive_Al": "正极–铝箔"}
fig, axes = plt.subplots(2, 2, figsize=(11.5, 8), constrained_layout=True)
for ax, interface in zip(axes.flat, interface_order):
    for force in FORCES:
        group = mean_theta[(mean_theta.force_N == force) & (mean_theta.interface == interface)].sort_values("actual_SOC")
        ax.plot(group.actual_SOC * 100, group.stoichiometry, "o-", ms=3.5, color=COLORS[force], label=LABELS[force])
    ax.axhspan(0, 1, color="0.92", zorder=-2)
    ax.axhline(0, color="crimson", ls="--", lw=0.7)
    ax.axhline(1, color="crimson", ls="--", lw=0.7)
    ax.set(xlabel="实际充电 SOC (%)", ylabel="界面平均嵌锂比", title=titles[interface])
axes[0, 0].legend(ncol=2, fontsize=8)
fig.suptitle("不同外力下四个界面的嵌锂状态演化", fontsize=14)
plots.append(save(fig, "03_interface_stoichiometry_force_comparison.png"))

# 4. Electrolyte concentration at charge end.
end_cl = electrolyte[electrolyte.stage == "cutoff"].copy()
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
region_labels = {"negative": "负极", "separator": "隔膜", "positive": "正极"}
for region, marker in [("negative", "o"), ("separator", "s"), ("positive", "^")]:
    group = end_cl[end_cl.region == region].sort_values("force_N")
    axes[0].plot(group.force_N, group.cl_mean_mol_m3, marker + "-", label=region_labels[region])
    axes[0].fill_between(group.force_N, group.cl_min_mol_m3, group.cl_max_mol_m3, alpha=0.12)
polarization = []
for force in FORCES:
    group = end_cl[end_cl.force_N == force]
    polarization.append(group.cl_max_mol_m3.max() - group.cl_min_mol_m3.min())
axes[1].plot(FORCES, polarization, "o-", color="#d62728")
axes[0].set(xlabel="外力 (N)", ylabel="电解液浓度 (mol/m³)", title="截止时各区域浓度（阴影：min–max）")
axes[0].legend(fontsize=8)
axes[1].set(xlabel="外力 (N)", ylabel="全电芯浓度极差 (mol/m³)", title="截止时浓差极化程度")
fig.suptitle("不同外力下的电解液传输状态", fontsize=14)
plots.append(save(fig, "04_electrolyte_concentration_force_comparison.png"))

# 5. Shell current-density maps at 50% SOC.
datasets = []
all_positive = []
for force in FORCES:
    nodes = pd.read_csv(DATA / f"shell_current_density_F{force}N_SOC50.csv")
    triangles = pd.read_csv(DATA / f"shell_triangles_F{force}N_SOC50.csv")
    datasets.append((force, nodes, triangles))
    all_positive.extend(nodes.loc[nodes.current_density_A_m2 > 0, "current_density_A_m2"].tolist())
norm = LogNorm(vmin=max(float(np.quantile(all_positive, 0.01)), 1e-6), vmax=float(np.max(all_positive)))
fig, axes = plt.subplots(1, 4, figsize=(15.5, 3.9), constrained_layout=True)
last = None
for ax, (force, nodes, triangles) in zip(axes, datasets):
    tri = mtri.Triangulation(nodes.r_um.to_numpy() / 1000, nodes.z_um.to_numpy() / 1000, triangles[["node_1", "node_2", "node_3"]].to_numpy())
    last = ax.tripcolor(tri, nodes.current_density_A_m2, shading="gouraud", cmap="viridis", norm=norm)
    ax.set(xlabel="r (mm)", ylabel="z (mm)", title=f"{force} N")
    ax.set_aspect("equal", adjustable="box")
cbar = fig.colorbar(last, ax=axes.tolist(), shrink=0.9)
cbar.set_label("|Js| (A/m²，对数色标)")
fig.suptitle("SOC 50%：不同外力下过流结构电流密度分布", fontsize=14)
plots.append(save(fig, "05_shell_current_density_force_comparison.png"))

# 6. Mechanical response.
fig, axes = plt.subplots(2, 2, figsize=(11.5, 8), constrained_layout=True)
series = [
    ("max_displacement_um", "最大位移 (μm)", "最大位移", "#2a6fbb"),
    ("mean_top_displacement_um", "顶面平均位移 (μm)", "顶面位移", "#007f5f"),
    ("max_von_mises_MPa", "最大 von Mises 应力 (MPa)", "等效应力峰值", "#d62728"),
    ("separator_eZZ_min", "隔膜最小轴向应变", "隔膜压缩应变", "#7b2cbf"),
]
for ax, (column, ylabel, title, color) in zip(axes.flat, series):
    ax.plot(mechanics.force_N, mechanics[column], "o-", color=color)
    ax.set(xlabel="外力 (N)", ylabel=ylabel, title=title)
fig.suptitle("V6 静力学已保存解：外力响应对比", fontsize=14)
plots.append(save(fig, "06_mechanical_response_force_comparison.png"))

summary = {
    "plots": plots,
    "cutoff": cutoff[["force_N", "actual_SOC", "time_s", "loaded_voltage_V"]].to_dict("records"),
    "voltage_shift_mV_at_SOC50_vs_0N": {
        str(int(row.force_N)): float((row.loaded_voltage_V - soc50.iloc[0].loaded_voltage_V) * 1000)
        for _, row in soc50.iterrows()
    },
    "mechanics": mechanics.to_dict("records"),
    "notes": [
        "截止电压取事件触发前最后一个充电解点；部分工况存在事件定位过冲。",
        "当前为单向顺序耦合灵敏度模型，压力通过孔隙率和等效接触电阻影响电化学，形变不反向更新几何。",
        "材料参数与压力敏感系数未标定，结果用于趋势比较而非定量寿命或强度判定。",
    ],
}
(RUN / "postprocess_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
