"""Single-cell vs module aging comparison skeleton.

This example keeps the expensive aging/DCR mechanics in the existing
``src.simulation.run_dcr_and_power_test`` lifecycle interface, then layers a
small pack proxy on top:

* reference single cell: one homogeneous 314Ah/587Ah lifecycle-DCR run;
* module cells: one lifecycle-DCR run per cell, with pack heterogeneity mapped
  to per-cell temperature, cooling/contact resistance, capacity, and impedance;
* outputs: comparable capacity-retention and DCR evolution tables/plots.

The pack path is a time-scale-separation skeleton, not a full closed-loop
Liionpack solve. It is intended to be the runnable bridge from the validated
314Ah/587Ah single-cell lifecycle workflow toward a later Liionpack current
redistribution loop.

Example
-------
Fast config validation without solving PyBaMM:

    python BatteryProject/examples/pack_aging_skeleton.py --validate-only

Small runnable smoke case:

    python BatteryProject/examples/pack_aging_skeleton.py --cell 314 \\
        --total-real-cycles 2 --dcr-interval-real-cycles 1 \\
        --acceleration-factor 1 --model-options light
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pybamm  # noqa: E402


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"
PARAMS_ROOT = WORKSPACE_ROOT / "params"
OUTPUT_ROOT = PROJECT_ROOT / "output" / "pack_aging_skeleton"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from params import load_cell_params  # noqa: E402
from src.analysis import get_discharge_capacity  # noqa: E402
from src.runtime import apply_pybamm_runtime_limits  # noqa: E402
from src.simulation import (  # noqa: E402
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    run_dcr_and_power_test,
)


CELL_DEFAULTS = {
    "314": {
        "nominal_capacity_ah": 314.0,
        "nominal_voltage_v": 3.2,
        "charge_cutoff_v": 3.65,
        "discharge_cutoff_v": 2.50,
    },
    "587": {
        "nominal_capacity_ah": 587.0,
        "nominal_voltage_v": 3.2,
        "charge_cutoff_v": 3.65,
        "discharge_cutoff_v": 2.50,
    },
}

VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


@dataclass(frozen=True)
class CellVariant:
    """Per-cell heterogeneity used by the module proxy."""

    cell_id: str
    role: str
    temperature_offset_k: float = 0.0
    cooling_factor: float = 1.0
    contact_resistance_factor: float = 1.0
    capacity_factor: float = 1.0
    impedance_factor: float = 1.0
    current_share: float = 1.0

    @property
    def display_name(self) -> str:
        return f"{self.role}:{self.cell_id}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a runnable single-cell vs module aging/DCR comparison using "
            "the existing 314Ah/587Ah lifecycle interface."
        )
    )
    parser.add_argument("--cell", choices=sorted(CELL_DEFAULTS), default="314")
    parser.add_argument("--module-cells", type=int, default=4)
    parser.add_argument("--rate-p", type=float, default=0.5)
    parser.add_argument("--total-real-cycles", type=int, default=100)
    parser.add_argument("--dcr-interval-real-cycles", type=int, default=50)
    parser.add_argument("--acceleration-factor", type=int, default=50)
    parser.add_argument("--temperature-k", type=float, default=298.15)
    parser.add_argument("--rest-minutes", type=float, default=10.0)
    parser.add_argument("--period-minutes", type=float, default=0.5)
    parser.add_argument("--target-soc", type=float, default=0.5)
    parser.add_argument("--dcr-charge-c-rate", type=float, default=0.5)
    parser.add_argument("--dcr-pulse-c-rate", type=float, default=1.0)
    parser.add_argument("--dcr-pulse-duration-s", type=float, default=30.0)
    parser.add_argument("--model-options", choices=["light", "full"], default="light")
    parser.add_argument("--parallel-cells", action="store_true")
    parser.add_argument("--max-workers", type=int, default=None)
    parser.add_argument("--showprogress", action="store_true")
    parser.add_argument("--output-name", default=None)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate config and write no simulation outputs.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[int, int]:
    if args.module_cells < 2:
        raise ValueError("--module-cells must be at least 2")
    if args.rate_p <= 0:
        raise ValueError("--rate-p must be positive")
    if args.total_real_cycles <= 0:
        raise ValueError("--total-real-cycles must be positive")
    if args.dcr_interval_real_cycles <= 0:
        raise ValueError("--dcr-interval-real-cycles must be positive")
    if args.acceleration_factor <= 0:
        raise ValueError("--acceleration-factor must be positive")
    if not 0 <= args.target_soc <= 1:
        raise ValueError("--target-soc must be in [0, 1]")
    if args.total_real_cycles % args.dcr_interval_real_cycles != 0:
        raise ValueError("--total-real-cycles must be divisible by --dcr-interval-real-cycles")

    sim_cycles = args.total_real_cycles / args.acceleration_factor
    block_cycles = args.dcr_interval_real_cycles / args.acceleration_factor
    if not sim_cycles.is_integer() or not block_cycles.is_integer():
        raise ValueError(
            "--total-real-cycles and --dcr-interval-real-cycles must be divisible "
            "by --acceleration-factor for this DCR lifecycle interface."
        )
    sim_cycles = int(sim_cycles)
    block_cycles = int(block_cycles)
    if sim_cycles <= 0 or block_cycles <= 0:
        raise ValueError("The accelerated simulation must contain at least one cycle per block")
    return sim_cycles, block_cycles


def make_module_variants(module_cells: int) -> list[CellVariant]:
    """Create a minimum module heterogeneity set.

    The generated cells deliberately cover three factors:

    1. temperature difference: ``temperature_offset_k``;
    2. cooling/contact difference: ``cooling_factor`` and
       ``contact_resistance_factor``;
    3. initial capacity/impedance dispersion: ``capacity_factor`` and
       ``impedance_factor``.
    """

    if module_cells < 2:
        raise ValueError("module_cells must be at least 2")

    x = np.linspace(-1.0, 1.0, module_cells)
    temp_offsets = 3.0 * x
    cooling_factors = 1.0 - 0.30 * x
    contact_factors = 1.0 + 0.25 * x
    capacity_factors = 1.0 - 0.015 * x
    impedance_factors = 1.0 + 0.08 * x

    conductance = 1.0 / np.clip(impedance_factors * contact_factors, 1e-6, None)
    current_share = conductance / conductance.mean()

    variants = []
    for idx in range(module_cells):
        variants.append(
            CellVariant(
                cell_id=f"cell_{idx + 1:02d}",
                role="module",
                temperature_offset_k=float(temp_offsets[idx]),
                cooling_factor=float(cooling_factors[idx]),
                contact_resistance_factor=float(contact_factors[idx]),
                capacity_factor=float(capacity_factors[idx]),
                impedance_factor=float(impedance_factors[idx]),
                current_share=float(current_share[idx]),
            )
        )
    return variants


def make_reference_variant() -> CellVariant:
    return CellVariant(cell_id="single_ref", role="single")


def choose_model_options(kind: str) -> dict:
    if kind == "full":
        return dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)
    return dict(LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS)


def build_model(model_options: dict) -> pybamm.BaseModel:
    return pybamm.lithium_ion.DFN(model_options)


def build_cell_param_func(
    base_get_params: Callable[..., dict],
    variant: CellVariant,
    base_temperature_k: float,
) -> Callable[..., dict]:
    """Wrap a 314Ah/587Ah parameter function with per-cell perturbations."""

    def get_params(t_factor=1, temperature=298.15):
        cell_temperature = float(temperature) + variant.temperature_offset_k
        params = dict(base_get_params(t_factor, cell_temperature))

        if "Total heat transfer coefficient [W.m-2.K-1]" in params:
            params["Total heat transfer coefficient [W.m-2.K-1]"] = (
                float(params["Total heat transfer coefficient [W.m-2.K-1]"])
                * variant.cooling_factor
            )
        if "Contact resistance [Ohm]" in params:
            params["Contact resistance [Ohm]"] = (
                float(params["Contact resistance [Ohm]"])
                * variant.contact_resistance_factor
                * variant.impedance_factor
            )

        # Capacity dispersion is represented by geometry plus nominal-capacity
        # scaling. This is a skeleton-level proxy; calibrated studies should
        # replace it with measured loading/lithium-inventory perturbations.
        if "Nominal cell capacity [A.h]" in params:
            params["Nominal cell capacity [A.h]"] = (
                float(params["Nominal cell capacity [A.h]"]) * variant.capacity_factor
            )
        if "Electrode width [m]" in params:
            params["Electrode width [m]"] = (
                float(params["Electrode width [m]"]) * variant.capacity_factor
            )
        params["Ambient temperature [K]"] = cell_temperature
        params["Initial temperature [K]"] = cell_temperature
        return params

    # Keep useful metadata for reporting/debugging without changing the public
    # lifecycle function signature.
    get_params.variant = variant  # type: ignore[attr-defined]
    get_params.base_temperature_k = base_temperature_k  # type: ignore[attr-defined]
    return get_params


def latest_discharge_capacity_ah(sol) -> float:
    capacities = np.asarray(get_discharge_capacity(sol).get("discharge_capacity", []), dtype=float)
    capacities = capacities[np.isfinite(capacities) & (capacities > 0)]
    return float(capacities[-1]) if capacities.size else math.nan


def rate_case_to_dataframe(
    rate_case: dict,
    variant: CellVariant,
    *,
    rate_p: float,
    base_temperature_k: float,
    nominal_current_a: float,
) -> pd.DataFrame:
    """Convert ``run_dcr_and_power_test`` output into comparison rows."""

    cycle_numbers = sorted(rate_case["dcr"].keys())
    stored_solutions = list(rate_case.get("sol_list", []))
    if len(stored_solutions) < len(cycle_numbers):
        raise RuntimeError(
            f"{variant.display_name} has {len(stored_solutions)} stored solutions "
            f"but {len(cycle_numbers)} DCR checkpoints."
        )

    # DCR checkpoints are conditioning/start plus block endpoints. The stored
    # solution order matches that sequence when return_solutions=True.
    checkpoint_solutions = stored_solutions[: len(cycle_numbers)]
    capacities = [latest_discharge_capacity_ah(sol) for sol in checkpoint_solutions]
    finite_caps = [cap for cap in capacities if np.isfinite(cap) and cap > 0]
    base_capacity = finite_caps[0] if finite_caps else math.nan

    rows = []
    for cycle_number, sol, capacity_ah in zip(cycle_numbers, checkpoint_solutions, capacities):
        if np.isfinite(base_capacity) and base_capacity > 0 and np.isfinite(capacity_ah):
            retention_pct = capacity_ah / base_capacity * 100.0
        else:
            retention_pct = math.nan
        rows.append(
            {
                "role": variant.role,
                "cell_id": variant.cell_id,
                "checkpoint_cycle": int(cycle_number),
                "rate_p": rate_p,
                "temperature_k": base_temperature_k + variant.temperature_offset_k,
                "temperature_offset_k": variant.temperature_offset_k,
                "cooling_factor": variant.cooling_factor,
                "contact_resistance_factor": variant.contact_resistance_factor,
                "capacity_factor": variant.capacity_factor,
                "impedance_factor": variant.impedance_factor,
                "current_share": variant.current_share,
                "nominal_current_a": nominal_current_a,
                "discharge_capacity_ah": capacity_ah,
                "capacity_retention_pct": retention_pct,
                "dcr_mean_mohm": float(rate_case["dcr"][cycle_number]) * 1000.0,
                "dcr_discharge_mohm": float(rate_case["dcr_discharge"][cycle_number]) * 1000.0,
                "dcr_charge_mohm": float(rate_case["dcr_charge"][cycle_number]) * 1000.0,
                "power_discharge_w": float(rate_case["power"][cycle_number]["power_discharge"]),
                "power_charge_w": float(rate_case["power"][cycle_number]["power_charge"]),
                "charge_time_h": float(rate_case["charge_time"][cycle_number]),
                "solution_present": sol is not None,
            }
        )
    return pd.DataFrame(rows)


def summarize_module(metrics_df: pd.DataFrame) -> pd.DataFrame:
    module_df = metrics_df[metrics_df["role"] == "module"].copy()
    if module_df.empty:
        return pd.DataFrame()
    rows = []
    for cycle, group in module_df.groupby("checkpoint_cycle", sort=True):
        rows.append(
            {
                "role": "module_aggregate",
                "cell_id": "mean_min_max",
                "checkpoint_cycle": int(cycle),
                "cell_count": int(group["cell_id"].nunique()),
                "capacity_retention_mean_pct": float(group["capacity_retention_pct"].mean()),
                "capacity_retention_min_pct": float(group["capacity_retention_pct"].min()),
                "capacity_retention_max_pct": float(group["capacity_retention_pct"].max()),
                "dcr_mean_mohm": float(group["dcr_mean_mohm"].mean()),
                "dcr_min_mohm": float(group["dcr_mean_mohm"].min()),
                "dcr_max_mohm": float(group["dcr_mean_mohm"].max()),
                "temperature_min_k": float(group["temperature_k"].min()),
                "temperature_max_k": float(group["temperature_k"].max()),
            }
        )
    return pd.DataFrame(rows)


def run_variant(
    variant: CellVariant,
    args: argparse.Namespace,
    *,
    base_get_params: Callable[..., dict],
    model_options: dict,
    total_sim_cycles: int,
    cycles_per_block: int,
) -> pd.DataFrame:
    defaults = CELL_DEFAULTS[args.cell]
    get_params = build_cell_param_func(base_get_params, variant, args.temperature_k)
    model = build_model(model_options)
    solver = pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6)

    nominal_current = (
        defaults["nominal_capacity_ah"]
        * variant.capacity_factor
        * variant.current_share
    )
    result = run_dcr_and_power_test(
        [args.rate_p],
        model,
        solver,
        VAR_PTS,
        get_params,
        get_discharge_capacity_func=get_discharge_capacity,
        total_cycles=total_sim_cycles,
        cycles_per_block=cycles_per_block,
        temperature=args.temperature_k,
        nominal_current=nominal_current,
        nominal_voltage=defaults["nominal_voltage_v"],
        target_soc=args.target_soc,
        conditioning_t_factor=1.0,
        aging_t_factor=args.acceleration_factor,
        record_conditioning_cycle=True,
        conditioning_cycle_number=0,
        cycle_number_factor=int(args.acceleration_factor),
        dcr_charge_c_rate=args.dcr_charge_c_rate,
        dcr_pulse_c_rate=args.dcr_pulse_c_rate,
        dcr_pulse_duration_s=args.dcr_pulse_duration_s,
        charge_cutoff_v=defaults["charge_cutoff_v"],
        discharge_cutoff_v=defaults["discharge_cutoff_v"],
        rest_minutes=args.rest_minutes,
        period_minutes=args.period_minutes,
        keep_only_last_cycle_solution=False,
        return_solutions=True,
        showprogress=args.showprogress,
    )
    rate_case = result["rate_results"][args.rate_p]
    return rate_case_to_dataframe(
        rate_case,
        variant,
        rate_p=args.rate_p,
        base_temperature_k=args.temperature_k,
        nominal_current_a=nominal_current,
    )


def make_output_dir(args: argparse.Namespace) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = args.output_name or (
        f"{args.cell}Ah_single_vs_module_{args.rate_p:g}P_"
        f"{args.total_real_cycles}cycles_{timestamp}"
    )
    output_dir = OUTPUT_ROOT / name
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def save_outputs(
    metrics_df: pd.DataFrame,
    module_summary_df: pd.DataFrame,
    config: dict,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(output_dir / "cell_metrics.csv", index=False, encoding="utf-8-sig")
    module_summary_df.to_csv(output_dir / "module_summary.csv", index=False, encoding="utf-8-sig")
    (output_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with pd.ExcelWriter(output_dir / "single_vs_module_aging.xlsx", engine="openpyxl") as writer:
        metrics_df.to_excel(writer, index=False, sheet_name="cell_metrics")
        module_summary_df.to_excel(writer, index=False, sheet_name="module_summary")

    plot_comparison(metrics_df, module_summary_df, output_dir)


def plot_comparison(metrics_df: pd.DataFrame, module_summary_df: pd.DataFrame, output_dir: Path) -> None:
    try:
        plt.style.use("science")
    except Exception:
        pass
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Calibri", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=180)
    single_df = metrics_df[metrics_df["role"] == "single"]
    module_df = metrics_df[metrics_df["role"] == "module"]

    axes[0].plot(
        single_df["checkpoint_cycle"],
        single_df["capacity_retention_pct"],
        "k-o",
        label="single reference",
    )
    for cell_id, group in module_df.groupby("cell_id"):
        axes[0].plot(group["checkpoint_cycle"], group["capacity_retention_pct"], "--", alpha=0.65, label=cell_id)
    if not module_summary_df.empty:
        axes[0].plot(
            module_summary_df["checkpoint_cycle"],
            module_summary_df["capacity_retention_mean_pct"],
            "r-o",
            label="module mean",
        )
    axes[0].set_xlabel("Real cycle")
    axes[0].set_ylabel("Capacity retention (%)")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(
        single_df["checkpoint_cycle"],
        single_df["dcr_mean_mohm"],
        "k-o",
        label="single reference",
    )
    for cell_id, group in module_df.groupby("cell_id"):
        axes[1].plot(group["checkpoint_cycle"], group["dcr_mean_mohm"], "--", alpha=0.65, label=cell_id)
    if not module_summary_df.empty:
        axes[1].plot(
            module_summary_df["checkpoint_cycle"],
            module_summary_df["dcr_mean_mohm"],
            "r-o",
            label="module mean",
        )
    axes[1].set_xlabel("Real cycle")
    axes[1].set_ylabel("DCR mean (mOhm)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="best", fontsize=7)
    fig.tight_layout()
    fig.savefig(output_dir / "capacity_dcr_comparison.png", bbox_inches="tight")
    plt.close(fig)


def build_config(args: argparse.Namespace, variants: list[CellVariant]) -> dict:
    return {
        "script": str(Path(__file__).resolve()),
        "cell": args.cell,
        "cell_defaults": CELL_DEFAULTS[args.cell],
        "rate_p": args.rate_p,
        "total_real_cycles": args.total_real_cycles,
        "dcr_interval_real_cycles": args.dcr_interval_real_cycles,
        "acceleration_factor": args.acceleration_factor,
        "temperature_k": args.temperature_k,
        "rest_minutes": args.rest_minutes,
        "period_minutes": args.period_minutes,
        "target_soc": args.target_soc,
        "dcr_charge_c_rate": args.dcr_charge_c_rate,
        "dcr_pulse_c_rate": args.dcr_pulse_c_rate,
        "dcr_pulse_duration_s": args.dcr_pulse_duration_s,
        "model_options": args.model_options,
        "var_pts": VAR_PTS,
        "variants": [asdict(variant) for variant in variants],
        "scope_note": (
            "Module cells reuse the existing single-cell lifecycle-DCR interface. "
            "Temperature, cooling/contact resistance, capacity, and impedance "
            "dispersion are mapped into per-cell parameter wrappers and current "
            "shares. This is a runnable pack-aging skeleton, not a calibrated "
            "closed-loop Liionpack current redistribution model."
        ),
    }


def main() -> int:
    args = parse_args()
    total_sim_cycles, cycles_per_block = validate_args(args)
    apply_pybamm_runtime_limits()
    pybamm.set_logging_level("WARNING")

    base_get_params = load_cell_params(args.cell)
    reference = make_reference_variant()
    module_variants = make_module_variants(args.module_cells)
    variants = [reference, *module_variants]
    config = build_config(args, variants)
    config["total_sim_cycles"] = total_sim_cycles
    config["cycles_per_block"] = cycles_per_block

    if args.validate_only:
        print(json.dumps(config, indent=2, ensure_ascii=False))
        print("VALIDATION_ONLY_OK")
        return 0

    model_options = choose_model_options(args.model_options)
    frames = []
    for variant in variants:
        print(f"Running {variant.display_name} ...")
        frames.append(
            run_variant(
                variant,
                args,
                base_get_params=base_get_params,
                model_options=model_options,
                total_sim_cycles=total_sim_cycles,
                cycles_per_block=cycles_per_block,
            )
        )

    metrics_df = pd.concat(frames, ignore_index=True)
    module_summary_df = summarize_module(metrics_df)
    output_dir = make_output_dir(args)
    save_outputs(metrics_df, module_summary_df, config, output_dir)

    final_cycle = int(metrics_df["checkpoint_cycle"].max())
    final_metrics = metrics_df[metrics_df["checkpoint_cycle"] == final_cycle]
    print(f"Output: {output_dir}")
    print(
        final_metrics[
            [
                "role",
                "cell_id",
                "capacity_retention_pct",
                "dcr_mean_mohm",
                "temperature_k",
                "current_share",
            ]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
