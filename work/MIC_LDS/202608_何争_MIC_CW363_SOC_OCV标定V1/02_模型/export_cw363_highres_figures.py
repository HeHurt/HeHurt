from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    import scienceplots  # noqa: F401
except ModuleNotFoundError:
    scienceplots = None


TASK_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = TASK_ROOT / "04_输出结果" / "20260904_101136_smooth_residual"
OUTPUT_DIR = RESULT_DIR / "高清图"


def configure_plot_style():
    if scienceplots is not None:
        plt.style.use(["science", "no-latex"])
    else:
        plt.style.use("default")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Calibri", "Microsoft YaHei", "Arial"],
            "font.size": 12,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "legend.fontsize": 11,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "axes.linewidth": 0.9,
        }
    )


def draw_panel(ax, curve, measured, temperature_c, direction):
    ax.plot(
        curve["soc_pct"],
        curve["baseline_pybamm_ocv_v"],
        color="#4C78A8",
        linewidth=2.0,
        linestyle="--",
        label="Original PyBaMM",
        zorder=2,
    )
    ax.plot(
        curve["soc_pct"],
        curve["smooth_calibrated_ocv_v"],
        color="#E45756",
        linewidth=2.6,
        label="Smooth calibrated",
        zorder=3,
    )
    ax.scatter(
        measured["soc_pct"],
        measured["measured_mean_ocv_v"],
        s=35,
        marker="o",
        facecolor="white",
        edgecolor="#222222",
        linewidth=1.2,
        label="Measured mean",
        zorder=5,
    )
    rmse_mv = ((measured["smooth_minus_mean_mv"] ** 2).mean()) ** 0.5
    ax.text(
        0.025,
        0.965,
        f"Anchor RMSE = {rmse_mv:.2f} mV",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11,
    )
    title_direction = "Charge" if direction == "charge" else "Discharge"
    ax.set_title(f"{temperature_c:.0f}°C {title_direction} Static SOC–OCV", pad=10)
    ax.set_xlim(-1, 101)
    ax.set_ylim(2.65, 3.55)
    ax.set_xticks(range(0, 101, 10))
    ax.set_xticks(range(0, 101, 5), minor=True)
    ax.set_yticks([2.65, 2.75, 2.85, 2.95, 3.05, 3.15, 3.25, 3.35, 3.45, 3.55])
    ax.grid(True, which="major", color="#D5D5D5", linewidth=0.7, alpha=0.75)
    ax.grid(True, which="minor", axis="x", color="#E8E8E8", linewidth=0.5, alpha=0.65)
    ax.set_xlabel("SOC (%)")
    ax.set_ylabel("OCV (V)")
    ax.legend(loc="lower right", frameon=False, ncol=1)


def main():
    configure_plot_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    curves = pd.read_csv(RESULT_DIR / "smooth_soc_ocv_1pct.csv")
    points = pd.read_csv(RESULT_DIR / "smooth_validation_points.csv")
    cases = [(25.0, "charge"), (25.0, "discharge"), (45.0, "charge"), (45.0, "discharge")]

    fig, axes = plt.subplots(2, 2, figsize=(16, 11), constrained_layout=True)
    for ax, (temperature_c, direction) in zip(axes.flat, cases):
        curve = curves[(curves["temperature_c"] == temperature_c) & (curves["direction"] == direction)]
        measured = points[(points["temperature_c"] == temperature_c) & (points["direction"] == direction)]
        draw_panel(ax, curve, measured, temperature_c, direction)
    fig.suptitle("CW363 Static SOC–OCV: Original PyBaMM vs Smooth Calibration", fontsize=19)
    combined_path = OUTPUT_DIR / "CW363_SOC_OCV_25C_45C_charge_discharge_highres.png"
    fig.savefig(combined_path, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    for temperature_c, direction in cases:
        curve = curves[(curves["temperature_c"] == temperature_c) & (curves["direction"] == direction)]
        measured = points[(points["temperature_c"] == temperature_c) & (points["direction"] == direction)]
        fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)
        draw_panel(ax, curve, measured, temperature_c, direction)
        output_path = OUTPUT_DIR / f"CW363_SOC_OCV_{temperature_c:.0f}C_{direction}_highres.png"
        fig.savefig(output_path, dpi=600, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    for path in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"{path.name}\t{path.stat().st_size}")


if __name__ == "__main__":
    main()
