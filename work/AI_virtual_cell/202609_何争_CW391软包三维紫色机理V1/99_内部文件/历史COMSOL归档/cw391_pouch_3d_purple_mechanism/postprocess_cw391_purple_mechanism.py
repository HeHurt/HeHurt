from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


WORKDIR = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\cw391_pouch_3d_purple_mechanism")
PLOTS_DIR = WORKDIR / "plots"
PLOTS_DIR.mkdir(exist_ok=True)


PARAMS = {
    "Lx": 0.086,
    "Ly": 0.682,
    "L_pos": 215.47213784610315e-6,
    "L_sep": 12.8e-6,
    "L_neg": 179.7082838568585e-6,
    "Q_nom_Ah": 3.03,
    "crate": 0.5,
    "t_end": 720.0,
    "TambK": 298.15,
    "tauT": 240.0,
    "TrefK": 298.15,
    "Ea_over_R": 4500.0,
    "sigma_center": 0.46,
    "tab_amp": 0.06,
    "j_center_amp_90": 0.34,
    "j_center_amp_full": 0.18,
    "dT_base_90": 1.6,
    "dT_center_90": 6.3,
    "dT_base_full": 1.1,
    "dT_center_full": 3.2,
    "high_soc_weight_90": 1.00,
    "high_soc_weight_full": 0.18,
    "dry_center_90": 0.22,
    "dry_center_full": 0.08,
    "risk_tau": 520.0,
    "risk_thr": 2.10,
    "risk_smooth": 0.055,
}


def fields(t: float, nx: int = 360, ny: int = 720) -> dict[str, np.ndarray]:
    p = PARAMS
    x = np.linspace(0.0, p["Lx"], nx)
    y = np.linspace(0.0, p["Ly"], ny)
    X, Y = np.meshgrid(x, y, indexing="xy")
    xn = (X - p["Lx"] / 2.0) / (p["Lx"] / 2.0)
    yn = (Y - p["Ly"] / 2.0) / (p["Ly"] / 2.0)
    rn = np.sqrt(xn**2 + yn**2)
    center_shape = np.exp(-(rn**2) / (2.0 * p["sigma_center"] ** 2))
    tab_shape = 1.0 + p["tab_amp"] * (Y / p["Ly"] - 0.5)
    thermal_ramp = 1.0 - np.exp(-t / p["tauT"])

    t90 = p["TambK"] + thermal_ramp * (p["dT_base_90"] + p["dT_center_90"] * center_shape)
    tfull = p["TambK"] + thermal_ramp * (p["dT_base_full"] + p["dT_center_full"] * center_shape)
    arr90 = np.exp(p["Ea_over_R"] * (1.0 / p["TrefK"] - 1.0 / t90))
    arrfull = np.exp(p["Ea_over_R"] * (1.0 / p["TrefK"] - 1.0 / tfull))

    jshape90 = (1.0 + p["j_center_amp_90"] * center_shape) * tab_shape
    jshapefull = (1.0 + p["j_center_amp_full"] * center_shape) * tab_shape
    wet90 = 1.0 + p["dry_center_90"] * center_shape
    wetfull = 1.0 + p["dry_center_full"] * center_shape

    xli90 = 0.955 + 0.025 * center_shape * tab_shape
    xlifull = 0.600 + 0.012 * center_shape * tab_shape
    soc_gate90 = 1.0 / (1.0 + np.exp(-(xli90 - 0.90) / 0.018))
    soc_gatefull = 1.0 / (1.0 + np.exp(-(xlifull - 0.90) / 0.018))

    risk_rate90 = (
        p["high_soc_weight_90"]
        * arr90
        * jshape90
        * wet90
        * (0.85 + 0.15 * soc_gate90)
        / p["risk_tau"]
    )
    risk_ratefull = (
        p["high_soc_weight_full"]
        * arrfull
        * jshapefull
        * wetfull
        * (0.85 + 0.15 * soc_gatefull)
        / p["risk_tau"]
    )
    risk90 = risk_rate90 * t
    riskfull = risk_ratefull * t
    mask90 = 0.5 * (1.0 + np.tanh((risk90 - p["risk_thr"]) / p["risk_smooth"]))
    maskfull = 0.5 * (1.0 + np.tanh((riskfull - p["risk_thr"]) / p["risk_smooth"]))

    return {
        "x": x,
        "y": y,
        "X": X,
        "Y": Y,
        "rn": rn,
        "center_shape": center_shape,
        "T90K": t90,
        "TfullK": tfull,
        "xLi90": xli90,
        "xLifull": xlifull,
        "risk90": risk90,
        "riskfull": riskfull,
        "mask90": mask90,
        "maskfull": maskfull,
    }


def radial_profile(rn: np.ndarray, value: np.ndarray, bins: np.ndarray) -> np.ndarray:
    out = np.full(len(bins) - 1, np.nan)
    for i in range(len(bins) - 1):
        sel = (rn >= bins[i]) & (rn < bins[i + 1])
        if np.any(sel):
            out[i] = float(np.mean(value[sel]))
    return out


def summarize(final: dict[str, np.ndarray]) -> dict[str, float]:
    p = PARAMS
    center_mask = 0.5 * (1.0 + np.tanh((0.45 - final["rn"]) / 0.04))
    edge_mask = 0.5 * (1.0 + np.tanh((final["rn"] - 0.82) / 0.04))
    center = lambda a: float(np.sum(a * center_mask) / np.sum(center_mask))
    edge = lambda a: float(np.sum(a * edge_mask) / np.sum(edge_mask))
    ah = p["crate"] * p["Q_nom_Ah"] * p["t_end"] / 3600.0
    return {
        "same_Ah_throughput": ah,
        "avg_risk_90": float(np.mean(final["risk90"])),
        "avg_risk_reference": float(np.mean(final["riskfull"])),
        "risk_ratio_90_to_reference": float(np.mean(final["risk90"]) / np.mean(final["riskfull"])),
        "purple_area_90_pct": float(np.mean(final["mask90"]) * 100.0),
        "purple_area_reference_pct": float(np.mean(final["maskfull"]) * 100.0),
        "center_edge_risk_ratio_90": center(final["risk90"]) / edge(final["risk90"]),
        "center_edge_risk_ratio_reference": center(final["riskfull"]) / edge(final["riskfull"]),
        "center_temp_90_C": center(final["T90K"]) - 273.15,
        "edge_temp_90_C": edge(final["T90K"]) - 273.15,
        "center_temp_reference_C": center(final["TfullK"]) - 273.15,
        "edge_temp_reference_C": edge(final["TfullK"]) - 273.15,
        "center_graphite_lithiation_90": center(final["xLi90"]),
        "edge_graphite_lithiation_90": edge(final["xLi90"]),
        "center_graphite_lithiation_reference": center(final["xLifull"]),
        "edge_graphite_lithiation_reference": edge(final["xLifull"]),
    }


def save_metrics(metrics: dict[str, float]) -> None:
    with (WORKDIR / "metrics_recomputed.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in metrics.items():
            writer.writerow([key, f"{value:.12g}"])


def plot_maps(final: dict[str, np.ndarray]) -> None:
    extent = [0, PARAMS["Ly"] * 1000, 0, PARAMS["Lx"] * 1000]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.2), constrained_layout=True)
    cases = [
        ("90-100% SOC", "risk90", "mask90", "T90K", "xLi90"),
        ("Reference", "riskfull", "maskfull", "TfullK", "xLifull"),
    ]
    for row, (label, risk_key, mask_key, temp_key, xli_key) in enumerate(cases):
        risk = axes[row, 0].imshow(final[risk_key], origin="lower", extent=extent, aspect="auto", cmap="magma")
        axes[row, 0].contour(
            final["Y"] * 1000,
            final["X"] * 1000,
            final[mask_key],
            levels=[0.5],
            colors="cyan",
            linewidths=1.1,
        )
        axes[row, 0].set_title(f"{label} risk")
        fig.colorbar(risk, ax=axes[row, 0], label="risk index")

        temp = axes[row, 1].imshow(final[temp_key] - 273.15, origin="lower", extent=extent, aspect="auto", cmap="inferno")
        axes[row, 1].set_title(f"{label} temperature")
        fig.colorbar(temp, ax=axes[row, 1], label="degC")

        xli = axes[row, 2].imshow(final[xli_key], origin="lower", extent=extent, aspect="auto", cmap="viridis")
        axes[row, 2].set_title(f"{label} graphite lithiation proxy")
        fig.colorbar(xli, ax=axes[row, 2], label="x in LixC6 proxy")

    for ax in axes.ravel():
        ax.set_xlabel("length y / mm")
        ax.set_ylabel("width x / mm")
    fig.savefig(PLOTS_DIR / "field_maps.png", dpi=220)
    plt.close(fig)


def plot_profiles(final: dict[str, np.ndarray]) -> None:
    bins = np.linspace(0.0, 1.15, 70)
    rmid = 0.5 * (bins[:-1] + bins[1:])
    rows = []
    for name, arr in [
        ("risk_90", final["risk90"]),
        ("risk_reference", final["riskfull"]),
        ("temperature_90_C", final["T90K"] - 273.15),
        ("temperature_reference_C", final["TfullK"] - 273.15),
        ("graphite_lithiation_90", final["xLi90"]),
        ("graphite_lithiation_reference", final["xLifull"]),
    ]:
        prof = radial_profile(final["rn"], arr, bins)
        rows.append((name, prof))

    with (WORKDIR / "radial_profile.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["r_normalized"] + [name for name, _ in rows])
        for i, r in enumerate(rmid):
            writer.writerow([f"{r:.6f}"] + [f"{prof[i]:.12g}" for _, prof in rows])

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.7), constrained_layout=True)
    axes[0].plot(rmid, rows[0][1], label="90-100% SOC", lw=2)
    axes[0].plot(rmid, rows[1][1], label="Reference", lw=2)
    axes[0].axhline(PARAMS["risk_thr"], color="k", ls="--", lw=1)
    axes[0].set_title("Risk radial profile")
    axes[0].set_xlabel("normalized radius")
    axes[0].set_ylabel("risk index")
    axes[0].legend()

    axes[1].plot(rmid, rows[2][1], label="90-100% SOC", lw=2)
    axes[1].plot(rmid, rows[3][1], label="Reference", lw=2)
    axes[1].set_title("Temperature radial profile")
    axes[1].set_xlabel("normalized radius")
    axes[1].set_ylabel("degC")
    axes[1].legend()

    axes[2].plot(rmid, rows[4][1], label="90-100% SOC", lw=2)
    axes[2].plot(rmid, rows[5][1], label="Reference", lw=2)
    axes[2].set_title("Graphite lithiation proxy")
    axes[2].set_xlabel("normalized radius")
    axes[2].set_ylabel("x in LixC6 proxy")
    axes[2].legend()
    fig.savefig(PLOTS_DIR / "radial_profiles.png", dpi=220)
    plt.close(fig)


def plot_timeseries() -> None:
    times = np.linspace(0.0, PARAMS["t_end"], 121)
    dose90 = []
    dosefull = []
    area90 = []
    areafull = []
    for t in times:
        f = fields(t, nx=180, ny=360)
        dose90.append(float(np.mean(f["risk90"])))
        dosefull.append(float(np.mean(f["riskfull"])))
        area90.append(float(np.mean(f["mask90"]) * 100.0))
        areafull.append(float(np.mean(f["maskfull"]) * 100.0))

    with (WORKDIR / "timeseries_recomputed.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["time_s", "avg_risk_90", "avg_risk_reference", "purple_area_90_pct", "purple_area_reference_pct"])
        for row in zip(times, dose90, dosefull, area90, areafull):
            writer.writerow([f"{v:.12g}" for v in row])

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), constrained_layout=True)
    axes[0].plot(times, dose90, label="90-100% SOC", lw=2)
    axes[0].plot(times, dosefull, label="Reference", lw=2)
    axes[0].axhline(PARAMS["risk_thr"], color="k", ls="--", lw=1)
    axes[0].set_xlabel("time / s")
    axes[0].set_ylabel("average risk index")
    axes[0].set_title("Average risk accumulation")
    axes[0].legend()

    axes[1].plot(times, area90, label="90-100% SOC", lw=2)
    axes[1].plot(times, areafull, label="Reference", lw=2)
    axes[1].set_xlabel("time / s")
    axes[1].set_ylabel("purple-risk area / %")
    axes[1].set_title("Thresholded area growth")
    axes[1].legend()
    fig.savefig(PLOTS_DIR / "timeseries.png", dpi=220)
    plt.close(fig)


def generate_report(metrics: dict[str, float]) -> Path:
    try:
        from docx import Document
        from docx.shared import Inches
    except Exception:
        report_md = WORKDIR / "CW391_pouch_purple_mechanism_report.md"
        report_md.write_text(report_text(metrics), encoding="utf-8")
        return report_md

    doc = Document()
    doc.add_heading("CW391软包3D紫斑机制验证模型", level=0)
    doc.add_paragraph(
        "模型类型：COMSOL 6.4 Java 生成的3D机制代理模型。"
        "该模型不是完整3D P2D老化模型，而是用CW391几何和LFP/Gr设计参数，"
        "把高SOC停留、中心热积累、局部电流密度放大和石墨嵌锂差异组合为可计算空间场。"
    )
    doc.add_heading("关键结论", level=1)
    bullets = [
        f"同等容量通量为 {metrics['same_Ah_throughput']:.3f} Ah。",
        f"90-100% SOC平均风险指数为 {metrics['avg_risk_90']:.3f}，参考工况为 {metrics['avg_risk_reference']:.3f}，倍率为 {metrics['risk_ratio_90_to_reference']:.2f}x。",
        f"紫斑proxy面积：90-100% SOC为 {metrics['purple_area_90_pct']:.2f}%，参考工况为 {metrics['purple_area_reference_pct']:.2f}%。",
        f"90-100% SOC中心/边缘风险比为 {metrics['center_edge_risk_ratio_90']:.2f}，参考工况为 {metrics['center_edge_risk_ratio_reference']:.2f}。",
        f"90-100% SOC中心温度约 {metrics['center_temp_90_C']:.2f} degC，边缘约 {metrics['edge_temp_90_C']:.2f} degC。",
    ]
    for item in bullets:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("模型假设", level=1)
    assumptions = [
        "活性区尺寸取CW391：86 mm x 682 mm；厚度取正极、隔膜、负极厚度之和。",
        "90-100% SOC工况的高SOC停留权重设为1.0；参考工况高SOC停留权重设为0.18。",
        "紫斑proxy由Arrhenius温度项、局部电流密度项、中心润湿/干涸放大项、石墨高嵌锂门控项共同决定。",
        "中心到边缘的圈状扩散来自中心热积累和中心局部副反应剂量更高，而非极耳方向主导梯度。",
    ]
    for item in assumptions:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("图形结果", level=1)
    for image, caption in [
        ("field_maps.png", "图1  风险、温度和石墨嵌锂proxy的极片面分布。"),
        ("radial_profiles.png", "图2  中心到边缘的径向profile。"),
        ("timeseries.png", "图3  平均风险和阈值面积的时间演化。"),
    ]:
        doc.add_paragraph(caption)
        doc.add_picture(str(PLOTS_DIR / image), width=Inches(6.2))

    doc.add_heading("使用限制", level=1)
    doc.add_paragraph(
        "该结果用于定位机制优先级和指导下一步建模。若要用于定量预测，"
        "需要用实测温升、局部拆解表征、OCV/GITT参数和夹具压力/润湿分布对proxy参数进行校准。"
    )
    out = WORKDIR / "CW391_pouch_purple_mechanism_report.docx"
    doc.save(out)
    return out


def report_text(metrics: dict[str, float]) -> str:
    return (
        "# CW391 pouch purple mechanism report\n\n"
        f"- same Ah throughput: {metrics['same_Ah_throughput']:.3f} Ah\n"
        f"- 90-100% average risk: {metrics['avg_risk_90']:.3f}\n"
        f"- reference average risk: {metrics['avg_risk_reference']:.3f}\n"
        f"- risk ratio: {metrics['risk_ratio_90_to_reference']:.2f}x\n"
        f"- 90-100% purple proxy area: {metrics['purple_area_90_pct']:.2f}%\n"
        f"- reference purple proxy area: {metrics['purple_area_reference_pct']:.2f}%\n"
    )


def main() -> None:
    final = fields(PARAMS["t_end"])
    metrics = summarize(final)
    save_metrics(metrics)
    plot_maps(final)
    plot_profiles(final)
    plot_timeseries()
    report = generate_report(metrics)
    print(f"Report: {report}")
    print(f"Risk ratio 90/reference: {metrics['risk_ratio_90_to_reference']:.3f}")
    print(f"Purple area 90/reference: {metrics['purple_area_90_pct']:.3f}% / {metrics['purple_area_reference_pct']:.3f}%")


if __name__ == "__main__":
    main()
