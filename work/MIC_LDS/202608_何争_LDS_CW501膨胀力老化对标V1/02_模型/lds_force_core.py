# -*- coding: utf-8 -*-
"""LDS CW501 膨胀力老化对标 核心模块。

体系参数: C:/HithiumSSD/hithium/params/paramsLDSCW501.py
仿真引擎: C:/HithiumSSD/hithium/BatteryProject (PyBaMM 26.4.2)

用法:
    python lds_force_core.py --smoke            # 2 圈冒烟
    python lds_force_core.py --baseline         # 双工况基线(12 圈 x t_factor=50)
    python lds_force_core.py --tune-aging ...   # 老化参数扫描
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(r"C:\HithiumSSD\hithium\BatteryProject")
PARAMS_ROOT = Path(r"C:\HithiumSSD\hithium\params")
CALIB_DIR = Path(__file__).resolve().parent
DATA_DIR = CALIB_DIR / "data"
OUTPUT_DIR = CALIB_DIR / "outputs"

for p in (str(PROJECT_ROOT), str(PARAMS_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pybamm

from src.runtime import apply_pybamm_runtime_limits

apply_pybamm_runtime_limits()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

from src.analysis import (
    calculate_cycle_swelling,
    get_discharge_capacity,
    retention_from_capacity,
)
from src.swelling_coupling import SwellingCoupler
from src.electrolyte_dryout import DryoutTracker, run_aging_with_dryout
from paramsLDSCW501 import get_hithium_params as get_hithium_params_cw501

# ---------------------------------------------------------------------------
# 模型与实验
# ---------------------------------------------------------------------------

AGING_OPTIONS = {
    "SEI": "ec reaction limited",
    "SEI porosity change": "true",
    "lithium plating": "irreversible",
    "lithium plating porosity change": "true",
    "particle mechanics": ("swelling and cracking", "swelling only"),
    "SEI on cracks": "true",
    "loss of active material": "stress-driven",
    "contact resistance": "true",
    "open-circuit potential": ("current sigmoid", "current sigmoid"),
}

SOLVER_KWARGS = dict(rtol=1e-6, atol=1e-6)
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}

# 实验工况 (P 率按 C 率近似)
CONDITIONS = {
    "25°C 0.125P": dict(temperature_c=25.0, c_rate=0.125, n_exp_cycles=369),
    "25°C 0.25P": dict(temperature_c=25.0, c_rate=0.25, n_exp_cycles=357),
}


def build_model():
    return pybamm.lithium_ion.DFN(AGING_OPTIONS)


def build_experiment(c_rate: float, n_cycles: int, temperature_k: float) -> pybamm.Experiment:
    step = (
        f"Charge at {c_rate}C until 3.65 V (5 minute period)",
        "Rest for 10 minutes (5 minute period)",
        f"Discharge at {c_rate}C until 2.5 V (5 minute period)",
        "Rest for 10 minutes (5 minute period)",
    )
    return pybamm.Experiment([step] * n_cycles, temperature=temperature_k)


def make_params(t_factor: float = 1.0, temperature_k: float = 298.15, overrides: dict | None = None):
    """OKane2022 基座 + paramsLDSCW501 体系参数 + 可选 override。"""
    params = pybamm.ParameterValues("OKane2022")
    params.update(get_hithium_params_cw501(t_factor=t_factor, temperature=temperature_k),
                  check_already_exists=False)
    params.update({"Ambient temperature [K]": temperature_k,
                   "Initial temperature [K]": temperature_k},
                  check_already_exists=False)
    if overrides:
        params.update(overrides, check_already_exists=False)
    return params


def run_aging(
    c_rate: float,
    temperature_k: float,
    t_factor: float = 50.0,
    n_sim_cycles: int = 12,
    cycles_per_block: int = 4,
    overrides: dict | None = None,
    use_dryout: bool = False,
    use_swelling_coupling: bool = False,
    swelling_kwargs: dict | None = None,
    solver_kwargs: dict | None = None,
    showprogress: bool = True,
):
    """分块老化仿真，返回最终 solution + 各块列表。

    n_sim_cycles 为仿真圈数，每圈代表 t_factor 圈等效老化。
    """
    solver = pybamm.IDAKLUSolver(**(solver_kwargs or SOLVER_KWARGS))
    params = make_params(t_factor=t_factor, temperature_k=temperature_k, overrides=overrides)
    model = build_model()

    tracker = DryoutTracker(params, excess_ratio=1.2) if use_dryout else None
    coupler = None
    if use_swelling_coupling:
        area = params["Electrode width [m]"] * params["Electrode height [m]"]
        kw = dict(
            k_stiffness=3.0e6,
            k_cell=None,
            preload_force=300.0,
            beta_irreversible=1.0,
            omega_n=0.1 * 3.1e-6,
            omega_p=0.0,
            expansion_function_n="graphite",
            expansion_function_p="lfp",
            method="engineering",
            compaction_moduli=None,
            max_step_compression=0.02,
            area=area,
        )
        if swelling_kwargs:
            kw.update(swelling_kwargs)
        coupler = SwellingCoupler(params, **kw)

    def experiment_fn(cycles_per_block):
        return build_experiment(c_rate, cycles_per_block, temperature_k)

    n_blocks = max(1, int(np.ceil(n_sim_cycles / cycles_per_block)))
    t0 = time.time()
    # 注意: get_hithium_params=None —— 参数已在 make_params 中带 t_factor 构建,
    # 若传入会被 run_aging_with_dryout 在块 0 重新应用而抹掉 overrides。
    sol_list = run_aging_with_dryout(
        model, params, experiment_fn, solver, VAR_PTS,
        tracker=tracker, swelling_coupler=coupler,
        n_blocks=n_blocks, cycles_per_block=cycles_per_block,
        t_factor=t_factor, temperature=temperature_k,
        get_hithium_params=None,
        showprogress=showprogress,
    )
    elapsed = time.time() - t0
    sol = sol_list[-1] if sol_list else None
    return dict(sol=sol, sol_list=sol_list, params=params, tracker=tracker,
                coupler=coupler, elapsed_min=elapsed / 60.0)


def extract_metrics(sol, params, force_kwargs: dict | None = None):
    """从 solution 提取每圈放电容量/保持率 + 膨胀力(F_max, F_min)。"""
    caps = get_discharge_capacity(sol)["discharge_capacity"]
    ret = retention_from_capacity(caps)
    kw = dict(
        k_stiffness=3.0e6, k_cell=None, preload_force=300.0,
        beta_irreversible=1.0, omega_n=0.1 * 3.1e-6, omega_p=0.0,
        expansion_function_n="graphite", expansion_function_p="lfp",
        method="engineering", reference="parameter_initial",
    )
    if force_kwargs:
        kw.update(force_kwargs)
    max_f, min_f = calculate_cycle_swelling(sol, params, **kw)
    cycles = np.arange(1, len(ret) + 1)
    return dict(cycles=cycles, retention=ret, capacity_ah=caps,
                max_force=max_f, min_force=min_f)


# ---------------------------------------------------------------------------
# 实验数据
# ---------------------------------------------------------------------------

def load_exp_cycle_force() -> dict:
    """加载循环膨胀力对比数据 (sheet 4EALDS+1EAMIC)。"""
    with open(DATA_DIR / "cycle_force_comparison.json", encoding="utf-8") as f:
        groups = json.load(f)
    out = {}
    for g in groups:
        cell, cond, tech = g["cell_id"], g["condition"], g["tech"]
        rows = [r for r in g["data"] if r.get("SOH") not in (None, "")]
        if not rows:
            continue
        cyc = np.arange(1, len(rows) + 1)
        soh = np.array([float(r["SOH"]) for r in rows])
        fmax = np.array([float(r["F_max"]) if r["F_max"] not in (None, "") else np.nan for r in rows])
        fmin = np.array([float(r["F_min"]) if r["F_min"] not in (None, "") else np.nan for r in rows])
        key = f"{cond} {tech}"
        out.setdefault(key, []).append(dict(
            label=f"25°C {cond} {tech}", cell=cell, condition=cond, tech=tech,
            cycle=cyc, retention=soh / 100.0, max_force=fmax, min_force=fmin,
        ))
    return out


def load_exp_single_cycle() -> dict:
    """加载单圈膨胀力数据 (LDS-A2样 / LDS-A4轮A组)。"""
    out = {}
    for fn, label in [
        ("single_cycle_LDS-A2样A1F9R00001-25C0.125P.json", "25°C 0.125P LDS-A2"),
        ("single_cycle_LDS-A4轮A组25C0.25P.json", "25°C 0.25P LDS-A4"),
    ]:
        with open(DATA_DIR / fn, encoding="utf-8") as f:
            groups = json.load(f)
        out[label] = groups
    return out


# ---------------------------------------------------------------------------
# 对标绘图
# ---------------------------------------------------------------------------

def plot_retention_force(sim_sets, exp_groups, force_kwargs, out_png):
    """sim_sets: [{label, retention, max_force, min_force, cycles}]"""
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    ax_ret, ax_fmax, ax_fmin = axes
    colors = {"25°C 0.125P": "#1f77b4", "25°C 0.25P": "#d62728"}

    for s in sim_sets:
        col = colors.get(s["label"], "#7f7f7f")
        n = len(s["retention"])
        cyc = np.arange(1, n + 1) * 50  # 等效圈数 = 仿真圈 x t_factor
        ax_ret.plot(cyc, s["retention"] * 100, "o-", color=col, ms=4,
                    label=f"Sim {s['label']}")
        ax_fmax.plot(cyc, s["max_force"], "o-", color=col, ms=4,
                     label=f"Sim {s['label']}")
        ax_fmin.plot(cyc, s["min_force"], "s-", color=col, ms=4,
                     label=f"Sim {s['label']}")

    for cond, lst in exp_groups.items():
        col = colors.get(cond, "#7f7f7f")
        for e in lst:
            ax_ret.plot(e["cycle"], e["retention"] * 100, "--", color=col, alpha=0.6)
            ax_fmax.plot(e["cycle"], e["max_force"], "--", color=col, alpha=0.6)
            ax_fmin.plot(e["cycle"], e["min_force"], "--", color=col, alpha=0.6)
        ax_ret.plot([], [], "--", color=col, alpha=0.7, label=f"Exp {cond}")

    ax_ret.set(xlabel="Cycle", ylabel="SOH [%]", title="容量保持率对标")
    ax_fmax.set(xlabel="Cycle", ylabel="Force [N]", title="最大膨胀力对标")
    ax_fmin.set(xlabel="Cycle", ylabel="Force [N]", title="最小膨胀力对标")
    for ax in axes:
        ax.legend(fontsize=8, frameon=False)
        ax.grid(True, alpha=0.3)
    fig.suptitle("LDS CW501 膨胀力老化对标 (Sim vs Exp)", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print("saved:", out_png)


def plot_single_cycle(sol, params, label, out_png, force_kwargs=None):
    """画最后一个仿真圈的圈内膨胀力曲线 vs 实验单圈。"""
    kw = dict(
        k_stiffness=3.0e6, k_cell=None, preload_force=300.0, beta_irreversible=1.0,
        omega_n=0.1 * 3.1e-6, omega_p=0.0,
        expansion_function_n="graphite", expansion_function_p="lfp",
        method="engineering", reference="cycle_start",
    )
    if force_kwargs:
        kw.update(force_kwargs)
    from src.analysis import _engineering_swelling_displacement, _get_engineering_swelling_params
    cycle = sol.cycles[-1]
    param_pack = _get_engineering_swelling_params(params)
    disp = _engineering_swelling_displacement(
        cycle, param_pack, kw["omega_n"], kw["omega_p"],
        _resolve_f(kw["expansion_function_n"]), _resolve_f(kw["expansion_function_p"]),
        kw["beta_irreversible"], {},
    )
    force = np.maximum(kw["k_stiffness"] * disp + kw["preload_force"], 0.0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    t = np.arange(len(force)) / len(force)
    ax.plot(t, force, "-", label=label + " Sim (圈内)")
    ax.set(xlabel="归一化圈内时间", ylabel="Force [N]", title="圈内膨胀力剖面")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def _resolve_f(f):
    from src.analysis import graphite_expansion_fraction, lfp_expansion_fraction
    return {"graphite": graphite_expansion_fraction,
            "lfp": lfp_expansion_fraction}.get(f, None)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--t-factor", type=float, default=50.0)
    ap.add_argument("--sim-cycles", type=int, default=12)
    ap.add_argument("--label", default="25°C 0.125P")
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.smoke:
        print("== SMOKE ==")
        r = run_aging(c_rate=0.125, temperature_k=298.15, t_factor=50.0,
                      n_sim_cycles=2, cycles_per_block=2, showprogress=False)
        m = extract_metrics(r["sol"], r["params"])
        print("retention:", np.round(m["retention"], 4))
        print("max_force:", np.round(m["max_force"], 1))
        print("min_force:", np.round(m["min_force"], 1))
        print(f"elapsed {r['elapsed_min']:.2f} min")
        return

    cond = CONDITIONS[args.label]
    r = run_aging(c_rate=cond["c_rate"], temperature_k=cond["temperature_c"] + 273.15,
                  t_factor=args.t_factor, n_sim_cycles=args.sim_cycles,
                  cycles_per_block=4, showprogress=False)
    m = extract_metrics(r["sol"], r["params"])
    fn = f"run_{args.label.replace('°C','C').replace(' ','_')}.json"
    with open(OUTPUT_DIR / fn, "w", encoding="utf-8") as f:
        json.dump({k: np.asarray(v).tolist() for k, v in m.items()}, f, ensure_ascii=False, indent=1)
    print(f"elapsed {r['elapsed_min']:.2f} min -> {fn}")


if __name__ == "__main__":
    main()
