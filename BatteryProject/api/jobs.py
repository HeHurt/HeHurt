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


# 进程内状态写锁：heartbeat 线程与 worker 主线程并发执行 read-modify-write
# 时保护临界区，避免互相覆盖丢失日志/进度。每个 job 运行在独立 spawn 子进程，
# 进程内只需一把锁即可覆盖同 job 的并发写。
_status_lock = threading.Lock()


def update_status(job_dir: Path, **changes: Any) -> None:
    status_path = job_dir / "status.json"
    with _status_lock:
        status = read_json(status_path, {}) or {}
        status.update(changes)
        status["updated_at"] = time.time()
        atomic_write_json(status_path, status)


def log_status(job_dir: Path, level: str, message: str, **changes: Any) -> None:
    status_path = job_dir / "status.json"
    with _status_lock:
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
    }
    # current sigmoid OCP needs lithiation/delithiation OCP data, which only the
    # project parameter sets provide; builtin sets (Chen2020/OKane2022) lack it.
    if PARAMETER_SETS[request["parameter_set"]]["kind"] == "project":
        options["open-circuit potential"] = ("current sigmoid", "current sigmoid")
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


# 退化机理逐圈变量（“衰减机理分析” tab）。键名 -> PyBaMM 变量候选（新旧版本命名兼容）。
DEGRADATION_VARIABLES = {
    "lli_pct": ["Loss of lithium inventory [%]"],
    "lam_neg_pct": ["Loss of active material in negative electrode [%]"],
    "lam_pos_pct": ["Loss of active material in positive electrode [%]"],
    "sei_ah": ["Loss of capacity to negative SEI [A.h]", "Loss of capacity to SEI [A.h]"],
    "sei_cracks_ah": ["Loss of capacity to negative SEI on cracks [A.h]", "Loss of capacity to SEI on cracks [A.h]"],
    "plating_ah": ["Loss of capacity to negative lithium plating [A.h]", "Loss of capacity to lithium plating [A.h]"],
}


def build_degradation_metrics(solution: Any, acceleration_factor: int = 1) -> dict[str, list] | None:
    """逐圈取各退化变量的圈末值。变量全部缺失（未开老化）时返回 None。"""
    try:
        cycles = solution.cycles
    except Exception:
        return None
    if not cycles:
        return None
    series: dict[str, list] = {key: [] for key in DEGRADATION_VARIABLES}
    cycle_numbers = []
    for index, cycle in enumerate(cycles):
        cycle_numbers.append((index + 1) * acceleration_factor)
        for key, names in DEGRADATION_VARIABLES.items():
            values = get_solution_entries(cycle, names)
            series[key].append(finite_or_none(values[-1]) if values.size else None)
    kept = {key: values for key, values in series.items() if any(v is not None for v in values)}
    if not kept:
        return None
    return {"cycle": cycle_numbers, **kept}


def build_heat_metrics(solution: Any, request: dict[str, Any]) -> dict[str, list] | None:
    """逐圈平均产热功率分量（不可逆/可逆 × 充/放）。

    完整计算依赖熵数据（src.config 的 dU/dT 表），加载失败时降级为仅不可逆热；
    再失败返回 None（前端显示“无产热数据”）。"""
    accel = request.get("acceleration_factor", 1)
    label = f"{request['temperature_c']}°C"
    try:
        from src.analysis import get_all_heat_components

        heat = get_all_heat_components(solution, label_for_temp=label)
    except Exception:
        try:
            from src.analysis import _collect_heat_components

            heat = _collect_heat_components(solution, label_for_temp=label, include_reversible=False)
        except Exception:
            return None
    cleaned: dict[str, list] = {}
    count = 0
    for key, values in heat.items():
        row = [finite_or_none(value) for value in values]
        if any(value is not None for value in row):
            cleaned[key] = row
            count = max(count, len(row))
    if not cleaned:
        return None
    cleaned["cycle"] = [(index + 1) * accel for index in range(count)]
    return cleaned


# “参数分布” tab 展示的关键参数（存在才收录；函数型参数标记不展开）。
KEY_PARAMETERS = [
    "Nominal cell capacity [A.h]",
    "Electrode height [m]",
    "Electrode width [m]",
    "Negative electrode thickness [m]",
    "Positive electrode thickness [m]",
    "Separator thickness [m]",
    "Negative electrode porosity",
    "Positive electrode porosity",
    "Separator porosity",
    "Negative particle radius [m]",
    "Positive particle radius [m]",
    "Maximum concentration in negative electrode [mol.m-3]",
    "Maximum concentration in positive electrode [mol.m-3]",
    "Initial concentration in negative electrode [mol.m-3]",
    "Initial concentration in positive electrode [mol.m-3]",
    "Initial concentration in electrolyte [mol.m-3]",
    "Negative electrode active material volume fraction",
    "Positive electrode active material volume fraction",
    "Contact resistance [Ohm]",
    "Ambient temperature [K]",
    "Upper voltage cut-off [V]",
    "Lower voltage cut-off [V]",
]


def snapshot_parameters(params: Any) -> list[dict[str, Any]]:
    snapshot = []
    for name in KEY_PARAMETERS:
        try:
            value = params[name]
        except KeyError:
            continue
        if isinstance(value, (int, float)):
            snapshot.append({"name": name, "value": float(value)})
        elif callable(value):
            snapshot.append({"name": name, "value": "函数（温度/浓度依赖）"})
        else:
            snapshot.append({"name": name, "value": str(value)})
    return snapshot


def build_result(solution: Any, request: dict[str, Any], solver_name: str, elapsed_s: float, dcr_series: Any = None, params: Any = None) -> dict[str, Any]:
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
        "degradation_metrics": build_degradation_metrics(solution, accel) if request.get("aging_enabled") else None,
        "heat_metrics": build_heat_metrics(solution, request),
        "parameters": snapshot_parameters(params) if params is not None else [],
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
            result = build_result(solution, request, solver_name, elapsed_s, dcr_series, params=params)
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
        result = build_result(solution, request, solver_name, elapsed_s, params=params)
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




# Studio PARAMETER_SETS 键 -> params registry 键(_CELL_PARAM_MODULES)
_CELL_ALIASES = {
    "hithium314": "314",
    "hithium587": "587",
    "hithium280": "280",
    "mic1175": "MIC1175",
}


from api.calibration import normalize_calibration_request, run_calibration_worker


def _registry_cell(cell: str) -> str:
    return _CELL_ALIASES.get(cell, cell)




def _json_array_from_text(raw: Any, default: list[Any]) -> list[Any]:
    """从请求解析 JSON 数组字符串或列表;解析失败回退默认。"""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return list(default)


def normalize_calendar_aging_request(request: dict[str, Any]) -> dict[str, Any]:
    run_mode = _normalize_run_mode(request)
    return {
        "job_type": "calendar_aging",
        "cell": _registry_cell(str(request.get("cell", "MIC"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "aging_mode": "activated" if str(request.get("aging_mode", "activated")) != "unactivated" else "unactivated",
        "activated_months": max(1, int(float(request.get("activated_months", 1)))),
        "diagnostic_rate_c": float(request.get("diagnostic_rate_c", 0.25)),
        "run_mode": run_mode,
        "cycles": 1,
        "cycles_requested": 1,
    }


def normalize_frequency_request(request: dict[str, Any]) -> dict[str, Any]:
    run_mode = _normalize_run_mode(request)
    scenarios = _json_array_from_text(
        request.get("scenarios"),
        [{"name": "A", "display_name": "30s/2.5MW", "pulse_seconds": 30, "total_pulses_per_day": 144, "sample_period_seconds": 900}],
    )
    real_days = max(1, int(float(request.get("real_days_total", 2))))
    if run_mode == "smoke":
        real_days = min(real_days, 1)
    return {
        "job_type": "frequency",
        "cell": _registry_cell(str(request.get("cell", "314"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "current_a": float(request.get("current_a", 293.5)),
        "real_days_total": real_days,
        "scenarios": scenarios,
        "run_mode": run_mode,
        "cycles": len(scenarios),
        "cycles_requested": len(scenarios),
    }


def normalize_pulse_request(request: dict[str, Any]) -> dict[str, Any]:
    run_mode = _normalize_run_mode(request)
    scenarios = _json_array_from_text(
        request.get("scenarios"),
        [{"name": "A", "display_name": "每5圈脉冲", "pulse_p_rate": 2.0, "pulse_seconds": 10, "base_p_rate": 0.25, "charge_interval_minutes": 60, "discharge_interval_minutes": 60}],
    )
    total_cycles = max(1, int(float(request.get("total_cycles", 4))))
    if run_mode == "smoke":
        total_cycles = min(total_cycles, 2)
    return {
        "job_type": "pulse",
        "cell": _registry_cell(str(request.get("cell", "314"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "base_p_rate": float(request.get("base_p_rate", 0.25)),
        "total_cycles": total_cycles,
        "scenarios": scenarios,
        "run_mode": run_mode,
        "cycles": total_cycles,
        "cycles_requested": total_cycles,
    }


def normalize_lifecycle_heat_request(request: dict[str, Any]) -> dict[str, Any]:
    run_mode = _normalize_run_mode(request)
    return {
        "job_type": "lifecycle_heat",
        "cell": _registry_cell(str(request.get("cell", "314"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "aging_p_rate": float(request.get("aging_p_rate", 0.5)),
        "diagnostic_p_rates": [float(v) for v in _json_array_from_text(request.get("diagnostic_p_rates"), [0.25, 0.5])],
        "contact_resistance_mohm": float(request.get("contact_resistance_mohm", 0.0)),
        "run_mode": run_mode,
        "cycles": 1,
        "cycles_requested": 1,
    }


def normalize_psd_request(request: dict[str, Any]) -> dict[str, Any]:
    run_mode = _normalize_run_mode(request)
    return {
        "job_type": "psd",
        "cell": _registry_cell(str(request.get("cell", "314"))),
        "selected_strategy": "bimodal" if str(request.get("selected_strategy", "bimodal")) != "single" else "single",
        "keep_percent": float(request.get("keep_percent", 99.0)),
        "materials": _json_array_from_text(request.get("materials"), []) or [],
        "run_mode": run_mode,
        "cycles": 1,
        "cycles_requested": 1,
    }


def normalize_regional_coupled_aging_request(request: dict[str, Any]) -> dict[str, Any]:
    run_mode = _normalize_run_mode(request)
    return {
        "job_type": "regional_coupled_aging",
        "cell": _registry_cell(str(request.get("cell", "314"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "run_mode": run_mode,
        "cycles": 1,
        "cycles_requested": 1,
    }


def _build_calendar_aging_spec(request: dict[str, Any]):
    from src.workflows.calendar_aging import CalendarAgingSpec

    return CalendarAgingSpec(
        cell=request["cell"],
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        temperature_c=request["temperature_c"],
        aging_mode=request["aging_mode"],
        activated_months=request["activated_months"],
        diagnostic_rate_c=request["diagnostic_rate_c"],
        output_name="日历老化",
    )


def _build_frequency_spec(request: dict[str, Any]):
    from src.workflows.frequency import FrequencyWorkflowSpec

    return FrequencyWorkflowSpec(
        cell=request["cell"],
        scenarios=tuple(dict(item) for item in request["scenarios"]),
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        real_days_total=request["real_days_total"],
        current_a=request["current_a"],
        temperature_c=request["temperature_c"],
        parallel=False,
        max_workers=1,
        output_name="调频",
    )


def _build_pulse_spec(request: dict[str, Any]):
    from src.workflows.pulse import PulseWorkflowSpec

    return PulseWorkflowSpec(
        cell=request["cell"],
        scenarios=tuple(dict(item) for item in request["scenarios"]),
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        total_cycles=request["total_cycles"],
        cycles_per_block=1,
        base_p_rate=request["base_p_rate"],
        temperature_c=request["temperature_c"],
        output_name="插入脉冲",
    )


def _build_lifecycle_heat_spec(request: dict[str, Any]):
    from src.workflows.lifecycle_heat import (
        ContactResistanceCase,
        EntropyCalibrationSpec,
        LifecycleHeatCondition,
        LifecycleHeatWorkflowSpec,
    )
    from src.workflow_specs import DatasetQuery

    return LifecycleHeatWorkflowSpec(
        cell=request["cell"],
        conditions=(
            LifecycleHeatCondition(
                temperature_c=request["temperature_c"],
                aging_p_rate=request["aging_p_rate"],
                diagnostic_p_rates=tuple(request["diagnostic_p_rates"]),
            ),
        ),
        contact_resistances=(ContactResistanceCase("base", request["contact_resistance_mohm"]),),
        entropy=EntropyCalibrationSpec(query=DatasetQuery(cell=request["cell"], test_type="熵")),
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        total_cycles=1,
        cycles_per_block=1,
        output_name="全生命周期产热",
    )


def _build_psd_spec(request: dict[str, Any]):
    from src.workflows.psd import PsdWorkflowSpec

    materials: dict[str, dict[str, Any]] = {}
    for item in request.get("materials") or []:
        if isinstance(item, dict) and item.get("name"):
            materials[str(item["name"])] = {k: v for k, v in item.items() if k != "name"}
    return PsdWorkflowSpec(
        cell=request["cell"],
        materials=materials,
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        selected_strategy=request["selected_strategy"],
        keep_percent=request["keep_percent"],
        rate_list=(0.5,),
        run_simulation=False,
        run_comsol_conversion=False,
        output_name="粒径分布",
    )


def _build_regional_coupled_aging_spec(request: dict[str, Any]):
    from src.workflows.regional_coupled_aging import RegionalCoupledAgingWorkflowSpec

    return RegionalCoupledAgingWorkflowSpec(
        cell=request["cell"],
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        temperature_c=request["temperature_c"],
        output_name="区域并联耦合老化",
    )


def run_calendar_aging_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.calendar_aging import run_calendar_aging_workflow

    _run_workflow_job(job_dir_raw, request, "calendar_aging", _build_calendar_aging_spec, run_calendar_aging_workflow)


def run_frequency_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.frequency import run_frequency_workflow

    _run_workflow_job(job_dir_raw, request, "frequency_regulation", _build_frequency_spec, run_frequency_workflow)


def run_pulse_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.pulse import run_pulse_workflow

    _run_workflow_job(job_dir_raw, request, "inserted_pulse", _build_pulse_spec, run_pulse_workflow)


def run_lifecycle_heat_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.lifecycle_heat import run_lifecycle_heat_workflow

    _run_workflow_job(job_dir_raw, request, "lifecycle_heat", _build_lifecycle_heat_spec, run_lifecycle_heat_workflow)


def run_psd_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.psd import run_psd_workflow

    _run_workflow_job(job_dir_raw, request, "psd", _build_psd_spec, run_psd_workflow)


def run_regional_coupled_aging_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.regional_coupled_aging import run_regional_coupled_aging_workflow

    _run_workflow_job(job_dir_raw, request, "regional_coupled_aging", _build_regional_coupled_aging_spec, run_regional_coupled_aging_workflow)


def _normalize_run_mode(request: dict[str, Any], default: str = "smoke") -> str:
    run_mode = str(request.get("run_mode", default)).lower()
    return run_mode if run_mode in {"smoke", "production"} else "smoke"


def normalize_peak_request(request: dict[str, Any]) -> dict[str, Any]:
    """峰值电流/功率任务请求规范化(progress 单位 = SOC 扫描点数)。"""
    run_mode = _normalize_run_mode(request)
    soc_list = [min(max(float(v), 0.02), 0.98) for v in request.get("soc_list", [0.95, 0.5, 0.2])]
    if run_mode == "smoke":
        soc_list = soc_list[:2]
    if not soc_list:
        soc_list = [0.5]
    return {
        "job_type": "peak_current",
        "cell": _registry_cell(str(request.get("cell", "hithium314"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "pulse_duration_s": float(request.get("pulse_duration_s", 10.0)),
        "mode": "W" if str(request.get("mode", "A")).upper() == "W" else "A",
        "direction": str(request.get("direction", "both")).lower(),
        "soc_list": soc_list,
        "run_mode": run_mode,
        "cycles": len(soc_list),
        "cycles_requested": len(soc_list),
    }


def normalize_eis_request(request: dict[str, Any]) -> dict[str, Any]:
    """EIS 阻抗任务请求规范化(progress 单位 = 频率点数)。"""
    run_mode = _normalize_run_mode(request)
    frequencies = [max(float(v), 1e-3) for v in request.get("frequencies_hz", [0.1, 1.0, 10.0, 100.0, 1000.0])]
    if run_mode == "smoke":
        frequencies = frequencies[:3]
    return {
        "job_type": "eis",
        "cell": _registry_cell(str(request.get("cell", "hithium314"))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "soc": min(max(float(request.get("soc", 0.5)), 0.05), 0.95),
        "frequencies_hz": frequencies,
        "run_lifecycle": bool(request.get("run_lifecycle", False)),
        "run_mode": run_mode,
        "cycles": len(frequencies),
        "cycles_requested": len(frequencies),
    }


def normalize_rate_benchmark_request(request: dict[str, Any]) -> dict[str, Any]:
    """倍率对标任务请求规范化(progress 单位 = 倍率组数)。"""
    run_mode = _normalize_run_mode(request)
    rates = [max(float(v), 0.05) for v in request.get("rates", [0.5, 1.0])]
    if run_mode == "smoke":
        rates = rates[:2]
    return {
        "job_type": "rate_benchmark",
        "cell": _registry_cell(str(request.get("cell", "hithium314"))),
        "rates": rates,
        "cycles_per_rate": max(1, int(float(request.get("cycles_per_rate", 1)))),
        "temperature_c": float(request.get("temperature_c", 25.0)),
        "compare_dataset": str(request.get("compare_dataset", "")),
        "run_mode": run_mode,
        "cycles": len(rates),
        "cycles_requested": len(rates),
    }


def _build_eis_spec(request: dict[str, Any]):
    from src.workflows.eis import EisWorkflowSpec

    return EisWorkflowSpec(
        cell=request["cell"],
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        base_temperature_c=request["temperature_c"],
        base_soc=request["soc"],
        quick_frequencies_hz=tuple(request["frequencies_hz"]),
        run_quick_eis=True,
        run_soc_sweep=False,
        run_temperature_sweep=False,
        run_lifecycle=request.get("run_lifecycle", False),
        output_name="EIS 阻抗分析",
    )


def _build_rate_benchmark_spec(request: dict[str, Any]):
    from src.workflows.cycle import CycleCondition, CycleWorkflowSpec

    conditions = tuple(CycleCondition(request["temperature_c"], rate) for rate in request["rates"])
    return CycleWorkflowSpec(
        cell=request["cell"],
        conditions=conditions,
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        total_cycles=request["cycles_per_rate"],
        rest_minutes=5.0,
        period_minutes=1.0,
        output_name="倍率对标",
    )


def _build_peak_spec(request: dict[str, Any]):
    from src.workflows.peak_current import PeakCurrentWorkflowSpec

    return PeakCurrentWorkflowSpec(
        cell=request["cell"],
        run_mode="study" if request["run_mode"] == "production" else "smoke",
        temperature_c=request["temperature_c"],
        pulse_duration_s=request["pulse_duration_s"],
        mode=request["mode"],
        direction=request["direction"],
        soc_list=tuple(request["soc_list"]),
    )


def _json_safe_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """把 workflow 返回的 summary 收敛为 JSON 安全结构(只保留标量/列表/字典)。"""
    safe: dict[str, Any] = {}
    for key, value in summary.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(value, (list, tuple)):
            try:
                json.dumps(list(value))
                safe[key] = list(value)
            except TypeError:
                safe[key] = [str(item) for item in value][:50]
        elif isinstance(value, dict):
            try:
                json.dumps(value)
                safe[key] = value
            except TypeError:
                safe[key] = {k: str(v) for k, v in value.items()}
        else:
            safe[key] = str(value)
    return safe


def _run_workflow_job(job_dir_raw: str, request: dict[str, Any], workflow_id: str, build_spec_fn, run_fn) -> None:
    """通用 workflow worker:构建 spec -> 调 run_*_workflow(run_id=job_id) -> 回写 result.json/status.json。"""
    job_dir = Path(job_dir_raw)
    start = time.perf_counter()
    try:
        ensure_runtime_env()
        ensure_project_import_paths()
        import pybamm  # noqa: F401  环境预热

        job_type = request.get("job_type", workflow_id)
        log_status(job_dir, "INFO", f"创建 {job_type} 工作流", status="running", progress=10, elapsed_s=0)
        spec = build_spec_fn(request)
        log_status(
            job_dir,
            "INFO",
            f"spec 已就绪: {job_type}, cell={request.get('cell')}, run_mode={request.get('run_mode')}",
            progress=25,
        )
        run_out = run_fn(spec, project_root=PROJECT_ROOT, run_id=job_dir.name)
        elapsed_s = round(time.perf_counter() - start, 1)
        summary = run_out.get("summary") if isinstance(run_out, dict) and run_out.get("summary") else {}
        if not summary and isinstance(run_out, dict):
            metrics = run_out.get("metrics")
            if metrics is not None:
                try:
                    summary = {"rows": int(len(metrics))}
                except (TypeError, ValueError):
                    summary = {}
        metrics_path = (
            str(run_out.get("metrics_path"))
            if isinstance(run_out, dict) and run_out.get("metrics_path")
            else ""
        )
        run_dir = str(Path(PROJECT_ROOT) / "output" / "runs" / workflow_id / job_dir.name)
        manifest = {
            "workflow_id": workflow_id,
            "job_type": job_type,
            "job_id": job_dir.name,
            "run_mode": request.get("run_mode"),
            "cell": request.get("cell"),
            "pybamm_version": pybamm.__version__,
            "parameter_source": f"params registry: {request.get('cell')}",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_s": elapsed_s,
            "request": request,
            "run_dir": run_dir,
        }
        run_dir_path = Path(run_dir)
        run_dir_path.mkdir(parents=True, exist_ok=True)
        atomic_write_json(run_dir_path / "manifest.json", manifest)
        result = {
            "job_type": job_type,
            "run_mode": request.get("run_mode"),
            "workflow_id": workflow_id,
            "run_dir": run_dir,
            "metrics_path": metrics_path,
            "summary": _json_safe_summary(summary),
            "manifest": manifest,
            "elapsed_s": elapsed_s,
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        atomic_write_json(job_dir / "result.json", result)
        log_status(
            job_dir,
            "INFO",
            f"{job_type} 完成: run_dir={run_dir}, rows={len(summary.get('results', []))}",
            status="completed",
            progress=100,
            elapsed_s=elapsed_s,
        )
    except Exception as exc:  # noqa: BLE001
        log_status(job_dir, "ERROR", f"{type(exc).__name__}: {exc}", status="failed", progress=100)
        log_status(job_dir, "DEBUG", traceback.format_exc())


def run_peak_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.peak_current import run_peak_workflow

    _run_workflow_job(job_dir_raw, request, "peak_current", _build_peak_spec, run_peak_workflow)


def run_eis_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.eis import run_eis_workflow

    _run_workflow_job(job_dir_raw, request, "eis", _build_eis_spec, run_eis_workflow)


def run_rate_benchmark_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    from src.workflows.cycle import run_cycle_workflow

    _run_workflow_job(job_dir_raw, request, "cycle_aging", _build_rate_benchmark_spec, run_cycle_workflow)


# 尚未接入 Studio 运行时的 workflow(任务中心显示为「规划中」)
PLANNED_JOB_TYPES: list[tuple[str, str]] = []


# 任务类型注册表：每类仿真在此登记 normalize（请求规范化）+ worker（子进程入口）。
# 新增仿真类型（干涸/RPT/EIS/峰值电流…）时在此注册新条目，
# worker 必须是模块级函数（spawn 进程要求可 pickle），不要往 run_cycle_worker 里加分支。
JOB_TYPES: dict[str, dict[str, Any]] = {
    "cycle": {
        "label": "循环老化仿真",
        "normalize": normalize_request,
        "worker": run_cycle_worker,
        "schema": [
            {"name": "parameter_set", "label": "参数集", "type": "select", "default": "hithium314",
             "options": ["hithium314", "hithium587", "mic1175", "hithium280", "chen2020", "okane2022"]},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "charge_rate", "label": "充电倍率", "type": "number", "default": 0.5, "unit": "C", "min": 0.05, "max": 10, "step": 0.05},
            {"name": "discharge_rate", "label": "放电倍率", "type": "number", "default": 0.5, "unit": "C", "min": 0.05, "max": 10, "step": 0.05},
            {"name": "cycles", "label": "循环次数", "type": "number", "default": 1, "unit": "圈", "min": 1, "max": 2000},
            {"name": "charge_cutoff_v", "label": "截止电压上限", "type": "number", "default": 3.65, "unit": "V", "min": 2.5, "max": 4.5, "step": 0.01},
            {"name": "discharge_cutoff_v", "label": "截止电压下限", "type": "number", "default": 2.5, "unit": "V", "min": 1.5, "max": 3.6, "step": 0.01},
            {"name": "rest_minutes", "label": "静置时长", "type": "number", "default": 5, "unit": "min", "min": 0, "max": 120},
            {"name": "initial_soc", "label": "初始 SOC", "type": "number", "default": 0.5, "min": 0.05, "max": 0.95, "step": 0.05},
            {"name": "aging_enabled", "label": "启用老化模型", "type": "checkbox", "default": True},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke",
             "options": ["smoke", "production"], "desc": "smoke 自动收敛到 ≤3 圈;production 最多 2000 圈"},
        ],
    },
    "peak_current": {
        "label": "峰值电流/功率",
        "normalize": normalize_peak_request,
        "worker": run_peak_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314",
             "desc": "params registry 键:314 / 587 / MIC / MIC1175 / 280 / 50 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "pulse_duration_s", "label": "脉冲时长", "type": "number", "default": 10.0, "unit": "s", "min": 1, "max": 120},
            {"name": "mode", "label": "搜索模式", "type": "select", "default": "A", "options": ["A", "W"], "desc": "A=恒流 / W=恒功率"},
            {"name": "direction", "label": "搜索方向", "type": "select", "default": "both", "options": ["both", "charge", "discharge"]},
            {"name": "soc_list", "label": "扫描 SOC 列表", "type": "text", "default": "0.9,0.5,0.2", "desc": "逗号分隔,取值 0-1"},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "eis": {
        "label": "EIS 阻抗分析",
        "normalize": normalize_eis_request,
        "worker": run_eis_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314",
             "desc": "params registry 键:314 / 587 / MIC / MIC1175 / 280 / 50 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "soc", "label": "测试 SOC", "type": "number", "default": 0.5, "min": 0.05, "max": 0.95, "step": 0.05},
            {"name": "frequencies_hz", "label": "频率点 (Hz)", "type": "text", "default": "0.1,1,10,100,1000", "desc": "逗号分隔"},
            {"name": "run_lifecycle", "label": "生命周期 EIS 扫描", "type": "checkbox", "default": False},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "rate_benchmark": {
        "label": "倍率对标",
        "normalize": normalize_rate_benchmark_request,
        "worker": run_rate_benchmark_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314",
             "desc": "params registry 键:314 / 587 / MIC / MIC1175 / 280 / 50 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "rates", "label": "倍率组", "type": "text", "default": "0.5,1.0", "desc": "逗号分隔"},
            {"name": "cycles_per_rate", "label": "每倍率圈数", "type": "number", "default": 1, "unit": "圈", "min": 1, "max": 200},
            {"name": "compare_dataset", "label": "对标数据集 (可选)", "type": "text", "default": "", "desc": "registry 数据集路径关键字"},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "calendar_aging": {
        "label": "日历老化",
        "normalize": normalize_calendar_aging_request,
        "worker": run_calendar_aging_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "MIC", "desc": "params registry 键:MIC / 314 / 587 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "aging_mode", "label": "老化模式", "type": "select", "default": "activated", "options": ["activated", "unactivated"]},
            {"name": "activated_months", "label": "活化后时长", "type": "number", "default": 1, "unit": "月", "min": 1, "max": 60},
            {"name": "diagnostic_rate_c", "label": "诊断倍率", "type": "number", "default": 0.25, "unit": "C", "min": 0.05, "max": 2},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "frequency": {
        "label": "调频",
        "normalize": normalize_frequency_request,
        "worker": run_frequency_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314", "desc": "params registry 键:314 / 587 / MIC 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "current_a", "label": "脉冲电流", "type": "number", "default": 293.5, "unit": "A", "min": 1, "max": 5000},
            {"name": "real_days_total", "label": "模拟真实天数", "type": "number", "default": 2, "unit": "天", "min": 1, "max": 30},
            {"name": "scenarios", "label": "场景 JSON", "type": "text", "default": "[{\"name\": \"A\", \"display_name\": \"30s/2.5MW\", \"pulse_seconds\": 30, \"total_pulses_per_day\": 144, \"sample_period_seconds\": 900}]", "desc": "JSON 数组,字段 name/display_name/pulse_seconds/total_pulses_per_day/sample_period_seconds"},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "pulse": {
        "label": "插入脉冲",
        "normalize": normalize_pulse_request,
        "worker": run_pulse_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314", "desc": "params registry 键:314 / 587 / MIC 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "base_p_rate", "label": "基准 P 倍率", "type": "number", "default": 0.25, "min": 0.05, "max": 2},
            {"name": "total_cycles", "label": "循环次数", "type": "number", "default": 4, "unit": "圈", "min": 1, "max": 500},
            {"name": "scenarios", "label": "场景 JSON", "type": "text", "default": "[{\"name\": \"A\", \"display_name\": \"每5圈脉冲\", \"pulse_p_rate\": 2.0, \"pulse_seconds\": 10, \"base_p_rate\": 0.25, \"charge_interval_minutes\": 60, \"discharge_interval_minutes\": 60}]", "desc": "JSON 数组,字段 name/display_name/pulse_p_rate/pulse_seconds"},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "lifecycle_heat": {
        "label": "全生命周期产热",
        "normalize": normalize_lifecycle_heat_request,
        "worker": run_lifecycle_heat_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314", "desc": "params registry 键:314 / 587 / MIC 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "aging_p_rate", "label": "老化 P 倍率", "type": "number", "default": 0.5, "min": 0.05, "max": 2},
            {"name": "diagnostic_p_rates", "label": "诊断 P 倍率", "type": "text", "default": "[0.25, 0.5]", "desc": "JSON 数组"},
            {"name": "contact_resistance_mohm", "label": "接触电阻", "type": "number", "default": 0.0, "unit": "mΩ", "min": 0, "max": 10},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "psd": {
        "label": "粒径分布 (PSD)",
        "normalize": normalize_psd_request,
        "worker": run_psd_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314", "desc": "params registry 键:314 / 587 / MIC 等"},
            {"name": "selected_strategy", "label": "拟合策略", "type": "select", "default": "bimodal", "options": ["bimodal", "single"]},
            {"name": "keep_percent", "label": "保留质量占比", "type": "number", "default": 99.0, "unit": "%", "min": 1, "max": 100},
            {"name": "materials", "label": "材料 JSON", "type": "text", "default": "[]", "desc": "JSON 数组,如 [{\"name\": \"NMC\", \"d50_um\": 5.0}]"},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "regional_coupled_aging": {
        "label": "区域并联耦合老化",
        "normalize": normalize_regional_coupled_aging_request,
        "worker": run_regional_coupled_aging_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314", "desc": "params registry 键:314 / 587 / MIC 等"},
            {"name": "temperature_c", "label": "环境温度", "type": "number", "default": 25.0, "unit": "°C", "min": -20, "max": 60},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
    "calibration": {
        "label": "参数标定",
        "normalize": normalize_calibration_request,
        "worker": run_calibration_worker,
        "schema": [
            {"name": "cell", "label": "电芯参数集", "type": "text", "default": "314", "desc": "params registry 键:314 / 587 / MIC 等"},
            {"name": "dataset_id", "label": "实验数据集 ID", "type": "text", "default": "", "desc": "已导入数据集 id(数据管理视图可查)"},
            {"name": "method", "label": "优化器", "type": "select", "default": "MO",
             "options": ["MO", "DA", "BO", "GO"], "desc": "MO=SLSQP(推荐,带损失收敛历史);DA=模拟退火;BO/GO 需 bayes-opt/pygad"},
            {"name": "n_iter", "label": "最大迭代", "type": "number", "default": 20, "min": 3, "max": 60},
            {"name": "cycles", "label": "每条件仿真圈数", "type": "number", "default": 1, "unit": "圈", "min": 1, "max": 3},
            {"name": "t_factor", "label": "等效圈加速", "type": "number", "default": 50, "min": 10, "max": 100, "desc": "1 仿真圈 = t_factor 等效圈"},
            {"name": "change_params", "label": "待辨识参数 JSON", "type": "text",
             "default": "{\"Negative electrode diffusivity [m2.s-1]\": {\"low\": 1e-15, \"high\": 1e-13}}",
             "desc": "JSON 对象:参数名 -> {low, high}(scope=user, log 缩放)"},
            {"name": "run_mode", "label": "运行模式", "type": "select", "default": "smoke", "options": ["smoke", "production"]},
        ],
    },
}


def resolve_job_type(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    job_type = str(request.get("job_type", "cycle")).lower()
    spec = JOB_TYPES.get(job_type)
    if spec is None:
        raise ValueError(f"未知任务类型: {job_type}（可用: {', '.join(sorted(JOB_TYPES))}）")
    return job_type, spec


def _upsert_job_record(status: dict[str, Any], job_dir: Path) -> None:
    """把任务快照写入 sqlite jobs 表(持久化队列的事实源,供独立 worker 消费)。"""
    from api.studio_db import StudioDatabase

    StudioDatabase().upsert_job(status, job_dir)


class JobManager:
    def __init__(self, job_root: Path = JOB_ROOT) -> None:
        self.job_root = job_root
        self.job_root.mkdir(parents=True, exist_ok=True)

    def create_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """入队模式:写 status.json(queued) + sqlite jobs 表,由独立 worker 消费。"""
        job_type, spec = resolve_job_type(request)
        normalized = spec["normalize"](request)
        normalized["job_type"] = job_type
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.job_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        status = {
            "job_id": job_id,
            "job_type": job_type,
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
        append_log(status, "INFO", "仿真任务已入队，等待独立 worker 执行")
        atomic_write_json(job_dir / "status.json", status)
        _upsert_job_record(status, job_dir)
        return status

    def get_status(self, job_id: str) -> dict[str, Any]:
        status = read_json(self.job_root / job_id / "status.json", None)
        if not status:
            raise KeyError(job_id)
        return status

    def get_result(self, job_id: str) -> dict[str, Any]:
        result = read_json(self.job_root / job_id / "result.json", None)
        if not result:
            raise KeyError(job_id)
        return result

    def stop_job(self, job_id: str) -> dict[str, Any]:
        job_dir = self.job_root / job_id
        status = self.get_status(job_id)
        if status.get("status") in {"queued", "running"}:
            log_status(
                job_dir,
                "WARN",
                "用户已请求停止任务(worker 将终止执行)",
                status="canceled",
                progress=status.get("progress", 0),
                cancel_requested=True,
            )
        return self.get_status(job_id)

    def delete_job(self, job_id: str) -> dict[str, Any]:
        """删除任务:sqlite 删除 + 删 job_dir + 删 run_dir(若存在)。running/queued 拒绝。"""
        status = read_json(self.job_root / job_id / "status.json", None)
        if not status:
            from api.studio_db import StudioDatabase as _SD

            _SD().delete_job(job_id)
            return {"ok": True, "deleted": False, "reason": "sqlite-only(无 status.json)"}
        if status.get("status") in {"running", "queued"}:
            raise ValueError(f"任务 {job_id} 正在 {status.get('status')},请先停止或等待完成后再删除")
        job_dir = self.job_root / job_id
        run_dir_text = (read_json(job_dir / "status.json", {}) or {}).get("request", {})
        from api.studio_db import StudioDatabase as _SD

        deleted_db = _SD().delete_job(job_id)
        from pathlib import Path as _Path

        removed_files: list[str] = []
        for path in (job_dir, _Path(str(status.get("run_dir", "") or "")) if status.get("run_dir") else None):
            if path and _Path(str(path)).exists():
                try:
                    shutil.rmtree(str(path))
                    removed_files.append(str(path))
                except OSError as exc:
                    removed_files.append(f"{path}(删除失败:{exc})")
        return {"ok": True, "deleted": deleted_db, "removed": removed_files}

    def export_csv(self, job_id: str) -> str:
        result = self.get_result(job_id)
        rows = []
        metrics = result.get("cycle_metrics", {})
        dcr_series = result.get("dcr_series") or {}
        dcr_by_cycle = {
            cycle: _list_get(dcr_series.get("dcr_mohm", []), index)
            for index, cycle in enumerate(dcr_series.get("cycle", []))
        }
        for index, cycle in enumerate(metrics.get("cycle", [])):
            rows.append(
                {
                    "cycle": cycle,
                    "capacity_ah": _list_get(metrics.get("capacity_ah", []), index),
                    "retention_pct": _list_get(metrics.get("retention_pct", []), index),
                    "efficiency_pct": _list_get(metrics.get("efficiency_pct", []), index),
                    "dcr_mohm": dcr_by_cycle.get(cycle, ""),
                }
            )
        metric_cycles = set(metrics.get("cycle", []))
        for cycle, dcr_mohm in dcr_by_cycle.items():
            if cycle in metric_cycles:
                continue
            rows.append(
                {
                    "cycle": cycle,
                    "capacity_ah": "",
                    "retention_pct": "",
                    "efficiency_pct": "",
                    "dcr_mohm": dcr_mohm,
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
