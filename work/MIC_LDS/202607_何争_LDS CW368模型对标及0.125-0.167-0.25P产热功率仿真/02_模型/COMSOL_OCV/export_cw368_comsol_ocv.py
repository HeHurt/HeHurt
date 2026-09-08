"""Export the calibrated CW368 graphite OCP tables for COMSOL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

TASK_ROOT = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW368模型对标及0.125-0.167-0.25P产热功率仿真"
)
MODEL_DIR = TASK_ROOT / "02_模型"
DEFAULT_OUTPUT_DIR = MODEL_DIR / "COMSOL_OCV"

if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from common import _load_profile  # noqa: E402
from paramsLDSCW368 import (  # noqa: E402
    NEGATIVE_OCP_STO_WARP_DELTA,
    NEGATIVE_OCP_STO_WARP_END,
    NEGATIVE_OCP_STO_WARP_SMOOTHING,
    NEGATIVE_OCP_STO_WARP_START,
    NEGATIVE_OCP_VOLTAGE_OFFSET_V,
)


def stoichiometry_warp(sto: np.ndarray) -> np.ndarray:
    """Return the calibrated OCP-table argument for physical graphite sto."""
    left = 1 / (
        1
        + np.exp(
            -(sto - NEGATIVE_OCP_STO_WARP_START)
            / NEGATIVE_OCP_STO_WARP_SMOOTHING
        )
    )
    right = 1 / (
        1
        + np.exp(
            (sto - NEGATIVE_OCP_STO_WARP_END)
            / NEGATIVE_OCP_STO_WARP_SMOOTHING
        )
    )
    return np.clip(
        sto + NEGATIVE_OCP_STO_WARP_DELTA * left * right,
        0,
        1,
    )


def write_dat(
    path: Path,
    columns: np.ndarray,
    column_names: str,
    description: str,
) -> None:
    """Write a COMSOL-readable whitespace-delimited interpolation table."""
    header = (
        f"% {description}\n"
        f"% {column_names}\n"
        "% Generated from paramsLDSCW368.py; dimensionless sto, voltage in V"
    )
    np.savetxt(
        path,
        columns,
        fmt="%.12g",
        delimiter=" ",
        header=header,
        comments="",
    )


def export_tables(output_dir: Path) -> None:
    """Export charge, discharge, warp, and audit tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    soc, charge_original = _load_profile("Gr_charge.csv")
    _, discharge_original = _load_profile("Gr_discharge.csv")
    effective_soc = stoichiometry_warp(soc)
    charge_calibrated = (
        np.interp(effective_soc, soc, charge_original)
        + NEGATIVE_OCP_VOLTAGE_OFFSET_V
    )
    discharge_calibrated = (
        np.interp(effective_soc, soc, discharge_original)
        + NEGATIVE_OCP_VOLTAGE_OFFSET_V
    )

    write_dat(
        output_dir / "CW368_Gr_charge_OCP_calibrated.dat",
        np.column_stack([soc, charge_calibrated]),
        "theta_neg  U_neg_charge_V",
        "CW368 calibrated graphite OCP for negative-electrode lithiation",
    )
    write_dat(
        output_dir / "CW368_Gr_discharge_OCP_calibrated.dat",
        np.column_stack([soc, discharge_calibrated]),
        "theta_neg  U_neg_discharge_V",
        "CW368 calibrated graphite OCP for negative-electrode delithiation",
    )
    write_dat(
        output_dir / "CW368_Gr_stoichiometry_warp.dat",
        np.column_stack([soc, effective_soc, effective_soc - soc]),
        "theta_physical  theta_effective  delta_theta",
        "CW368 graphite stoichiometry mapping used inside the calibrated OCP",
    )
    write_dat(
        output_dir / "CW368_Gr_OCP_original_vs_calibrated.dat",
        np.column_stack(
            [
                soc,
                effective_soc,
                charge_original,
                charge_calibrated,
                discharge_original,
                discharge_calibrated,
            ]
        ),
        (
            "theta_physical  theta_effective  "
            "U_charge_original_V  U_charge_calibrated_V  "
            "U_discharge_original_V  U_discharge_calibrated_V"
        ),
        "CW368 graphite OCP audit table",
    )

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    axes[0].plot(soc, charge_original, lw=1.1, label="Charge original")
    axes[0].plot(soc, charge_calibrated, lw=1.5, label="Charge calibrated")
    axes[0].plot(soc, discharge_original, lw=1.1, ls="--", label="Discharge original")
    axes[0].plot(
        soc,
        discharge_calibrated,
        lw=1.5,
        ls="--",
        label="Discharge calibrated",
    )
    axes[0].set_xlim(0, 0.85)
    axes[0].set_ylim(0, 0.5)
    axes[0].set_xlabel(r"Physical negative stoichiometry $\theta_n$")
    axes[0].set_ylabel("Negative OCP [V]")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("Graphite OCP")

    axes[1].plot(soc, effective_soc, lw=1.5, label=r"$f(\theta_n)$")
    axes[1].plot(soc, soc, color="#777777", ls="--", lw=1.0, label="Identity")
    axes[1].set_xlabel(r"Physical negative stoichiometry $\theta_n$")
    axes[1].set_ylabel(r"Effective OCP-table argument $f(\theta_n)$")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].set_title("Stoichiometry warp")
    fig.tight_layout()
    fig.savefig(
        output_dir / "CW368_Gr_OCP_original_vs_calibrated.png",
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    export_tables(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
