import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs")
POUCH_RUN = ROOT / "20260831_150000_single_layer_pouch_dual_tab_v1"
POST = POUCH_RUN / "postprocess_v8_coin_comparison"
POUCH_DATA = POST / "exported_data"
COIN_RUN = ROOT / "20260820_140000_coin_v9_nonlinear_breathing_cycle"
COIN_DATA = COIN_RUN / "exported_data"
PLOTS = POST / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)


plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 220,
})


def save(fig, name):
    path = PLOTS / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def arr(series, key):
    return np.asarray(series[key], dtype=float)


def phase_xy(series, phase, xkey, ykey):
    current = arr(series, "current_Crate")
    mask = current > 0.1 if phase == "charge" else current < -0.1
    return arr(series, xkey)[mask], arr(series, ykey)[mask]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def p99_current(path):
    rows = read_csv(path)
    values = np.asarray([float(row[list(row)[-1]]) for row in rows])
    return float(np.percentile(values, 99)), float(np.max(values))


pouch = json.loads((POST / "pouch_v8_full_cycle_comparison.json").read_text(encoding="utf-8"))
coin = json.loads((COIN_RUN / "full_cycle_comparison.json").read_text(encoding="utf-8"))

pouch_base = pouch["cases"]["baseline"]
pouch_cpl = pouch["cases"]["coupled_100N"]
coin_base = coin["cases"]["off"]
coin_cpl = coin["cases"]["literature_nonlinear"]
pb, pc = pouch_base["series"], pouch_cpl["series"]
cb, cc = coin_base["series"], coin_cpl["series"]
coin_m, pouch_m = coin_cpl["metrics"], pouch_cpl["metrics"]
plot_files = []

# 1. Full-cycle voltage and voltage-SOC comparison.
fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.8))
for series, label, color, style in (
    (cb, "扣电：无呼吸基线", "#6b7280", "--"),
    (cc, "扣电：100 N非线性呼吸", "#1d4ed8", "-"),
    (pb, "软包：0 N基线", "#f59e0b", "--"),
    (pc, "软包：100 N非线性呼吸", "#dc2626", "-"),
):
    axes[0].plot(arr(series, "time_s") / 3600, arr(series, "voltage_V"), style, color=color, lw=1.7, label=label)
axes[0].axhline(3.65, color="#be123c", lw=1, ls=":")
axes[0].axhline(2.50, color="#be123c", lw=1, ls=":")
axes[0].set(xlabel="时间 (h)", ylabel="负载端电压 (V)", title="完整0.5C充电–静置–放电")
axes[0].grid(alpha=0.25)
axes[0].legend(ncol=2, frameon=False)

for series, label, color in ((cc, "扣电", "#1d4ed8"), (pc, "软包", "#dc2626")):
    for phase, suffix in (("charge", "充电"), ("discharge", "放电")):
        x, y = phase_xy(series, phase, "actual_SOC", "voltage_V")
        axes[1].plot(100 * x, y, "-" if phase == "charge" else "--", color=color, lw=1.7, label=f"{label}-{suffix}")
axes[1].axhline(3.65, color="#be123c", lw=1, ls=":")
axes[1].axhline(2.50, color="#be123c", lw=1, ls=":")
axes[1].set(xlabel="电极平均SOC (%)", ylabel="负载端电压 (V)", title="统一SOC口径下的电压曲线")
axes[1].grid(alpha=0.25)
axes[1].legend(frameon=False)
fig.suptitle("扣电与单层双侧极耳软包：完整循环电压对比", fontsize=14, weight="bold")
plot_files.append(save(fig, "01_voltage_cycle_coin_vs_pouch_v8.png"))

# 2. Performance metrics.
coin_i1c = max(abs(value) for value in cc["current_A"]) / 0.5
pouch_i1c = 0.13
coin_usable = coin_m["charge_capacity_Ah"] / coin_i1c * 100
pouch_usable = pouch_m["charge_capacity_Ah"] / pouch_i1c * 100
metrics = [
    ("充电容量\n(%额定容量)", coin_usable, pouch_usable),
    ("库仑效率\n(%)", coin_m["coulombic_efficiency_pct"], pouch_m["coulombic_efficiency_pct"]),
    ("能量效率\n(%)", coin_m["energy_efficiency_pct"], pouch_m["energy_efficiency_pct"]),
    ("充电截止SOC\n(%)", coin_m["maximum_charge_SOC_pct"], pouch_m["maximum_SOC_pct"]),
]
fig, ax = plt.subplots(figsize=(10.5, 5.2))
x = np.arange(len(metrics))
width = 0.34
bars1 = ax.bar(x - width / 2, [item[1] for item in metrics], width, color="#1d4ed8", label="扣电 100 N")
bars2 = ax.bar(x + width / 2, [item[2] for item in metrics], width, color="#dc2626", label="软包 100 N")
ax.set_xticks(x, [item[0] for item in metrics])
ax.set_ylim(0, 106)
ax.set_ylabel("数值 (%)")
ax.set_title("性能指标：各自额定容量定义下的0.5C对比")
ax.grid(axis="y", alpha=0.25)
ax.legend(frameon=False)
ax.bar_label(bars1, fmt="%.1f", padding=3)
ax.bar_label(bars2, fmt="%.1f", padding=3)
plot_files.append(save(fig, "02_performance_metrics_coin_vs_pouch_v8.png"))

# 3. Mechanics, porosity and breathing. Coin solid.disp is a magnitude under preload;
# expansion is therefore initial magnitude minus current magnitude.
fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.4), constrained_layout=True)
axes[0, 0].plot(arr(cc, "time_s") / 3600, 1000 * arr(cc, "p_neg_MPa"), color="#1d4ed8", label="扣电-负极")
axes[0, 0].plot(arr(cc, "time_s") / 3600, 1000 * arr(cc, "p_sep_MPa"), color="#1d4ed8", ls="--", label="扣电-隔膜")
axes[0, 0].plot(arr(pc, "time_s") / 3600, arr(pc, "pressure_neg_kPa"), color="#dc2626", label="软包-负极")
axes[0, 0].plot(arr(pc, "time_s") / 3600, arr(pc, "pressure_sep_kPa"), color="#dc2626", ls="--", label="软包-隔膜")
axes[0, 0].set(xlabel="时间 (h)", ylabel="平均压缩压力 (kPa)", title="局部压力演化")
axes[0, 0].grid(alpha=0.25); axes[0, 0].legend(frameon=False, ncol=2)

axes[0, 1].plot(100 * arr(cc, "actual_SOC"), arr(cc, "epsl_neg"), color="#1d4ed8", label="扣电-负极")
axes[0, 1].plot(100 * arr(cc, "actual_SOC"), arr(cc, "epsl_sep"), color="#1d4ed8", ls="--", label="扣电-隔膜")
axes[0, 1].plot(100 * arr(pc, "actual_SOC"), arr(pc, "porosity_neg"), color="#dc2626", label="软包-负极")
axes[0, 1].plot(100 * arr(pc, "actual_SOC"), arr(pc, "porosity_sep"), color="#dc2626", ls="--", label="软包-隔膜")
axes[0, 1].set(xlabel="电极平均SOC (%)", ylabel="平均孔隙率", title="压力–孔隙率反馈")
axes[0, 1].grid(alpha=0.25); axes[0, 1].legend(frameon=False, ncol=2)

axes[1, 0].plot(100 * arr(cc, "actual_SOC"), 100 * arr(cc, "eps_breath_neg"), color="#1d4ed8", label="扣电-石墨")
axes[1, 0].plot(100 * arr(cc, "actual_SOC"), 100 * arr(cc, "eps_breath_pos"), color="#1d4ed8", ls="--", label="扣电-LFP")
axes[1, 0].plot(100 * arr(pc, "actual_SOC"), arr(pc, "breathing_neg_pct"), color="#dc2626", label="软包-石墨")
axes[1, 0].plot(100 * arr(pc, "actual_SOC"), arr(pc, "breathing_pos_pct"), color="#dc2626", ls="--", label="软包-LFP")
axes[1, 0].set(xlabel="电极平均SOC (%)", ylabel="呼吸应变 (%)", title="非线性嵌锂呼吸")
axes[1, 0].grid(alpha=0.25); axes[1, 0].legend(frameon=False, ncol=2)

coin_expansion = arr(cc, "top_disp_um")[0] - arr(cc, "top_disp_um")
pouch_expansion = arr(pc, "relative_thickness_change_um")
axes[1, 1].plot(arr(cc, "time_s") / 3600, coin_expansion, color="#1d4ed8", label="扣电")
axes[1, 1].plot(arr(pc, "time_s") / 3600, pouch_expansion, color="#dc2626", label="软包")
axes[1, 1].axhline(0, color="#999999", lw=0.8)
axes[1, 1].set(xlabel="时间 (h)", ylabel="相对厚度增加 (μm)", title="统一正方向后的厚度响应")
axes[1, 1].grid(alpha=0.25); axes[1, 1].legend(frameon=False)
fig.suptitle("力学–压力–孔隙率–呼吸双向耦合对比", fontsize=14, weight="bold")
plot_files.append(save(fig, "03_mechanics_coupling_coin_vs_pouch_v8.png"))

# 4. Electrochemical nonuniformity.
fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.4), constrained_layout=True)
coin_span = arr(cc, "cl_max_mol_m3") - arr(cc, "cl_min_mol_m3")
pouch_span = arr(pc, "electrolyte_max_mol_m3") - arr(pc, "electrolyte_min_mol_m3")
axes[0, 0].plot(100 * arr(cc, "actual_SOC"), coin_span, color="#1d4ed8", label="扣电")
axes[0, 0].plot(100 * arr(pc, "actual_SOC"), pouch_span, color="#dc2626", label="软包")
axes[0, 0].set(xlabel="电极平均SOC (%)", ylabel="电解液浓度极差 (mol m$^{-3}$)", title="浓差极化表征")
axes[0, 0].grid(alpha=0.25); axes[0, 0].legend(frameon=False)

for series, label, color in ((cc, "扣电", "#1d4ed8"), (pc, "软包", "#dc2626")):
    axes[0, 1].plot(100 * arr(series, "actual_SOC"), arr(series, "theta_neg"), color=color, label=f"{label}-石墨")
    axes[0, 1].plot(100 * arr(series, "actual_SOC"), arr(series, "theta_pos"), color=color, ls="--", label=f"{label}-LFP")
axes[0, 1].set(xlabel="电极平均SOC (%)", ylabel="平均嵌锂比例", title="正负极嵌锂状态")
axes[0, 1].grid(alpha=0.25); axes[0, 1].legend(frameon=False, ncol=2)

for base, coupled, label, color in ((cb, cc, "扣电", "#1d4ed8"), (pb, pc, "软包", "#dc2626")):
    t = arr(coupled, "time_s")
    v0 = np.interp(t, arr(base, "time_s"), arr(base, "voltage_V"))
    axes[1, 0].plot(t / 3600, 1000 * (arr(coupled, "voltage_V") - v0), color=color, label=label)
axes[1, 0].set(xlabel="时间 (h)", ylabel="耦合引起的电压差 (mV)", title="压力反馈与呼吸机制的电压影响")
axes[1, 0].grid(alpha=0.25); axes[1, 0].legend(frameon=False)

coin_j99, coin_jmax = p99_current(COIN_DATA / "shell_current_literature_nonlinear_charge_SOC50.csv")
pouch_j99, pouch_jmax = p99_current(POUCH_DATA / "spatial_coupled_100N_charge_SOC50_collector_current_density.csv")
bars = axes[1, 1].bar(["扣电", "软包"], [coin_j99, pouch_j99], color=["#1d4ed8", "#dc2626"])
axes[1, 1].set_yscale("log")
axes[1, 1].set_ylabel("集流体电流密度P99 (A m$^{-2}$)")
axes[1, 1].set_title("充电50% SOC的集流不均匀程度")
axes[1, 1].grid(axis="y", alpha=0.25)
axes[1, 1].bar_label(bars, labels=[f"{coin_j99:.2g}", f"{pouch_j99:.2g}"], padding=3)
fig.suptitle("电化学非均匀性与几何效应对比", fontsize=14, weight="bold")
plot_files.append(save(fig, "04_electrochemical_nonuniformity_coin_vs_pouch_v8.png"))

# 5. Pouch current-density maps.
stage_specs = [
    ("charge", "SOC10", "充电10% SOC"),
    ("charge", "SOC50", "充电50% SOC"),
    ("charge", "SOC85", "充电85% SOC"),
    ("discharge", "SOC50", "放电50% SOC"),
    ("discharge", "SOC10", "放电10% SOC"),
]
loaded, all_values = [], []
for phase, soc_tag, title in stage_specs:
    rows = read_csv(POUCH_DATA / f"spatial_coupled_100N_{phase}_{soc_tag}_collector_current_density.csv")
    x_mm = np.asarray([float(row["x_m"]) / 1000 for row in rows])
    y_mm = np.asarray([float(row["y_m"]) / 1000 for row in rows])
    values = np.asarray([float(row["collector_current_density"]) for row in rows])
    loaded.append((x_mm, y_mm, values, title))
    all_values.append(values)
positive = np.concatenate([value[value > 0] for value in all_values])
vmin, vmax = np.percentile(positive, [2, 99.5])
fig, axes = plt.subplots(2, 3, figsize=(15, 7.2), constrained_layout=True)
for ax, (x_mm, y_mm, values, title) in zip(axes.flat, loaded):
    scatter = ax.scatter(x_mm, y_mm, c=np.maximum(values, vmin), s=4, cmap="viridis", norm=matplotlib.colors.LogNorm(vmin=vmin, vmax=vmax))
    ax.set_title(title)
    ax.set_xlabel("长度方向x (mm)")
    ax.set_ylabel("厚度方向y (mm)")
    ax.grid(alpha=0.15)
axes.flat[-1].axis("off")
fig.colorbar(scatter, ax=axes.ravel().tolist(), label="|集流体电流密度| (A m$^{-2}$)", shrink=0.9)
fig.suptitle("V8软包双侧极耳：集流体电流密度空间分布", fontsize=14, weight="bold")
plot_files.append(save(fig, "05_pouch_collector_current_density_maps_v8.png"))

# 6. Pressure and porosity distribution at charge 50% SOC.
fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.8), constrained_layout=True)
for name, label, color in (("neg", "负极", "#2563eb"), ("sep", "隔膜", "#059669"), ("pos", "正极", "#dc2626")):
    pressure_rows = read_csv(POUCH_DATA / f"spatial_coupled_100N_charge_SOC50_pressure_{name}_kPa.csv")
    porosity_rows = read_csv(POUCH_DATA / f"spatial_coupled_100N_charge_SOC50_porosity_{name}.csv")
    for ax, rows, field in ((axes[0], pressure_rows, f"pressure_{name}_kPa"), (axes[1], porosity_rows, f"porosity_{name}")):
        x = np.asarray([float(row["x_m"]) / 1000 for row in rows])
        y = np.asarray([float(row[field]) for row in rows])
        if field.startswith("pressure"):
            y = y / 1000
        rounded = np.round(x, 3)
        unique_x = np.unique(rounded)
        mean_y = np.asarray([np.mean(y[rounded == value]) for value in unique_x])
        min_y = np.asarray([np.min(y[rounded == value]) for value in unique_x])
        max_y = np.asarray([np.max(y[rounded == value]) for value in unique_x])
        ax.plot(unique_x, mean_y, color=color, lw=1.6, label=label)
        ax.fill_between(unique_x, min_y, max_y, color=color, alpha=0.12)
axes[0].set(xlabel="长度方向x (mm)", ylabel="局部压缩压力 (kPa)", title="充电50% SOC局部压力")
axes[1].set(xlabel="长度方向x (mm)", ylabel="局部孔隙率", title="压力反馈后的孔隙率分布")
for ax in axes:
    ax.grid(alpha=0.25); ax.legend(frameon=False)
fig.suptitle("V8软包局部压力–孔隙率空间非均匀性", fontsize=14, weight="bold")
plot_files.append(save(fig, "06_pouch_pressure_porosity_spatial_SOC50_v8.png"))

summary = {
    "basis": {
        "coin_i1C_A": coin_i1c,
        "pouch_i1C_A": pouch_i1c,
        "C_rate": 0.5,
        "displacement_sign": {
            "coin": "solid.disp is a magnitude under preload; expansion = initial magnitude - current magnitude",
            "pouch": "expansion = (top normal displacement - bottom normal displacement) - initial value",
        },
    },
    "coin_coupled_100N": {
        "charge_capacity_pct_rated": coin_usable,
        **coin_m,
        "thickness_expansion_peak_um": float(np.max(coin_expansion)),
        "collector_current_density_p99_SOC50_A_m2": coin_j99,
    },
    "pouch_coupled_100N": {
        "charge_capacity_pct_rated": pouch_usable,
        **pouch_m,
        "thickness_expansion_peak_um": float(np.max(pouch_expansion)),
        "collector_current_density_p99_SOC50_A_m2": pouch_j99,
    },
    "plots": plot_files,
}
(POST / "coin_pouch_v8_quantitative_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

with (POST / "coin_pouch_v8_metrics.csv").open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.writer(handle)
    writer.writerow(["metric", "coin_coupled_100N", "pouch_coupled_100N", "unit"])
    writer.writerow(["charge_capacity", coin_usable, pouch_usable, "% rated capacity"])
    writer.writerow(["coulombic_efficiency", coin_m["coulombic_efficiency_pct"], pouch_m["coulombic_efficiency_pct"], "%"])
    writer.writerow(["energy_efficiency", coin_m["energy_efficiency_pct"], pouch_m["energy_efficiency_pct"], "%"])
    writer.writerow(["charge_cutoff_SOC", coin_m["maximum_charge_SOC_pct"], pouch_m["maximum_SOC_pct"], "%"])
    writer.writerow(["pressure_peak", coin_m["pressure_peak_MPa"] * 1000, pouch_m["pressure_peak_kPa"], "kPa"])
    writer.writerow(["thickness_expansion_peak", np.max(coin_expansion), np.max(pouch_expansion), "um"])
    writer.writerow(["graphite_breathing_peak", coin_m["maximum_graphite_breathing_pct"], pouch_m["maximum_graphite_breathing_pct"], "%"])
    writer.writerow(["electrolyte_span_peak", coin_m["maximum_electrolyte_span_mol_m3"], pouch_m["maximum_electrolyte_span_mol_m3"], "mol/m3"])
    writer.writerow(["collector_current_density_p99_SOC50", coin_j99, pouch_j99, "A/m2"])

print(json.dumps({"ok": True, "plots": plot_files, "summary": str(POST / "coin_pouch_v8_quantitative_summary.json")}, ensure_ascii=False))
