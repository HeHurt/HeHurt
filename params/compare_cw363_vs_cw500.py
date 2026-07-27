"""CW363 vs CW500 并排对比：相同 0.5C 满充(至3.65V)-满放(至2.5V)协议下，对比放电容量与电压窗。

- 用电压截止（until 3.65 V / until 2.5 V）避免时长协议导致的过充/不可行。
- 修复 CW500 源文件的 Electrode width bug：运行时把 52094 m 修正为 213.5*61*2*2/1000=52.094 m。
- 容量用 src.analysis.get_discharge_capacity 提取。
"""
import sys
sys.path.insert(0, r"C:/HithiumSSD/hithium/BatteryProject")
sys.path.insert(0, r"C:/HithiumSSD/hithium/params")

import numpy as np
import pybamm
from src.analysis import get_discharge_capacity

from params1300CW363 import get_hithium_params as get_cw363
from paramsMICCW500 import get_hithium_params as get_cw500

NOMINAL = {
    "CW363": 1199.4680548035492,  # 表中设计容量
    "CW500": 1300.0,              # paramsMICCW500 标称
}
CW500_WIDTH = 213.5 * 61 * 2 * 2 / 1000   # = 52.094 m

EXP = pybamm.Experiment([
    ("Charge at 0.5C until 3.65 V",),
    ("Rest for 5 minutes",),
    ("Discharge at 0.5C until 2.5 V",),
])
VAR_PTS = {"x_n": 8, "x_s": 8, "x_p": 8, "r_n": 16, "r_p": 16}


def build(tag, get_params):
    p = dict(get_params(temperature=298.15))
    if tag == "CW500":
        p["Electrode width [m]"] = CW500_WIDTH
    return p


def run(tag, get_params):
    model = pybamm.lithium_ion.DFN()
    param = pybamm.ParameterValues("OKane2022")
    param.update(build(tag, get_params), check_already_exists=False)
    sim = pybamm.Simulation(
        model, parameter_values=param, experiment=EXP, var_pts=VAR_PTS,
        solver=pybamm.CasadiSolver(rtol=1e-6, atol=1e-6, mode="safe"),
    )
    sol = sim.solve()
    cap = get_discharge_capacity(sol)
    dcap = float(cap["discharge_capacity"][0]) if len(cap["discharge_capacity"]) else float("nan")
    V = sol["Terminal voltage [V]"].entries
    return {"Q": dcap, "Vmin": float(np.min(V)), "Vmax": float(np.max(V)), "nominal": NOMINAL[tag]}


def main():
    res = {}
    for tag, fn in [("CW363", get_cw363), ("CW500", get_cw500)]:
        print(f"[*] 正在仿真 {tag} ...", flush=True)
        res[tag] = run(tag, fn)

    print("\n" + "=" * 64)
    print("CW363 vs CW500 并排对比 (相同 0.5C 满充-满放协议, 25°C)")
    print("=" * 64)
    print(f"{'电芯':<8}{'标称(Ah)':>12}{'实测(Ah)':>12}{'偏差%':>10}{'Vmin':>9}{'Vmax':>9}")
    print("-" * 64)
    for tag in ["CW363", "CW500"]:
        r = res[tag]
        dev = (r["Q"] - r["nominal"]) / r["nominal"] * 100
        print(f"{tag:<8}{r['nominal']:>12.1f}{r['Q']:>12.3f}{dev:>10.2f}{r['Vmin']:>9.3f}{r['Vmax']:>9.3f}")
    print("-" * 64)
    print(f"CW363/CW500 容量比 : {res['CW363']['Q']/res['CW500']['Q']:.3f}  "
          f"(标称比 {res['CW363']['nominal']/res['CW500']['nominal']:.3f})")
    print("=" * 64)


if __name__ == "__main__":
    main()
