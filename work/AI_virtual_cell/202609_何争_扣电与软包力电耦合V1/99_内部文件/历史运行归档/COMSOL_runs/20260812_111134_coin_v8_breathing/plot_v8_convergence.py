import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing")
data = json.loads((RUN / "full_100N_result.json").read_text(encoding="utf-8"))
s = data["series"]

csv_path = RUN / "metrics.csv"
columns = list(s)
with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.writer(handle)
    writer.writerow(columns)
    writer.writerows(zip(*(s[name] for name in columns)))

plt.rcParams.update({"font.family": ["Calibri", "Microsoft YaHei", "sans-serif"], "font.size": 10})
fig, axes = plt.subplots(2, 2, figsize=(10, 6.8), constrained_layout=True)
t = [value / 3600 for value in s["time_s"]]

ax = axes[0, 0]
ax.plot(t, s["voltage_V"], color="#0057b8", lw=2)
ax.axhline(3.65, color="#d62728", ls="--", lw=1, label="3.65 V cutoff")
ax.set(ylabel="Loaded voltage (V)", title="Voltage and cutoff")
ax.legend(frameon=False)

ax = axes[0, 1]
ax.plot(t, [100 * value for value in s["theta_neg"]], label="Graphite lithiation", color="#222222")
ax.plot(t, [100 * value for value in s["theta_pos"]], label="LFP lithiation", color="#d62728")
ax.set(ylabel="Average lithiation (%)", title="Electrode lithiation states")
ax.legend(frameon=False)

ax = axes[1, 0]
ax.plot(t, [100 * value for value in s["eps_breath_neg"]], label="Graphite breathing", color="#ff7f0e")
ax.plot(t, [100 * value for value in s["eps_breath_pos"]], label="LFP breathing", color="#2ca02c")
ax.axhline(20, color="#ff7f0e", ls="--", lw=1, alpha=0.7, label="Graphite 20% cap")
ax.set(xlabel="Time (h)", ylabel="Axial eigenstrain (%)", title="Intercalation breathing")
ax.legend(frameon=False)

ax = axes[1, 1]
ax.plot(t, s["p_neg_MPa"], label="Negative", color="#222222")
ax.plot(t, s["p_sep_MPa"], label="Separator", color="#7f7f7f")
ax.plot(t, s["p_pos_MPa"], label="Positive", color="#d62728")
ax.set(xlabel="Time (h)", ylabel="Mean compressive pressure (MPa)", title="Pressure feedback")
ax.legend(frameon=False)

for ax in axes.flat:
    ax.grid(True, ls="--", lw=0.5, alpha=0.4)
    ax.set_xlim(min(t), max(t))

fig.suptitle("V8 breathing-coupled model: 100 N, graphite full-range expansion = 20%", fontsize=13)
plot_path = RUN / "plots" / "v8_100N_20pct_breathing_convergence.png"
plot_path.parent.mkdir(exist_ok=True)
fig.savefig(plot_path, dpi=220, bbox_inches="tight")
plt.close(fig)

print(json.dumps({"ok": True, "csv": str(csv_path), "plot": str(plot_path)}, ensure_ascii=False))
