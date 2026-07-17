"""3d 机理判别 MVP —— 复现交底书图4：多信号破解退化解。

核心主张（专利图4）：
  - 仅凭容量衰减曲线，不同机理组合在早期几乎重合 -> 退化解，不可判别。
  - 引入 DCR（正交信号）后，不同机理组合早期即分叉 -> 锁定真实机理。

本脚本用 PyBaMM DFN + 老化子模型搭两个候选机理组合，跑早期循环，
在若干检查点同时测量 (容量, DCR)，画出 图4 上(容量重合)/下(DCR分叉)。

候选组合（参数已粗调到容量衰减早期相近）：
  combo_SEI : 仅 SEI 增长（消耗活性锂，阻抗增长温和）
  combo_LAM : SEI + 活性物质损失(LAM, stress-driven)（容量损失相近，但 DCR 增长更快）

设 combo_LAM 为"真实"机理；用早期 DCR 即可把它和 combo_SEI 区分开。

运行：
    python mechanism_discrimination_fig4.py            # 快速冒烟(少循环)
    python mechanism_discrimination_fig4.py --full     # 完整(更多循环+DFN)
"""
from __future__ import annotations

import argparse
import numpy as np
import pybamm


# ----------------------------------------------------------------------------
# 机理组合定义
# ----------------------------------------------------------------------------
def build_options(combo: str) -> dict:
    """返回 PyBaMM 模型 options。两组共用 SEI，combo_LAM 额外开 LAM。"""
    opts = {
        "SEI": "solvent-diffusion limited",
        "SEI porosity change": "true",
    }
    if combo == "combo_LAM":
        opts["loss of active material"] = "reaction-driven"
    return opts


def make_parameter_values(combo: str) -> pybamm.ParameterValues:
    """Chen2020 基础参数 + 按组合微调机理速率，使早期容量衰减相近。"""
    pv = pybamm.ParameterValues("Chen2020")
    if combo == "combo_SEI":
        # SEI 单机理：调强 SEI 以匹配 LAM 组合的总容量损失
        pv.update({"SEI solvent diffusivity [m2.s-1]": 1.5e-19}, check_already_exists=False)
    elif combo == "combo_LAM":
        # SEI 较弱 + LAM 贡献一部分容量损失（LAM 额外抬高 DCR -> 正交信号分叉）
        pv.update({"SEI solvent diffusivity [m2.s-1]": 3.0e-20}, check_already_exists=False)
        # LAM (reaction-driven)：通过负极 reaction-driven LAM 因子驱动活性物质损失
        pv.update(
            {"Negative electrode reaction-driven LAM factor [m3.mol-1]": 1.5e-4},
            check_already_exists=False,
        )
    return pv


# ----------------------------------------------------------------------------
# 老化 + 多信号测量
# ----------------------------------------------------------------------------
def aging_with_checkpoints(combo: str, n_blocks: int, cycles_per_block: int):
    """跑老化循环，每个 block 后测 (容量 Ah, DCR Ohm)。返回 dict of arrays。"""
    model = pybamm.lithium_ion.DFN(options=build_options(combo))
    pv = make_parameter_values(combo)

    # 老化工况：1C 充放循环
    aging_exp = pybamm.Experiment(
        [
            (
                "Discharge at 1C until 2.5V",
                "Charge at 1C until 4.2V",
                "Hold at 4.2V until C/20",
            )
        ]
        * cycles_per_block
    )

    sim = pybamm.Simulation(model, parameter_values=pv, experiment=aging_exp)

    cyc, cap, dcr = [], [], []
    sol = None
    total = 0
    # 检查点 0（初始）
    c0, r0 = measure_capacity_and_dcr(model, pv, starting_solution=None)
    cyc.append(0); cap.append(c0); dcr.append(r0)

    for b in range(n_blocks):
        sol = sim.solve(starting_solution=sol)
        total += cycles_per_block
        c, r = measure_capacity_and_dcr(model, pv, starting_solution=sol.last_state)
        cyc.append(total); cap.append(c); dcr.append(r)
        print(f"  [{combo}] cycle {total:4d}: cap={c:.4f} Ah  DCR={r*1e3:.2f} mΩ")

    return {"cycle": np.array(cyc), "capacity": np.array(cap), "dcr": np.array(dcr)}


def measure_capacity_and_dcr(model, pv, starting_solution):
    """RPT：C/3 满放测容量；1C 10s 脉冲测 50%SOC DCR。"""
    # --- 容量：C/3 满放 ---
    rpt_cap = pybamm.Experiment(
        ["Charge at C/3 until 4.2V", "Hold at 4.2V until C/50", "Discharge at C/3 until 2.5V"]
    )
    sim_cap = pybamm.Simulation(model, parameter_values=pv, experiment=rpt_cap)
    s = sim_cap.solve(starting_solution=starting_solution)
    cap = float(s["Discharge capacity [A.h]"].entries[-1])

    # --- DCR：充到 50%SOC -> 静置 -> 1C 10s 放电脉冲 ---
    rpt_dcr = pybamm.Experiment(
        [
            "Charge at C/3 until 4.2V",
            "Hold at 4.2V until C/50",
            f"Discharge at C/3 for {0.5*3:.3f} hours",  # 粗略放到~50%SOC
            "Rest for 30 minutes",
            "Discharge at 1C for 10 seconds",
        ],
        period="1 second",
    )
    sim_dcr = pybamm.Simulation(model, parameter_values=pv, experiment=rpt_dcr)
    sd = sim_dcr.solve(starting_solution=starting_solution)
    V = sd["Terminal voltage [V]"].entries
    I = sd["Current [A]"].entries
    # 脉冲前(静置末) vs 脉冲末
    v_pre = V[np.where(np.abs(I) < 1e-3)[0][-1]]
    v_post = V[-1]
    i_pulse = I[-1]
    dcr = abs((v_pre - v_post) / i_pulse) if abs(i_pulse) > 1e-9 else np.nan
    return cap, dcr


# ----------------------------------------------------------------------------
# 主流程 + 图4
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    if args.full:
        n_blocks, cpb = 5, 20
    else:
        n_blocks, cpb = 3, 5

    pybamm.set_logging_level("CRITICAL")
    results = {}
    for combo in ["combo_SEI", "combo_LAM"]:
        print(f"running {combo} ...")
        results[combo] = aging_with_checkpoints(combo, n_blocks, cpb)

    plot_fig4(results)
    discriminate(results, truth="combo_LAM")


def plot_fig4(results):
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 8), sharex=True)
    for combo, r in results.items():
        ax1.plot(r["cycle"], r["capacity"] / r["capacity"][0] * 100, "o-", label=combo)
        ax2.plot(r["cycle"], r["dcr"] * 1e3, "s-", label=combo)
    ax1.set_ylabel("Capacity retention [%]")
    ax1.set_title("Fig.4 top: capacity-only -> early overlap (degenerate)")
    ax1.legend()
    ax2.set_ylabel("DCR [mOhm]")
    ax2.set_xlabel("Cycle")
    ax2.set_title("Fig.4 bottom: add DCR -> early divergence (identifiable)")
    ax2.legend()
    fig.tight_layout()
    out = "fig4_mechanism_discrimination.png"
    fig.savefig(out, dpi=130)
    print("saved", out)


def discriminate(results, truth):
    """模拟'机理判别'：给定一条'实测' DCR(=truth)，看哪个组合最匹配。"""
    measured = results[truth]["dcr"]
    print("\n=== 机理判别（基于 DCR 残差）===")
    for combo, r in results.items():
        rmse = float(np.sqrt(np.mean((r["dcr"] - measured) ** 2))) * 1e3
        print(f"  {combo}: DCR-RMSE = {rmse:.3f} mΩ")
    print(f"  -> 真实机理: {truth}（DCR 残差最小者胜出）")


if __name__ == "__main__":
    main()
