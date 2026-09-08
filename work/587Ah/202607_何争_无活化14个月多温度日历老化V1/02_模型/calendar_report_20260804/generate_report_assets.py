from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import scienceplots  # noqa: F401
    plt.style.use("science")
except Exception:
    plt.style.use("default")

plt.rcParams.update({
    "font.family": ["Calibri", "Microsoft YaHei"],
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
})

TASK = Path(r"C:\HithiumSSD\hithium\work\587Ah\202607_何争_无活化14个月多温度日历老化V1")
RUN = TASK / r"04_输出结果\20260727_587calander_50SOC_full_v1"
CAL = TASK / r"04_输出结果\20260727_587_calendar_activated_calibration"
OUT = Path(r"D:\Users\hez\Desktop\hithium\scratch\calendar_report_20260804\assets")
OUT.mkdir(parents=True, exist_ok=True)

matrix = pd.read_csv(RUN / r"artifacts\calendar_aging_587Ah_50SOC_matrix.csv")
summary = pd.read_csv(RUN / r"artifacts\summary_month_14.csv")
comparison = pd.read_csv(RUN / r"artifacts\calibrated_vs_original_comparison.csv")
baseline = pd.read_csv(RUN / r"artifacts\baseline_25C_C0.csv").iloc[0]
cal = pd.read_csv(CAL / "calibration_comparison.csv")
sensitivity = pd.read_csv(CAL / "sensitivity_summary.csv")

BLUE = "#1E63F3"
ORANGE = "#E67E22"
GRAY = "#8A8A8A"
RED = "#C8102E"
TEAL = "#1B9E77"


def save(fig, name):
    fig.savefig(OUT / name, dpi=260)
    plt.close(fig)


# 1. Activated calibration comparison: measured dashed, model solid.
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.2), sharey=True)
for ax, temp in zip(axes, [25, 45]):
    d = cal[cal.temperature_c == temp]
    ax.plot(d.storage_days / 30, d.exp_recovery_rate * 100, "o--", color=ORANGE, lw=1.4, ms=3.5, label="实测")
    ax.plot(d.storage_days / 30, d.default_recovery_rate * 100, color=GRAY, lw=1.4, label="原参数")
    ax.plot(d.storage_days / 30, d.calibrated_recovery_rate * 100, color=BLUE, lw=1.8, label="标定参数")
    ax.set_xlabel("存储月数")
    ax.set_title(f"{temp}°C")
    ax.grid(alpha=0.25)
axes[0].set_ylabel("恢复容量 / %")
axes[1].legend(frameon=False, fontsize=8, loc="lower left")
fig.tight_layout()
save(fig, "calibration_exp_vs_model.png")

# 2. Sensitivity screening.
rank = sensitivity.sort_values("rmse_all_pp", ascending=True)
labels = {
    "ec_d_0p30": "EC扩散系数×0.30",
    "sei_ea_40k": "SEI活化能40 kJ/mol",
    "sei_k_0p30": "SEI速率×0.30",
    "default": "原参数",
    "crack_rate_0p10": "裂纹速率×0.10",
    "sei_l0_2nm": "初始SEI 2 nm",
    "sei_ea_60k": "SEI活化能60 kJ/mol",
}
fig, ax = plt.subplots(figsize=(5.2, 3.7))
colors = [BLUE if x == "ec_d_0p30" else "#AFC6F9" for x in rank.candidate]
ax.barh([labels.get(x, x) for x in rank.candidate], rank.rmse_all_pp, color=colors)
ax.set_xlabel("整体 RMSE / pp")
ax.grid(axis="x", alpha=0.25)
ax.invert_yaxis()
for i, v in enumerate(rank.rmse_all_pp):
    ax.text(v + 0.08, i, f"{v:.2f}", va="center", fontsize=8)
fig.tight_layout()
save(fig, "sensitivity_rmse.png")

# 3. C0 and 50% SOC target.
fig, ax = plt.subplots(figsize=(4.6, 3.1))
vals = [baseline.c0_ah, baseline.target_half_c0_ah, baseline.charged_to_storage_ah]
bars = ax.bar(["C0", "50%C0目标", "实际充入"], vals, color=[BLUE, "#9AB8F7", TEAL])
ax.set_ylabel("容量 / Ah")
ax.set_ylim(0, 680)
ax.grid(axis="y", alpha=0.25)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 12, f"{v:.1f}", ha="center", fontsize=8)
fig.tight_layout()
save(fig, "baseline_storage_target.png")

selected = [0, 25, 35, 45, 50]
colors = plt.cm.viridis(np.linspace(0.08, 0.92, len(selected)))

def selected_curve(column, ylabel, name):
    fig, ax = plt.subplots(figsize=(4.8, 3.15))
    for temp, color in zip(selected, colors):
        d = matrix[matrix.temperature_c == temp]
        ax.plot(d.storage_month, d[column] * 100, color=color, lw=1.6, label=f"{temp}°C")
    ax.set_xlabel("存储月数")
    ax.set_ylabel(ylabel)
    ax.set_xlim(1, 14)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    save(fig, name)

selected_curve("retention_rate", "保持容量 / %", "retention_selected.png")
selected_curve("recovery_rate", "恢复容量 / %", "recovery_selected.png")


def heatmap(column, name, cmap, vmin=None, vmax=None):
    pivot = matrix.pivot(index="temperature_c", columns="storage_month", values=column) * 100
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xlabel("存储月数")
    ax.set_ylabel("存储温度 / °C")
    ax.set_xticks(np.arange(0, 14, 2), [str(x) for x in range(1, 15, 2)])
    ax.set_yticks(np.arange(len(pivot.index)), [str(int(x)) for x in pivot.index])
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.ax.tick_params(labelsize=7)
    fig.tight_layout()
    save(fig, name)

heatmap("retention_rate", "retention_heatmap_report.png", "YlGn", 80, 100)
heatmap("recovery_rate", "recovery_heatmap_report.png", "YlGn", 90, 100)

# 8. Irreversible loss evolution.
fig, ax = plt.subplots(figsize=(5.0, 3.4))
for temp, color in zip(selected, colors):
    d = matrix[matrix.temperature_c == temp]
    ax.plot(d.storage_month, d.irreversible_capacity_loss_rate * 100, color=color, lw=1.7, label=f"{temp}°C")
ax.set_xlabel("存储月数")
ax.set_ylabel("不可逆容量损失 / %")
ax.grid(alpha=0.25)
ax.legend(frameon=False, fontsize=7, ncol=2)
fig.tight_layout()
save(fig, "irreversible_selected.png")

# 9. Month-14 loss decomposition.
reversible = (1 - summary.retention_rate) * 100 - summary.irreversible_capacity_loss_rate * 100
irreversible = summary.irreversible_capacity_loss_rate * 100
fig, ax = plt.subplots(figsize=(5.0, 3.4))
ax.bar(summary.temperature_c, reversible, width=3.4, color="#AFC6F9", label="静置后可恢复损失")
ax.bar(summary.temperature_c, irreversible, width=3.4, bottom=reversible, color=BLUE, label="不可逆损失")
ax.set_xlabel("存储温度 / °C")
ax.set_ylabel("相对50%C0容量损失 / %")
ax.grid(axis="y", alpha=0.25)
ax.legend(frameon=False, fontsize=7)
fig.tight_layout()
save(fig, "loss_split_month14.png")

# 10. Month-14 temperature summary.
fig, ax = plt.subplots(figsize=(6.0, 3.6))
ax.plot(summary.temperature_c, summary.retention_rate * 100, "o-", color=ORANGE, lw=1.8, ms=4, label="保持容量")
ax.plot(summary.temperature_c, summary.recovery_rate * 100, "o-", color=BLUE, lw=1.8, ms=4, label="恢复容量")
ax.set_xlabel("存储温度 / °C")
ax.set_ylabel("容量保持率 / %")
ax.set_xticks(summary.temperature_c)
ax.set_ylim(78, 101)
ax.grid(alpha=0.25)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
save(fig, "month14_temperature_summary.png")

# 11. Original vs calibrated recovery at month 14.
m14 = comparison[comparison.storage_month == 14].sort_values("temperature_c")
fig, ax = plt.subplots(figsize=(5.2, 3.5))
ax.plot(m14.temperature_c, m14.recovery_rate_original * 100, "o-", color=GRAY, lw=1.5, ms=3.5, label="原参数")
ax.plot(m14.temperature_c, m14.recovery_rate_calibrated * 100, "o-", color=BLUE, lw=1.8, ms=3.5, label="标定参数")
ax.set_xlabel("存储温度 / °C")
ax.set_ylabel("14个月恢复容量 / %")
ax.grid(alpha=0.25)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
save(fig, "original_vs_calibrated_month14.png")

print(f"Generated {len(list(OUT.glob('*.png')))} assets in {OUT}")
