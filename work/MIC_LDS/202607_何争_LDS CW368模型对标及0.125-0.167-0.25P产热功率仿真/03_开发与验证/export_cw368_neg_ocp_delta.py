"""Export the CW368 negative-OCP *delta* (calibrated - original) table for COMSOL.

The two baseline OCP files (Gr_charge.csv, Gr_discharge.csv) already exist in
02_模型/. The CW368 calibration applies a stoichiometry warp + voltage bias to
both lithiation and delithiation baselines. This script exports the *change*
induced by that calibration so it can be imported into COMSOL as a separate
interpolation table (useful for sanity-checking that the warp only acts in
the 0.21-0.60 region).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

TASK_ROOT = Path(
    r"C:\HithiumSSD\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW368模型对标及0.125-0.167-0.25P产热功率仿真"
)
MODEL_DIR = TASK_ROOT / "02_模型"
OUTPUT_DIR = MODEL_DIR / "COMSOL_OCV"

for p in [MODEL_DIR, TASK_ROOT / "02_模型", MODEL_DIR.parent]:
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from common import _load_profile  # noqa: E402
from paramsLDSCW368 import (  # noqa: E402
    NEGATIVE_OCP_STO_WARP_DELTA,
    NEGATIVE_OCP_STO_WARP_END,
    NEGATIVE_OCP_STO_WARP_SMOOTHING,
    NEGATIVE_OCP_STO_WARP_START,
    NEGATIVE_OCP_VOLTAGE_OFFSET_V,
)


def warp(sto: np.ndarray) -> np.ndarray:
    left = 1.0 / (
        1.0 + np.exp(-(sto - NEGATIVE_OCP_STO_WARP_START) / NEGATIVE_OCP_STO_WARP_SMOOTHING)
    )
    right = 1.0 / (
        1.0 + np.exp((sto - NEGATIVE_OCP_STO_WARP_END) / NEGATIVE_OCP_STO_WARP_SMOOTHING)
    )
    return np.clip(sto + NEGATIVE_OCP_STO_WARP_DELTA * left * right, 0.0, 1.0)


def write_dat(path: Path, cols: np.ndarray, column_names: str, description: str) -> None:
    header = (
        f"% {description}\n"
        f"% {column_names}\n"
        "% Generated from paramsLDSCW368.py; dimensionless sto, voltage in V"
    )
    np.savetxt(path, cols, fmt="%.12g", delimiter=" ", header=header, comments="")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    soc, charge_original = _load_profile("Gr_charge.csv")
    _, discharge_original = _load_profile("Gr_discharge.csv")
    effective_soc = warp(soc)

    charge_calibrated = (
        np.interp(effective_soc, soc, charge_original) + NEGATIVE_OCP_VOLTAGE_OFFSET_V
    )
    discharge_calibrated = (
        np.interp(effective_soc, soc, discharge_original) + NEGATIVE_OCP_VOLTAGE_OFFSET_V
    )

    delta_charge = charge_calibrated - charge_original
    delta_discharge = discharge_calibrated - discharge_original

    # ----- .dat: 4 columns (theta, delta_V_charge, delta_V_discharge, effective_theta) -----
    cols = np.column_stack(
        [soc, delta_charge, delta_discharge, effective_soc]
    )
    write_dat(
        OUTPUT_DIR / "CW368_NegOCP_delta.dat",
        cols,
        "theta_neg  delta_U_charge_V  delta_U_discharge_V  theta_effective",
        "CW368 negative-OCP delta (calibrated - original) and effective sto",
    )

    # ----- .dat: compact, screenshot-style 2-column format (charge delta only) -----
    compact_charge = np.column_stack([soc, delta_charge])
    write_dat(
        OUTPUT_DIR / "CW368_NegOCP_delta_charge_2col.dat",
        compact_charge,
        "t  f(t)_delta_charge_V",
        "CW368 negative-OCP delta for lithiation (compact 2-column, COMSOL 局部表格式)",
    )
    compact_discharge = np.column_stack([soc, delta_discharge])
    write_dat(
        OUTPUT_DIR / "CW368_NegOCP_delta_discharge_2col.dat",
        compact_discharge,
        "t  f(t)_delta_discharge_V",
        "CW368 negative-OCP delta for delithiation (compact 2-column, COMSOL 局部表格式)",
    )

    # ----- figure: visualize the warp + delta -----
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    axes[0].plot(soc, effective_soc, lw=1.5, label=r"$f(\theta_n)$")
    axes[0].plot(soc, soc, color="#777777", ls="--", lw=1.0, label="Identity")
    axes[0].axvspan(0.212309, 0.6, color="#FAC775", alpha=0.18, label="warp window")
    axes[0].set_xlabel(r"Physical negative stoichiometry $\theta_n$")
    axes[0].set_ylabel(r"Effective OCP-table argument $f(\theta_n)$")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("Stoichiometry warp")

    axes[1].plot(soc, delta_charge * 1000.0, lw=1.5, label="Δ charge")
    axes[1].plot(soc, delta_discharge * 1000.0, lw=1.5, ls="--", label="Δ discharge")
    axes[1].axvspan(0.212309, 0.6, color="#FAC775", alpha=0.18, label="warp window")
    axes[1].axhline(NEGATIVE_OCP_VOLTAGE_OFFSET_V * 1000.0, color="#777777", ls=":", lw=1.0,
                    label=f"bias = {NEGATIVE_OCP_VOLTAGE_OFFSET_V*1000:.2f} mV")
    axes[1].set_xlabel(r"Physical negative stoichiometry $\theta_n$")
    axes[1].set_ylabel(r"$\Delta U_{neg}$  [mV]")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].set_title("OCP delta (calibrated − original)")

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "CW368_NegOCP_delta.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # report key markers
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"rows = {len(soc)}")
    print(f"max |delta charge|  = {np.max(np.abs(delta_charge))*1000:.3f} mV at theta = {soc[np.argmax(np.abs(delta_charge))]:.4f}")
    print(f"max |delta discharge| = {np.max(np.abs(delta_discharge))*1000:.3f} mV at theta = {soc[np.argmax(np.abs(delta_discharge))]:.4f}")
    print(f"theta_endpoints warp: f({soc[0]:.4f})={effective_soc[0]:.4f}, f({soc[-1]:.4f})={effective_soc[-1]:.4f}")
    print(f"warp window: [{NEGATIVE_OCP_STO_WARP_START}, {NEGATIVE_OCP_STO_WARP_END}], delta={NEGATIVE_OCP_STO_WARP_DELTA}, smoothing={NEGATIVE_OCP_STO_WARP_SMOOTHING}")


if __name__ == "__main__":
    main()