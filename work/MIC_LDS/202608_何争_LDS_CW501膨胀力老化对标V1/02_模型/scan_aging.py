# -*- coding: utf-8 -*-
"""老化参数扫描: 找同时对标 SOH + 膨胀力的机制配比。

用法: python scan_aging.py [--c-rate 0.125] [--k-eff 3e6] [--preload 296]
每个组合跑 8 圈 x t_factor=50 (≈400 等效圈), 输出指标表。
"""
import os, sys, json, time, argparse
CALIB = r"C:\Users\hez\WorkBuddy\2026-08-05-19-58-13\exp_force_calib"
sys.path.insert(0, CALIB)
os.chdir(CALIB)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

from lds_force_core import run_aging, extract_metrics, CONDITIONS, OUTPUT_DIR

# 基线老化参数 (paramsLDSCW501 25C, t_factor=1)
BASE = {
    "SEI kinetic rate constant [m.s-1]": 4.809982610110174e-14 * 0.1,   # k_sei=0.1 @T>=298
    "EC diffusivity [m2.s-1]": 3.487219488169518e-22 * 2.0,             # D_sei=2
    "Negative electrode LAM constant proportional term [s-1]": 1.5e-7,
    "Negative electrode cracking rate": None,  # 复杂函数, 用倍率处理
    "Positive electrode cracking rate": 0.0,
    "Lithium plating kinetic rate constant [m.s-1]": 3.181158194366325e-05,
    "Electrolyte dry out rate [m3.s-1]": 1e-12,
}

# 组合定义: 各参数倍率 (None = 不变)
COMBOS = {
    "C1_baseline": {},
    "C2_negLAM_x0.2": {"lam_n": 0.2},
    "C3_C2_posCrack": {"lam_n": 0.2, "pos_crack": 0.5},
    "C4_C3_sei_x1.5": {"lam_n": 0.2, "pos_crack": 0.5, "sei": 1.5},
    "C5_C3_sei_x2.5": {"lam_n": 0.2, "pos_crack": 0.5, "sei": 2.5},
    "C6_negLAM_x0.2_sei_x1.5": {"lam_n": 0.2, "sei": 1.5},
}


def build_overrides(combo, t_factor=50.0):
    ov = {}
    if "lam_n" in combo:
        ov["Negative electrode LAM constant proportional term [s-1]"] = (
            1.5e-7 * t_factor * combo["lam_n"])
    if "pos_crack" in combo:
        # 正极裂纹率用标量近似 (build_cracking_rate 只接收 t_factor)
        ov["Positive electrode cracking rate"] = 0.2 * 2.1939307272313407e-21 * combo["pos_crack"]
    if "sei" in combo:
        ov["SEI kinetic rate constant [m.s-1]"] = (
            BASE["SEI kinetic rate constant [m.s-1]"] * t_factor * combo["sei"])
    return ov


def run_combo(name, combo, c_rate, k_eff, preload, n_cycles=8, t_factor=50.0):
    ov = build_overrides(combo, t_factor=t_factor)
    t0 = time.time()
    r = run_aging(c_rate=c_rate, temperature_k=298.15, t_factor=t_factor,
                  n_sim_cycles=n_cycles, cycles_per_block=4,
                  overrides=ov, showprogress=False)
    m = extract_metrics(r["sol"], r["params"],
                        force_kwargs=dict(k_stiffness=k_eff, preload_force=preload))
    ret = np.asarray(m["retention"])
    fmin = np.asarray(m["min_force"])
    fmax = np.asarray(m["max_force"])
    n = len(ret)
    cyc_total = n * 50
    slope_min = (fmin[-1] - fmin[0]) / cyc_total * 100
    slope_max = (fmax[-1] - fmax[0]) / cyc_total * 100
    row = dict(
        combo=name, overrides=ov,
        soh_loss_pct=(1 - ret[-1]) * 100,
        fmin_0=float(fmin[0]), fmin_end=float(fmin[-1]),
        fmax_0=float(fmax[0]), fmax_end=float(fmax[-1]),
        slope_min_N100c=float(slope_min), slope_max_N100c=float(slope_max),
        amp_0=float(fmax[0] - fmin[0]), amp_end=float(fmax[-1] - fmin[-1]),
        elapsed_s=round(time.time() - t0, 1),
    )
    print(f"[{name}] SOH loss={row['soh_loss_pct']:.2f}% | "
          f"Fmin {row['fmin_0']:.0f}->{row['fmin_end']:.0f} ({row['slope_min_N100c']:.1f}N/100c) | "
          f"Fmax {row['fmax_0']:.0f}->{row['fmax_end']:.0f} ({row['slope_max_N100c']:.1f}N/100c) | "
          f"amp {row['amp_0']:.0f}->{row['amp_end']:.0f} | {row['elapsed_s']}s")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c-rate", type=float, default=0.125)
    ap.add_argument("--k-eff", type=float, default=3.0e6)
    ap.add_argument("--preload", type=float, default=296.0)
    ap.add_argument("--combos", default="C1_baseline,C2_negLAM_x0.2,C3_C2_posCrack,C4_C3_sei_x1.5,C5_C3_sei_x2.5,C6_negLAM_x0.2_sei_x1.5")
    args = ap.parse_args()

    results = []
    for name in [c.strip() for c in args.combos.split(",") if c.strip()]:
        if name not in COMBOS:
            print(f"skip unknown {name}")
            continue
        results.append(run_combo(name, COMBOS[name], args.c_rate, args.k_eff, args.preload))

    with open(OUTPUT_DIR / f"scan_{args.c_rate}P.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1, default=str)
    print("\n== 扫描完成 ->", f"scan_{args.c_rate}P.json", "==")


if __name__ == "__main__":
    main()
