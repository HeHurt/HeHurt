import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
OUT = RUN / "postprocess_v8_rated_0p13Ah"
CSV_PATH = OUT / "timeseries_v8_rated_0p13Ah.csv"
JSON_PATH = OUT / "v8_rated_0p13Ah_result.json"
PLOT_PATH = OUT / "01_v8_0p13Ah_full_cycle_and_thickness.png"


with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

for row in rows:
    delta_um = float(row["relative_thickness_change_um"])
    row["relative_thickness_strain_pct"] = str(100.0 * delta_um / 345.5)

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
strain = [float(row["relative_thickness_strain_pct"]) for row in rows]
payload["metrics"]["relative_thickness_strain_min_pct"] = min(strain)
payload["metrics"]["relative_thickness_strain_max_pct"] = max(strain)
payload["thickness_postprocessing"] = {
    "definition": "((average(v, top)-average(v, bottom))-initial_value)",
    "sign_convention": "positive means expansion; negative means compression relative to initial preloaded state",
    "reference_stack_thickness_um": 345.5,
}
JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

time_h = [float(row["time_s"]) / 3600.0 for row in rows]
voltage = [float(row["voltage_V"]) for row in rows]
current = [float(row["current_A"]) for row in rows]
soc = [100.0 * float(row["electrode_SOC"]) for row in rows]
thickness = [float(row["relative_thickness_change_um"]) for row in rows]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial"],
    "axes.unicode_minus": False,
    "figure.dpi": 150,
})
fig, axes = plt.subplots(2, 2, figsize=(12, 7.2), sharex=True)
axes[0, 0].plot(time_h, voltage, color="#0057c8", lw=1.8)
axes[0, 0].axhline(3.65, color="#d62728", ls="--", lw=1.0)
axes[0, 0].axhline(2.50, color="#d62728", ls="--", lw=1.0)
axes[0, 0].set_ylabel("端电压 (V)")
axes[0, 0].set_title("0.5C 充放电电压")

axes[0, 1].plot(time_h, current, color="#3a3a3a", lw=1.6)
axes[0, 1].axhline(0, color="#999999", lw=0.8)
axes[0, 1].set_ylabel("电流 (A)")
axes[0, 1].set_title("额定容量 0.13 Ah：±0.065 A")

axes[1, 0].plot(time_h, soc, color="#00a36c", lw=1.8)
axes[1, 0].set_ylabel("电极平均 SOC (%)")
axes[1, 0].set_xlabel("时间 (h)")
axes[1, 0].set_title("正负极归一化平均 SOC")

axes[1, 1].plot(time_h, thickness, color="#e53935", lw=1.8)
axes[1, 1].axhline(0, color="#999999", lw=0.8)
axes[1, 1].set_ylabel("相对厚度变化 (μm)")
axes[1, 1].set_xlabel("时间 (h)")
axes[1, 1].set_title("统一法向与初始预紧态后的厚度响应")

for axis in axes.flat:
    axis.grid(True, color="#dddddd", lw=0.7, alpha=0.8)
fig.suptitle("单层软包 V8：0.13 Ah 额定容量、0.5C、100 N 双向耦合", fontsize=14, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(PLOT_PATH, bbox_inches="tight")
plt.close(fig)

print(PLOT_PATH)
print(JSON_PATH)
