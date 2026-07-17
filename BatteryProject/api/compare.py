"""对比分析：仿真 job 结果 vs 实测数据集（保持率/能效叠图 + RRMSE）。

纯函数，不依赖 FastAPI；误差指标复用 src.analysis.calc_rrmse。
"""
from __future__ import annotations

from typing import Any


def _exp_series(records: list[dict[str, Any]], key: str) -> tuple[list[float], list[float]]:
    pairs = sorted(
        (float(record["cycle"]), float(record[key]))
        for record in records
        if record.get("cycle") is not None and record.get(key) is not None
    )
    return [cycle for cycle, _v in pairs], [value for _c, value in pairs]


def _overlay(sim_cycles: Any, sim_values: Any, exp_cycles: list[float], exp_values: list[float]) -> dict[str, Any] | None:
    """把仿真序列插值到实测循环点上（仅重叠区间），返回叠图数据 + RMSE/RRMSE。"""
    import numpy as np

    from src.analysis import calc_rrmse

    sim_c = np.asarray(sim_cycles, dtype=float)
    sim_v = np.asarray(sim_values, dtype=float)
    finite = np.isfinite(sim_c) & np.isfinite(sim_v)
    sim_c, sim_v = sim_c[finite], sim_v[finite]
    if sim_c.size < 2 or len(exp_cycles) < 2:
        return None
    exp_c = np.asarray(exp_cycles, dtype=float)
    exp_v = np.asarray(exp_values, dtype=float)
    overlap = (exp_c >= sim_c.min()) & (exp_c <= sim_c.max())
    if overlap.sum() < 2:
        return None
    exp_c, exp_v = exp_c[overlap], exp_v[overlap]
    sim_interp = np.interp(exp_c, sim_c, sim_v)
    rmse, rrmse = calc_rrmse(exp_v, sim_interp)
    return {
        "cycle": exp_c.tolist(),
        "exp": exp_v.tolist(),
        "sim": sim_interp.tolist(),
        "sim_full": {"cycle": sim_c.tolist(), "values": sim_v.tolist()},
        "rmse": float(rmse),
        "rrmse_pct": float(rrmse) * 100.0,
    }


def compare_job_to_dataset(result: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = result.get("cycle_metrics") or {}
    sim_cycles = metrics.get("cycle") or []

    exp_cap_cycles, exp_caps = _exp_series(records, "capacity_ah")
    retention_block = None
    if exp_caps and exp_caps[0] > 0:
        exp_retention = [value / exp_caps[0] * 100.0 for value in exp_caps]
        retention_block = _overlay(sim_cycles, metrics.get("retention_pct") or [], exp_cap_cycles, exp_retention)

    exp_eff_cycles, exp_effs = _exp_series(records, "efficiency_pct")
    efficiency_block = _overlay(sim_cycles, metrics.get("efficiency_pct") or [], exp_eff_cycles, exp_effs)

    if retention_block is None and efficiency_block is None:
        raise ValueError("仿真与实测循环区间无重叠（或有效数据点不足），无法对比。")
    return {
        "ok": True,
        "retention": retention_block,
        "efficiency": efficiency_block,
        "sim_cycle_range": [min(sim_cycles), max(sim_cycles)] if sim_cycles else None,
        "exp_cycle_range": [exp_cap_cycles[0], exp_cap_cycles[-1]] if exp_cap_cycles else None,
    }
