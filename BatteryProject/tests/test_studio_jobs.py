"""Studio API 任务框架单元测试：请求规范化与 job_type 注册表分发。

只测纯逻辑（不 import pybamm、不 spawn 进程），保持毫秒级运行。
"""
from __future__ import annotations

import pytest

from api import jobs


def test_normalize_request_smoke_caps_cycles():
    normalized = jobs.normalize_request({"cycles": 500, "run_mode": "smoke"})
    assert normalized["cycles"] == jobs.MAX_UI_CYCLES
    assert normalized["cycles_requested"] == 500


def test_normalize_request_production_caps_cycles():
    normalized = jobs.normalize_request({"cycles": 999999, "run_mode": "production"})
    assert normalized["cycles"] == jobs.MAX_PRODUCTION_CYCLES
    assert normalized["run_mode"] == "production"


def test_normalize_request_acceleration_factor_by_parameter_kind():
    builtin = jobs.normalize_request({"parameter_set": "chen2020"})
    project = jobs.normalize_request({"parameter_set": "hithium314"})
    assert builtin["acceleration_factor"] == 1
    assert project["acceleration_factor"] == jobs.ACCELERATION_FACTOR


def test_normalize_aging_options_consistency_rules():
    options = jobs.normalize_aging_options(
        {"SEI": "none", "particle mechanics": "none", "lithium plating": "none"},
        aging_enabled=True,
    )
    assert options["SEI film resistance"] == "none"
    assert options["SEI porosity change"] == "false"
    assert options["SEI on cracks"] == "false"
    assert options["stress-induced diffusion"] == "false"
    assert options["lithium plating porosity change"] == "false"


def test_normalize_aging_options_disabled_returns_empty():
    assert jobs.normalize_aging_options({"SEI": "constant"}, aging_enabled=False) == {}


def test_resolve_job_type_defaults_to_cycle():
    job_type, spec = jobs.resolve_job_type({})
    assert job_type == "cycle"
    assert spec["normalize"] is jobs.normalize_request
    assert spec["worker"] is jobs.run_cycle_worker


def test_resolve_job_type_unknown_raises_value_error():
    with pytest.raises(ValueError, match="未知任务类型"):
        jobs.resolve_job_type({"job_type": "does-not-exist"})


def test_job_types_registry_shape():
    for name, spec in jobs.JOB_TYPES.items():
        assert isinstance(name, str) and name == name.lower()
        assert callable(spec["normalize"])
        assert callable(spec["worker"])
        assert spec["label"]
