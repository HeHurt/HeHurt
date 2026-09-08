import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing")
PLOT_DIR = RUN / "plots"
PLOT_DIR.mkdir(exist_ok=True)
data = json.loads((RUN / "full_100N_result.json").read_text(encoding="utf-8"))
s = data["series"]

font_candidates = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]
font_path = next(path for path in font_candidates if path.exists())
font_manager.fontManager.addfont(str(font_path))
font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
plt.rcParams.update({
    "font.family": font_name,
    "axes.unicode_minus": False,
    "font.size": 11,
    "axes.linewidth": 1.0,
})

time_h = [value / 3600 for value in s["time_s"]]
theta0 = s["theta_neg"][0]
charge_soc = [100 * max(0, min(1, (value - theta0) / (1 - theta0))) for value in s["theta_neg"]]


def finish(fig, name):
    path = PLOT_DIR / name
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def style(ax):
    ax.grid(True, color="#d9d9d9", linestyle="--", linewidth=0.6, alpha=0.8)
    ax.tick_params(direction="in", top=True, right=True)


outputs = []

# 1. Voltage and current versus time.
fig, ax1 = plt.subplots(figsize=(8.4, 5.2))
ax2 = ax1.twinx()
ax1.plot(time_h, s["voltage_V"], color="#0057b8", linewidth=2.2, label="加载端电压")
ax1.axhline(3.65, color="#d62728", linestyle="--", linewidth=1.3, label="3.65 V 截止")
ax2.plot(time_h, s["current_Crate"], color="#f28e2b", linewidth=1.8, label="充电倍率")
ax1.set(xlabel="时间 (h)", ylabel="加载端电压 (V)", title="V8 充电电压与电流响应（100 N，石墨膨胀 20%）")
ax2.set_ylabel("充电倍率 (C)")
style(ax1)
lines = ax1.get_lines() + ax2.get_lines()
ax1.legend(lines, [line.get_label() for line in lines], loc="lower right", frameon=False)
outputs.append(finish(fig, "01_充电电压与电流_100N.png"))

# 2. Voltage versus actual charged SOC.
fig, ax = plt.subplots(figsize=(8.4, 5.2))
ax.plot(charge_soc, s["voltage_V"], color="#0057b8", linewidth=2.2)
ax.axhline(3.65, color="#d62728", linestyle="--", linewidth=1.3, label="3.65 V 截止")
imax = max(range(len(s["voltage_V"])), key=s["voltage_V"].__getitem__)
ax.scatter([charge_soc[imax]], [s["voltage_V"][imax]], color="#d62728", zorder=4)
ax.annotate(
    f"峰值 {s['voltage_V'][imax]:.3f} V\nSOC {charge_soc[imax]:.1f}%",
    (charge_soc[imax], s["voltage_V"][imax]), xytext=(-88, -48), textcoords="offset points",
    arrowprops={"arrowstyle": "->", "color": "#555555"},
)
ax.set(xlabel="实际充电 SOC (%)", ylabel="加载端电压 (V)", title="V8 充电电压–SOC 曲线")
style(ax)
ax.legend(frameon=False)
outputs.append(finish(fig, "02_充电电压_SOC_100N.png"))

# 3. Lithiation and breathing.
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.8), sharex=True)
ax1.plot(charge_soc, [100 * value for value in s["theta_neg"]], color="#222222", linewidth=2, label="石墨")
ax1.plot(charge_soc, [100 * value for value in s["theta_pos"]], color="#d62728", linewidth=2, label="LFP")
ax1.set(xlabel="实际充电 SOC (%)", ylabel="平均嵌锂比例 (%)", title="正负极平均嵌锂状态")
ax1.legend(frameon=False)
style(ax1)
ax2.plot(charge_soc, [100 * value for value in s["eps_breath_neg"]], color="#f28e2b", linewidth=2, label="石墨呼吸")
ax2.plot(charge_soc, [100 * value for value in s["eps_breath_pos"]], color="#59a14f", linewidth=2, label="LFP 呼吸")
ax2.axhline(20, color="#f28e2b", linestyle="--", linewidth=1.2, alpha=0.8, label="石墨 20% 满量程")
ax2.set(xlabel="实际充电 SOC (%)", ylabel="轴向呼吸应变 (%)", title="嵌锂呼吸应变")
ax2.legend(frameon=False)
style(ax2)
fig.suptitle("V8 嵌锂状态与材料呼吸耦合", fontsize=14)
outputs.append(finish(fig, "03_嵌锂状态与呼吸应变_100N.png"))

# 4. Pressure and porosity.
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.8), sharex=True)
colors = {"负极": "#222222", "隔膜": "#7f7f7f", "正极": "#d62728"}
for label, key in [("负极", "p_neg_MPa"), ("隔膜", "p_sep_MPa"), ("正极", "p_pos_MPa")]:
    ax1.plot(charge_soc, s[key], linewidth=2, color=colors[label], label=label)
ax1.set(xlabel="实际充电 SOC (%)", ylabel="平均压缩压力 (MPa)", title="局部压缩压力演化")
ax1.legend(frameon=False)
style(ax1)
for label, key in [("负极", "epsl_neg"), ("隔膜", "epsl_sep"), ("正极", "epsl_pos")]:
    ax2.plot(charge_soc, s[key], linewidth=2, color=colors[label], label=label)
ax2.set(xlabel="实际充电 SOC (%)", ylabel="平均孔隙率", title="压力反馈后的孔隙率演化")
ax2.legend(frameon=False)
style(ax2)
fig.suptitle("V8 局部压力–孔隙率双向耦合", fontsize=14)
outputs.append(finish(fig, "04_局部压力与孔隙率_100N.png"))

# 5. Top displacement.
fig, ax = plt.subplots(figsize=(8.4, 5.2))
ax.plot(charge_soc, s["top_disp_um"], color="#9467bd", linewidth=2.2)
ax.set(xlabel="实际充电 SOC (%)", ylabel="顶部最大位移 (μm)", title="V8 顶部位移响应（外压与材料呼吸共同作用）")
style(ax)
outputs.append(finish(fig, "05_顶部位移_SOC_100N.png"))

manifest = {
    "source": str(RUN / "full_100N_result.json"),
    "case": data["case"],
    "plots": outputs,
    "key_metrics": {
        "maximum_voltage_V": max(s["voltage_V"]),
        "maximum_graphite_breathing_pct": 100 * max(s["eps_breath_neg"]),
        "maximum_lfp_breathing_pct": 100 * max(s["eps_breath_pos"]),
        "final_actual_charge_soc_pct": charge_soc[-1],
        "top_displacement_range_um": [min(s["top_disp_um"]), max(s["top_disp_um"])],
    },
}
(RUN / "postprocess_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False))
