# -*- coding: utf-8 -*-
"""实验数据概览图 (用 BatteryProject venv 跑)。"""
import os, sys
CALIB = r"C:\Users\hez\WorkBuddy\2026-08-05-19-58-13\exp_force_calib"
sys.path.insert(0, CALIB)
os.chdir(CALIB)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

from lds_force_core import load_exp_cycle_force, load_exp_single_cycle

exp = load_exp_cycle_force()
fig, axes = plt.subplots(1, 3, figsize=(17, 5))
styles = {"25℃ 0.125P": ("#1f77b4", "-"), "25℃ 0.25P": ("#d62728", "-")}
for key, lst in exp.items():
    cond = key.split(" LDS")[0]
    col, ls = styles.get(cond, ("#999999", "--"))
    for e in lst:
        axes[0].plot(e["cycle"], e["retention"] * 100, ls, color=col, alpha=0.7, lw=1.0)
        axes[1].plot(e["cycle"], e["max_force"], ls, color=col, alpha=0.7, lw=1.0)
        axes[2].plot(e["cycle"], e["min_force"], ls, color=col, alpha=0.7, lw=1.0)
        print(f"{e['label']} | cycles={e['cycle'][-1]} | SOH={e['retention'][-1]*100:.2f} | "
              f"Fmax {e['max_force'][0]:.0f}->{np.nanmax(e['max_force']):.0f} | "
              f"Fmin {e['min_force'][0]:.0f}->{np.nanmax(e['min_force']):.0f}")
axes[0].set(xlabel="Cycle", ylabel="SOH [%]", title="容量保持率")
axes[1].set(xlabel="Cycle", ylabel="Force [N]", title="最大膨胀力")
axes[2].set(xlabel="Cycle", ylabel="Force [N]", title="最小膨胀力")
for ax in axes:
    ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(CALIB, "outputs", "exp_overview.png"), dpi=150)
print("saved exp_overview.png")

# 单圈膨胀力剖面
sc = load_exp_single_cycle()
fig2, axes2 = plt.subplots(1, 2, figsize=(13, 4.5))
for ax, (label, groups) in zip(axes2, sc.items()):
    for grp in groups:
        pts = np.array([p[2] for p in grp["points"] if p[2] is not None], dtype=float)
        t = np.arange(len(pts)) / max(len(pts) - 1, 1)
        ax.plot(t, pts, lw=1.0, label=grp["cycle_marker"])
    ax.set(xlabel="归一化圈内时间", ylabel="Force [N]", title=label)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(True, alpha=0.3)
fig2.tight_layout()
fig2.savefig(os.path.join(CALIB, "outputs", "exp_single_cycle.png"), dpi=150)
print("saved exp_single_cycle.png")
