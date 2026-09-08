import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from matplotlib.colors import LogNorm

try:
    import scienceplots  # noqa: F401
except ImportError:
    scienceplots = None


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding")
DATA = RUN / "exported_data"
PLOTS = RUN / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

try:
    plt.style.use(["science", "no-latex"])
except OSError:
    pass
plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 11

stages = ["SOC01", "SOC10", "SOC30", "SOC50", "SOC70", "SOC85", "cutoff_SOC99_9"]
titles = {
    "SOC01": "SOC 1.0%", "SOC10": "SOC 9.9%", "SOC30": "SOC 29.9%",
    "SOC50": "SOC 49.9%", "SOC70": "SOC 69.9%", "SOC85": "SOC 84.9%",
    "cutoff_SOC99_9": "截止 SOC 99.9%",
}


# 1. Voltage-SOC
with (DATA / "voltage_soc_v5_final.csv").open(encoding="utf-8-sig") as handle:
    voltage_rows = list(csv.DictReader(handle))
soc = np.array([float(row["actual_SOC"]) for row in voltage_rows])
voltage = np.array([float(row["terminal_voltage_V"]) for row in voltage_rows])
crate = np.array([float(row["current_Crate"]) for row in voltage_rows])
charge = crate > 0.25
event_index = np.where(charge)[0][-1]

fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
ax.plot(soc[charge] * 100, voltage[charge], color="#0057b8", linewidth=1.8)
ax.axhline(3.65, color="crimson", linestyle="--", linewidth=1.2, label="3.65 V 截止线")
ax.scatter(soc[event_index] * 100, voltage[event_index], color="crimson", s=36, zorder=3,
           label=f"事件切换 SOC {soc[event_index]*100:.1f}%")
ax.set_xlabel("实际充电 SOC (%)")
ax.set_ylabel("端电压 (V)")
ax.set_title("V5 已保存解：充电电压–SOC 曲线")
ax.legend(loc="lower right")
voltage_plot = PLOTS / "V5_terminal_voltage_vs_SOC.png"
fig.savefig(voltage_plot, dpi=240, bbox_inches="tight")
plt.close(fig)


# 2. Interface mean stoichiometry
with (DATA / "interface_stoichiometry_profiles_v5.csv").open(encoding="utf-8-sig") as handle:
    interface_rows = list(csv.DictReader(handle))
profiles = defaultdict(list)
soc_by_stage = {}
for row in interface_rows:
    profiles[(row["interface"], row["stage"])].append(float(row["surface_stoichiometry"]))
    soc_by_stage[row["stage"]] = float(row["actual_SOC"])
mean_theta = {key: float(np.mean(values)) for key, values in profiles.items()}
stage_soc = np.array([soc_by_stage[stage] for stage in stages]) * 100

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
axes[0].plot(stage_soc, [mean_theta[("negative_Cu", stage)] for stage in stages], "o-", label="负极–铜箔")
axes[0].plot(stage_soc, [mean_theta[("negative_separator", stage)] for stage in stages], "s-", label="负极–隔膜")
axes[1].plot(stage_soc, [mean_theta[("positive_separator", stage)] for stage in stages], "o-", label="正极–隔膜")
axes[1].plot(stage_soc, [mean_theta[("positive_Al", stage)] for stage in stages], "s-", label="正极–铝箔")
for ax, title in zip(axes, ["负极厚度两侧", "正极厚度两侧"]):
    ax.axhspan(0, 1, color="0.9", zorder=-2)
    ax.axhline(0, color="crimson", linewidth=0.8, linestyle="--")
    ax.axhline(1, color="crimson", linewidth=0.8, linestyle="--")
    ax.set_xlim(0, 102)
    ax.set_xlabel("实际充电 SOC (%)")
    ax.set_ylabel("界面平均嵌锂化学计量比")
    ax.set_title(title)
    ax.legend()
fig.suptitle("V5 界面嵌锂状态随 SOC 演化（灰区为物理范围 0–1）", fontsize=14)
stoich_plot = PLOTS / "V5_interface_mean_stoichiometry_vs_SOC.png"
fig.savefig(stoich_plot, dpi=240, bbox_inches="tight")
plt.close(fig)


# 3. Shell current density
with (DATA / "shell_current_density_nodes_v5.csv").open(encoding="utf-8-sig") as handle:
    node_rows = list(csv.DictReader(handle))
with (DATA / "shell_current_density_triangles_v5.csv").open(encoding="utf-8-sig") as handle:
    triangle_rows = list(csv.DictReader(handle))
r_mm = np.array([float(row["r_um"]) / 1000 for row in node_rows])
z_mm = np.array([float(row["z_um"]) / 1000 for row in node_rows])
triangles = np.array([[int(row["node_1"]), int(row["node_2"]), int(row["node_3"])] for row in triangle_rows])
triangulation = mtri.Triangulation(r_mm, z_mm, triangles)
values = {stage: np.array([float(row[stage + "_A_m2"]) for row in node_rows]) for stage in stages}
positive = np.concatenate([array[array > 0] for array in values.values()])
norm = LogNorm(vmin=max(float(np.quantile(positive, 0.01)), 1e-6), vmax=float(positive.max()))

fig, axes = plt.subplots(2, 4, figsize=(15, 5.5), constrained_layout=True)
last = None
for ax, stage in zip(axes.flat, stages):
    last = ax.tripcolor(triangulation, values[stage], shading="gouraud", cmap="viridis", norm=norm)
    ax.set_title(titles[stage])
    ax.set_xlabel("径向位置 r (mm)")
    ax.set_ylabel("轴向位置 z (mm)")
    ax.set_aspect("equal", adjustable="box")
axes.flat[-1].axis("off")
cbar = fig.colorbar(last, ax=axes.ravel().tolist(), shrink=0.92)
cbar.set_label("壳体电流密度 |Js| (A/m²，对数色标)")
fig.suptitle("V5 已保存解：不同 SOC 的壳体电流密度分布", fontsize=14)
shell_plot = PLOTS / "V5_shell_current_density_SOC_stages.png"
fig.savefig(shell_plot, dpi=240, bbox_inches="tight")
plt.close(fig)

print(voltage_plot)
print(stoich_plot)
print(shell_plot)
