from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


TASK = Path(r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V1")
RESULT = TASK / "99_内部文件" / "JSON" / "pouch_v8_100N_matched_rebound_comparison.json"
DATA = TASK / "99_内部文件" / "中间数据" / "软包V8_100N呼吸前后匹配对照"
PLOTS = TASK / "04_输出结果" / "图表"


plt.rcParams.update({
    "font.family": ["Calibri", "Microsoft YaHei", "DejaVu Sans"],
    "font.size": 10,
    "axes.unicode_minus": False,
    "figure.dpi": 150,
})


def arr(case, key):
    return np.asarray(case["series"][key], dtype=float)


def save(fig, name):
    path = PLOTS / name
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def read_field(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return (
        np.asarray([float(row["x"]) for row in rows]) / 1000.0,
        np.asarray([float(row["y"]) for row in rows]),
        np.asarray([float(row["value"]) for row in rows]),
    )


def main():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    no_breath = payload["cases"]["pressure_only_100N"]
    breathing = payload["cases"]["pressure_breathing_100N"]
    colors = {"no": "#5b6472", "yes": "#d62728"}
    PLOTS.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.4))
    for case, color, label in (
        (no_breath, colors["no"], "100 N，无呼吸"),
        (breathing, colors["yes"], "100 N，有呼吸"),
    ):
        axes[0].plot(arr(case, "time_s") / 3600, arr(case, "voltage_V"), color=color, lw=1.8, label=label)
        tau = (arr(case, "time_s") - case["metrics"]["discharge_end_time_s"]) / 60
        mask = (tau >= -8) & (tau <= 55)
        axes[1].plot(tau[mask], arr(case, "voltage_V")[mask], color=color, lw=2.0, label=label)
    axes[0].axhline(3.65, color="#dc2626", ls=":", lw=1)
    axes[0].axhline(2.50, color="#2563eb", ls=":", lw=1)
    axes[0].set(xlabel="时间 (h)", ylabel="负载端电压 (V)", title="完整 0.5C 充电—静置—放电")
    axes[0].legend(frameon=False)
    axes[1].axvline(0, color="#111827", ls="--", lw=1)
    axes[1].set(xlabel="相对放电截止时间 (min)", ylabel="负载端电压 (V)", title="放电截止后的电压回弹")
    axes[1].legend(frameon=False)
    text = (
        f"无呼吸：{no_breath['metrics']['total_rebound_mV']:.2f} mV\n"
        f"有呼吸：{breathing['metrics']['total_rebound_mV']:.2f} mV\n"
        f"差值：+{breathing['metrics']['total_rebound_mV']-no_breath['metrics']['total_rebound_mV']:.2f} mV"
    )
    axes[1].text(0.98, 0.05, text, transform=axes[1].transAxes, ha="right", va="bottom",
                 bbox={"facecolor": "white", "edgecolor": "#d1d5db", "alpha": 0.9})
    for ax in axes:
        ax.grid(alpha=0.25, ls="--")
    fig.suptitle("软包 V8：同为 100 N 时的呼吸机制匹配对照", fontweight="bold")
    save(fig, "08_软包V8_100N呼吸前后电压回弹匹配对照.png")

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0))
    t_h = arr(breathing, "time_s") / 3600
    axes[0, 0].plot(t_h, arr(breathing, "pressure_neg_kPa"), color="#111827", label="负极平均")
    axes[0, 0].plot(t_h, arr(breathing, "pressure_sep_kPa"), color="#2563eb", label="隔膜平均")
    axes[0, 0].plot(t_h, arr(breathing, "pressure_pos_kPa"), color="#dc2626", label="正极平均")
    axes[0, 0].axhline(22.361, color="#6b7280", ls="--", lw=1, label="100 N名义压力")
    axes[0, 0].set(title="厚度压缩压力（有呼吸）", xlabel="时间 (h)", ylabel="平均压力 (kPa)")
    axes[0, 0].legend(frameon=False, ncol=2)

    axes[0, 1].plot(t_h, arr(breathing, "pressure_stack_max_kPa"), color="#7c3aed", label="最大厚度压缩压力")
    axes[0, 1].plot(t_h, arr(breathing, "mises_stack_max_kPa"), color="#f59e0b", label="最大 von Mises")
    axes[0, 1].set(title="局部峰值：压缩压力与等效应力应分开看", xlabel="时间 (h)", ylabel="局部峰值 (kPa)")
    axes[0, 1].legend(frameon=False)

    soc = 100 * arr(breathing, "actual_SOC")
    axes[1, 0].plot(soc, arr(breathing, "porosity_neg"), color="#111827", label="负极")
    axes[1, 0].plot(soc, arr(breathing, "porosity_sep"), color="#2563eb", label="隔膜")
    axes[1, 0].plot(soc, arr(breathing, "porosity_pos"), color="#dc2626", label="正极")
    axes[1, 0].set(title="压力反馈后的平均孔隙率", xlabel="实际 SOC (%)", ylabel="孔隙率")
    axes[1, 0].legend(frameon=False)

    axes[1, 1].plot(t_h, arr(breathing, "relative_thickness_change_um"), color="#d62728", label="电芯厚度变化")
    ax2 = axes[1, 1].twinx()
    ax2.plot(t_h, arr(breathing, "breathing_neg_pct"), color="#2563eb", ls="--", label="石墨呼吸应变")
    axes[1, 1].set(title="厚度响应与石墨呼吸", xlabel="时间 (h)", ylabel="相对厚度变化 (μm)")
    ax2.set_ylabel("石墨呼吸应变 (%)", color="#2563eb")
    lines = axes[1, 1].lines + ax2.lines
    axes[1, 1].legend(lines, [line.get_label() for line in lines], frameon=False)
    for ax in axes.flat:
        ax.grid(alpha=0.25, ls="--")
    fig.suptitle("软包 V8：100 N + 嵌锂呼吸的力—孔隙率反馈", fontweight="bold")
    fig.tight_layout()
    save(fig, "09_软包V8_100N力学压力孔隙率诊断.png")

    maps = [
        ("field_pressure_only_100N_pressure_peak_pressure_thickness.csv", "无呼吸：厚度压缩压力", "viridis", "kPa"),
        ("field_pressure_breathing_100N_pressure_peak_pressure_thickness.csv", "有呼吸：厚度压缩压力", "viridis", "kPa"),
        ("field_pressure_breathing_100N_pressure_peak_mises.csv", "有呼吸：von Mises 等效应力", "magma", "kPa"),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(12.2, 7.8), sharex=True)
    for ax, (filename, title, cmap, unit) in zip(axes, maps):
        x_mm, y_um, values = read_field(filename)
        artist = ax.scatter(x_mm, y_um, c=values, s=2.2, cmap=cmap, linewidths=0, rasterized=True)
        ax.set_ylabel("厚度 y (μm)")
        ax.set_title(title, loc="left", fontweight="bold")
        cbar = fig.colorbar(artist, ax=ax, pad=0.012, aspect=24)
        cbar.set_label(unit)
    axes[-1].set_xlabel("电芯长度 x (mm)")
    fig.suptitle(
        "软包二维截面的压力/应力场（厚度方向为显示需要大幅放大，非等比例）\n"
        f"有呼吸峰值出现在 SOC {breathing['metrics']['pressure_peak_SOC_pct']:.1f}%：平均压力与局部峰值不可混用",
        fontweight="bold",
    )
    fig.tight_layout()
    save(fig, "10_软包V8_厚度压力与vonMises场分开展示.png")


main()
