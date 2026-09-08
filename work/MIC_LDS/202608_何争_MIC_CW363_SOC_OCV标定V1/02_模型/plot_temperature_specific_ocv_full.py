"""Plot the final 25/45 degC CW363 temperature-specific SOC-OCV curves."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


TASK_ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260827_140159_temperature_specific"
OUTPUT_DIR = TASK_ROOT / "04_输出结果" / RUN_ID
CURVE_PATH = OUTPUT_DIR / "temperature_specific_soc_ocv.csv"
MEASURED_PATH = OUTPUT_DIR / "measured_comparison.csv"
FIGURE_PATH = OUTPUT_DIR / "cw363_temperature_specific_soc_ocv_full.png"


def main():
    curves = pd.read_csv(CURVE_PATH)
    measured = pd.read_csv(MEASURED_PATH)
    colors = {25.0: "#0066CC", 45.0: "#E63946"}

    plt.style.use("science")
    plt.rcParams["font.family"] = ["Calibri", "Microsoft YaHei"]
    fig, ax = plt.subplots(figsize=(8.6, 5.7))
    for temperature_c in (25.0, 45.0):
        curve = curves[curves["temperature_c"] == temperature_c].sort_values("soc_pct")
        points = measured[measured["temperature_c"] == temperature_c].sort_values("soc_pct")
        ax.plot(
            curve["soc_pct"],
            curve["temperature_specific_ocv_v"],
            color=colors[temperature_c],
            linewidth=1.7,
            label=f"{temperature_c:.0f}°C Sim",
        )
        ax.scatter(
            points["soc_pct"],
            points["ocv_v"],
            s=27,
            facecolors="none",
            edgecolors=colors[temperature_c],
            linewidths=1.1,
            marker="o",
            zorder=3,
            label=f"{temperature_c:.0f}°C Exp",
        )

    voltage_min = min(curves["temperature_specific_ocv_v"].min(), measured["ocv_v"].min())
    voltage_max = max(curves["temperature_specific_ocv_v"].max(), measured["ocv_v"].max())
    margin = max(0.03, 0.06 * (voltage_max - voltage_min))
    ax.set_xlim(-5, 105)
    ax.set_ylim(voltage_min - margin, voltage_max + margin)
    ax.set_xlabel("SOC (%)")
    ax.set_ylabel("OCV (V)")
    ax.set_title("CW363 Discharge Static SOC-OCV Calibration")
    ax.grid(True, linestyle="--", linewidth=0.55, alpha=0.28)
    ax.legend(loc="upper left", frameon=False)
    fig.text(
        0.985,
        0.018,
        "45°C below 90% SOC: extrapolated from 25°C shape + entropy",
        ha="right",
        va="bottom",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIGURE_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(FIGURE_PATH)


if __name__ == "__main__":
    main()
