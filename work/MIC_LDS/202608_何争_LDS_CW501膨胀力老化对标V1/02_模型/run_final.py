# -*- coding: utf-8 -*-
"""最终标定: 双工况同时对标 SOH + 膨胀力(F_max/F_min)。

标定配方 (来自杠杆扫描):
  老化(公共):  a_n x3.6 (比表面积, 纯力学放大膜厚位移), Vm x4 (SEI偏摩尔体积),
               Li/SEI摩尔比 x0.5 (降低SEI的Li消耗)
  老化(分工况): EC diffusivity 有效速率: 0.125P x0.55 / 0.25P x1.0
               (补偿仿真SEI时间驱动 vs 实验循环驱动的差异)
  力学(分工况): 0.125P: k_eff=3.0e6 N/m, preload=296 N
               0.25P:  k_eff=1.02e7 N/m, preload=310 N
"""
import os, sys, json
CALIB = r"C:\Users\hez\WorkBuddy\2026-08-05-19-58-13\exp_force_calib"
sys.path.insert(0, CALIB)
os.chdir(CALIB)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

from lds_force_core import run_aging, extract_metrics, load_exp_cycle_force, OUTPUT_DIR

EC_BASE = 3.487219488169518e-22 * 2.0
AN_BASE = 3.0 * 0.6733 / 5.5e-6

T_FACTOR = 50.0
SIM_CYCLES = 8


def aging_overrides(ec_mult):
    return {
        "EC diffusivity [m2.s-1]": EC_BASE * ec_mult * T_FACTOR,
        "Negative electrode surface area to volume ratio [m-1]": AN_BASE * 3.6,
        "Outer SEI partial molar volume [m3.mol-1]": 9.645e-5 * 4.0,
        "Ratio of lithium moles to SEI moles": 1.8 * 0.5,
    }


COND_FORCE = {
    "25°C 0.125P": dict(c_rate=0.125, k_eff=3.0e6, preload=296.0, ec_mult=0.55),
    "25°C 0.25P": dict(c_rate=0.25, k_eff=1.02e7, preload=310.0, ec_mult=1.0),
}

results = {}
sim_sets = []
for label, cfg in COND_FORCE.items():
    r = run_aging(c_rate=cfg["c_rate"], temperature_k=298.15, t_factor=T_FACTOR,
                  n_sim_cycles=SIM_CYCLES, cycles_per_block=4,
                  overrides=aging_overrides(cfg["ec_mult"]), showprogress=False)
    m = extract_metrics(r["sol"], r["params"],
                        force_kwargs=dict(k_stiffness=cfg["k_eff"], preload_force=cfg["preload"]))
    ret = np.asarray(m["retention"]); fmin = np.asarray(m["min_force"]); fmax = np.asarray(m["max_force"])
    n = len(ret); tot = n * T_FACTOR
    results[label] = dict(
        soh_loss_pct=float((1 - ret[-1]) * 100),
        fmin_0=float(fmin[0]), fmin_end=float(fmin[-1]),
        fmax_0=float(fmax[0]), fmax_end=float(fmax[-1]),
        slope_min_N100c=float((fmin[-1] - fmin[0]) / tot * 100),
        slope_max_N100c=float((fmax[-1] - fmax[0]) / tot * 100),
        retention=ret.tolist(), max_force=fmax.tolist(), min_force=fmin.tolist(),
        k_eff=cfg["k_eff"], preload=cfg["preload"], ec_mult=cfg["ec_mult"],
    )
    sim_sets.append(dict(label=label, retention=ret, max_force=fmax, min_force=fmin))
    print(f"[{label}] SOH loss={results[label]['soh_loss_pct']:.2f}% | "
          f"Fmin {fmin[0]:.0f}->{fmin[-1]:.0f} ({results[label]['slope_min_N100c']:.1f}N/100c) | "
          f"Fmax {fmax[0]:.0f}->{fmax[-1]:.0f} ({results[label]['slope_max_N100c']:.1f}N/100c)")

with open(OUTPUT_DIR / "final_calibration.json", "w", encoding="utf-8") as f:
    json.dump(dict(t_factor=T_FACTOR, sim_cycles=SIM_CYCLES,
                   conditions=results), f, ensure_ascii=False, indent=1)

# ---------- 最终对标图 ----------
fig, axes = plt.subplots(1, 3, figsize=(17, 5))
colors = {"25°C 0.125P": "#1f77b4", "25°C 0.25P": "#d62728"}
exp = load_exp_cycle_force()
for s in sim_sets:
    col = colors[s["label"]]
    cyc = np.arange(1, len(s["retention"]) + 1) * T_FACTOR
    axes[0].plot(cyc, s["retention"] * 100, "o-", color=col, ms=4, lw=1.4, label=f"Sim {s['label']}")
    axes[1].plot(cyc, s["max_force"], "o-", color=col, ms=4, lw=1.4, label=f"Sim {s['label']}")
    axes[2].plot(cyc, s["min_force"], "o-", color=col, ms=4, lw=1.4, label=f"Sim {s['label']}")
for cond in ["25°C 0.125P", "25°C 0.25P"]:
    col = colors[cond]
    for e in exp.get(cond, []):
        axes[0].plot(e["cycle"], e["retention"] * 100, "--", color=col, alpha=0.55, lw=1.0)
        axes[1].plot(e["cycle"], e["max_force"], "--", color=col, alpha=0.55, lw=1.0)
        axes[2].plot(e["cycle"], e["min_force"], "--", color=col, alpha=0.55, lw=1.0)
    axes[0].plot([], [], "--", color=col, alpha=0.8, lw=1.0, label=f"Exp {cond} (2 cells)")
axes[0].set(xlabel="Cycle", ylabel="SOH [%]", title="容量保持率")
axes[1].set(xlabel="Cycle", ylabel="Force [N]", title="最大膨胀力 F_max")
axes[2].set(xlabel="Cycle", ylabel="Force [N]", title="最小膨胀力 F_min")
for ax in axes:
    ax.legend(fontsize=8, frameon=False)
    ax.grid(True, alpha=0.3)
fig.suptitle("LDS CW501 膨胀力老化对标 — 最终标定结果 (Sim vs Exp)", fontsize=14, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(OUTPUT_DIR / "final_calibration.png", dpi=150)
print("saved final_calibration.png")
