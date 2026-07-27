"""CW363 vs CW500 充放电产热功率对比 (0.125P / 0.167P / 0.25P)。

- 沿用 examples/全生命周期产热 的口径：不可逆热 |V-U_ocv|*|I| + 可逆热 I*T*dU/dT
  (dU/dT 用 config 解析回退 LFP-graphite)，取每圈充/放电平均总产热功率 (W)。
- 循环工况：2.5~3.65 V（电压窗口，CC 满充/满放）。
- 不考老化（单轮窗口，老化项不累积）。
- CW500 的 Electrode width 在源文件里少了 /1000（=52094 m），这里运行时修正为
  213.5*61*2*2/1000 = 52.094 m，不改动 DLP 加密源文件。
"""
import sys, os, warnings, json
warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:/HithiumSSD/hithium/BatteryProject")
sys.path.insert(0, r"C:/HithiumSSD/hithium/params")
import numpy as np
import pybamm
from src import config
config.ensure_entropy_loaded()
from src.analysis import get_all_heat_components
from params1300CW363 import get_hithium_params as g363
from paramsMICCW500 import get_hithium_params as g500

# 中等网格：平衡精度与速度（两电芯同网格，保证对比一致）
GRID = {"x_n": 8, "x_s": 8, "x_p": 8, "r_n": 16, "r_p": 16}
RATES = [0.125, 0.167, 0.25]   # P = 电芯自身标称容量
CW500_WIDTH = 213.5 * 61 * 2 * 2 / 1000   # = 52.094 m

def build_params(fn, cell):
    p = dict(fn(temperature=298.15))
    if cell == "CW500":
        p["Electrode width [m]"] = CW500_WIDTH   # 修正源文件 bug
    return p

def run_cell(cell, fn):
    p = build_params(fn, cell)
    pv = pybamm.ParameterValues("OKane2022"); pv.update(p, check_already_exists=False)
    model = pybamm.lithium_ion.DFN()
    # 每一倍率一轮：满充(至3.65V) -> 休 -> 满放(至2.5V)
    cycles = []
    for r in RATES:
        cycles.append((
            f"Charge at {r}C until 3.65 V",
            "Rest for 5 minutes",
            f"Discharge at {r}C until 2.5 V",
        ))
    exp = pybamm.Experiment(cycles)
    sim = pybamm.Simulation(model, parameter_values=pv, experiment=exp, var_pts=GRID,
                            solver=pybamm.CasadiSolver(rtol=1e-6, atol=1e-6, mode="safe"))
    sol = sim.solve()
    out = {}
    for i, r in enumerate(RATES):
        h = get_all_heat_components(sol, label_for_temp=f"25°C {r}P")
        def gv(arr):
            return float(arr[i]) if i < len(arr) else None
        out[r] = {
            "charge_total_W": gv(h["total_chg"]),
            "charge_irrev_W": gv(h["irrev_chg"]),
            "charge_rev_W": gv(h["rev_chg"]),
            "discharge_total_W": gv(h["total_dchg"]),
            "discharge_irrev_W": gv(h["irrev_dchg"]),
            "discharge_rev_W": gv(h["rev_dchg"]),
        }
    return out

results = {}
results["CW363"] = run_cell("CW363", g363)
results["CW500"] = run_cell("CW500", g500)

print("\n=== 充放电平均产热功率 (W) | 满充/满放 2.5~3.65V, 25°C, 不考老化 ===")
hdr = f"{'电芯':<7}{'倍率':<7}{'充-总':>9}{'充-不可逆':>11}{'充-可逆':>9}{'放-总':>9}{'放-不可逆':>11}{'放-可逆':>9}"
print(hdr)
for cell in ["CW363", "CW500"]:
    for r in RATES:
        d = results[cell][r]
        print(f"{cell:<7}{r:<7}"
              f"{d['charge_total_W']:>9.2f}{d['charge_irrev_W']:>11.2f}{d['charge_rev_W']:>9.2f}"
              f"{d['discharge_total_W']:>9.2f}{d['discharge_irrev_W']:>11.2f}{d['discharge_rev_W']:>9.2f}")

with open(r"C:/HithiumSSD/hithium/params/heat_power_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\nwrote heat_power_results.json")
