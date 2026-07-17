"""Studio 数据分析 API 纯逻辑测试：寿命外推 + 仿真-实测对比。"""
from __future__ import annotations

import pytest

from api.compare import compare_job_to_dataset
from api.studio_io import extrapolate_retention


def linear_fade_records(n: int = 100, initial: float = 100.0, fade_per_cycle: float = 0.05):
    """线性衰减合成数据：retention = 100 - 0.05*cycle (%)。"""
    return [
        {"cycle": cycle, "capacity_ah": initial * (1 - fade_per_cycle / 100.0 * cycle), "efficiency_pct": 95.0}
        for cycle in range(1, n + 1)
    ]


def test_extrapolate_linear_fade_predicts_target_cycle():
    records = linear_fade_records(n=200)
    result = extrapolate_retention(records, target_soh_pct=65.0)
    assert result["method"] == "linear-tail-fit"
    # retention = 100 - 0.05*c（归一到首圈后斜率不变），65% → c ≈ 700/1.0005 ≈ 699
    assert abs(result["predicted_cycle"] - 700) <= 5
    assert result["r_squared"] > 0.999
    assert result["extrapolated"]["cycle"][0] == pytest.approx(200.0)
    assert result["extrapolated"]["retention_pct"][-1] == pytest.approx(65.0, abs=0.1)


def test_extrapolate_too_few_points_raises():
    with pytest.raises(ValueError, match="不足"):
        extrapolate_retention(linear_fade_records(n=3))


def test_extrapolate_rising_capacity_raises():
    records = [{"cycle": c, "capacity_ah": 100.0 + c} for c in range(1, 30)]
    with pytest.raises(ValueError, match="下降趋势"):
        extrapolate_retention(records)


def test_extrapolate_measured_already_below_target():
    records = linear_fade_records(n=900)  # 降到 55%，已越过 65%
    result = extrapolate_retention(records, target_soh_pct=65.0)
    assert result["method"] == "measured-crossing"
    assert abs(result["predicted_cycle"] - 700) <= 5
    assert result["extrapolated"]["cycle"] == []


def fake_result(cycles, retention, efficiency=None):
    return {
        "cycle_metrics": {
            "cycle": cycles,
            "retention_pct": retention,
            "efficiency_pct": efficiency or [None] * len(cycles),
        }
    }


def test_compare_identical_series_gives_zero_rrmse():
    records = linear_fade_records(n=100)
    sim_cycles = list(range(1, 101))
    sim_retention = [100.0 * (1 - 0.0005 * c) / (1 - 0.0005) for c in sim_cycles]  # 与实测同源归一
    result = compare_job_to_dataset(fake_result(sim_cycles, sim_retention), records)
    assert result["retention"]["rrmse_pct"] < 0.01
    assert result["efficiency"] is None  # 仿真能效全 None


def test_compare_no_overlap_raises():
    records = linear_fade_records(n=50)  # 实测 1-50 圈
    with pytest.raises(ValueError, match="无法对比"):
        compare_job_to_dataset(fake_result([1000, 2000], [99.0, 98.0]), records)


def test_compare_partial_overlap_uses_overlap_only():
    records = linear_fade_records(n=500)
    sim_cycles = [50, 100, 150]
    sim_retention = [99.0, 98.0, 97.0]
    result = compare_job_to_dataset(fake_result(sim_cycles, sim_retention), records)
    block = result["retention"]
    assert min(block["cycle"]) >= 50
    assert max(block["cycle"]) <= 150
    assert block["rmse"] >= 0
