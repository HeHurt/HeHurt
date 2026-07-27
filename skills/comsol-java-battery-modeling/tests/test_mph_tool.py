import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "mph_tool.py"
SPEC = importlib.util.spec_from_file_location("mph_tool", SCRIPT)
mph_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mph_tool)


def test_recursive_diff_reports_only_changed_paths():
    left = {"model": {"params": {"L": "1[m]", "C": 1}}, "tool_version": "1"}
    right = {"model": {"params": {"L": "2[m]", "C": 1}}, "tool_version": "2"}
    result = mph_tool.recursive_diff(left, right, {"tool_version"})
    assert result == [{"path": "model.params.L", "left": "1[m]", "right": "2[m]"}]


def test_patch_refuses_source_overwrite(tmp_path):
    source = tmp_path / "source.mph"
    source.touch()
    with pytest.raises(ValueError, match="must differ"):
        mph_tool.ensure_save_as(str(source), str(source))


def test_validate_config_requires_action_keys():
    with pytest.raises(ValueError, match="Missing config keys"):
        mph_tool.validate_config({"action": "audit", "models": []})


def test_diff_action_writes_json(tmp_path):
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    output = tmp_path / "diff.json"
    left.write_text('{"x": 1}', encoding="utf-8")
    right.write_text('{"x": 2}', encoding="utf-8")
    result = mph_tool.action_diff({"left": str(left), "right": str(right), "output": str(output)})
    assert result["differences"][0]["path"] == "x"
    assert output.exists()
