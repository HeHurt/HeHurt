# -*- coding: utf-8 -*-
"""力学参数扫描: 在老化机制固定下, 扫 k_eff 与 preload 对标膨胀力水平。

用法: python scan_force.py --c-rate 0.25 --combos F1:3e6:310,F2:6e6:310,F3:1.1e7:310
"""
import os, sys, json, time, argparse
CALIB = r"C:\Users\hez\WorkBuddy\2026-08-05-19-58-13\exp_force_calib"
sys.path.insert(0, CALIB)
os.chdir(CALIB)

import numpy as np
from lds_force_core import run_aging, extract_metrics, OUTPUT_DIR

def run_one(c_rate, k_eff, preload, aging_overrides, n_cycles=8):
    t0 = time.time()
    r = run_aging(c_rate=c_rate, temperature_k=298.15, t_factor=50.0,
                  n_sim_cycles=n_cycles, cycles_per_block=4,
                  overrides=aging_overrides, showprogress=False)
    m = extract_metrics(r["sol"], r["params"],
                        force_kwargs=dict(k_stiffness=k_eff, preload_force=preload))
    ret = np.asarray(m["retention"]); fmin = np.asarray(m["min_force"]); fmax = np.asarray(m["max_force"])
    n = len(ret); tot = n * 50
    row = dict(
        c_rate=c_rate, k_eff=k_eff, preload=preload,
        soh_loss_pct=float((1 - ret[-1]) * 100),
        fmin_0=float(fmin[0]), fmin_end=float(fmin[-1]),
        fmax_0=float(fmax[0]), fmax_end=float(fmax[-1]),
        slope_min_N100c=float((fmin[-1] - fmin[0]) / tot * 100),
        slope_max_N100c=float((fmax[-1] - fmax[0]) / tot * 100),
        amp_0=float(fmax[0] - fmin[0]), amp_end=float(fmax[-1] - fmin[-1]),
        elapsed_s=round(time.time() - t0, 1),
    )
    print(f"[{c_rate}P k={k_eff:.1e}] SOH loss={row['soh_loss_pct']:.2f}% | "
          f"Fmin {row['fmin_0']:.0f}->{row['fmin_end']:.0f} ({row['slope_min_N100c']:.1f}N/100c) | "
          f"Fmax {row['fmax_0']:.0f}->{row['fmax_end']:.0f} ({row['slope_max_N100c']:.1f}N/100c) | "
          f"amp {row['amp_0']:.0f}->{row['amp_end']:.0f} | {row['elapsed_s']}s")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c-rate", type=float, default=0.25)
    ap.add_argument("--combos", default="F1:3e6:310,F2:6e6:310,F3:1.1e7:310")
    ap.add_argument("--aging-overrides", default="{}")
    args = ap.parse_args()
    aging_overrides = json.loads(args.aging_overrides)
    results = []
    for c in args.combos.split(","):
        name, k, p = c.split(":")
        results.append(run_one(args.c_rate, float(k), float(p), aging_overrides))
    with open(OUTPUT_DIR / f"scan_force_{args.c_rate}P.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("== force scan done ==")


if __name__ == "__main__":
    main()
