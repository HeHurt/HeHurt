"""最小验证：用 PyBaMM DFN 跑 params1300CW363 的 0.5C 充-放，核对容量/SOC/电压窗。

用法（在 params 目录下，用带 pybamm 26.4.2 的 venv）：
    python verify_cw363.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pybamm
import numpy as np

from params1300CW363 import get_hithium_params

NOMINAL = 1199.4680548035492  # 表中设计容量


def discharge_capacity_ah(sol):
    """遍历所有 cycle/step，对放电段（电流<0）积分得到容量(Ah)。"""
    Q = 0.0
    for cyc in getattr(sol, "cycles", []):
        for st in getattr(cyc, "steps", []):
            try:
                t = st["Time [s]"].entries
                I = st["Current [A]"].entries
            except Exception:
                continue
            if len(t) < 2:
                continue
            dt = np.diff(t)
            neg = I[1:] < 0
            Q += -float(np.sum(I[1:][neg] * dt[neg] / 3600.0))
    return Q


def main():
    model = pybamm.lithium_ion.DFN()
    # 与项目一致：以 OKane2022 为基，check_already_exists=False 允许覆盖/追加
    param = pybamm.ParameterValues("OKane2022")
    param.update(get_hithium_params(temperature=298.15), check_already_exists=False)

    # 粗网格加速
    var_pts = {
        "x_n": 10, "x_s": 10, "x_p": 10,
        "r_n": 20, "r_p": 20, "y": 20, "z": 20,
    }
    # 容量测试：先 0.5C 充到截止电压（不恒压，避开 CV 长尾），休息，再 0.5C 放到 2.5V
    exp = pybamm.Experiment([
        ("Charge at 0.5C until 3.65 V",),
        ("Rest for 5 minutes",),
        ("Discharge at 0.5C until 2.5 V",),
    ])
    sim = pybamm.Simulation(
        model, parameter_values=param, experiment=exp, var_pts=var_pts,
        solver=pybamm.CasadiSolver(rtol=1e-6, atol=1e-6, mode="safe"),
    )
    sol = sim.solve()

    Q = discharge_capacity_ah(sol)
    V_all = sol["Terminal voltage [V]"].entries
    V_min = float(np.min(V_all))
    V_max = float(np.max(V_all))

    print("=" * 60)
    print("params1300CW363 验证结果 (0.5C 充-放)")
    print("=" * 60)
    print(f"标称容量(设计值)      : {NOMINAL:.3f} Ah")
    print(f"0.5C 放电实测容量     : {Q:.3f} Ah")
    print(f"容量偏差              : {(Q-NOMINAL)/NOMINAL*100:+.2f} %")
    print(f"端电压范围            : {V_min:.3f} ~ {V_max:.3f} V")
    ok_cap = abs((Q - NOMINAL) / NOMINAL) < 0.12   # 无 CV 恒压，容量略低于标称属正常
    ok_v = (V_min >= 2.45) and (V_max <= 3.7)
    print(f"容量合理性(<12%偏差)   : {'PASS' if ok_cap else 'CHECK'}")
    print(f"电压窗(2.45~3.7V)     : {'PASS' if ok_v else 'CHECK'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
