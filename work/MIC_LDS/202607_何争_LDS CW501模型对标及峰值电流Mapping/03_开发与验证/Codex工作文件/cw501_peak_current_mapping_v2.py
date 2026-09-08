"""CW501 multi-temperature DFN peak-current mapping workflow.

The current is supplied as a PyBaMM input parameter so that one processed DFN
can be reused throughout a temperature/direction/duration group. Results are
checkpointed after every complete group for resumable notebook execution.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pybamm
from scipy.optimize import root_scalar


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
from src.simulation_peak import (  # noqa: E402
    _prepare_peak_current_parameter_values,
)


DEFAULT_DURATIONS_S = (10, 30, 60)
DEFAULT_CHARGE_TEMPERATURES_C = tuple(range(0, 56, 5))
DEFAULT_DISCHARGE_TEMPERATURES_C = (-30, -20, -10) + tuple(range(0, 56, 5))
DEFAULT_CHARGE_SOC = tuple(np.round(np.arange(0.95, -1e-8, -0.05), 2))
DEFAULT_DISCHARGE_SOC = tuple(np.round(np.arange(1.0, 0.05 - 1e-8, -0.05), 2))
DEFAULT_OUTPUT_PERIOD_S = 2.0
DEFAULT_RATIO_XTOL = 1e-3
ALGORITHM_VERSION = "reusable-input-dfn-v3-ocv-dcr"
DEFAULT_NODE_EXECUTABLE = Path(
    r"C:\Users\hez\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\node\bin\node.exe"
)
EXCEL_BUILDER = Path(__file__).with_name("build_cw501_pulse_map_excel.mjs")
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


def build_peak_model() -> pybamm.BaseModel:
    """Build the CW501 DFN with contact resistance enabled."""
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


def _pulse_time_grid(duration_s: float, output_period_s: float) -> np.ndarray:
    if duration_s <= 0 or output_period_s <= 0:
        raise ValueError("duration_s and output_period_s must be positive")
    values = np.arange(0.0, duration_s + 0.5 * output_period_s, output_period_s)
    values = values[values < duration_s]
    return np.append(values, float(duration_s))


def _build_reusable_simulation(
    model: pybamm.BaseModel,
    parameters: pybamm.ParameterValues,
) -> pybamm.Simulation:
    prepared = _prepare_peak_current_parameter_values(parameters, model)
    prepared.update({"Current function [A]": "[input]"})
    solver = pybamm.IDAKLUSolver(
        output_variables=[
            "Time [s]",
            "Current [A]",
            "Voltage [V]",
            "Battery open-circuit voltage [V]",
        ],
        rtol=1e-6,
        atol=1e-6,
    )
    return pybamm.Simulation(
        model,
        parameter_values=prepared,
        solver=solver,
        var_pts=VAR_PTS,
    )


def _find_local_bracket(
    objective,
    current_guess: float,
    expansion_factor: float = 1.6,
    min_ratio: float = 1e-4,
    max_ratio: float = 200.0,
    max_extensions: int = 30,
) -> tuple[float | None, float | None, list[tuple[float, float]]]:
    """Bracket the monotonic voltage-limit root around the previous SOC result."""
    guess = float(np.clip(current_guess, min_ratio, max_ratio))
    value = float(objective(guess))
    samples = [(guess, value)]
    if abs(value) < 1e-8:
        return guess, guess, samples

    if value > 0:
        left_ratio, left_value = guess, value
        for _ in range(max_extensions):
            right_ratio = min(left_ratio * expansion_factor, max_ratio)
            if right_ratio <= left_ratio:
                break
            right_value = float(objective(right_ratio))
            samples.append((right_ratio, right_value))
            if right_value <= 0:
                return left_ratio, right_ratio, samples
            left_ratio, left_value = right_ratio, right_value
    else:
        right_ratio, right_value = guess, value
        for _ in range(max_extensions):
            left_ratio = max(right_ratio / expansion_factor, min_ratio)
            if left_ratio >= right_ratio:
                break
            left_value = float(objective(left_ratio))
            samples.append((left_ratio, left_value))
            if left_value >= 0:
                return left_ratio, right_ratio, samples
            right_ratio, right_value = left_ratio, left_value

    return None, None, samples


def run_peak_current_reusable(
    model: pybamm.BaseModel,
    parameters: pybamm.ParameterValues,
    nominal_capacity_ah: float,
    duration_s: int,
    direction: str,
    soc_values: tuple[float, ...],
    output_period_s: float = DEFAULT_OUTPUT_PERIOD_S,
    ratio_xtol: float = DEFAULT_RATIO_XTOL,
    x0: float = 1.0,
) -> dict:
    """Search one mapping group while reusing a single processed DFN."""
    if direction not in {"charge", "discharge"}:
        raise ValueError("direction must be 'charge' or 'discharge'")

    voltage_limit_v = 3.65 if direction == "charge" else 2.5
    current_sign = -1.0 if direction == "charge" else 1.0
    time_grid = _pulse_time_grid(float(duration_s), float(output_period_s))
    simulation = _build_reusable_simulation(model, parameters)
    peak_current_a = []
    equivalent_peak_power_w = []
    first_voltage_v = []
    first_ocv_voltage_v = []
    current_guess = float(x0)

    for soc in soc_values:
        cache: dict[float, tuple[float, float, float]] = {}

        def evaluate(ratio: float) -> tuple[float, float, float]:
            ratio = float(ratio)
            if ratio in cache:
                return cache[ratio]
            signed_current_a = current_sign * ratio * nominal_capacity_ah
            try:
                solution = simulation.solve(
                    t_eval=time_grid,
                    initial_soc=float(np.clip(soc, 0.0, 1.0)),
                    direction=direction,
                    inputs={"Current function [A]": signed_current_a},
                )
            except pybamm.SolverError as error:
                if "non-positive at initial conditions" not in str(error):
                    raise
                result = (-float(duration_s), np.nan, np.nan)
                cache[ratio] = result
                return result

            if isinstance(solution, pybamm.EmptySolution):
                result = (-float(duration_s), np.nan, np.nan)
                cache[ratio] = result
                return result

            time_s = float(solution["Time [s]"].entries[-1])
            voltage = np.asarray(solution["Voltage [V]"].entries, dtype=float)
            ocv_voltage = np.asarray(
                solution["Battery open-circuit voltage [V]"].entries,
                dtype=float,
            )
            pulse_first_voltage = float(voltage[0])
            pulse_first_ocv_voltage = float(ocv_voltage[0])
            if abs(time_s - duration_s) < 0.02:
                margin = (
                    voltage_limit_v - float(voltage[-1])
                    if direction == "charge"
                    else float(voltage[-1]) - voltage_limit_v
                )
            else:
                margin = time_s - float(duration_s)
            result = (
                float(margin),
                pulse_first_voltage,
                pulse_first_ocv_voltage,
            )
            cache[ratio] = result
            return result

        def objective(ratio: float) -> float:
            return evaluate(ratio)[0]

        logger = logging.getLogger("cw501_peak_mapping")
        logger.info(
            "[Start] %s SOC=%.2f, %ds, output %.1fs",
            direction,
            soc,
            duration_s,
            output_period_s,
        )
        try:
            left_ratio, right_ratio, samples = _find_local_bracket(
                objective,
                current_guess,
            )
            if left_ratio is None:
                logger.warning("No sign change found: %s", samples)
                result_ratio = np.nan
            elif left_ratio == right_ratio:
                result_ratio = left_ratio
            else:
                result_ratio = float(
                    root_scalar(
                        objective,
                        bracket=[left_ratio, right_ratio],
                        method="brentq",
                        xtol=ratio_xtol,
                    ).root
                )
        except Exception as error:
            logger.warning("Optimization failed: %s", error)
            result_ratio = np.nan

        if np.isfinite(result_ratio):
            _, first_voltage, first_ocv_voltage = evaluate(result_ratio)
            if not np.isfinite(first_voltage):
                feasible = [
                    (abs(ratio - result_ratio), voltage, ocv_voltage)
                    for ratio, (margin, voltage, ocv_voltage) in cache.items()
                    if margin >= 0
                    and np.isfinite(voltage)
                    and np.isfinite(ocv_voltage)
                ]
                if feasible:
                    _, first_voltage, first_ocv_voltage = min(feasible)
                else:
                    first_voltage = np.nan
                    first_ocv_voltage = np.nan
            current_a = result_ratio * nominal_capacity_ah
            peak_current_a.append(current_a)
            equivalent_peak_power_w.append(current_a * 3.2)
            first_voltage_v.append(first_voltage)
            first_ocv_voltage_v.append(first_ocv_voltage)
            current_guess = result_ratio
        else:
            peak_current_a.append(np.nan)
            equivalent_peak_power_w.append(np.nan)
            first_voltage_v.append(np.nan)
            first_ocv_voltage_v.append(np.nan)
            current_guess = float(x0)
        logger.info(
            "[Done] %s SOC=%.2f -> ratio=%.4f",
            direction,
            soc,
            result_ratio,
        )

    return {
        "soc": list(soc_values),
        "peak_current_a": peak_current_a,
        "equivalent_peak_power_w": equivalent_peak_power_w,
        "first_voltage_v": first_voltage_v,
        "first_ocv_voltage_v": first_ocv_voltage_v,
    }


def _group_is_complete(
    existing: pd.DataFrame,
    direction: str,
    temperature_c: float,
    duration_s: int,
    expected_soc: tuple[float, ...],
    output_period_s: float,
) -> bool:
    required = {
        "algorithm_version",
        "output_period_s",
        "pulse_ocv_voltage_v",
        "pulse_dcr_mohm",
    }
    if existing.empty or not required.issubset(existing.columns):
        return False
    group = existing[
        (existing["direction"] == direction)
        & np.isclose(existing["temperature_c"], temperature_c)
        & (existing["duration_s"] == duration_s)
        & (existing["algorithm_version"] == ALGORITHM_VERSION)
        & np.isclose(existing["output_period_s"], output_period_s)
    ]
    actual_soc = set(np.round(group["soc"].astype(float), 4))
    return set(np.round(expected_soc, 4)).issubset(actual_soc)


def _rows_from_result(
    result: dict,
    direction: str,
    temperature_c: float,
    duration_s: int,
    nominal_capacity_ah: float,
    output_period_s: float,
    ratio_xtol: float,
) -> list[dict]:
    rows = []
    for soc, current_a, equivalent_power_w, first_voltage_v, first_ocv_voltage_v in zip(
        result["soc"],
        result["peak_current_a"],
        result["equivalent_peak_power_w"],
        result["first_voltage_v"],
        result["first_ocv_voltage_v"],
    ):
        is_valid = np.isfinite(current_a)
        pulse_power_w = (
            float(current_a) * float(first_voltage_v)
            if is_valid and np.isfinite(first_voltage_v)
            else np.nan
        )
        voltage_delta_v = (
            float(first_voltage_v) - float(first_ocv_voltage_v)
            if direction == "charge"
            else float(first_ocv_voltage_v) - float(first_voltage_v)
        )
        pulse_dcr_mohm = (
            voltage_delta_v / float(current_a) * 1000
            if is_valid
            and current_a > 0
            and np.isfinite(voltage_delta_v)
            else np.nan
        )
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
                    float(equivalent_power_w) / 1000
                    if np.isfinite(equivalent_power_w)
                    else np.nan
                ),
                "pulse_power_w": pulse_power_w,
                "pulse_power_kw": (
                    pulse_power_w / 1000 if np.isfinite(pulse_power_w) else np.nan
                ),
                "pulse_first_voltage_v": (
                    float(first_voltage_v) if np.isfinite(first_voltage_v) else np.nan
                ),
                "pulse_ocv_voltage_v": (
                    float(first_ocv_voltage_v)
                    if np.isfinite(first_ocv_voltage_v)
                    else np.nan
                ),
                "pulse_dcr_mohm": (
                    pulse_dcr_mohm if np.isfinite(pulse_dcr_mohm) else np.nan
                ),
                "contact_resistance_ohm": 9.0549e-5,
                "output_period_s": float(output_period_s),
                "ratio_xtol": float(ratio_xtol),
                "algorithm_version": ALGORITHM_VERSION,
                "status": "ok" if is_valid else "no_solution",
            }
        )
    return rows


def _write_checkpoint(frame: pd.DataFrame, output_file: Path) -> None:
    ordered = frame.sort_values(
        ["direction", "duration_s", "temperature_c", "soc"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)
    temporary = output_file.with_suffix(".tmp.txt")
    ordered.to_csv(temporary, index=False, encoding="utf-8-sig")
    try:
        temporary.replace(output_file)
    except PermissionError:
        ordered.to_csv(output_file, index=False, encoding="utf-8-sig")
        temporary.unlink(missing_ok=True)


def export_peak_current_excel(
    frame: pd.DataFrame,
    output_path: Path | None = None,
    node_executable: Path = DEFAULT_NODE_EXECUTABLE,
) -> Path:
    """Export the mapping in the Hithium 314Ah pulse-map workbook layout."""
    required_columns = {
        "direction",
        "temperature_c",
        "duration_s",
        "soc_pct",
        "peak_current_a",
        "pulse_power_w",
        "pulse_dcr_mohm",
        "algorithm_version",
    }
    missing_columns = required_columns.difference(frame.columns)
    if frame.empty:
        raise ValueError("Cannot export an empty peak-current mapping")
    if missing_columns:
        raise ValueError(
            "Peak-current mapping must be rerun with the OCV/DCR-enabled algorithm; "
            f"missing columns: {sorted(missing_columns)}"
        )

    output_path = Path(
        output_path
        or DEFAULT_OUTPUT_DIR / "CW501_10s30s60s峰值电流Mapping.xlsx"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    node_executable = Path(node_executable)
    if not node_executable.exists():
        raise FileNotFoundError(f"Bundled Node.js not found: {node_executable}")
    if not EXCEL_BUILDER.exists():
        raise FileNotFoundError(f"Excel builder not found: {EXCEL_BUILDER}")

    current_rows = frame[
        frame["algorithm_version"] == ALGORITHM_VERSION
    ].copy()
    if current_rows.empty:
        raise ValueError(
            f"No rows were generated by algorithm {ALGORITHM_VERSION}"
        )
    json_path = output_path.with_suffix(".export.json")
    export_rows = current_rows.replace({np.nan: None}).to_dict(orient="records")
    json_path.write_text(
        json.dumps(
            {
                "cell_model": "CW501",
                "algorithm_version": ALGORITHM_VERSION,
                "rows": export_rows,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                str(node_executable),
                str(EXCEL_BUILDER),
                str(json_path),
                str(output_path),
            ],
            cwd=EXCEL_BUILDER.parent,
            check=True,
        )
        output_path.with_suffix(output_path.suffix + ".inspect.ndjson").unlink(
            missing_ok=True
        )
    finally:
        json_path.unlink(missing_ok=True)
    return output_path


def run_peak_current_mapping(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    durations_s: tuple[int, ...] = DEFAULT_DURATIONS_S,
    charge_temperatures_c: tuple[float, ...] = DEFAULT_CHARGE_TEMPERATURES_C,
    discharge_temperatures_c: tuple[float, ...] = DEFAULT_DISCHARGE_TEMPERATURES_C,
    charge_soc: tuple[float, ...] = DEFAULT_CHARGE_SOC,
    discharge_soc: tuple[float, ...] = DEFAULT_DISCHARGE_SOC,
    output_period_s: float = DEFAULT_OUTPUT_PERIOD_S,
    ratio_xtol: float = DEFAULT_RATIO_XTOL,
    resume: bool = True,
) -> pd.DataFrame:
    """Run or resume the complete CW501 peak-current mapping matrix."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # A .txt checkpoint avoids DLP locking an overwritten protected .csv.
    # The content remains standard UTF-8 CSV and is loaded transparently.
    output_file = output_dir / "peak_current_map_v3_checkpoint.txt"
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
        "algorithm_version": ALGORITHM_VERSION,
        "nominal_capacity_ah": nominal_capacity_ah,
        "durations_s": list(durations_s),
        "charge_temperatures_c": list(charge_temperatures_c),
        "discharge_temperatures_c": list(discharge_temperatures_c),
        "charge_soc": list(charge_soc),
        "discharge_soc": list(discharge_soc),
        "contact_resistance_enabled": True,
        "contact_resistance_ohm": 9.0549e-5,
        "voltage_limits_v": {"charge": 3.65, "discharge": 2.5},
        "output_period_s": float(output_period_s),
        "ratio_xtol": float(ratio_xtol),
        "internal_time_step": "IDAKLU adaptive",
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

    model = build_peak_model()
    for group_index, (direction, temperature_c, duration_s, soc_values) in enumerate(
        groups,
        start=1,
    ):
        if resume and _group_is_complete(
            existing,
            direction,
            temperature_c,
            duration_s,
            soc_values,
            output_period_s,
        ):
            logger.info(
                "[%d/%d] Skip completed %s, %.1f°C, %ds",
                group_index,
                len(groups),
                direction,
                temperature_c,
                duration_s,
            )
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
        result = run_peak_current_reusable(
            model=model,
            parameters=parameters,
            nominal_capacity_ah=nominal_capacity_ah,
            duration_s=duration_s,
            direction=direction,
            soc_values=soc_values,
            output_period_s=output_period_s,
            ratio_xtol=ratio_xtol,
        )
        new_rows = pd.DataFrame(
            _rows_from_result(
                result,
                direction,
                temperature_c,
                duration_s,
                nominal_capacity_ah,
                output_period_s,
                ratio_xtol,
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
        logger.info(
            "[%d/%d] Saved %s, %.1f°C, %ds",
            group_index,
            len(groups),
            direction,
            temperature_c,
            duration_s,
        )

    logger.info("Completed %d groups. Output: %s", len(groups), output_file)
    return pd.read_csv(output_file, encoding="utf-8-sig")


def load_peak_current_mapping(output_dir: Path = DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    """Load mapping rows generated by the current reusable-DFN algorithm."""
    path = Path(output_dir) / "peak_current_map_v3_checkpoint.txt"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if "algorithm_version" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["algorithm_version"] == ALGORITHM_VERSION].reset_index(drop=True)
