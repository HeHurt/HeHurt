import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import task_delivery
from tools.task_delivery import create_task, publish_task


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "BatteryProject" / "examples").mkdir(parents=True)
    (tmp_path / "BatteryProject" / "output" / "runs").mkdir(parents=True)
    (tmp_path / "work").mkdir()
    (tmp_path / "BatteryProject" / "examples" / "template.ipynb").write_bytes(b"notebook-bytes")
    return tmp_path


def test_create_task_builds_upload_package_and_copies_template(tmp_path):
    workspace = _workspace(tmp_path)
    task_dir = create_task(
        cell="587Ah",
        name="全生命周期产热0p5P",
        month="202608",
        template="BatteryProject/examples/template.ipynb",
        workspace_root=workspace,
    )

    assert task_dir.name == "202608_何争_全生命周期产热0p5PV1"
    assert (task_dir / "02_模型" / "587Ah_全生命周期产热0p5P.ipynb").read_bytes() == b"notebook-bytes"
    assert all((task_dir / subdir).is_dir() for subdir in (
        "01_仿真报告", "02_模型", "03_输入数据", "04_输出结果", "05_复现说明"
    ))
    manifest = json.loads((task_dir / "task_manifest.json").read_text(encoding="utf-8"))
    assert manifest["owner"] == "何争"
    assert manifest["template"] == "BatteryProject/examples/template.ipynb"


def test_create_task_refuses_overwrite(tmp_path):
    workspace = _workspace(tmp_path)
    kwargs = dict(cell="314Ah", name="峰值电流", month="202608", workspace_root=workspace)
    create_task(**kwargs)
    with pytest.raises(FileExistsError):
        create_task(**kwargs)


def test_invalid_template_does_not_leave_partial_task(tmp_path):
    workspace = _workspace(tmp_path)
    with pytest.raises(ValueError, match="模板必须是存在的 examples Notebook"):
        create_task(
            cell="314Ah",
            name="无效模板",
            month="202608",
            template="BatteryProject/examples/missing.ipynb",
            workspace_root=workspace,
        )
    assert not (workspace / "work" / "314Ah" / "202608_何争_无效模板V1").exists()


def test_publish_selected_copies_snapshot_and_preserves_run(tmp_path):
    workspace = _workspace(tmp_path)
    task_dir = create_task(cell="314Ah", name="峰值电流", month="202608", workspace_root=workspace)
    run_dir = workspace / "BatteryProject" / "output" / "runs" / "peak" / "run_001"
    run_dir.mkdir(parents=True)
    (run_dir / "metrics.csv").write_text("soc,current\n0.5,100\n", encoding="utf-8")
    (run_dir / "cache.bin").write_bytes(b"cache")

    destination = publish_task(task=task_dir, run=run_dir, mode="selected", workspace_root=workspace)

    assert (destination / "metrics.csv").is_file()
    assert not (destination / "cache.bin").exists()
    assert (run_dir / "metrics.csv").is_file()
    manifest = json.loads((task_dir / "05_复现说明" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["published_runs"][0]["run_id"] == "run_001"
    assert manifest["published_runs"][0]["files"][0]["sha256"]


def test_publish_rejects_run_outside_runtime_root(tmp_path):
    workspace = _workspace(tmp_path)
    task_dir = create_task(cell="314Ah", name="峰值电流", month="202608", workspace_root=workspace)
    outside = workspace / "outside_run"
    outside.mkdir()
    (outside / "metrics.csv").write_text("x\n1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="run 目录必须位于"):
        publish_task(task=task_dir, run=outside, workspace_root=workspace)


def test_cli_new_task_smoke(tmp_path):
    workspace = _workspace(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(task_delivery.__file__)),
            "--workspace-root",
            str(workspace),
            "new-task",
            "--cell",
            "587Ah",
            "--name",
            "CLI烟雾测试",
            "--month",
            "202608",
            "--template",
            "BatteryProject/examples/template.ipynb",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (workspace / "work" / "587Ah" / "202608_何争_CLI烟雾测试V1" / "task_manifest.json").is_file()
