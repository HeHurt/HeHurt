"""CW501 multi-temperature peak-current mapping workflow.

The workflow reuses BatteryProject's validated ``run_peak_current`` search,
adds fresh parameter construction for every temperature, and checkpoints each
temperature/direction/duration group for resumable notebook execution.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pybamm


PROJECT_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
BATTERY_PROJECT = PROJECT_ROOT / "BatteryProject"
PARAMS_ROOT = PROJECT_ROOT / "params"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "work"
    / "MIC_LDS"
    / "202607_何争_LDS CW501模型对标及峰值电流Mapping"
    / "04_输出结果"
    / "峰值电流Mapping"
)

for path in [BATTERY_PROJECT, PARAMS_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from paramsLDSCW501 import get_hithium_params  # noqa: E402
from src.simulation_peak import run_peak_current  # noqa: E402


DEFAULT_DURATIONS_S = (10, 30, 60)
DEFAULT_CHARGE_TEMPERATURES_C = tuple(range(0, 56, 5))
DEFAULT_DISCHARGE_TEMPERATURES_C = (-30, -20, -10) + tuple(range(0, 56, 5))
DEFAULT_CHARGE_SOC = tuple(np.round(np.arange(0.95, -1e-8, -0.05), 2))
DEFAULT_DISCHARGE_SOC = tuple(np.round(np.arange(1.0, 0.05 - 1e-8, -0.05), 2))
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


def build_peak_model() -> pybamm.BaseModel:
    """Build the CW501 DFN used for current-limited pulse searches."""
    return pybamm.lithium_ion.DFN(
        {
            "calculate discharge energy": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )


def fresh_parameter_values(temperature_c: float) -> pybamm.ParameterValues:
    """Create an uncontaminated parameter set for one temperature."""
    temperature_k = float(temperature_c) + 273.15
    parameters = pybamm.ParameterValues("OKane2022")
    parameters.update(
        get_hithium_params(t_factor=1, temperature=temperature_k),
        check_already_exists=False,
    )
    parameters.update(
        {
            "Ambient temperature [K]": temperature_k,
            "Initial temperature [K]": temperature_k,
        },
        check_already_exists=False,
    )
    return parameters


def _group_is_complete(
    existing: pd.DataFrame,
    direction: str,
    temperature_c: float,
    duration_s: int,
    expected_soc: tuple[float, ...],
) -> bool:
    if existing.empty:
        return False
    group = existing[
        (existing["direction"] == direction)
        & np.isclose(existing["temperature_c"], temperature_c)
        & (existing["duration_s"] == duration_s)
    ]
    actual_soc = set(np.round(group["soc"].astype(float), 4))
    return set(np.round(expected_soc, 4)).issubset(actual_soc)


def _rows_from_result(
    result: dict,
    direction: str,
    temperature_c: float,
    duration_s: int,
    nominal_capacity_ah: float,
) -> list[dict]:
    if direction == "charge":
        soc_values = result["charge_soc"]
        current_values = result["charge_peak_current"]
        power_values = result["charge_peak_power"]
        voltage_values = result["charge_first_voltage"]
    else:
        soc_values = result["discharge_soc"]
        current_values = result["discharge_peak_current"]
        power_values = result["discharge_peak_power"]
        voltage_values = result["discharge_first_voltage"]

    rows = []
    for soc, current_a, power_w, first_voltage_v in zip(
        soc_values,
        current_values,
        power_values,
        voltage_values,
    ):
        is_valid = np.isfinite(current_a)
        rows.append(
            {
                "direction": direction,
                "temperature_c": float(temperature_c),
                "duration_s": int(duration_s),
                "soc": float(soc),
                "soc_pct": float(soc) * 100,
                "peak_current_a": float(current_a) if is_valid else np.nan,
                "peak_current_ka": float(current_a) / 1000 if is_valid else np.nan,
                "peak_c_rate": float(current_a) / nominal_capacity_ah if is_valid else np.nan,
                "equivalent_peak_power_kw_at_3p2v": (
                    float(power_w) / 1000 if np.isfinite(power_w) else np.nan
                ),
                "pulse_first_voltage_v": (
                    float(first_voltage_v) if np.isfinite(first_voltage_v) else np.nan
                ),
                "contact_resistance_ohm": 9.0549e-5,
                "status": "ok" if is_valid else "no_solution",
            }
        )
    return rows


def _write_checkpoint(frame: pd.DataFrame, output_file: Path) -> None:
    ordered = frame.sort_values(
        ["direction", "duration_s", "temperature_c", "soc"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)
    temporary = output_file.with_suffix(".tmp.csv")
    ordered.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(output_file)


def run_peak_current_mapping(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    durations_s: tuple[int, ...] = DEFAULT_DURATIONS_S,
    charge_temperatures_c: tuple[float, ...] = DEFAULT_CHARGE_TEMPERATURES_C,
    discharge_temperatures_c: tuple[float, ...] = DEFAULT_DISCHARGE_TEMPERATURES_C,
    charge_soc: tuple[float, ...] = DEFAULT_CHARGE_SOC,
    discharge_soc: tuple[float, ...] = DEFAULT_DISCHARGE_SOC,
    resume: bool = True,
) -> pd.DataFrame:
    """Run or resume the complete CW501 peak-current mapping matrix."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "peak_current_map.csv"
    log_file = output_dir / "run.log"

    logger = logging.getLogger("cw501_peak_mapping")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    existing = (
        pd.read_csv(output_file, encoding="utf-8-sig")
        if resume and output_file.exists()
        else pd.DataFrame()
    )
    nominal_capacity_ah = float(
        get_hithium_params(t_factor=1, temperature=298.15)["Nominal cell capacity [A.h]"]
    )
    config = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "pybamm_version": pybamm.__version__,
        "mode": "A",
        "nominal_capacity_ah": nominal_capacity_ah,
        "durations_s": list(durations_s),
        "charge_temperatures_c": list(charge_temperatures_c),
        "discharge_temperatures_c": list(discharge_temperatures_c),
        "charge_soc": list(charge_soc),
        "discharge_soc": list(discharge_soc),
        "contact_resistance_enabled": True,
        "contact_resistance_ohm": 9.0549e-5,
        "voltage_limits_v": {"charge": 3.65, "discharge": 2.5},
        "var_pts": VAR_PTS,
        "resume": resume,
    }
    (output_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    groups = []
    for duration_s in durations_s:
        groups.extend(
            ("charge", temperature_c, int(duration_s), tuple(charge_soc))
            for temperature_c in charge_temperatures_c
        )
        groups.extend(
            ("discharge", temperature_c, int(duration_s), tuple(discharge_soc))
            for temperature_c in discharge_temperatures_c
        )

    completed_groups = 0
    model = build_peak_model()
    for group_index, (direction, temperature_c, duration_s, soc_values) in enumerate(groups, start=1):
        if resume and _group_is_complete(
            existing,
            direction,
            temperature_c,
            duration_s,
            soc_values,
        ):
            logger.info(
                "[%d/%d] Skip completed %s, %.1f°C, %ds",
                group_index,
                len(groups),
                direction,
                temperature_c,
                duration_s,
            )
            completed_groups += 1
            continue

        logger.info(
            "[%d/%d] Start %s, %.1f°C, %ds, %d SOC points",
            group_index,
            len(groups),
            direction,
            temperature_c,
            duration_s,
            len(soc_values),
        )
        parameters = fresh_parameter_values(temperature_c)
        result = run_peak_current(
            model=model,
            param=parameters,
            var_pts=VAR_PTS,
            temperature=temperature_c + 273.15,
            nominal=nominal_capacity_ah,
            t_period=duration_s,
            x0=1,
            charge_soc_list=soc_values if direction == "charge" else (),
            discharge_soc_list=soc_values if direction == "discharge" else (),
            mode="A",
        )
        new_rows = pd.DataFrame(
            _rows_from_result(
                result,
                direction,
                temperature_c,
                duration_s,
                nominal_capacity_ah,
            )
        )
        if existing.empty:
            existing = new_rows
        else:
            keep = ~(
                (existing["direction"] == direction)
                & np.isclose(existing["temperature_c"], temperature_c)
                & (existing["duration_s"] == duration_s)
            )
            existing = pd.concat([existing.loc[keep], new_rows], ignore_index=True)
        _write_checkpoint(existing, output_file)
        completed_groups += 1
        logger.info(
            "[%d/%d] Saved %s, %.1f°C, %ds",
            group_index,
            len(groups),
            direction,
            temperature_c,
            duration_s,
        )

    logger.info("Completed %d/%d groups. Output: %s", completed_groups, len(groups), output_file)
    return pd.read_csv(output_file, encoding="utf-8-sig")


def load_peak_current_mapping(output_dir: Path = DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    """Load a previously generated mapping table."""
    path = Path(output_dir) / "peak_current_map.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")
