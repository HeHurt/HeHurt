"""Plot coin/pouch comparisons using true 0 N uncoupled no-breathing baselines."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


TASK = Path(r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V1")
INTERNAL = TASK / "99_内部文件"
COIN_BASE_JSON = INTERNAL / "JSON" / "coin_v9_0N_uncoupled_no_breath_baseline.json"
COIN_BASE_CSV = INTERNAL / "中间数据" / "扣电V9_0N无耦合无呼吸基线时序.csv"
COIN_COUPLED_JSON = (
    INTERNAL
    / "历史运行归档"
    / "COMSOL_runs"
    / "20260820_140000_coin_v9_nonlinear_breathing_cycle"
    / "full_cycle_comparison.json"
)
POUCH_JSON = INTERNAL / "JSON" / "pouch_v8_full_cycle_comparison.json"
OUTPUT = TASK / "04_输出结果" / "图表" / "11_扣电软包_统一0N基线与100N呼吸对比.png"


plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "figure.dpi": 150,
        "savefig.dpi": 240,
    }
)


def read_csv_series(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {name: np.asarray([float(row[name]) for row in rows]) for name in rows[0]}


def as_array(series, name):
    return np.asarray(series[name], dtype=float)


def rebound_window(series):
    time_s = as_array(series, "time_s")
    voltage = as_array(series, "voltage_V")
    current = as_array(series, "current_A")
    discharge = np.flatnonzero(current < -1e-8)
    end = int(discharge[-1])
    mask = (time_s >= time_s[end] - 120) & (time_s <= time_s[end] + 650)
    return (time_s[mask] - time_s[end]) / 60, voltage[mask]


def rebound_metrics(series):
    voltage = as_array(series, "voltage_V")
    current = as_array(series, "current_A")
    end = int(np.flatnonzero(current < -1e-8)[-1])
    return float(voltage[end]), float(voltage[-1]), float(1000 * (voltage[-1] - voltage[end]))


coin_base_payload = json.loads(COIN_BASE_JSON.read_text(encoding="utf-8"))
coin_base = read_csv_series(COIN_BASE_CSV)
coin_coupled_payload = json.loads(COIN_COUPLED_JSON.read_text(encoding="utf-8"))
coin_coupled = coin_coupled_payload["cases"]["literature_nonlinear"]["series"]
coin_coupled_metrics = coin_coupled_payload["cases"]["literature_nonlinear"]["metrics"]
pouch_payload = json.loads(POUCH_JSON.read_text(encoding="utf-8"))
pouch_base = pouch_payload["cases"]["baseline"]["series"]
pouch_coupled = pouch_payload["cases"]["coupled_100N"]["series"]
coin_base_metrics = coin_base_payload["metrics"]
_, coin_settled, coin_rebound = rebound_metrics(coin_coupled)
_, pouch_base_settled, pouch_base_rebound = rebound_metrics(pouch_base)
_, pouch_coupled_settled, pouch_coupled_rebound = rebound_metrics(pouch_coupled)

cases = (
    (coin_base, "扣电：0 N无耦合无呼吸", "#6b7280", "--"),
    (coin_coupled, "扣电：100 N非线性呼吸", "#1d4ed8", "-"),
    (pouch_base, "软包：0 N无耦合无呼吸", "#f59e0b", "--"),
    (pouch_coupled, "软包：100 N非线性呼吸", "#dc2626", "-"),
)

fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.2), constrained_layout=True)
for series, label, color, style in cases:
    axes[0, 0].plot(as_array(series, "time_s") / 3600, as_array(series, "voltage_V"), style, color=color, lw=1.7, label=label)
axes[0, 0].axhline(3.65, color="#be123c", lw=1, ls=":")
axes[0, 0].axhline(2.50, color="#be123c", lw=1, ls=":")
axes[0, 0].set(xlabel="时间 (h)", ylabel="负载端电压 (V)", title="完整0.5C充电–静置–放电")
axes[0, 0].grid(alpha=0.25)
axes[0, 0].legend(frameon=False, ncol=2)

for series, label, color, style in cases:
    x, y = rebound_window(series)
    axes[0, 1].plot(x, y, style, color=color, lw=1.7, label=label)
axes[0, 1].axvline(0, color="#111827", lw=0.8, ls=":")
axes[0, 1].set(xlabel="相对放电截止时间 (min)", ylabel="负载端电压 (V)", title="放电截止后的电压松弛")
axes[0, 1].grid(alpha=0.25)

labels = ["扣电\n0 N基线", "扣电\n100 N呼吸", "软包\n0 N基线", "软包\n100 N呼吸"]
settled = [
    coin_base_metrics["settled_voltage_V"],
    coin_settled,
    pouch_base_settled,
    pouch_coupled_settled,
]
rebound = [
    coin_base_metrics["total_rebound_mV"],
    coin_rebound,
    pouch_base_rebound,
    pouch_coupled_rebound,
]
colors = ["#6b7280", "#1d4ed8", "#f59e0b", "#dc2626"]
bars = axes[1, 0].bar(labels, settled, color=colors)
axes[1, 0].set_ylim(2.80, 2.93)
axes[1, 0].set_ylabel("静置末端电压 (V)")
axes[1, 0].set_title("绝对静置电压：由最终嵌锂状态决定")
axes[1, 0].grid(axis="y", alpha=0.25)
axes[1, 0].bar_label(bars, fmt="%.3f", padding=3)

bars = axes[1, 1].bar(labels, rebound, color=colors)
axes[1, 1].set_ylim(350, 450)
axes[1, 1].set_ylabel(r"总回弹幅度 $V_{rest}-V_{cut}$ (mV)")
axes[1, 1].set_title("严格回弹幅度：不要与静置平台高低混用")
axes[1, 1].grid(axis="y", alpha=0.25)
axes[1, 1].bar_label(bars, fmt="%.1f", padding=3)

fig.suptitle("扣电与软包：统一0 N无耦合基线后的完整循环对比", fontsize=15, weight="bold")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(json.dumps({"ok": True, "output": str(OUTPUT), "settled_V": settled, "rebound_mV": rebound}, ensure_ascii=False))
