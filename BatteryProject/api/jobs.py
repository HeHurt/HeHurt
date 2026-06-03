from __future__ import annotations

import csv
import importlib
import json
import multiprocessing as mp
import os
import sys
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
PARAMS_ROOT = WORKSPACE_ROOT / "params"
JOB_ROOT = PROJECT_ROOT / "output" / "studio_jobs"
VAR_PTS_STANDARD = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
MAX_UI_CYCLES = 3
MAX_PRODUCTION_CYCLES = 2000
# 退化加速因子：项目参数集把退化速率(SEI/析锂/裂纹/LAM)乘以此值，
# 1 个仿真圈 = ACCELERATION_FACTOR 个真实圈（与 src.config / notebook 对齐）。
ACCELERATION_FACTOR = 50

AGING_OPTIONS = {
    "SEI": [
        "none",
        "constant",
        "reaction limited",
        "reaction limited (asymmetric)",
        "solvent-diffusion limited",
        "electron-migration limited",
        "interstitial-diffusion limited",
        "ec reaction limited",
        "ec reaction limited (asymmetric)",
        "VonKolzenberg2020",
        "tunnelling limited",
    ],
    "SEI film resistance": ["none", "distributed", "average"],
    "SEI on cracks": ["false", "true"],
    "SEI porosity change": ["false", "true"],
    "lithium plating": ["none", "reversible", "partially reversible", "irreversible"],
    "lithium plating porosity change": ["false", "true"],
    "loss of active material": [
        "none",
        "stress-driven",
        "asymmetric stress-driven",
        "reaction-driven",
        "current-driven",
        "stress and reaction-driven",
        "asymmetric stress and reaction-driven",
    ],
    "particle mechanics": ["none", "swelling only", "swelling and cracking"],
    "stress-induced diffusion": ["false", "true"],
}

DEFAULT_AGING_OPTIONS = {
    "SEI": "ec reaction limited",
    "SEI film resistance": "none",
    "SEI on cracks": "true",
    "SEI porosity change": "true",
    "lithium plating": "irreversible",
    "lithium plating porosity change": "true",
    "loss of active material": "stress-driven",
    "particle mechanics": "swelling and cracking",
    "stress-induced diffusion": "false",
}

PARAMETER_SETS = {
    "chen2020": {"kind": "builtin", "name": "Chen2020", "label": "Chen2020"},
    "okane2022": {"kind": "builtin", "name": "OKane2022", "label": "OKane2022"},
    "hithium314": {"kind": "project", "base": "OKane2022", "module": "params.params", "label": "314Ah 默认参数"},
    "hithium587": {"kind": "project", "base": "OKane2022", "module": "params.params587", "label": "587Ah 参数"},
    "mic1175": {"kind": "project", "base": "OKane2022", "module": "params.paramsMIC", "label": "MIC 1175Ah 参数"},
    "hithium280": {"kind": "project", "base": "OKane2022", "module": "params.params280", "label": "280Ah 参数"},
}


def ensure_runtime_env() -> None:
    runtime_root = Path(tempfile.gettempdir()) / "batteryproject_studio_api"
    runtime_home = runtime_root / "home"
    mpl_config = runtime_root / "mpl"
    runtime_home.mkdir(parents=True, exist_ok=True)
    mpl_config.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PYBAMM_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("HOME", str(runtime_home))
    os.environ.setdefault("USERPROFILE", str(runtime_home))
    os.environ.setdefault("HOMEDRIVE", runtime_home.drive)
    os.environ.setdefault("HOMEPATH", "\\" + "\\".join(runtime_home.parts[1:]) if len(runtime_home.parts) > 1 else "\\")
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))


def ensure_project_import_paths() -> None:
    for path in (PROJECT_ROOT, WORKSPACE_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def import_project_parameter_module(module_name: str) -> Any:
    ensure_project_import_paths()
    if module_name.startswith("params."):
        loaded_params = sys.modules.get("params")
        if loaded_params is not None and not hasattr(loaded_params, "__path__"):
            del sys.modules["params"]
        importlib.import_module("params")
        if str(PARAMS_ROOT) not in sys.path:
            sys.path.append(str(PARAMS_ROOT))
    return importlib.import_module(module_name)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def adaptive_period_minutes(cycles: int) -> int:
    """记录周期随圈数自适应：圈少用细周期（充放电曲线平滑），圈多自动放粗
    （控制求解输出点数 -> 内存/耗时）。曲线平滑度与长跑可行性的折中。"""
    if cycles <= 60:
        return 1
    if cycles <= 150:
        return 2
    if cycles <= 400:
        return 3
    if cycles <= 1000:
        return 5
    return 10


def normalize_request(request: dict[str, Any]) -> dict[str, Any]:
    cycles_requested = max(1, int(float(request.get("cycles", 1))))
    run_mode = str(request.get("run_mode", "smoke")).lower()
    if run_mode not in {"smoke", "production"}:
        run_mode = "smoke"
    if run_mode == "smoke":
        cycles = min(cycles_requested, MAX_UI_CYCLES)
    else:
        cycles = min(cycles_requested, MAX_PRODUCTION_CYCLES)
    charge_rate = float(request.get("charge_rate", 0.5))
    discharge_rate = float(request.get("discharge_rate", charge_rate))
    rate_unit = str(request.get("rate_unit", "C")).upper()
    if rate_unit not in {"C", "P"}:
        rate_unit = "C"
    nominal_voltage_v = float(request.get("nominal_voltage_v", 3.2))
    temperature_c = float(request.get("temperature_c", 25.0))
    parameter_set = str(request.get("parameter_set", "chen2020"))
    if parameter_set not in PARAMETER_SETS:
        parameter_set = "chen2020"
    model = str(request.get("model", "dfn")).lower()
    if model not in {"dfn", "spme"}:
        model = "dfn"
    aging_enabled = bool(request.get("aging_enabled", True))
    aging_options = normalize_aging_options(request.get("aging_options", {}), aging_enabled)

    return {
        "model": model,
        "parameter_set": parameter_set,
        "parameter_set_label": PARAMETER_SETS[parameter_set]["label"],
        "charge_rate": charge_rate,
        "discharge_rate": discharge_rate,
        "rate_unit": rate_unit,
        "nominal_voltage_v": nominal_voltage_v,
        "charge_cutoff_v": float(request.get("charge_cutoff_v", 3.65)),
        "discharge_cutoff_v": float(request.get("discharge_cutoff_v", 2.5)),
        "temperature_c": temperature_c,
        "temperature_k": temperature_c + 273.15,
        "cycles": cycles,
        "cycles_requested": cycles_requested,
        "run_mode": run_mode,
        "initial_soc": float(request.get("initial_soc", 0.5)),
        "aging_enabled": aging_enabled,
        "aging_options": aging_options,
        "rest_minutes": int(float(request.get("rest_minutes", 5))),
        "period_minutes": adaptive_period_minutes(cycles),
        "acceleration_factor": ACCELERATION_FACTOR if PARAMETER_SETS[parameter_set]["kind"] == "project" else 1,
        "dcr_enabled": bool(request.get("dcr_enabled", False)),
        "dcr_soc": min(max(float(request.get("dcr_soc", 0.5)), 0.05), 0.95),
        "dcr_rate": float(request.get("dcr_rate", 0.5)),
        "dcr_duration_s": float(request.get("dcr_duration_s", 10)),
        "dcr_every_cycles": max(1, int(float(request.get("dcr_every_cycles", 100)))),
    }


def normalize_aging_options(raw_options: Any, aging_enabled: bool) -> dict[str, str]:
    if not aging_enabled:
        return {}
    if not isinstance(raw_options, dict):
        raw_options = {}

    normalized: dict[str, str] = {}
    for name, allowed_values in AGING_OPTIONS.items():
        fallback = DEFAULT_AGING_OPTIONS[name]
        value = str(raw_options.get(name, fallback))
        normalized[name] = value if value in allowed_values else fallback

    if normalized["SEI"] == "none":
        normalized["SEI film resistance"] = "none"
        normalized["SEI porosity change"] = "false"
        normalized["SEI on cracks"] = "false"
    if normalized["particle mechanics"] != "swelling and cracking":
        normalized["SEI on cracks"] = "false"
    if normalized["particle mechanics"] == "none":
        normalized["stress-induced diffusion"] = "false"
    if normalized["lithium plating"] == "none":
        normalized["lithium plating porosity change"] = "false"
    return normalized


def append_log(status: dict[str, Any], level: str, message: str) -> None:
    status.setdefault("logs", []).append(
        {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        }
    )


def update_status(job_dir: Path, **changes: Any) -> None:
    status_path = job_dir / "status.json"
    status = read_json(status_path, {}) or {}
    status.update(changes)
    status["updated_at"] = time.time()
    atomic_write_json(status_path, status)


def log_status(job_dir: Path, level: str, message: str, **changes: Any) -> None:
    status_path = job_dir / "status.json"
    status = read_json(status_path, {}) or {}
    append_log(status, level, message)
    status.update(changes)
    status["updated_at"] = time.time()
    atomic_write_json(status_path, status)


def extrema_sample_indices(reference: Any, limit: int = 180) -> Any:
    """Pick <= `limit` sample indices preserving the per-window min and max of
    `reference`. Oscillating signals (voltage/current) keep their true peaks and
    troughs instead of being aliased away by uniform decimation. All series are
    sampled at the SAME indices so they stay aligned for plotting and CSV export."""
    import numpy as np

    array = np.asarray(reference, dtype=float).reshape(-1)
    size = array.size
    if size <= limit:
        return np.arange(size)
    n_windows = max(1, limit // 2)
    bounds = np.linspace(0, size, n_windows + 1).astype(int)
    picked: set[int] = {0, size - 1}
    for start, end in zip(bounds[:-1], bounds[1:]):
        if end <= start:
            continue
        window = array[start:end]
        local = np.where(np.isfinite(window))[0]
        if local.size == 0:
            picked.add(int(start))
            continue
        picked.add(int(start + local[np.argmin(window[local])]))
        picked.add(int(start + local[np.argmax(window[local])]))
    return np.array(sorted(picked))


def sample_at(values: Any, indices: Any) -> list:
    import numpy as np

    array = np.asarray(values, dtype=float).reshape(-1)
    if array.size == 0:
        return []
    indices = np.asarray(indices, dtype=int)
    indices = indices[indices < array.size]
    return [float(v) if np.isfinite(v) else None for v in array[indices]]


def finite_or_none(value: Any) -> float | None:
    import numpy as np

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def get_solution_entries(solution: Any, candidates: list[str]) -> Any:
    import numpy as np

    for candidate in candidates:
        try:
            return np.asarray(solution[candidate].entries, dtype=float)
        except Exception:
            continue
    return np.array([], dtype=float)


def build_parameter_values(pybamm: Any, request: dict[str, Any]) -> Any:
    ensure_project_import_paths()
    spec = PARAMETER_SETS[request["parameter_set"]]
    if spec["kind"] == "builtin":
        return pybamm.ParameterValues(spec["name"])

    params = pybamm.ParameterValues(spec["base"])
    crack_defaults = {
        key: params[key]
        for key in [
            "Positive electrode initial crack length [m]",
            "Positive electrode initial crack width [m]",
            "Negative electrode initial crack length [m]",
            "Negative electrode initial crack width [m]",
        ]
    }
    module = import_project_parameter_module(spec["module"])
    getter = getattr(module, "get_hithium_params")
    params.update(getter(request.get("acceleration_factor", 1), temperature=request["temperature_k"]))
    if request.get("aging_options", {}).get("particle mechanics") == "swelling and cracking":
        repaired = {}
        for key, fallback in crack_defaults.items():
            try:
                value = float(params[key])
            except (TypeError, ValueError):
                value = fallback
            if value <= 0:
                repaired[key] = fallback
        if repaired:
            params.update(repaired, check_already_exists=False)
    return params


def build_model(pybamm: Any, request: dict[str, Any]) -> Any:
    options = {
        "calculate discharge energy": "true",
        "contact resistance": "true",
        "open-circuit potential": ("current sigmoid", "current sigmoid"),
    }
    options.update(request.get("aging_options", {}))
    # PyBaMM tuple value = per-electrode (negative, positive). The parameter set
    # has no positive-electrode crack data (initial crack length = 0); running the
    # cracking model on the positive electrode gives NaN at t=0. So cracking is
    # applied to the negative electrode only: negative "swelling and cracking",
    # positive "swelling only" (matches the notebook config).
    if options.get("particle mechanics") == "swelling and cracking":
        options["particle mechanics"] = ("swelling and cracking", "swelling only")
    if request["model"] == "spme":
        return pybamm.lithium_ion.SPMe(options)
    return pybamm.lithium_ion.DFN(options)


def build_cycle_step(request: dict[str, Any], params: Any) -> tuple:
    if request["rate_unit"] == "P":
        nominal_capacity = float(params["Nominal cell capacity [A.h]"])
        reference_power = nominal_capacity * request["nominal_voltage_v"]
        charge_action = f"Charge at {round(request['charge_rate'] * reference_power, 3)} W"
        discharge_action = f"Discharge at {round(request['discharge_rate'] * reference_power, 3)} W"
    else:
        charge_action = f"Charge at {request['charge_rate']}C"
        discharge_action = f"Discharge at {request['discharge_rate']}C"
    return (
        f"{charge_action} until {request['charge_cutoff_v']} V "
        f"({request['period_minutes']} minute period)",
        f"Rest for {request['rest_minutes']} minutes ({request['period_minutes']} minute period)",
        f"{discharge_action} until {request['discharge_cutoff_v']} V "
        f"({request['period_minutes']} minute period)",
        f"Rest for {request['rest_minutes']} minutes ({request['period_minutes']} minute period)",
    )


def build_experiment(pybamm: Any, request: dict[str, Any], params: Any) -> Any:
    step = build_cycle_step(request, params)
    return pybamm.Experiment([step] * request["cycles"], temperature=request["temperature_k"])


def build_solver(pybamm: Any) -> tuple[Any, str]:
    try:
        return pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-6), "IDAKLUSolver"
    except Exception:
        return pybamm.CasadiSolver(mode="safe", rtol=1e-6, atol=1e-6), "CasadiSolver"


def fallback_solver(pybamm: Any) -> tuple[Any, str]:
    return pybamm.CasadiSolver(mode="safe", rtol=1e-6, atol=1e-6), "CasadiSolver"


def heartbeat(job_dir: Path, stop_event: threading.Event, start: float, cycles: int) -> None:
    while not stop_event.wait(1.0):
        current = read_json(job_dir / "status.json", {}) or {}
        if current.get("status") != "running":
            continue
        current_progress = float(current.get("progress", 20.0))
        progress = min(92.0, current_progress + 2.4)
        cycle = max(1, min(cycles, round(progress / 100 * cycles)))
        update_status(
            job_dir,
            progress=progress,
            current_cycle=cycle,
            elapsed_s=round(time.perf_counter() - start, 1),
        )


def compute_cycle_metrics(solution: Any, acceleration_factor: int = 1) -> dict[str, list[float]]:
    import numpy as np

    from src.analysis import compute_cycle_energies, get_discharge_capacity

    try:
        capacities = np.asarray(get_discharge_capacity(solution).get("discharge_capacity", []), dtype=float)
    except Exception:
        capacities = np.array([], dtype=float)
    try:
        energies = compute_cycle_energies(solution)
        efficiencies = np.asarray(energies.get("efficiency", []), dtype=float) * 100.0
        efficiencies[(efficiencies <= 0) | (efficiencies > 110)] = np.nan
    except Exception:
        efficiencies = np.array([], dtype=float)

    if capacities.size == 0:
        throughput = get_solution_entries(solution, ["Throughput capacity [A.h]", "Discharge capacity [A.h]"])
        if throughput.size:
            capacities = np.array([float(np.nanmax(throughput) - np.nanmin(throughput))], dtype=float)
    if efficiencies.size == 0 and capacities.size:
        efficiencies = np.full(capacities.shape, np.nan, dtype=float)

    common_len = int(min(capacities.size, efficiencies.size))
    if common_len == 0:
        return {"cycle": [], "capacity_ah": [], "efficiency_pct": []}
    capacity_list = [finite_or_none(value) for value in capacities[:common_len]]
    initial_capacity = next((value for value in capacity_list if value is not None and value > 0), None)
    retention_list = [
        (value / initial_capacity * 100.0 if value is not None and initial_capacity else None)
        for value in capacity_list
    ]
    return {
        "cycle": [int(value) * acceleration_factor for value in range(1, common_len + 1)],
        "capacity_ah": capacity_list,
        "retention_pct": retention_list,
        "efficiency_pct": [finite_or_none(value) for value in efficiencies[:common_len]],
    }


def build_cycle_curves(solution: Any, max_cycles: int = 30, seg_points: int = 1000, acceleration_factor: int = 1) -> list:
    """Per-cycle charge/discharge voltage-vs-capacity curves for the "curve
    evolution" plot (mirrors the notebook Cell 12). Each cycle yields a charge
    segment (I < 0) and a discharge segment (I > 0), capacity reset to start at 0.
    Cycles are sub-sampled to at most `max_cycles` evenly spaced indices so the
    chart stays light regardless of total cycle count."""
    import numpy as np

    try:
        cycles = solution.cycles
    except Exception:
        return []
    n = len(cycles)
    if n == 0:
        return []
    if n <= max_cycles:
        chosen = list(range(n))
    else:
        chosen = sorted(set(np.linspace(0, n - 1, max_cycles).round().astype(int).tolist()))

    curves = []
    for i in chosen:
        cyc = cycles[i]
        try:
            current = np.asarray(cyc["Current [A]"].entries, dtype=float)
            capacity = np.asarray(cyc["Throughput capacity [A.h]"].entries, dtype=float)
            voltage = np.asarray(cyc["Voltage [V]"].entries, dtype=float)
        except Exception:
            continue
        entry = {"cycle": (i + 1) * acceleration_factor}
        for key, mask in (("charge", current < 0), ("discharge", current > 0)):
            if not np.any(mask):
                entry[key] = []
                continue
            cap = capacity[mask]
            volt = voltage[mask]
            cap = cap - cap[0]
            if cap.size > seg_points:
                idx = np.linspace(0, cap.size - 1, seg_points).round().astype(int)
                cap = cap[idx]
                volt = volt[idx]
            entry[key] = [
                [float(c), float(v)]
                for c, v in zip(cap, volt)
                if np.isfinite(c) and np.isfinite(v)
            ]
        curves.append(entry)
    return curves


def build_result(solution: Any, request: dict[str, Any], solver_name: str, elapsed_s: float, dcr_series: Any = None) -> dict[str, Any]:
    import numpy as np

    time_h = get_solution_entries(solution, ["Time [h]"])
    voltage_v = get_solution_entries(solution, ["Voltage [V]", "Terminal voltage [V]"])
    current_a = get_solution_entries(solution, ["Current [A]"])
    temperature_k = get_solution_entries(
        solution,
        [
            "X-averaged cell temperature [K]",
            "Volume-averaged cell temperature [K]",
            "Cell temperature [K]",
        ],
    )
    capacity_ah = get_solution_entries(solution, ["Discharge capacity [A.h]", "Throughput capacity [A.h]"])
    if temperature_k.size:
        temperature_c = temperature_k - 273.15
    else:
        temperature_c = np.full_like(time_h, request["temperature_c"], dtype=float)

    accel = request.get("acceleration_factor", 1)
    cycle_metrics = compute_cycle_metrics(solution, accel)
    initial_capacity = cycle_metrics["capacity_ah"][0] if cycle_metrics["capacity_ah"] else None
    final_capacity = cycle_metrics["capacity_ah"][-1] if cycle_metrics["capacity_ah"] else None
    retention_pct = None
    if initial_capacity and final_capacity is not None:
        retention_pct = final_capacity / initial_capacity * 100.0
    finite_efficiencies = [value for value in cycle_metrics["efficiency_pct"] if value is not None]

    sample_idx = extrema_sample_indices(voltage_v if voltage_v.size else time_h)

    return {
        "request": request,
        "solver_name": solver_name,
        "elapsed_s": elapsed_s,
        "series": {
            "time_h": sample_at(time_h, sample_idx),
            "voltage_v": sample_at(voltage_v, sample_idx),
            "current_a": sample_at(current_a, sample_idx),
            "temperature_c": sample_at(temperature_c, sample_idx),
            "capacity_ah": sample_at(capacity_ah, sample_idx),
        },
        "cycle_curves": build_cycle_curves(solution, acceleration_factor=accel),
        "dcr_series": dcr_series,
        "cycle_metrics": cycle_metrics,
        "summary": {
            "cycle_count": len(cycle_metrics["cycle"]),
            "initial_capacity_ah": initial_capacity,
            "final_capacity_ah": final_capacity,
            "retention_pct": retention_pct,
            "mean_efficiency_pct": float(np.mean(finite_efficiencies)) if finite_efficiencies else None,
        },
    }


def run_dcr_simulation(pybamm, model, params, request, solver, solver_name, job_dir, start):
    """Block cycling + a DCR pulse test after each block (reuses
    src.simulation_dcr.perform_dcr_test). The DCR pulse branches from the aging
    end-state and is not fed back, so it does not pollute the aging trajectory.
    Returns (solution, dcr_series, solver_name)."""
    import numpy as np
    from src.simulation_dcr import perform_dcr_test
    from src.analysis import get_discharge_capacity

    accel = request.get("acceleration_factor", 1)
    sim_cycles = request["cycles"]
    block = max(1, round(request["dcr_every_cycles"] / accel))
    soc = request["dcr_soc"]
    pulse_c = request["dcr_rate"]
    pulse_s = request["dcr_duration_s"]
    precharge_c = 0.25
    nominal_current = float(params["Nominal cell capacity [A.h]"])
    step = build_cycle_step(request, params)

    dcr_cycles, dcr_values = [], []
    solution = None
    done = 0
    while done < sim_cycles:
        n = min(block, sim_cycles - done)
        exp = pybamm.Experiment([step] * n, temperature=request["temperature_k"])
        sim = pybamm.Simulation(model, parameter_values=params, experiment=exp, solver=solver, var_pts=VAR_PTS_STANDARD)
        try:
            if solution is None:
                solution = sim.solve(initial_soc=request["initial_soc"], calc_esoh=False)
            else:
                solution = sim.solve(starting_solution=solution, calc_esoh=False)
        except Exception as exc:
            if solver_name == "CasadiSolver" or solution is not None:
                raise
            log_status(job_dir, "WARN", f"IDAKLUSolver solve failed, switching CasadiSolver: {exc}")
            solver, solver_name = fallback_solver(pybamm)
            update_status(job_dir, solver_name=solver_name)
            sim = pybamm.Simulation(model, parameter_values=params, experiment=exp, solver=solver, var_pts=VAR_PTS_STANDARD)
            solution = sim.solve(initial_soc=request["initial_soc"], calc_esoh=False)
        done += n

        disch = np.asarray(get_discharge_capacity(solution).get("discharge_capacity", []), dtype=float)
        disch = disch[np.isfinite(disch)]
        cap = float(disch[-1]) if disch.size else nominal_current
        charge_time = cap / (nominal_current * precharge_c) if precharge_c > 0 else 1.0
        dcr = perform_dcr_test(
            solution, params, model, solver, VAR_PTS_STANDARD,
            current=nominal_current, C1=precharge_c, C2=pulse_c, t=pulse_s,
            charge_time=charge_time, target_soc=soc,
        )
        real_cycle = int(done * accel)
        dcr_cycles.append(real_cycle)
        dcr_values.append(round(float(dcr["dcr_mean"]) * 1000, 4))
        elapsed_s = round(time.perf_counter() - start, 1)
        log_status(
            job_dir, "INFO",
            f"DCR @ {real_cycle} cyc: {dcr['dcr_mean'] * 1000:.2f} mOhm",
            current_cycle=done, progress=min(92, 32 + int(60 * done / sim_cycles)),
            elapsed_s=elapsed_s,
        )
    return solution, {"cycle": dcr_cycles, "dcr_mohm": dcr_values}, solver_name


def run_cycle_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    job_dir = Path(job_dir_raw)
    start = time.perf_counter()
    heartbeat_stop = threading.Event()
    try:
        ensure_runtime_env()
        ensure_project_import_paths()

        import pybamm

        log_status(job_dir, "INFO", "正在创建 PyBaMM 模型", status="running", progress=10, elapsed_s=0)
        if request["run_mode"] == "smoke" and request["cycles_requested"] > request["cycles"]:
            log_status(
                job_dir,
                "WARN",
                f"当前 UI API 闭环限制为 {request['cycles']} 圈，已从 {request['cycles_requested']} 圈自动收敛到 smoke run。",
            )
        elif request["run_mode"] == "production" and request["cycles_requested"] > request["cycles"]:
            log_status(
                job_dir,
                "WARN",
                f"完整运行最多允许 {request['cycles']} 圈，已从 {request['cycles_requested']} 圈自动收敛。",
            )
        elif request["run_mode"] == "production":
            log_status(job_dir, "INFO", f"完整运行模式：按输入执行 {request['cycles']} 圈。")

        model = build_model(pybamm, request)
        log_status(job_dir, "INFO", f"模型: {request['model'].upper()}, 参数集: {request['parameter_set_label']}", progress=18)
        if request.get("aging_enabled"):
            aging_summary = ", ".join(f"{key}={value}" for key, value in request["aging_options"].items())
            log_status(job_dir, "INFO", f"老化接口: {aging_summary}")
        else:
            log_status(job_dir, "INFO", "老化接口: 未启用")
        params = build_parameter_values(pybamm, request)
        solver, solver_name = build_solver(pybamm)
        experiment = build_experiment(pybamm, request, params)
        log_status(job_dir, "INFO", f"求解器: {solver_name}", progress=25)
        log_status(
            job_dir,
            "INFO",
            (
                f"工况: {request['charge_rate']}{request['rate_unit']}/{request['discharge_rate']}{request['rate_unit']}, "
                f"{request['discharge_cutoff_v']}-{request['charge_cutoff_v']}V, "
                f"{request['temperature_c']}°C, 静置 {request['rest_minutes']} min, {request['cycles']} 圈"
            ),
            progress=32,
        )

        if request.get("dcr_enabled"):
            solution, dcr_series, solver_name = run_dcr_simulation(
                pybamm, model, params, request, solver, solver_name, job_dir, start
            )
            elapsed_s = round(time.perf_counter() - start, 1)
            result = build_result(solution, request, solver_name, elapsed_s, dcr_series)
            atomic_write_json(job_dir / "result.json", result)
            log_status(
                job_dir, "INFO",
                f"DCR done: {len(dcr_series['cycle'])} resistance points.",
                status="completed", progress=100,
                current_cycle=request["cycles"], elapsed_s=elapsed_s,
            )
            return

        hb_thread = threading.Thread(
            target=heartbeat,
            args=(job_dir, heartbeat_stop, start, request["cycles"]),
            daemon=True,
        )
        hb_thread.start()

        try:
            simulation = pybamm.Simulation(
                model,
                parameter_values=params,
                experiment=experiment,
                solver=solver,
                var_pts=VAR_PTS_STANDARD,
            )
            solution = simulation.solve(initial_soc=request["initial_soc"], calc_esoh=False)
        except Exception as first_exc:
            if solver_name == "CasadiSolver":
                raise
            log_status(job_dir, "WARN", f"{solver_name} 求解失败，切换 CasadiSolver 重试: {first_exc}")
            solver, solver_name = fallback_solver(pybamm)
            update_status(job_dir, solver_name=solver_name)
            simulation = pybamm.Simulation(
                model,
                parameter_values=params,
                experiment=experiment,
                solver=solver,
                var_pts=VAR_PTS_STANDARD,
            )
            solution = simulation.solve(initial_soc=request["initial_soc"], calc_esoh=False)
        heartbeat_stop.set()

        elapsed_s = round(time.perf_counter() - start, 1)
        log_status(job_dir, "INFO", "仿真求解完成，正在整理结果", progress=94, elapsed_s=elapsed_s)
        result = build_result(solution, request, solver_name, elapsed_s)
        atomic_write_json(job_dir / "result.json", result)
        log_status(
            job_dir,
            "INFO",
            f"结果整理完成，共 {result['summary']['cycle_count']} 个循环指标点。",
            status="completed",
            progress=100,
            current_cycle=request["cycles"],
            elapsed_s=elapsed_s,
        )
    except Exception as exc:
        heartbeat_stop.set()
        elapsed_s = round(time.perf_counter() - start, 1)
        log_status(
            job_dir,
            "ERROR",
            f"仿真失败: {exc}",
            status="failed",
            progress=100,
            elapsed_s=elapsed_s,
            error=str(exc),
            traceback=traceback.format_exc(),
        )


class JobManager:
    def __init__(self, job_root: Path = JOB_ROOT) -> None:
        self.job_root = job_root
        self.job_root.mkdir(parents=True, exist_ok=True)
        self.processes: dict[str, mp.Process] = {}
        self.context = mp.get_context("spawn")

    def create_job(self, request: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_request(request)
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.job_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        status = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "current_cycle": 0,
            "total_cycles": normalized["cycles"],
            "cycles_requested": normalized["cycles_requested"],
            "sim_time_h": 0,
            "elapsed_s": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
            "request": normalized,
            "logs": [],
        }
        append_log(status, "INFO", "仿真任务已创建")
        atomic_write_json(job_dir / "status.json", status)
        process = self.context.Process(target=run_cycle_worker, args=(str(job_dir), normalized), daemon=False)
        process.start()
        self.processes[job_id] = process
        update_status(job_dir, status="running", worker_pid=process.pid)
        return self.get_status(job_id)

    def get_status(self, job_id: str) -> dict[str, Any]:
        job_dir = self.job_root / job_id
        status = read_json(job_dir / "status.json", None)
        if not status:
            raise KeyError(job_id)
        process = self.processes.get(job_id)
        if process and not process.is_alive() and status.get("status") == "running":
            status["status"] = "failed"
            status["error"] = "Worker process exited unexpectedly."
            append_log(status, "ERROR", "Worker process exited unexpectedly.")
            atomic_write_json(job_dir / "status.json", status)
        return status

    def get_result(self, job_id: str) -> dict[str, Any]:
        result = read_json(self.job_root / job_id / "result.json", None)
        if not result:
            raise KeyError(job_id)
        return result

    def stop_job(self, job_id: str) -> dict[str, Any]:
        job_dir = self.job_root / job_id
        status = self.get_status(job_id)
        process = self.processes.get(job_id)
        if process and process.is_alive():
            process.terminate()
            process.join(timeout=3)
        log_status(job_dir, "WARN", "用户已停止仿真任务", status="canceled", progress=status.get("progress", 0))
        return self.get_status(job_id)

    def export_csv(self, job_id: str) -> str:
        result = self.get_result(job_id)
        rows = []
        metrics = result.get("cycle_metrics", {})
        for index, cycle in enumerate(metrics.get("cycle", [])):
            rows.append(
                {
                    "cycle": cycle,
                    "capacity_ah": _list_get(metrics.get("capacity_ah", []), index),
                    "efficiency_pct": _list_get(metrics.get("efficiency_pct", []), index),
                }
            )
        if not rows:
            series = result.get("series", {})
            for index, time_h in enumerate(series.get("time_h", [])):
                rows.append(
                    {
                        "time_h": time_h,
                        "voltage_v": _list_get(series.get("voltage_v", []), index),
                        "current_a": _list_get(series.get("current_a", []), index),
                        "temperature_c": _list_get(series.get("temperature_c", []), index),
                    }
                )

        if not rows:
            return ""

        output = []
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(_ListWriter(output), fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return "".join(output)


def _list_get(values: list[Any], index: int) -> Any:
    return values[index] if index < len(values) else ""


class _ListWriter:
    def __init__(self, rows: list[str]) -> None:
        self.rows = rows

    def write(self, value: str) -> None:
        self.rows.append(value)
