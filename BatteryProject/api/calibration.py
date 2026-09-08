"""参数标定与可辨识性 worker。

通过 api.jobs 的 JOB_TYPES["calibration"] 注册,由独立 worker 队列执行。
- 优化:MO(SLSQP,记录损失收敛历史,默认)/ DA(dual_annealing,无历史);
        BO/GO 保留 run_parameter_optimization 扩展(需 bayes-opt/pygad)。
- 可辨识性:最优参数局部 ±1% 扰动敏感度(敏感度低 -> 平坦方向,不可辨识)。
- run 目录:output/runs/calibration/<job_id>/(manifest + result)。

依赖 src.parameter_identification 的 build_aging_objective / params_to_model_input。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

# 惰性导入 api.jobs(避免循环 import)
def _jobs() -> Any:
    from api import jobs as _j

    return _j


def normalize_calibration_request(request: dict[str, Any]) -> dict[str, Any]:
    """标定请求规范化:change_params -> {name: [scope, scale, low, high]}。"""
    run_mode = str(request.get("run_mode", "smoke")).lower()
    if run_mode not in {"smoke", "production"}:
        run_mode = "smoke"
    raw_change = request.get("change_params") or {}
    change: dict[str, list[Any]] = {}
    for name, spec in raw_change.items():
        if isinstance(spec, dict):
            low = float(spec["low"])
            high = float(spec["high"])
            scale = str(spec.get("scale", "log" if low > 0 and high > 0 else "line"))
            change[str(name)] = [str(spec.get("scope", "user")), scale, low, high]
        else:
            change[str(name)] = [str(spec[0]), str(spec[1]), float(spec[2]), float(spec[3])]
    n_iter = max(3, min(int(float(request.get("n_iter", 20))), 60))
    cycles = max(1, min(int(float(request.get("cycles", 1))), 3))
    t_factor = int(float(request.get("t_factor", 50)))
    return {
        "job_type": "calibration",
        "cell": _jobs()._registry_cell(str(request.get("cell", "314"))),
        "dataset_id": str(request.get("dataset_id", "")),
        "method": str(request.get("method", "MO")).upper(),
        "n_iter": n_iter,
        "cycles": cycles,
        "t_factor": t_factor,
        "change_params": change,
        "run_mode": run_mode,
        # 进度单位:标定视为单步任务
        "cycles_requested": 1,
    }


def _build_simulate_fn(cell: str, cycles: int, t_factor: int):
    """构造标定目标用的 simulate_fn:任意参数修改 -> 短循环仿真 -> PyBaMM solution。"""
    import pybamm

    from src.notebook import load_params
    from src.simulation_pulse_lifecycle import DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS

    var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
    base_params = load_params(cell)(t_factor, 298.15)
    model_options = dict(DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS)

    def simulate_fn(model_input_params: dict[str, dict[str, float]]):
        merged = dict(base_params)
        merged.update(model_input_params.get("user") or {})
        merged.update(model_input_params.get("model") or {})
        model = pybamm.lithium_ion.DFN(options=model_options)
        param = pybamm.ParameterValues("OKane2022")
        param.update(merged, check_already_exists=False)
        solver = pybamm.IDAKLUSolver(rtol=1e-5, atol=1e-5)
        steps = [
            ("Discharge at C/2 until 2.5 V", "Charge at C/2 until 3.65 V", "Rest for 5 minutes")
        ] * cycles
        experiment = pybamm.Experiment(steps)
        simulation = pybamm.Simulation(
            model,
            parameter_values=param,
            experiment=experiment,
            solver=solver,
            var_pts=var_pts,
        )
        return simulation.solve(calc_esoh=False)

    return simulate_fn


def _build_exp_data(records: list[dict[str, Any]]) -> dict[str, list[np.ndarray]]:
    """从已导入数据集记录构造 exp_data:{cond -> [cycles, 归一化保持率]}。"""
    pairs = sorted(
        (float(record["cycle"]), float(record["capacity_ah"]))
        for record in records
        if record.get("cycle") is not None and record.get("capacity_ah") is not None
    )
    if not pairs or pairs[0][1] <= 0:
        raise ValueError("实验数据集缺少可用的 cycle/capacity_ah 序列")
    cycles = np.asarray([p[0] for p in pairs], dtype=float)
    caps = np.asarray([p[1] for p in pairs], dtype=float)
    return {"default": [cycles, caps / caps[0]]}


def _run_mo(objective, bounds: dict[str, tuple[float, float]], init: dict[str, float], max_iter: int) -> dict[str, Any]:
    """SLSQP 最小化(记录每次评估的损失历史)。"""
    from scipy.optimize import minimize

    keys = list(bounds)
    x0 = np.asarray([init.get(k, (lo + hi) / 2.0) for k, (lo, hi) in bounds.items()], dtype=float)
    scipy_bounds = [bounds[k] for k in keys]
    history: list[dict[str, Any]] = []

    def neg(x: np.ndarray) -> float:
        loss = -float(objective(dict(zip(keys, np.asarray(x, dtype=float)))))
        history.append({"iter": len(history) + 1, "loss": round(loss, 6)})
        return loss

    res = minimize(
        neg,
        x0,
        method="SLSQP",
        bounds=scipy_bounds,
        options={"maxiter": max_iter, "ftol": 1e-6},
    )
    return {
        "method": "MO",
        "success": bool(res.success),
        "message": str(res.message),
        "best_fitness": float(-res.fun),
        "best_params": {k: float(v) for k, v in zip(keys, res.x)},
        "loss_history": history,
    }


def _run_da(objective, bounds: dict[str, tuple[float, float]], init: dict[str, float], max_iter: int) -> dict[str, Any]:
    """dual_annealing 最小化(无历史)。"""
    from scipy.optimize import dual_annealing

    keys = list(bounds)
    x0 = np.asarray([init.get(k, (lo + hi) / 2.0) for k, (lo, hi) in bounds.items()], dtype=float)
    res = dual_annealing(lambda x: -float(objective(dict(zip(keys, x)))), bounds=list(bounds.values()), x0=x0, maxiter=max_iter)
    return {
        "method": "DA",
        "success": bool(res.success),
        "message": str(res.message),
        "best_fitness": float(-res.fun),
        "best_params": {k: float(v) for k, v in zip(keys, res.x)},
        "loss_history": [],
    }


def _local_sensitivity(objective, best_params: dict[str, float], rel: float = 0.01) -> list[dict[str, Any]]:
    """最优参数局部 ±rel 扰动敏感度(可辨识性指示)。"""
    rows: list[dict[str, Any]] = []
    for name, value in best_params.items():
        if value == 0:
            continue
        delta = abs(value) * rel
        try:
            up = float(objective({**best_params, name: value + delta}))
            down = float(objective({**best_params, name: value - delta}))
        except Exception:  # noqa: BLE001
            continue
        rows.append(
            {
                "param": name,
                "value": round(value, 8),
                "fitness_up": round(up, 6),
                "fitness_down": round(down, 6),
                "sensitivity": round(abs(up - down), 6),
            }
        )
    return sorted(rows, key=lambda row: -row["sensitivity"])


def run_calibration_worker(job_dir_raw: str, request: dict[str, Any]) -> None:
    job_dir = Path(job_dir_raw)
    start = time.perf_counter()
    try:
        jobs = _jobs()
        jobs.ensure_runtime_env()
        jobs.ensure_project_import_paths()
        jobs.log_status(job_dir, "INFO", "启动参数标定(构建仿真目标)", status="running", progress=5, elapsed_s=0)

        from src.parameter_identification import build_aging_objective

        # 1) 实验数据(已导入数据集)
        from api.studio_db import StudioDatabase
        from api.studio_io import StudioDataManager

        records = StudioDataManager(db=StudioDatabase()).load_records(request["dataset_id"])
        exp_data = _build_exp_data(records)
        jobs.log_status(job_dir, "INFO", f"实验数据: {len(records)} 行(cycle/capacity)", progress=15)

        # 2) 仿真目标
        simulate_fn = _build_simulate_fn(request["cell"], request["cycles"], request["t_factor"])
        change_params = {name: tuple(spec) for name, spec in request["change_params"].items()}
        objective = build_aging_objective(
            simulate_fn,
            change_params,
            exp_data,
            loss_type="cycle_line",
            t_factor=request["t_factor"],
            fail_penalty=100.0,
        )
        jobs.log_status(job_dir, "INFO", f"优化器: {request['method']}, 参数: {list(change_params)}", progress=25)

        # 3) 优化(搜索空间物理界 -> 优化空间由 _to_search_space 处理,这里直接给物理界)
        from src.parameter_identification import _parse_change_params, _to_search_space

        specs = _parse_change_params(change_params)
        bounds = _to_search_space(specs)  # 优化空间(log 已转)
        keys = list(bounds)

        def dict_objective(x: dict[str, float]) -> float:
            return float(objective(x))

        if request["method"] == "DA":
            out = _run_da(dict_objective, bounds, {}, request["n_iter"])
        else:  # 默认 MO
            out = _run_mo(dict_objective, bounds, {}, request["n_iter"])
        opt_best = out["best_params"]
        from src.parameter_identification import params_to_model_input

        model_input = params_to_model_input(opt_best, change_params, {})
        best = {**model_input.get("user", {}), **model_input.get("model", {})}
        jobs.log_status(job_dir, "INFO", f"优化完成: fitness={out['best_fitness']:.4g}", progress=75)

        # 4) 可辨识性:局部敏感度(在优化空间扰动,与 objective 一致)
        sensitivity = _local_sensitivity(dict_objective, opt_best)
        for row in sensitivity:
            if row["param"] in best:
                row["value"] = float(best[row["param"]])  # 保持原始精度(可能极小)
        out["best_params"] = best

        # 5) 落盘 run 目录 + result.json
        from src.workflow_runtime import create_run_context

        context = create_run_context(
            "calibration",
            {"job_type": "calibration", "request": request},
            project_root=jobs.PROJECT_ROOT,
            run_id=job_dir.name,
        )
        elapsed_s = round(time.perf_counter() - start, 1)
        manifest = {
            "workflow_id": "calibration",
            "job_type": "calibration",
            "job_id": job_dir.name,
            "cell": request["cell"],
            "run_mode": request.get("run_mode"),
            "pybamm_version": __import__("pybamm").__version__,
            "parameter_source": f"params registry: {request['cell']}",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_s": elapsed_s,
            "run_dir": str(context.run_dir),
        }
        import json as _json

        from src.workflow_runtime import write_json

        write_json(context.run_dir / "manifest.json", manifest)
        result = {
            "job_type": "calibration",
            "run_dir": str(context.run_dir),
            "manifest": manifest,
            "method": out["method"],
            "success": out.get("success"),
            "message": out.get("message", ""),
            "best_fitness": out["best_fitness"],
            "best_params": best,
            "loss_history": out.get("loss_history", []),
            "sensitivity": sensitivity,
            "bounds": {name: {"scope": spec.scope, "scale": spec.scale, "low": spec.low, "high": spec.high} for name, spec in specs.items()},
            "cell": request["cell"],
            "t_factor": request["t_factor"],
            "cycles": request["cycles"],
            "elapsed_s": elapsed_s,
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        jobs.atomic_write_json(job_dir / "result.json", result)
        jobs.log_status(
            job_dir,
            "INFO",
            f"标定完成: fitness={out['best_fitness']:.4g}, 用时 {elapsed_s}s",
            status="completed",
            progress=100,
            elapsed_s=elapsed_s,
        )
    except Exception as exc:  # noqa: BLE001
        jobs = _jobs()
        jobs.log_status(job_dir, "ERROR", f"标定失败: {type(exc).__name__}: {exc}", status="failed", progress=100)
        jobs.log_status(job_dir, "DEBUG", __import__("traceback").format_exc())
