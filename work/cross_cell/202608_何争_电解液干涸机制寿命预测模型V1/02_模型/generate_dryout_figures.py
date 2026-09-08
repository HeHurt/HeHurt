"""Generate report figures from the current BatteryProject dry-out implementation.

The reduced-order demonstration calls ``DryoutTracker.update`` with controlled
block-end state snapshots. It verifies bookkeeping and branch behavior; it is
not an experiment-calibrated cycle-life prediction.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "BatteryProject"))
sys.path.insert(0, str(ROOT / "params"))

from src.electrolyte_dryout import DryoutTracker  # noqa: E402
from paramsMIC import get_hithium_params as get_mic_params  # noqa: E402
from paramsCW391_pouch import get_hithium_params as get_cw391_params  # noqa: E402


OUT = ROOT / "work" / "cross_cell" / "202608_何争_电解液干涸机制寿命预测模型V1" / "04_输出结果" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "no-latex"])
except ImportError:
    pass
plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160
plt.rcParams["savefig.dpi"] = 220


def add_box(ax, xy, text, width=0.22, height=0.16, facecolor="#eef4f8"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        linewidth=1.1,
        edgecolor="#31566f",
        facecolor=facecolor,
    )
    ax.add_patch(box)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=10)
    return box


def add_arrow(ax, start, end, label=None):
    arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, linewidth=1.1, color="#31566f")
    ax.add_patch(arrow)
    if label:
        ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.025, label, ha="center", fontsize=8.5)


def plot_mechanism():
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    add_box(ax, (0.04, 0.66), "SEI / 裂纹SEI增长\nLoss of Li to SEI")
    add_box(ax, (0.39, 0.66), "EC 溶剂消耗\nV_EC = Δn_SEI × V̄_EC")
    add_box(ax, (0.74, 0.66), "全电芯电解液减少\nV_tot,new = V_tot,old − V_EC")
    add_arrow(ax, (0.26, 0.74), (0.39, 0.74))
    add_arrow(ax, (0.61, 0.74), (0.74, 0.74))

    add_box(ax, (0.04, 0.28), "副反应 / 力学耦合\n改变三域孔隙率")
    add_box(ax, (0.39, 0.28), "卷芯孔隙体积更新\nV_pore = Σ(L_i ε_i) L_y L_z")
    add_box(ax, (0.74, 0.28), "储液区补液或挤液\n比较 V_need 与储备量")
    add_arrow(ax, (0.26, 0.36), (0.39, 0.36))
    add_arrow(ax, (0.61, 0.36), (0.74, 0.36))
    add_arrow(ax, (0.85, 0.66), (0.85, 0.45), "体积守恒")

    add_box(ax, (0.39, 0.03), "下一分块初始条件\n浓度比例 + 等效宽度 + 上一块末态", width=0.30, height=0.14, facecolor="#fff4df")
    add_arrow(ax, (0.79, 0.28), (0.67, 0.17), "Ratio_dryout")
    ax.text(0.5, 0.95, "BatteryProject 电解液干涸准静态耦合链", ha="center", va="center", fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig_2_1_dryout_mechanism.png", bbox_inches="tight")
    plt.close(fig)


def plot_branch_logic():
    fig, ax = plt.subplots(figsize=(9.8, 5.7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    add_box(ax, (0.35, 0.80), "V_need = V_EC,consumed − ΔV_pore", width=0.30, height=0.12)
    add_box(ax, (0.05, 0.53), "V_need < 0\n孔隙收缩量更大", width=0.24, height=0.13, facecolor="#eaf6ec")
    add_box(ax, (0.38, 0.53), "V_need ≥ 0 且储备充足\n完全补液", width=0.24, height=0.13, facecolor="#eaf6ec")
    add_box(ax, (0.71, 0.53), "储备不足或无储备\n部分补液 / 不补液", width=0.24, height=0.13, facecolor="#fff0ee")
    add_arrow(ax, (0.43, 0.80), (0.19, 0.66))
    add_arrow(ax, (0.50, 0.80), (0.50, 0.66))
    add_arrow(ax, (0.57, 0.80), (0.83, 0.66))
    add_box(ax, (0.05, 0.24), "电解液挤入储液区\nRatio_dryout 不限幅至 1", width=0.24, height=0.13)
    add_box(ax, (0.38, 0.24), "卷芯孔隙完全润湿\nRatio_dryout = 1", width=0.24, height=0.13)
    add_box(ax, (0.71, 0.24), "卷芯欠液\nRatio_dryout < 1\n等效宽度缩减", width=0.24, height=0.13, facecolor="#fff4df")
    add_arrow(ax, (0.17, 0.53), (0.17, 0.37))
    add_arrow(ax, (0.50, 0.53), (0.50, 0.37))
    add_arrow(ax, (0.83, 0.53), (0.83, 0.37))
    ax.text(0.5, 0.95, "干涸体积平衡的三类分支", ha="center", fontsize=15, weight="bold")
    ax.text(0.5, 0.08, "说明：储液区是等效体积仓；更新发生在寿命分块之间。", ha="center", fontsize=9.5, color="#444444")
    fig.tight_layout()
    fig.savefig(OUT / "fig_5_2_branch_logic.png", bbox_inches="tight")
    plt.close(fig)


def pore_volume_ml(params):
    return (
        params["Negative electrode thickness [m]"] * params["Negative electrode porosity"]
        + params["Positive electrode thickness [m]"] * params["Positive electrode porosity"]
        + params["Separator thickness [m]"] * params["Separator porosity"]
    ) * params["Electrode width [m]"] * params["Electrode height [m]"] * 1e6


def plot_initial_inventory():
    cells = [("MIC 1175Ah", get_mic_params), ("CW391 pouch", get_cw391_params)]
    ratios = np.array([1.00, 1.05, 1.10, 1.20, 1.30])
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, (name, getter) in zip(axes, cells):
        params = getter(1, temperature=298.15)
        pore = pore_volume_ml(params)
        total = pore * ratios
        reserve = total - pore
        ax.plot(ratios, total, "o-", label="总电解液")
        ax.plot(ratios, reserve, "s-", label="等效储备量")
        ax.axhline(pore, color="#666666", linestyle="--", linewidth=1, label="卷芯孔隙体积")
        ax.set_title(f"{name}\n初始孔隙体积 = {pore:.2f} mL")
        ax.set_xlabel("excess_ratio")
        ax.set_ylabel("体积 (mL)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("当前实现中 excess_ratio 对初始电解液库存的控制", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig_5_1_initial_inventory.png", bbox_inches="tight")
    plt.close(fig)


class _Var:
    def __init__(self, entries):
        self.entries = np.asarray(entries, dtype=float)


class _BlockEndSolution:
    def __init__(self, values):
        self.values = {key: _Var(value) for key, value in values.items()}

    def __getitem__(self, key):
        return self.values[key]


def make_block_solution(params, block_index, lli_per_block=0.25):
    eps_n0 = float(params["Negative electrode porosity"])
    eps_p0 = float(params["Positive electrode porosity"])
    eps_s0 = float(params["Separator porosity"])
    eps_drop = 0.0002 * block_index
    jr_vol = float(params["Current total electrolyte volume in jelly roll [m3]"])
    c_e = float(params["Initial concentration in electrolyte [mol.m-3]"])
    return _BlockEndSolution({
        "Loss of lithium to negative SEI [mol]": [0.0, lli_per_block],
        "Loss of lithium to negative SEI on cracks [mol]": [0.0, 0.0],
        "X-averaged electrolyte concentration [mol.m-3]": [c_e, c_e],
        "X-averaged negative electrode porosity": [eps_n0, max(eps_n0 - eps_drop, 0.05)],
        "X-averaged separator porosity": [eps_s0, eps_s0],
        "X-averaged positive electrode porosity": [eps_p0, max(eps_p0 - eps_drop, 0.05)],
        "Total lithium in electrolyte [mol]": [c_e * jr_vol, c_e * jr_vol],
    })


def simulate_reduced_order(excess_ratio, n_blocks=40):
    params = get_mic_params(1, temperature=298.15)
    tracker = DryoutTracker(params, excess_ratio=excess_ratio)
    for block in range(1, n_blocks + 1):
        tracker.update(make_block_solution(params, block), params)
        if tracker.history["Ratio_Dryout"][-1] <= 0.25:
            break
    return tracker.history


def plot_reduced_order_demo():
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
    for ratio, color in zip((1.0, 1.1, 1.2), ("#c84545", "#d58b2b", "#2f6ca3")):
        h = simulate_reduced_order(ratio)
        x = np.arange(len(h["Ratio_Dryout"]))
        axes[0].plot(x, h["Ratio_Dryout"], "o-", markersize=3, color=color, label=f"excess_ratio={ratio:.1f}")
        width = np.asarray(h["Width"])
        axes[1].plot(x, width / width[0] * 100, "o-", markersize=3, color=color, label=f"excess_ratio={ratio:.1f}")
    axes[0].axhline(1.0, color="#777777", linestyle="--", linewidth=1)
    axes[0].set_title("卷芯干涸比例")
    axes[0].set_ylabel("Ratio_Dryout")
    axes[1].set_title("等效有效宽度")
    axes[1].set_ylabel("Width / Width$_0$ (%)")
    for ax in axes:
        ax.set_xlabel("干涸更新块序号")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("基于当前体积守恒代码的降阶分块核算示例（非寿命标定结果）", fontsize=13, weight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig_6_1_reduced_order_demo.png", bbox_inches="tight")
    plt.close(fig)


def main():
    plot_mechanism()
    plot_branch_logic()
    plot_initial_inventory()
    plot_reduced_order_demo()
    print(f"Generated figures in {OUT}")


if __name__ == "__main__":
    main()
