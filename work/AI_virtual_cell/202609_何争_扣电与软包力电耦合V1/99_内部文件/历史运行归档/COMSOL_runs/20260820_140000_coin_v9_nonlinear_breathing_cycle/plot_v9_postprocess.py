import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors, font_manager


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle")
DATA = RUN / "exported_data"
PLOTS = RUN / "plots"
PLOTS.mkdir(exist_ok=True)
RESULT = json.loads((RUN / "full_cycle_comparison.json").read_text(encoding="utf-8"))
BUILD = json.loads((RUN / "build_result.json").read_text(encoding="utf-8"))

font_path = next(
    path for path in (
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    )
    if path.exists()
)
font_manager.fontManager.addfont(str(font_path))
font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
plt.rcParams.update({
    "font.family": font_name,
    "axes.unicode_minus": False,
    "font.size": 10.5,
    "axes.linewidth": 1.0,
})

COLORS = {
    "off": "#6f6f6f",
    "legacy_linear_20pct": "#f28e2b",
    "literature_nonlinear": "#0057b8",
}
LABELS = {
    "off": "关闭呼吸",
    "legacy_linear_20pct": "旧线性（石墨20%）",
    "literature_nonlinear": "文献非线性",
}


def style(ax):
    ax.grid(True, color="#d9d9d9", linestyle="--", linewidth=0.6, alpha=0.75)
    ax.tick_params(direction="in", top=True, right=True)


def save(fig, name):
    path = PLOTS / name
    fig.savefig(path, dpi=260, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def phase_mask(series, phase):
    current = np.asarray(series["current_Crate"])
    return current > 0.1 if phase == "charge" else current < -0.1


outputs = []

# 1. Imported nonlinear laws and old linear exploratory law.
gr_table = np.asarray(BUILD["after_reload"]["function_tables"]["graphite"], dtype=float)
lfp_table = np.asarray(BUILD["after_reload"]["function_tables"]["lfp"], dtype=float)
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.7))
axes[0].plot(gr_table[:, 0] * 100, gr_table[:, 1] * 7, "o-", color="#0057b8", lw=2.2, ms=4,
             label="文献曲线（满量程约7%）")
axes[0].plot([0, 100], [0, 20], "--", color="#f28e2b", lw=1.8, label="旧线性探索值（20%）")
axes[0].axvline(50, color="#777777", ls=":", lw=1)
axes[0].text(51, 0.7, r"LiC$_{12}$→LiC$_6$" + "\n斜率再次增大", color="#444444", fontsize=9)
axes[0].set(xlabel="石墨嵌锂比例 $x$ in Li$_x$C$_6$ (%)", ylabel="电极轴向应变 (%)",
            title="石墨：staging 导致非线性厚度变化")
axes[0].legend(frameon=False)
style(axes[0])
axes[1].plot(lfp_table[:, 0] * 100, lfp_table[:, 1] * 0.6, "s-", color="#d62728", lw=2.2, ms=4)
axes[1].annotate("充电方向：脱锂 → 收缩", xy=(20, 0.08), xytext=(50, 0.22),
                 arrowprops={"arrowstyle": "->", "color": "#555555"})
axes[1].set(xlabel="LFP 嵌锂比例 $x$ in Li$_x$FePO$_4$ (%)", ylabel="复合电极应变 (%)",
            title="LFP：两相转化区的 S 形应变")
style(axes[1])
fig.suptitle("V9 导入的 SOC–呼吸关系（形状与幅值分开参数化）", fontsize=14)
outputs.append(save(fig, "01_导入的非线性SOC呼吸曲线.png"))

# 2. Full-cycle voltage and current.
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True, gridspec_kw={"height_ratios": [2.1, 1]})
for name, case in RESULT["cases"].items():
    s = case["series"]
    ax1.plot(np.asarray(s["time_s"]) / 3600, s["voltage_V"], color=COLORS[name], lw=2 if name == "literature_nonlinear" else 1.4,
             ls="-" if name != "legacy_linear_20pct" else "--", label=LABELS[name])
s = RESULT["cases"]["literature_nonlinear"]["series"]
ax2.plot(np.asarray(s["time_s"]) / 3600, s["current_Crate"], color="#222222", lw=1.8)
ax1.axhline(3.65, color="#d62728", ls=":", lw=1.2)
ax1.axhline(2.50, color="#d62728", ls=":", lw=1.2)
ax1.set(ylabel="加载端电压 (V)", title="100 N、0.5C 完整充电–静置–放电循环")
ax2.set(xlabel="时间 (h)", ylabel="电流倍率 (C)")
ax1.legend(frameon=False, ncol=3, loc="best")
style(ax1); style(ax2)
outputs.append(save(fig, "02_完整充放电电压电流对比.png"))

# 3. Voltage-SOC loop.
fig, ax = plt.subplots(figsize=(8.8, 5.6))
for name, case in RESULT["cases"].items():
    s = case["series"]
    soc = np.asarray(s["actual_SOC"]) * 100
    for phase, ls in (("charge", "-"), ("discharge", "--")):
        mask = phase_mask(s, phase)
        ax.plot(soc[mask], np.asarray(s["voltage_V"])[mask], color=COLORS[name], lw=2 if name == "literature_nonlinear" else 1.4,
                ls=ls, label=f"{LABELS[name]}·{'充电' if phase == 'charge' else '放电'}")
ax.set(xlabel="积分 SOC (%)", ylabel="加载端电压 (V)", title="加入呼吸机制前后：电压–SOC 回线")
style(ax)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, frameon=False, ncol=2, fontsize=9)
outputs.append(save(fig, "03_电压_SOC回线_机制前后.png"))

# 4. Mechanical and porosity response from the literature nonlinear case versus baseline.
fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.2))
for name in ("off", "literature_nonlinear"):
    s = RESULT["cases"][name]["series"]
    soc = np.asarray(s["actual_SOC"]) * 100
    for phase, ls in (("charge", "-"), ("discharge", "--")):
        mask = phase_mask(s, phase)
        axes[0, 0].plot(soc[mask], np.asarray(s["p_neg_MPa"])[mask], color=COLORS[name], ls=ls, lw=2,
                        label=f"{LABELS[name]}·{'充' if phase == 'charge' else '放'}")
        axes[0, 1].plot(soc[mask], 1e4 * (np.asarray(s["epsl_neg"])[mask] - s["epsl_neg"][0]), color=COLORS[name], ls=ls, lw=2)
        axes[1, 0].plot(soc[mask], np.asarray(s["top_disp_um"])[mask] - s["top_disp_um"][0], color=COLORS[name], ls=ls, lw=2)
nl = RESULT["cases"]["literature_nonlinear"]["series"]
soc = np.asarray(nl["actual_SOC"]) * 100
for phase, ls in (("charge", "-"), ("discharge", "--")):
    mask = phase_mask(nl, phase)
    axes[1, 1].plot(soc[mask], 100 * np.asarray(nl["eps_breath_neg"])[mask], color="#0057b8", ls=ls, lw=2, label="石墨")
    axes[1, 1].plot(soc[mask], 100 * np.asarray(nl["eps_breath_pos"])[mask], color="#d62728", ls=ls, lw=2, label="LFP")
axes[0, 0].set(ylabel="负极平均压应力 (MPa)", title="局部压力反馈")
axes[0, 1].set(ylabel=r"负极孔隙率变化 ($\times10^{-4}$)", title="孔隙率随压力局部演化")
axes[1, 0].set(xlabel="积分 SOC (%)", ylabel="顶部位移相对变化 (μm)", title="外壳/堆叠位移响应")
axes[1, 1].set(xlabel="积分 SOC (%)", ylabel="本征呼吸应变 (%)", title="正负极呼吸方向与非线性")
axes[0, 0].legend(frameon=False, fontsize=8, ncol=2)
axes[1, 1].legend(frameon=False)
for ax in axes.flat:
    style(ax)
fig.suptitle("机制链：SOC → 非线性呼吸 → 压力 → 孔隙率/位移", fontsize=14)
outputs.append(save(fig, "04_呼吸压力孔隙率位移多角度对比.png"))

# 5. Key performance metrics and relative changes.
names = list(RESULT["cases"])
metrics = [RESULT["cases"][name]["metrics"] for name in names]
fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.8))
x = np.arange(len(names))
bar_colors = [COLORS[n] for n in names]
panels = [
    ([1000 * m["discharge_capacity_Ah"] for m in metrics], "放电容量 (mAh)", "截止容量"),
    ([m["energy_efficiency_pct"] for m in metrics], "能量效率 (%)", "充放电能量效率"),
    ([m["pressure_peak_MPa"] for m in metrics], "峰值压力 (MPa)", "压力放大效应"),
    ([m["top_displacement_range_um"][1] - m["top_displacement_range_um"][0] for m in metrics], "循环位移幅值 (μm)", "可观测机械信号"),
]
for ax, (values, ylabel, title) in zip(axes.flat, panels):
    bars = ax.bar(x, values, color=bar_colors, width=0.65)
    ax.set_xticks(x, ["关闭", "旧线性", "文献非线性"])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.3g}", ha="center", va="bottom", fontsize=9)
    style(ax)
fig.suptitle("机制加入前后：电性能影响较小，机械可观测量显著增强", fontsize=14)
outputs.append(save(fig, "05_关键性能指标对比.png"))

# 6. Spatial difference maps at 50% SOC, nonlinear minus breathing-off.
fig, axes = plt.subplots(2, 2, figsize=(12.2, 6.8), sharex=True, sharey=True)
delta_sets = []
for phase in ("charge", "discharge"):
    frames = []
    for region in ("negative", "separator", "positive"):
        off = pd.read_csv(DATA / f"spatial_off_{phase}_SOC50_{region}.csv")
        nl = pd.read_csv(DATA / f"spatial_literature_nonlinear_{phase}_SOC50_{region}.csv")
        frame = nl.copy()
        frame["delta_pressure_kPa"] = (nl["pressure_Pa"] - off["pressure_Pa"]) / 1000
        frame["delta_porosity_1e4"] = (nl["porosity"] - off["porosity"]) * 1e4
        frames.append(frame)
    delta_sets.append(pd.concat(frames, ignore_index=True))
pmax = max(np.percentile(np.abs(df["delta_pressure_kPa"]), 99.5) for df in delta_sets)
emax = max(np.percentile(np.abs(df["delta_porosity_1e4"]), 99.5) for df in delta_sets)
for col, (phase, df) in enumerate(zip(("charge", "discharge"), delta_sets)):
    r = df["r_um"] / 1000
    z = df["z_um"] - 2360
    sc1 = axes[0, col].scatter(r, z, c=df["delta_pressure_kPa"], s=2.0, cmap="coolwarm",
                              norm=colors.TwoSlopeNorm(vmin=-pmax, vcenter=0, vmax=pmax), rasterized=True)
    sc2 = axes[1, col].scatter(r, z, c=df["delta_porosity_1e4"], s=2.0, cmap="PiYG",
                              norm=colors.TwoSlopeNorm(vmin=-emax, vcenter=0, vmax=emax), rasterized=True)
    axes[0, col].set_title(f"{'充电' if phase == 'charge' else '放电'} 50% SOC：Δ压力")
    axes[1, col].set_title(f"{'充电' if phase == 'charge' else '放电'} 50% SOC：Δ孔隙率")
    axes[1, col].set_xlabel("径向位置 r (mm)")
for ax in axes[:, 0]:
    ax.set_ylabel("电极堆叠厚度坐标 (μm)")
fig.colorbar(sc1, ax=axes[0, :], label="非线性−关闭 (kPa)", fraction=0.025, pad=0.02)
fig.colorbar(sc2, ax=axes[1, :], label=r"非线性−关闭 ($\times10^{-4}$)", fraction=0.025, pad=0.02)
fig.suptitle("空间差值图：呼吸机制改变局部压力与孔隙率，而非整体统一平移", fontsize=14)
outputs.append(save(fig, "06_SOC50空间压力孔隙率差值图.png"))

# 7. Interface stoichiometry profiles at high SOC.
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=False)
for ax, phase in zip(axes, ("charge", "discharge")):
    for mode, color, ls in (("off", COLORS["off"], "--"), ("literature_nonlinear", COLORS["literature_nonlinear"], "-")):
        df = pd.read_csv(DATA / f"interfaces_{mode}_{phase}_SOC85.csv")
        for interface, marker in (("negative_separator", "o"), ("positive_separator", "s")):
            sub = df[df["interface"] == interface]
            ax.plot(sub["r_um"] / 1000, sub["surface_stoichiometry"], color=color, ls=ls, lw=1.6,
                    marker=marker, markevery=max(1, len(sub) // 12), ms=3,
                    label=f"{LABELS[mode]}·{'负极/隔膜' if interface.startswith('negative') else '正极/隔膜'}")
    ax.set(xlabel="径向位置 r (mm)", ylabel="界面颗粒表面嵌锂比例",
           title=f"{'充电' if phase == 'charge' else '放电'} 85% SOC")
    style(ax)
axes[0].legend(frameon=False, fontsize=8)
fig.suptitle("界面嵌锂状态：机制前后径向非均匀性对比", fontsize=14)
outputs.append(save(fig, "07_SOC85界面嵌锂径向分布.png"))

# Export compact metrics table.
metrics_path = RUN / "metrics_summary.csv"
with metrics_path.open("w", newline="", encoding="utf-8-sig") as handle:
    fieldnames = ["case", *metrics[0].keys()]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for name, metric in zip(names, metrics):
        row = {"case": name, **metric}
        row["top_displacement_range_um"] = json.dumps(metric["top_displacement_range_um"])
        writer.writerow(row)

manifest = {
    "source": str(RUN / "full_cycle_comparison.json"),
    "plots": outputs,
    "metrics_summary": str(metrics_path),
    "solved_model": RESULT["solved_model"],
    "key_findings": {
        "graphite_peak_breathing_pct": RESULT["cases"]["literature_nonlinear"]["metrics"]["maximum_graphite_breathing_pct"],
        "lfp_peak_contraction_pct": RESULT["cases"]["literature_nonlinear"]["metrics"]["minimum_lfp_breathing_pct"],
        "nonlinear_pressure_peak_MPa": RESULT["cases"]["literature_nonlinear"]["metrics"]["pressure_peak_MPa"],
        "off_pressure_peak_MPa": RESULT["cases"]["off"]["metrics"]["pressure_peak_MPa"],
        "nonlinear_energy_efficiency_pct": RESULT["cases"]["literature_nonlinear"]["metrics"]["energy_efficiency_pct"],
    },
}
(RUN / "postprocess_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False))
