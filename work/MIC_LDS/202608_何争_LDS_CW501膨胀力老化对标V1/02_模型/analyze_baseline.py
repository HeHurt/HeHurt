# -*- coding: utf-8 -*-
"""基线对标分析 + 老化机制分解。"""
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

from lds_force_core import (
    run_aging, extract_metrics, load_exp_cycle_force, CONDITIONS, make_params, build_model,
    OUTPUT_DIR,
)

# ---------- 1. 画基线对标图 ----------
fig, axes = plt.subplots(1, 3, figsize=(17, 5))
colors = {"25°C 0.125P": "#1f77b4", "25°C 0.25P": "#d62728"}
exp = load_exp_cycle_force()
for cond in ["25°C 0.125P", "25°C 0.25P"]:
    fn = f"run_{cond.replace('°C','C').replace(' ','_')}.json"
    with open(OUTPUT_DIR / fn, encoding="utf-8") as f:
        m = json.load(f)
    col = colors[cond]
    cyc = np.arange(1, len(m["retention"]) + 1) * 50
    axes[0].plot(cyc, np.array(m["retention"]) * 100, "o-", color=col, ms=4, label=f"Sim {cond}")
    axes[1].plot(cyc, m["max_force"], "o-", color=col, ms=4, label=f"Sim {cond}")
    axes[2].plot(cyc, m["min_force"], "o-", color=col, ms=4, label=f"Sim {cond}")
    # 打印指标
    r = np.array(m["retention"]); fmin = np.array(m["min_force"]); fmax = np.array(m["max_force"])
    n = len(r)
    print(f"[{cond}] SOH {r[0]*100:.2f}->{r[-1]*100:.2f}% (loss {(1-r[-1])*100:.2f}% at {n*50}c)")
    print(f"   Fmin {fmin[0]:.1f}->{fmin[-1]:.1f} N, slope {(fmin[-1]-fmin[0])/(n*50)*100:.1f} N/100c")
    print(f"   Fmax {fmax[0]:.1f}->{fmax[-1]:.1f} N, slope {(fmax[-1]-fmax[0])/(n*50)*100:.1f} N/100c")
    print(f"   amplitude {fmax[0]-fmin[0]:.1f}->{fmax[-1]-fmin[-1]:.1f} N")
    # 实验对比
    for e in exp.get(cond, []):
        axes[0].plot(e["cycle"], e["retention"] * 100, "--", color=col, alpha=0.5, lw=1)
        axes[1].plot(e["cycle"], e["max_force"], "--", color=col, alpha=0.5, lw=1)
        axes[2].plot(e["cycle"], e["min_force"], "--", color=col, alpha=0.5, lw=1)
    axes[0].plot([], [], "--", color=col, alpha=0.7, label=f"Exp {cond}")
axes[0].set(xlabel="Cycle", ylabel="SOH [%]", title="容量保持率基线对标")
axes[1].set(xlabel="Cycle", ylabel="Force [N]", title="最大膨胀力基线对标")
axes[2].set(xlabel="Cycle", ylabel="Force [N]", title="最小膨胀力基线对标")
for ax in axes:
    ax.legend(fontsize=8, frameon=False)
    ax.grid(True, alpha=0.3)
fig.suptitle("LDS CW501 基线对标 (k_stiffness=3e6, preload=300N, t_factor=50)", fontsize=13, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(OUTPUT_DIR / "baseline_compare.png", dpi=150)
plt.close(fig)
print("saved baseline_compare.png")

# ---------- 2. 机制分解: 跑一遍并提取膜厚/损失分解 ----------
print("\n=== 机制分解 (0.125P, 8 cycles) ===")
r = run_aging(c_rate=0.125, temperature_k=298.15, t_factor=50.0,
              n_sim_cycles=8, cycles_per_block=4, showprogress=False)
sol = r["sol"]
loss = {"SEI": [], "plating": [], "dead": [], "crackSEI": [], "rough": []}
for cyc in sol.cycles:
    for k, var in [("SEI", "X-averaged negative SEI thickness [m]"),
                   ("plating", "X-averaged negative lithium plating thickness [m]"),
                   ("dead", "X-averaged negative dead lithium thickness [m]"),
                   ("crackSEI", "X-averaged negative SEI on cracks thickness [m]"),
                   ("rough", "X-averaged negative electrode roughness ratio")]:
        try:
            loss[k].append(float(np.asarray(cyc[var].entries).reshape(-1)[-1]))
        except Exception:
            loss[k].append(np.nan)
for k, v in loss.items():
    v = np.asarray(v) * (1e9 if k != "rough" else 1)
    unit = "nm" if k != "rough" else "-"
    print(f"  {k:9s}: {v[0]:8.2f} -> {v[-1]:8.2f} {unit} (d={v[-1]-v[0]:.2f})")

# 每圈 EOC 电解液浓度 (干涸检查)
ce = []
for cyc in sol.cycles:
    try:
        ce.append(float(np.asarray(cyc["X-averaged electrolyte concentration [mol.m-3]"].entries).reshape(-1)[-1]))
    except Exception:
        ce.append(np.nan)
print(f"  electrolyte c_e: {np.asarray(ce)[0]:.0f} -> {np.asarray(ce)[-1]:.0f} mol/m3")

# 圈内浓度摆幅 (验证呼吸位移来源)
for idx in [0, -1]:
    cyc = sol.cycles[idx]
    cn = np.asarray(cyc["X-averaged negative particle concentration [mol.m-3]"].entries)
    cn_avg = np.mean(cn, axis=0) if cn.ndim > 1 else cn
    cp = np.asarray(cyc["X-averaged positive particle concentration [mol.m-3]"].entries)
    cp_avg = np.mean(cp, axis=0) if cp.ndim > 1 else cp
    cmax_n, cmax_p = 29094.0, 20042.0
    print(f"  cycle {idx+1}: sto_n {cn_avg.min()/cmax_n:.3f}->{cn_avg.max()/cmax_n:.3f} (swing {cn_avg.max()-cn_avg.min():.0f} mol/m3), "
          f"sto_p {cp_avg.min()/cmax_p:.3f}->{cp_avg.max()/cmax_p:.3f}")
