# -*- coding: utf-8 -*-
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib import font_manager

from fig_helpers import arrow, box, save


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


def f1_signal_acquisition():
    fig, ax = plt.subplots(figsize=(8.6, 5.3))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("图1  储能电芯电解液干涸早期诊断对象与信号采集示意", pad=10, fontsize=12)

    # Cell stack
    ax.add_patch(mp.Rectangle((0.8, 2.1), 3.5, 3.5, fill=False, lw=1.8, ec="black"))
    layers = [
        ("1 正极", 0.95, "0.82"),
        ("2 隔膜", 1.55, "1.0"),
        ("3 负极", 2.15, "0.72"),
        ("2 隔膜", 2.75, "1.0"),
        ("1 正极", 3.35, "0.82"),
    ]
    for label, x, gray in layers:
        ax.add_patch(mp.Rectangle((x, 2.35), 0.45, 3.0, facecolor=gray, edgecolor="black", lw=1.0))
        ax.text(x + 0.22, 5.55, label, ha="center", va="bottom", fontsize=8)
    ax.text(2.55, 1.75, "4 被诊断储能电芯", ha="center", fontsize=9, fontweight="bold")

    # Sensors and pulse
    ax.plot([0.8, 0.4], [5.25, 6.2], color="black", lw=1.2)
    ax.plot([4.3, 4.8], [5.25, 6.2], color="black", lw=1.2)
    ax.text(2.6, 6.45, "5 电压采样 V(t)", ha="center", fontsize=8.5)
    ax.add_patch(mp.Circle((4.0, 3.0), 0.18, fill=False, lw=1.3))
    ax.text(4.35, 3.0, "6 温度采样 T(t)", va="center", fontsize=8.5)
    ax.annotate(
        "7 诊断脉冲 I(t)",
        xy=(0.8, 1.55),
        xytext=(0.8, 0.8),
        arrowprops=dict(arrowstyle="-|>", lw=1.3),
        fontsize=8.5,
    )

    box(ax, 5.2, 4.9, 2.3, 1.6, "8 BMS/测试设备", ["电流/电压/温度", "容量与DCR片段"], fc="0.90")
    box(ax, 5.2, 2.1, 2.3, 1.6, "9 历史数据库", ["循环周次/SOC", "温度/倍率/SOH"], fc="0.96")
    box(ax, 8.4, 4.9, 2.7, 1.6, "10 模型预测单元", ["同工况预测 V,T", "输出基准曲线"], fc="0.90")
    box(ax, 8.4, 2.1, 2.7, 1.6, "11 残差诊断单元", ["残差形状识别", "干涸风险评分"], fc="0.96")

    arrow(ax, 4.55, 4.1, 5.2, 5.45)
    arrow(ax, 4.55, 2.8, 5.2, 2.9)
    arrow(ax, 7.5, 5.7, 8.4, 5.7)
    arrow(ax, 7.5, 2.9, 8.4, 2.9)
    arrow(ax, 9.75, 4.9, 9.75, 3.72)
    arrow(ax, 11.1, 2.9, 11.65, 2.9)
    ax.text(11.75, 2.9, "12 维护策略\n降额/复测/隔离", va="center", fontsize=8.5)

    ax.text(0.8, 0.25, "注：采样信号在相同温度、SOC、倍率窗口下与模型预测结果对齐。", fontsize=8.2)
    save(fig, FIG / "f1.png")


def f2_residual_shapes():
    soc = np.linspace(5, 95, 220)
    normal = 1.2 * np.sin((soc - 5) / 90 * np.pi) + 0.4
    sei = 2.0 + 0.02 * soc
    lam = 1.5 + 3.2 * np.exp(-((soc - 58) / 18) ** 2)
    plating = 1.1 + 5.8 / (1 + np.exp(-(soc - 78) / 5))
    dry = 2.2 + 0.025 * soc + 6.0 * np.exp(-((soc - 42) / 16) ** 2) + 4.2 * np.exp(-((soc - 82) / 11) ** 2)

    t = np.linspace(0, 900, 180)
    relax_normal = 2.5 * np.exp(-t / 120)
    relax_dry = 7.5 * np.exp(-t / 420) + 1.2 * np.exp(-t / 60)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.3, 6.0), sharex=False, gridspec_kw={"height_ratios": [1.25, 1]})
    fig.suptitle("图2  模型预测电压与实测电压残差形状对比", y=0.98, fontsize=12)

    ax1.plot(soc, normal, color="0.55", lw=1.6, ls=":", label="正常波动")
    ax1.plot(soc, sei, color="0.35", lw=1.5, ls="--", label="SEI增长")
    ax1.plot(soc, lam, color="0.15", lw=1.5, ls="-.", label="LAM")
    ax1.plot(soc, plating, color="0.25", lw=1.4, ls=(0, (4, 2, 1, 2)), label="锂析出")
    ax1.plot(soc, dry, color="black", lw=2.2, label="电解液干涸")
    ax1.set_ylabel("残差包络 |V模型 - V实测| / mV")
    ax1.set_xlabel("SOC / %")
    ax1.grid(True, color="0.86", lw=0.7)
    ax1.legend(ncol=3, fontsize=8, frameon=False, loc="upper left")
    ax1.annotate("中SOC扩散极化\n与高SOC传输受限同时增强", xy=(80, 11.0), xytext=(52, 13.2),
                 arrowprops=dict(arrowstyle="-|>", lw=1.1), fontsize=8.3)

    ax2.plot(t, relax_normal, color="0.45", lw=1.8, ls="--", label="现有正常/SEI主导")
    ax2.plot(t, relax_dry, color="black", lw=2.2, label="本方法识别的干涸长尾")
    ax2.set_xlabel("脉冲结束后的静置时间 / s")
    ax2.set_ylabel("弛豫残差 / mV")
    ax2.grid(True, color="0.86", lw=0.7)
    ax2.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax2.text(455, 4.2, "长尾残差 + 温升增量\n作为干涸判据组合", fontsize=8.5,
             bbox=dict(fc="white", ec="0.75", lw=0.8))
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, FIG / "f2.png")


def f3_mechanism_matrix():
    rows = ["SEI增长", "LAM", "锂析出", "电解液干涸"]
    cols = ["容量衰减", "DCR增长", "脉冲温升", "极化残差形状", "弛豫长尾"]
    levels = np.array([
        [2, 1, 1, 1, 0],
        [2, 0, 0, 2, 0],
        [1, 1, 1, 2, 1],
        [1, 2, 2, 2, 2],
    ])
    text = {0: "弱", 1: "中", 2: "强"}
    gray = {0: "1.0", 1: "0.82", 2: "0.55"}

    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("图3  老化机理与可观测特征映射表", pad=10, fontsize=12)

    x0, y0 = 2.15, 4.85
    cw, rh = 1.45, 0.82
    ax.text(1.05, y0, "机理", ha="center", va="center", fontweight="bold")
    for j, c in enumerate(cols):
        ax.add_patch(mp.Rectangle((x0 + j * cw, y0 - rh / 2), cw, rh, fill=False, lw=1.0))
        ax.text(x0 + (j + 0.5) * cw, y0, c, ha="center", va="center", fontsize=8.2, fontweight="bold")

    for i, r in enumerate(rows):
        yy = y0 - (i + 1) * rh
        ax.add_patch(mp.Rectangle((0.25, yy - rh / 2), 1.65, rh, fill=False, lw=1.0))
        ax.text(1.075, yy, r, ha="center", va="center", fontsize=8.8, fontweight="bold")
        for j in range(len(cols)):
            val = int(levels[i, j])
            ax.add_patch(mp.Rectangle((x0 + j * cw, yy - rh / 2), cw, rh, facecolor=gray[val], edgecolor="black", lw=0.9))
            ax.text(x0 + (j + 0.5) * cw, yy, text[val], ha="center", va="center", fontsize=8.8,
                    color="white" if val == 2 else "black", fontweight="bold")

    ax.text(0.35, 0.78, "诊断逻辑：容量衰减、DCR增长、脉冲温升与残差形状同时进入评分；\n"
                        "当 DCR 与温升强、容量衰减中等且存在残差长尾时，优先判定为电解液干涸趋势。",
            fontsize=8.6, va="top")
    save(fig, FIG / "f3.png")


def f4_system_architecture():
    fig, ax = plt.subplots(figsize=(8.6, 5.7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("图4  电解液干涸早期诊断系统架构", pad=10, fontsize=12)

    box(ax, 0.6, 5.4, 2.45, 1.35, "1 数据采集模块", ["V/I/T/SOC", "容量与DCR片段"], fc="0.93")
    box(ax, 0.6, 3.45, 2.45, 1.35, "2 片段筛选模块", ["静置/脉冲/循环", "温度倍率归一"], fc="0.98")
    box(ax, 0.6, 1.5, 2.45, 1.35, "3 设备接口", ["BMS/EMS", "测试柜/数据库"], fc="0.93")

    box(ax, 4.05, 5.4, 3.0, 1.35, "4 电化学-热模型", ["同工况预测 V模型,T模型", "更新SOH与温度边界"], fc="0.90")
    box(ax, 4.05, 3.45, 3.0, 1.35, "5 残差特征提取", ["eV(t,SOC)", "DCR分量/温升系数"], fc="0.98")
    box(ax, 4.05, 1.5, 3.0, 1.35, "6 机理区分模块", ["SEI/LAM/析锂/干涸", "置信度校验"], fc="0.90")

    box(ax, 8.25, 4.6, 3.0, 1.45, "7 干涸风险评分", ["Rdry=0-100", "绿/黄/橙/红分级"], fc="0.93")
    box(ax, 8.25, 2.25, 3.0, 1.45, "8 维护控制输出", ["降额/均衡/复测", "隔离与寿命策略"], fc="0.98")

    for y in [6.05, 4.1, 2.18]:
        arrow(ax, 3.05, y, 4.05, y)
    arrow(ax, 5.55, 5.4, 5.55, 4.8)
    arrow(ax, 5.55, 3.45, 5.55, 2.85)
    arrow(ax, 7.05, 4.1, 8.25, 5.3)
    arrow(ax, 7.05, 2.18, 8.25, 3.0)
    arrow(ax, 9.75, 4.6, 9.75, 3.7)
    arrow(ax, 8.25, 2.85, 3.05, 2.18, ls="--", color="0.35")
    ax.text(5.4, 0.65, "虚线表示维护动作回写至BMS/EMS或测试计划，形成闭环诊断。", ha="center", fontsize=8.6)
    save(fig, FIG / "f4.png")


def f5_effect_curve():
    cycles = np.arange(0, 1501)
    risk = 8 + 78 / (1 + np.exp(-(cycles - 930) / 115))
    dcr = 100 + 8 * (cycles / 1500) + 30 / (1 + np.exp(-(cycles - 1120) / 105))
    power_existing = 100 - 0.010 * cycles - 19 / (1 + np.exp(-(cycles - 1180) / 90))
    power_method = 100 - 0.008 * cycles - 8 / (1 + np.exp(-(cycles - 1240) / 130))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.3, 6.0), sharex=True, gridspec_kw={"height_ratios": [1.1, 1]})
    fig.suptitle("图5  提前预警与维护控制技术效果示意", y=0.98, fontsize=12)

    ax1.plot(cycles, risk, color="black", lw=2.1, label="干涸风险评分 Rdry")
    ax1.axhline(60, color="0.30", lw=1.4, ls="--", label="预警阈值")
    ax1.plot(cycles, (dcr - 100) * 1.8, color="0.50", lw=1.5, ls="-.", label="DCR异常等效信号")
    ax1.axvline(900, color="black", lw=1.0, ls=":")
    ax1.axvline(1160, color="0.35", lw=1.0, ls=":")
    ax1.text(760, 66, "本方法预警", fontsize=8.5, bbox=dict(fc="white", ec="0.7", lw=0.8))
    ax1.text(1110, 42, "传统DCR阈值\n较晚触发", fontsize=8.5, bbox=dict(fc="white", ec="0.7", lw=0.8))
    ax1.set_ylabel("风险/异常归一值")
    ax1.set_ylim(0, 100)
    ax1.grid(True, color="0.86", lw=0.7)
    ax1.legend(frameon=False, fontsize=8.2, loc="upper left")

    ax2.plot(cycles, power_existing, color="0.45", lw=1.8, ls="--", label="现有阈值维护")
    ax2.plot(cycles, power_method, color="black", lw=2.1, label="本方法闭环维护")
    ax2.set_xlabel("循环周次")
    ax2.set_ylabel("可用功率保持率 / %")
    ax2.set_ylim(58, 104)
    ax2.grid(True, color="0.86", lw=0.7)
    ax2.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax2.text(970, 88, "提前降额和复测\n降低极化热累积", fontsize=8.5,
             bbox=dict(fc="white", ec="0.7", lw=0.8))
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, FIG / "f5.png")


def main():
    setup_font()
    f1_signal_acquisition()
    f2_residual_shapes()
    f3_mechanism_matrix()
    f4_system_architecture()
    f5_effect_curve()
    for p in sorted(FIG.glob("f*.png")):
        print(p.name)


if __name__ == "__main__":
    main()
