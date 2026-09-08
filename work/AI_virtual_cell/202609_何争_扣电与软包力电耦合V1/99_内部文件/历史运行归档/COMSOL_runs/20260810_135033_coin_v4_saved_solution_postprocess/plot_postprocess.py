import csv
import json
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


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_135033_coin_v4_saved_solution_postprocess")
DATA = RUN / "exported_data"
PLOTS = RUN / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

try:
    plt.style.use(["science", "no-latex"])
except OSError:
    pass
plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

stage_order = ["SOC01", "SOC10", "SOC30", "SOC50", "SOC70", "SOC85", "cutoff_SOC89"]
stage_title = {
    "SOC01": "SOC 1.0%", "SOC10": "SOC 9.9%", "SOC30": "SOC 29.9%",
    "SOC50": "SOC 49.9%", "SOC70": "SOC 69.9%", "SOC85": "SOC 84.9%",
    "cutoff_SOC89": "截止 SOC 89.1%",
}


with (DATA / "shell_current_density_nodes.csv").open(encoding="utf-8-sig") as handle:
    node_rows = list(csv.DictReader(handle))
with (DATA / "shell_current_density_triangles.csv").open(encoding="utf-8-sig") as handle:
    tri_rows = list(csv.DictReader(handle))
r_mm = np.array([float(row["r_um"]) / 1000 for row in node_rows])
z_mm = np.array([float(row["z_um"]) / 1000 for row in node_rows])
triangles = np.array([[int(row["node_1"]), int(row["node_2"]), int(row["node_3"])] for row in tri_rows])
triangulation = mtri.Triangulation(r_mm, z_mm, triangles)
shell_values = {stage: np.array([float(row[stage + "_A_m2"]) for row in node_rows]) for stage in stage_order}
positive = np.concatenate([values[values > 0] for values in shell_values.values()])
norm = LogNorm(vmin=max(float(np.quantile(positive, 0.01)), 1e-6), vmax=float(positive.max()))

fig, axes = plt.subplots(2, 4, figsize=(15, 6.8), constrained_layout=True)
last = None
for ax, stage in zip(axes.flat, stage_order):
    last = ax.tripcolor(triangulation, shell_values[stage], shading="gouraud", cmap="viridis", norm=norm)
    ax.set_title(stage_title[stage])
    ax.set_xlabel("径向位置 r (mm)")
    ax.set_ylabel("轴向位置 z (mm)")
    ax.set_aspect("equal", adjustable="box")
axes.flat[-1].axis("off")
cbar = fig.colorbar(last, ax=axes.ravel().tolist(), shrink=0.88)
cbar.set_label("壳体电流密度 |Js| (A/m²，对数色标)")
fig.suptitle("V4 已保存解：不同 SOC 的壳体电流密度分布", fontsize=14)
shell_plot = PLOTS / "shell_current_density_SOC_stages.png"
fig.savefig(shell_plot, dpi=220, bbox_inches="tight")
plt.close(fig)


with (DATA / "interface_stoichiometry_profiles.csv").open(encoding="utf-8-sig") as handle:
    profile_rows = list(csv.DictReader(handle))
profiles = defaultdict(lambda: {"r": [], "theta": [], "soc": None})
for row in profile_rows:
    key = (row["interface"], row["stage"])
    profiles[key]["r"].append(float(row["r_um"]) / 1000)
    profiles[key]["theta"].append(float(row["surface_stoichiometry"]))
    profiles[key]["soc"] = float(row["actual_SOC"])

interface_order = ["negative_Cu", "negative_separator", "positive_separator", "positive_Al"]
interface_title = {
    "negative_Cu": "负极–铜箔", "negative_separator": "负极–隔膜",
    "positive_separator": "正极–隔膜", "positive_Al": "正极–铝箔",
}
colors = plt.cm.viridis(np.linspace(0.05, 0.95, len(stage_order)))
fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, constrained_layout=True)
for ax, interface in zip(axes.flat, interface_order):
    for color, stage in zip(colors, stage_order):
        item = profiles[(interface, stage)]
        order = np.argsort(item["r"])
        ax.plot(np.asarray(item["r"])[order], np.asarray(item["theta"])[order], color=color, label=stage_title[stage])
    ax.axhspan(0, 1, color="0.9", zorder=-2)
    ax.axhline(0, color="crimson", linewidth=0.8, linestyle="--")
    ax.axhline(1, color="crimson", linewidth=0.8, linestyle="--")
    ax.set_title(interface_title[interface])
    ax.set_xlabel("径向位置 r (mm)")
    ax.set_ylabel("表面嵌锂化学计量比 θ")
axes[0, 0].legend(ncol=2, fontsize=8)
fig.suptitle("V4 已保存解：四个界面的嵌锂状态径向分布", fontsize=14)
profile_plot = PLOTS / "interface_stoichiometry_SOC_stages.png"
fig.savefig(profile_plot, dpi=220, bbox_inches="tight")
plt.close(fig)


mean_theta = defaultdict(dict)
for (interface, stage), item in profiles.items():
    mean_theta[interface][stage] = float(np.mean(item["theta"]))
soc_values = np.array([profiles[("negative_Cu", stage)]["soc"] for stage in stage_order])
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
axes[0].plot(soc_values * 100, [mean_theta["negative_Cu"][s] for s in stage_order], "o-", label="负极–铜箔")
axes[0].plot(soc_values * 100, [mean_theta["negative_separator"][s] for s in stage_order], "s-", label="负极–隔膜")
axes[1].plot(soc_values * 100, [mean_theta["positive_separator"][s] for s in stage_order], "o-", label="正极–隔膜")
axes[1].plot(soc_values * 100, [mean_theta["positive_Al"][s] for s in stage_order], "s-", label="正极–铝箔")
for ax, title in zip(axes, ["负极厚度两侧", "正极厚度两侧"]):
    ax.axhspan(0, 1, color="0.9", zorder=-2)
    ax.axhline(0, color="crimson", linewidth=0.8, linestyle="--")
    ax.axhline(1, color="crimson", linewidth=0.8, linestyle="--")
    ax.set_title(title)
    ax.set_xlabel("实际充电 SOC (%)")
    ax.set_ylabel("界面平均嵌锂化学计量比")
    ax.legend()
fig.suptitle("界面嵌锂状态随 SOC 演化（灰区为物理范围 0–1）", fontsize=14)
mean_plot = PLOTS / "interface_mean_stoichiometry_vs_SOC.png"
fig.savefig(mean_plot, dpi=220, bbox_inches="tight")
plt.close(fig)


with (DATA / "voltage_soc.csv").open(encoding="utf-8-sig") as handle:
    voltage_rows = list(csv.DictReader(handle))
soc = np.array([float(row["actual_SOC"]) for row in voltage_rows])
voltage = np.array([float(row["terminal_b20_V"]) for row in voltage_rows])
crate = np.array([float(row["current_Crate"]) for row in voltage_rows])
charge_mask = crate > 0.25
fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
ax.plot(soc[charge_mask] * 100, voltage[charge_mask], color="#0057b8", linewidth=1.8)
ax.axhline(3.65, color="crimson", linestyle="--", label="3.65 V 截止")
ax.scatter([soc[318] * 100], [voltage[318]], color="crimson", zorder=3, label=f"截止 SOC {soc[318]*100:.1f}%")
ax.set_xlabel("实际充电 SOC (%)")
ax.set_ylabel("端电压 (V)")
ax.set_title("V4 已保存解：充电电压–SOC 曲线")
ax.legend()
voltage_plot = PLOTS / "terminal_voltage_vs_SOC.png"
fig.savefig(voltage_plot, dpi=220, bbox_inches="tight")
plt.close(fig)

summary = {
    "plots": [str(shell_plot), str(profile_plot), str(mean_plot), str(voltage_plot)],
    "cutoff_SOC": float(soc[318]),
    "cutoff_voltage_V": float(voltage[318]),
    "shell_current_density_stage_relative_span": float((max(v.max() for v in shell_values.values()) - min(v.max() for v in shell_values.values())) / max(v.max() for v in shell_values.values())),
    "interface_mean_stoichiometry": mean_theta,
}
(RUN / "postprocess_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
