# -*- coding: utf-8 -*-
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib import font_manager

from fig_helpers import arrow, box, flowchart, save


ROOT = Path(__file__).resolve().parent
FIG = ROOT / "fig"
FIG.mkdir(exist_ok=True)


def setup_font():
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simkai.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            font_manager.fontManager.addfont(p)
            name = font_manager.FontProperties(fname=p).get_name()
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 9


def f1_structure():
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("图1  内置电解液储库与芯吸补液结构示意", pad=10, fontsize=12)

    # Cell shell
    ax.add_patch(mp.Rectangle((0.8, 1.0), 10.4, 6.0, fill=False, lw=2.0))
    ax.text(6.0, 0.55, "1 方壳壳体", ha="center", fontsize=9, fontweight="bold")

    # Electrode stack
    ax.add_patch(mp.Rectangle((1.4, 1.55), 6.7, 4.9, facecolor="0.94", edgecolor="black", lw=1.3))
    for i in range(9):
        y = 1.85 + i * 0.48
        ax.plot([1.65, 7.85], [y, y], color="black", lw=0.8)
    ax.text(4.75, 6.65, "2 卷芯/叠芯主体", ha="center", fontsize=9, fontweight="bold")

    # Reservoir
    ax.add_patch(mp.FancyBboxPatch((8.65, 2.0), 1.55, 3.8, boxstyle="round,pad=0.04,rounding_size=0.12",
                                   facecolor="0.82", edgecolor="black", lw=1.6, hatch="////"))
    ax.text(9.42, 5.95, "3 定容储库", ha="center", fontsize=9, fontweight="bold")
    ax.text(9.42, 3.9, "补偿电解液\nV$_r$", ha="center", va="center", fontsize=8.5)

    # Wick paths
    paths = [(8.65, 5.1, 7.8, 5.1), (8.65, 4.0, 7.1, 4.0), (8.65, 2.9, 7.7, 2.4)]
    for idx, (x0, y0, x1, y1) in enumerate(paths):
        ax.plot([x0, x1], [y0, y1], color="black", lw=2.0)
        ax.add_patch(mp.Circle((x1, y1), 0.09, facecolor="black"))
        ax.text((x0 + x1) / 2, y0 + 0.22, f"4{chr(97+idx)}", ha="center", fontsize=8)
    ax.text(6.95, 1.15, "4 芯吸路径：端部/角部/厚度方向低润湿区", ha="center", fontsize=8.5)

    # Rate-control membrane
    ax.add_patch(mp.Rectangle((8.42, 2.15), 0.18, 3.5, facecolor="0.55", edgecolor="black", lw=1.0))
    ax.text(8.15, 5.9, "5 限流膜", ha="center", fontsize=8.5)

    # Hotspot marks
    for x, y, label in [(7.7, 5.1, "6a 端部"), (7.1, 4.0, "6b 中段"), (7.7, 2.4, "6c 角部")]:
        ax.add_patch(mp.Circle((x, y), 0.22, fill=False, lw=1.3))
        ax.text(x - 0.1, y - 0.55, label, ha="center", fontsize=8)

    arrow(ax, 9.7, 1.7, 9.7, 1.05, lw=1.2)
    ax.text(10.0, 1.18, "7 储库固定/隔离支架", fontsize=8.3, va="center")
    ax.text(1.0, 7.25, "按寿命期电解液消耗量定容，按干涸热点布置芯吸路径", fontsize=8.6)
    save(fig, FIG / "f1.png")


def f2_curves():
    cycles = np.linspace(0, 12000, 300)
    consumption = 0.04 + 0.000055 * cycles + 0.18 / (1 + np.exp(-(cycles - 7600) / 900))
    release = 0.02 + 0.000018 * cycles + 0.28 / (1 + np.exp(-(cycles - 6500) / 1300))
    without = 1.0 - consumption
    with_res = 1.0 - consumption + np.minimum(release, 0.58)
    with_res = np.minimum(with_res, 1.0)
    capacity_without = 100 - 0.0011 * cycles - 8 / (1 + np.exp(-(cycles - 7600) / 600))
    capacity_with = 100 - 0.0009 * cycles - 3.5 / (1 + np.exp(-(cycles - 9000) / 850))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.3, 6.0), sharex=True)
    fig.suptitle("图2  储库定容与循环后期补液效果示意", y=0.98, fontsize=12)
    ax1.plot(cycles, without * 100, "--", color="0.45", lw=1.8, label="现有：有效液量")
    ax1.plot(cycles, with_res * 100, "-", color="black", lw=2.1, label="本方案：有效液量")
    ax1.fill_between(cycles, without * 100, with_res * 100, color="0.85", label="被动补液窗口")
    ax1.axvline(6500, color="0.25", ls=":", lw=1.2)
    ax1.text(6700, 91, "限流膜进入\n持续释放区", fontsize=8.5, bbox=dict(fc="white", ec="0.7", lw=0.8))
    ax1.set_ylabel("有效电解液量 / %")
    ax1.set_ylim(30, 105)
    ax1.grid(True, color="0.86", lw=0.7)
    ax1.legend(frameon=False, fontsize=8.4, loc="lower left")

    ax2.plot(cycles, capacity_without, "--", color="0.45", lw=1.8, label="现有电芯")
    ax2.plot(cycles, capacity_with, "-", color="black", lw=2.1, label="内置储库+芯吸")
    ax2.set_xlabel("循环周次")
    ax2.set_ylabel("容量保持率 / %")
    ax2.grid(True, color="0.86", lw=0.7)
    ax2.set_ylim(70, 102)
    ax2.legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, FIG / "f2.png")


def f3_mechanism():
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("图3  储库-芯吸路径的补液机理示意", pad=10, fontsize=12)

    box(ax, 0.6, 5.5, 2.5, 1.25, "1 电解液消耗", ["SEI副反应", "气体带液/局部贫液"], fc="0.94")
    box(ax, 4.0, 5.5, 2.6, 1.25, "2 局部干涸热点", ["端部/角部/厚度方向", "离子传输阻力上升"], fc="0.98")
    box(ax, 7.7, 5.5, 2.8, 1.25, "3 毛细压差", ["低润湿区吸液", "限流膜控制速率"], fc="0.94")
    box(ax, 4.0, 2.8, 2.6, 1.25, "4 被动补液", ["沿芯吸路径输运", "不依赖外部泵"], fc="0.98")
    box(ax, 7.7, 2.8, 2.8, 1.25, "5 极化降低", ["液相通道恢复", "温升和DCR受控"], fc="0.94")
    box(ax, 0.6, 2.8, 2.5, 1.25, "6 储库定容", ["V$_r$匹配寿命需求", "预留安全气隙"], fc="0.98")

    arrow(ax, 3.1, 6.12, 4.0, 6.12)
    arrow(ax, 6.6, 6.12, 7.7, 6.12)
    arrow(ax, 9.1, 5.5, 9.1, 4.05)
    arrow(ax, 7.7, 3.42, 6.6, 3.42)
    arrow(ax, 4.0, 3.42, 3.1, 3.42)
    arrow(ax, 1.85, 4.05, 1.85, 5.5)
    ax.text(6.0, 1.4, "功能目标：储库容量与寿命期消耗匹配，芯吸路径与干涸热点匹配，释放速率与后期贫液速率匹配。", ha="center", fontsize=9)
    save(fig, FIG / "f3.png")


def f4_process():
    fig, ax = plt.subplots(figsize=(6.4, 7.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("图4  储库与芯吸结构的设计制造流程", pad=10, fontsize=12)
    steps = [
        ("S1", "建立长时循环电解液消耗模型\n确定目标寿命与补偿液量 V$_r$"),
        ("S2", "通过仿真/拆解/CT确定贫液热点\n端部、角部或厚度方向低润湿区"),
        ("S3", "制备定容储库与限流膜\n设定孔径、破液阈值和释放速率"),
        ("S4", "布置芯吸路径并与热点接触\n避开焊接区和安全阀通道"),
        ("S5", "装配、注液、化成与浸润验证\n校验储库残液量和电芯安全余量"),
    ]
    flowchart(ax, steps, x=0.8, w=8.4, top=9.25, bh=1.3, gap=0.45)
    save(fig, FIG / "f4.png")


def f5_effect():
    x = np.linspace(0, 100, 200)
    dry_existing = 35 + 42 * np.exp(-((x - 18) / 18) ** 2) + 35 * np.exp(-((x - 85) / 16) ** 2)
    dry_invention = 20 + 14 * np.exp(-((x - 18) / 24) ** 2) + 12 * np.exp(-((x - 85) / 22) ** 2)
    dcr_existing = 100 + 0.0026 * (np.arange(0, 12001)) + 28 / (1 + np.exp(-(np.arange(0, 12001) - 7600) / 700))
    dcr_invention = 100 + 0.0019 * (np.arange(0, 12001)) + 11 / (1 + np.exp(-(np.arange(0, 12001) - 8800) / 900))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.4, 6.0), gridspec_kw={"height_ratios": [1, 1]})
    fig.suptitle("图5  贫液均化与DCR增长抑制效果示意", y=0.98, fontsize=12)
    ax1.plot(x, dry_existing, "--", color="0.45", lw=1.8, label="现有：端部/角部贫液")
    ax1.plot(x, dry_invention, "-", color="black", lw=2.1, label="本方案：芯吸补液后")
    ax1.set_xlabel("卷芯长度方向位置 / %")
    ax1.set_ylabel("贫液风险指数")
    ax1.grid(True, color="0.86", lw=0.7)
    ax1.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2)

    cycles = np.arange(0, 12001)
    ax2.plot(cycles, dcr_existing, "--", color="0.45", lw=1.8, label="现有电芯")
    ax2.plot(cycles, dcr_invention, "-", color="black", lw=2.1, label="内置储库+芯吸")
    ax2.set_xlabel("循环周次")
    ax2.set_ylabel("DCR 归一化 / %")
    ax2.grid(True, color="0.86", lw=0.7)
    ax2.legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, FIG / "f5.png")


def main():
    setup_font()
    f1_structure()
    f2_curves()
    f3_mechanism()
    f4_process()
    f5_effect()
    for p in sorted(FIG.glob("f*.png")):
        print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
