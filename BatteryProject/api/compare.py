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


# ============ Sim-Exp 对标工作台(2026-08-05) ============

def _anomaly_windows(block: dict[str, Any], threshold_pct: float, window_ratio: float = 0.1) -> list[dict[str, Any]]:
    """滑动窗口定位异常区间:每窗口计算 RRMSE,超阈值的窗口合并为异常区间。"""
    import numpy as np

    if not block:
        return []
    cycles = np.asarray(block["cycle"], dtype=float)
    exp = np.asarray(block["exp"], dtype=float)
    sim = np.asarray(block["sim"], dtype=float)
    n = len(cycles)
    if n < 4:
        return []
    win = max(3, int(round(n * window_ratio)))
    step = max(1, win // 2)
    windows: list[dict[str, Any]] = []
    for start in range(0, n - win + 1, step):
        e = exp[start : start + win]
        s = sim[start : start + win]
        diff = e - s
        rmse = float(np.sqrt(np.mean(diff**2)))
        scale = float(np.mean(np.abs(e))) or 1.0
        rrmse = rmse / scale * 100.0
        if rrmse > threshold_pct:
            windows.append(
                {
                    "start_cycle": round(float(cycles[start]), 1),
                    "end_cycle": round(float(cycles[start + win - 1]), 1),
                    "rmse": round(rmse, 4),
                    "rrmse_pct": round(rrmse, 2),
                    "severity": "高" if rrmse > threshold_pct * 2 else "中",
                }
            )
    merged: list[dict[str, Any]] = []
    for window in windows:
        if merged and window["start_cycle"] <= merged[-1]["end_cycle"]:
            merged[-1]["end_cycle"] = max(merged[-1]["end_cycle"], window["end_cycle"])
            merged[-1]["rmse"] = max(merged[-1]["rmse"], window["rmse"])
            merged[-1]["rrmse_pct"] = max(merged[-1]["rrmse_pct"], window["rrmse_pct"])
            merged[-1]["severity"] = "高" if merged[-1]["rrmse_pct"] > threshold_pct * 2 else "中"
        else:
            merged.append(dict(window))
    return merged


def bench_sim_exp(
    job_id: str,
    dataset_id: str,
    result: dict[str, Any],
    records: list[dict[str, Any]],
    threshold_pct: float = 5.0,
) -> dict[str, Any]:
    """对标工作台主入口:对齐 + RRMSE + 异常区间 + 仿真参数版本(manifest)。"""
    base = compare_job_to_dataset(result, records)
    anomalies: list[dict[str, Any]] = []
    if base.get("retention"):
        anomalies = _anomaly_windows(base["retention"], threshold_pct)
    manifest = (result or {}).get("manifest") or {}
    manifest_safe = {key: value for key, value in manifest.items() if key != "request"}
    return {
        "ok": True,
        "job_id": job_id,
        "dataset_id": dataset_id,
        "threshold_pct": threshold_pct,
        "retention": base.get("retention"),
        "efficiency": base.get("efficiency"),
        "sim_cycle_range": base.get("sim_cycle_range"),
        "exp_cycle_range": base.get("exp_cycle_range"),
        "anomalies": anomalies,
        "manifest": manifest_safe,
    }


def bench_runs_manifest(result_a: dict[str, Any], result_b: dict[str, Any]) -> dict[str, Any]:
    """两个 run 的参数版本对比:manifest 字段 + request 字段 diff。"""
    ma = (result_a or {}).get("manifest") or {}
    mb = (result_b or {}).get("manifest") or {}
    req_a = ma.get("request") or {}
    req_b = mb.get("request") or {}
    manifest_fields = ["workflow_id", "job_type", "cell", "run_mode", "pybamm_version", "parameter_source", "created_at"]

    rows: list[dict[str, Any]] = []
    for field in manifest_fields:
        va, vb = ma.get(field), mb.get(field)
        if va != vb:
            rows.append({"field": field, "job_a": va, "job_b": vb, "diff": True})
    for key in sorted(set(req_a) | set(req_b)):
        va, vb = req_a.get(key), req_b.get(key)
        if va != vb:
            rows.append({"field": f"request.{key}", "job_a": va, "job_b": vb, "diff": True})

    return {
        "ok": True,
        "job_a_manifest": {field: ma.get(field) for field in manifest_fields},
        "job_b_manifest": {field: mb.get(field) for field in manifest_fields},
        "differences": rows,
    }


# ============ Run 对比与复现(2026-08-05) ============

def _extract_curves(result: dict[str, Any]) -> list[dict[str, Any]]:
    """从 job result 提取可比曲线:cycle_metrics 优先;peak summary 兜底。"""
    curves: list[dict[str, Any]] = []
    metrics = (result or {}).get("cycle_metrics") or {}
    if metrics.get("cycle"):
        cycles = metrics["cycle"]
        for key, label in (
            ("retention_pct", "容量保持率 %"),
            ("efficiency_pct", "能效 %"),
            ("capacity_ah", "放电容量 Ah"),
        ):
            values = metrics.get(key)
            if values:
                curves.append({"name": label, "x": cycles, "y": values})
        return curves
    summary = (result or {}).get("summary") or {}
    results = summary.get("results") or []
    if results and any("soc" in row for row in results):
        for direction in ("charge", "discharge"):
            rows = [row for row in results if row.get("direction") == direction]
            if rows:
                curves.append(
                    {
                        "name": f"峰值电流-{direction} (A)",
                        "x": [float(row["soc"]) for row in rows],
                        "y": [float(row.get("peak_current_A") or 0) for row in rows],
                    }
                )
    return curves


def bench_runs_curve(result_a: dict[str, Any], result_b: dict[str, Any]) -> dict[str, Any]:
    """两个 Run 曲线对比:同名曲线对齐 + 曲线间 RRMSE;附元信息(manifest 摘要)。"""
    curves_a = _extract_curves(result_a)
    curves_b = _extract_curves(result_b)

    pairs: list[dict[str, Any]] = []
    for curve_a in curves_a:
        curve_b = next((c for c in curves_b if c["name"] == curve_a["name"]), None)
        if curve_b is None:
            continue
        import numpy as np

        xa = np.asarray(curve_a["x"], dtype=float)
        ya = np.asarray(curve_a["y"], dtype=float)
        xb = np.asarray(curve_b["x"], dtype=float)
        yb = np.asarray(curve_b["y"], dtype=float)
        overlap = (xa >= xb.min()) & (xa <= xb.max())
        if overlap.sum() < 2:
            continue
        xa_o, ya_o = xa[overlap], ya[overlap]
        yb_interp = np.interp(xa_o, xb, yb)
        finite = np.isfinite(ya_o) & np.isfinite(yb_interp)
        xa_o, ya_o, yb_interp = xa_o[finite], ya_o[finite], yb_interp[finite]
        if ya_o.size < 2:
            continue
        diff = ya_o - yb_interp
        rmse = float(np.sqrt(np.mean(diff**2)))
        scale = float(np.mean(np.abs(ya_o))) or 1.0
        pairs.append(
            {
                "name": curve_a["name"],
                "x": xa_o.tolist(),
                "y_a": ya_o.tolist(),
                "y_b": yb_interp.tolist(),
                "rmse": round(rmse, 4),
                "rrmse_pct": round(rmse / scale * 100.0, 2),
            }
        )

    manifest_fields = ["workflow_id", "job_type", "cell", "run_mode", "pybamm_version", "parameter_source"]
    meta = lambda result: {field: ((result or {}).get("manifest") or {}).get(field) for field in manifest_fields}
    return {
        "ok": True,
        "curves_a": curves_a,
        "curves_b": curves_b,
        "pairs": pairs,
        "meta_a": meta(result_a),
        "meta_b": meta(result_b),
    }
