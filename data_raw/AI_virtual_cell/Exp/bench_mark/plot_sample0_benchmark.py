from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PNG = BASE_DIR / "sample0_benchmark_plot.png"
OUTPUT_CSV = BASE_DIR / "sample0_extracted_all.csv"

GROUP_ORDER = ["D组", "G组", "L组", "A组", "H组", "E组", "M组"]
RATE_LABELS = {
    0: "25°C-0.5P",
    1: "25°C-1P",
    2: "25°C-2P",
}
COLORS = {
    "D组": "black",
    "G组": "red",
    "L组": "#20b7ff",
    "A组": "#19a35b",
    "H组": "#b45a10",
    "E组": "#224ccf",
    "M组": "#d764ea",
}


def load_curve(file_path: Path) -> np.ndarray:
    return np.loadtxt(file_path)


def collect_sample0_files() -> dict[int, list[tuple[str, Path]]]:
    grouped_files: dict[int, list[tuple[str, Path]]] = {0: [], 1: [], 2: []}
    for group_name in GROUP_ORDER:
        for rate_index in grouped_files:
            file_name = f"{group_name}_sample0_{rate_index}.dat"
            file_path = BASE_DIR / file_name
            if not file_path.exists():
                raise FileNotFoundError(f"Missing benchmark file: {file_path}")
            grouped_files[rate_index].append((group_name, file_path))
    return grouped_files


def export_combined_csv(grouped_files: dict[int, list[tuple[str, Path]]]) -> None:
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["rate_index", "rate_label", "group_name", "file_name", "x", "voltage"])
        for rate_index, file_entries in grouped_files.items():
            for group_name, file_path in file_entries:
                curve = load_curve(file_path)
                for x_value, voltage in curve:
                    writer.writerow(
                        [
                            rate_index,
                            RATE_LABELS[rate_index],
                            group_name,
                            file_path.name,
                            float(x_value),
                            float(voltage),
                        ]
                    )


def plot_grouped_curves(grouped_files: dict[int, list[tuple[str, Path]]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 3, figsize=(20.48, 7.68), dpi=100)

    for subplot_index, rate_index in enumerate(sorted(grouped_files)):
        axis = axes[subplot_index]
        for group_name, file_path in grouped_files[rate_index]:
            curve = load_curve(file_path)
            axis.plot(
                curve[:, 0],
                curve[:, 1],
                label=f"{group_name}_sample0_{rate_index}",
                color=COLORS[group_name],
                linewidth=2.4,
            )

        axis.set_title(RATE_LABELS[rate_index], fontsize=24, fontweight="bold", pad=10)
        axis.grid(axis="y", linestyle="--", linewidth=1.2, alpha=0.55)
        axis.tick_params(axis="both", labelsize=14, width=1.2)
        axis.set_ylim(2.5, 3.7)
        for spine in axis.spines.values():
            spine.set_linewidth(1.5)

        legend = axis.legend(
            loc="lower left",
            bbox_to_anchor=(0.16, 0.03),
            fontsize=18,
            frameon=False,
            handlelength=2.7,
        )
        for text in legend.get_texts():
            text.set_fontweight("bold")

    fig.tight_layout(w_pad=3)
    fig.savefig(OUTPUT_PNG, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    grouped_files = collect_sample0_files()
    export_combined_csv(grouped_files)
    plot_grouped_curves(grouped_files)
    print(f"Saved figure to: {OUTPUT_PNG}")
    print(f"Saved combined csv to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()