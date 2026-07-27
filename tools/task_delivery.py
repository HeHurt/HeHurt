"""Create upload-ready task packages and publish BatteryProject run snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
TASK_SUBDIRS = (
    "01_仿真报告",
    "02_模型",
    "03_输入数据",
    "04_输出结果",
    "05_复现说明",
)
SELECTED_SUFFIXES = {
    ".csv",
    ".json",
    ".log",
    ".md",
    ".npy",
    ".npz",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".txt",
    ".xls",
    ".xlsx",
}
INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*]')


def _safe_segment(value: str, label: str) -> str:
    value = value.strip()
    if not value or value in {".", ".."} or INVALID_WINDOWS_CHARS.search(value):
        raise ValueError(f"{label} 含空值或 Windows 路径非法字符: {value!r}")
    value = value.rstrip(" .")
    if not value:
        raise ValueError(f"{label} 不能只包含点或空格")
    return value


def _inside(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"{label}必须位于 {root_resolved}: {resolved}") from exc
    return resolved


def _resolve_from_workspace(path: str | Path, workspace_root: Path) -> Path:
    value = Path(path)
    return value.resolve() if value.is_absolute() else (workspace_root / value).resolve()


def _git_snapshot(workspace_root: Path) -> dict[str, object]:
    def run(*args: str) -> str | None:
        result = subprocess.run(
            ["git", *args],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status) if status is not None else None,
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_task(
    *,
    cell: str,
    name: str,
    owner: str = "何争",
    month: str | None = None,
    version: int = 1,
    template: str | Path | None = None,
    notebook_name: str | None = None,
    workspace_root: Path = WORKSPACE_ROOT,
) -> Path:
    workspace_root = workspace_root.resolve()
    cell = _safe_segment(cell, "cell")
    name = _safe_segment(name, "name")
    owner = _safe_segment(owner, "owner")
    month = month or datetime.now().strftime("%Y%m")
    if not re.fullmatch(r"\d{6}", month):
        raise ValueError("month 必须为 YYYYMM")
    if version < 1:
        raise ValueError("version 必须大于等于 1")

    folder_name = f"{month}_{owner}_{name}V{version}"
    task_dir = _inside(workspace_root / "work" / cell / folder_name, workspace_root / "work", "任务目录")
    if task_dir.exists():
        raise FileExistsError(f"任务目录已存在，禁止覆盖: {task_dir}")

    template_path = None
    template_relative = None
    target_name = None
    if template is not None:
        template_path = _resolve_from_workspace(template, workspace_root)
        _inside(template_path, workspace_root / "BatteryProject" / "examples", "模板")
        if not template_path.is_file() or template_path.suffix.lower() != ".ipynb":
            raise ValueError(f"模板必须是存在的 examples Notebook: {template_path}")
        target_name = notebook_name or f"{cell}_{name}.ipynb"
        target_name = _safe_segment(target_name, "notebook_name")
        if not target_name.lower().endswith(".ipynb"):
            target_name += ".ipynb"

    task_dir.mkdir(parents=True)
    for subdir in TASK_SUBDIRS:
        (task_dir / subdir).mkdir()

    created_at = datetime.now().isoformat(timespec="seconds")
    copied_notebook = None
    if template_path is not None:
        copied_notebook = task_dir / "02_模型" / target_name
        shutil.copy2(template_path, copied_notebook)
        template_relative = template_path.relative_to(workspace_root).as_posix()

    task_manifest = {
        "schema_version": 1,
        "task_id": folder_name,
        "cell": cell,
        "task_name": name,
        "owner": owner,
        "month": month,
        "version": f"V{version}",
        "status": "created",
        "created_at": created_at,
        "template": template_relative,
        "task_notebook": copied_notebook.name if copied_notebook else None,
    }
    _write_json(task_dir / "task_manifest.json", task_manifest)
    _write_json(
        task_dir / "02_模型" / "source_manifest.json",
        {"created_at": created_at, "template": template_relative, "git": _git_snapshot(workspace_root)},
    )
    _write_json(task_dir / "05_复现说明" / "run_manifest.json", {"published_runs": []})

    (task_dir / "00_任务说明.md").write_text(
        f"# {name}\n\n"
        f"- 任务编号：`{folder_name}`\n"
        f"- 电芯/体系：`{cell}`\n"
        f"- 负责人：{owner}\n"
        f"- 版本：V{version}\n"
        f"- 状态：已创建，待补充目标、输入、验收标准和结论。\n",
        encoding="utf-8",
    )
    (task_dir / "03_输入数据" / "config.yaml").write_text(
        f"cell: {cell}\ntask: {name}\nrun_mode: smoke\n",
        encoding="utf-8",
    )
    (task_dir / "05_复现说明" / "README.md").write_text(
        "# 复现说明\n\n"
        "1. 核对 `03_输入数据/config.yaml`。\n"
        "2. 从 `02_模型/` 运行任务 Notebook 或脚本。\n"
        "3. 原始运行产物写入 `BatteryProject/output/runs/<workflow>/<run_id>/`。\n"
        "4. 使用 `publish-task` 将确认后的 run 发布到 `04_输出结果/`。\n",
        encoding="utf-8",
    )
    return task_dir


def publish_task(
    *,
    task: str | Path,
    run: str | Path,
    mode: str = "selected",
    workspace_root: Path = WORKSPACE_ROOT,
) -> Path:
    workspace_root = workspace_root.resolve()
    task_dir = _inside(_resolve_from_workspace(task, workspace_root), workspace_root / "work", "任务目录")
    run_dir = _inside(
        _resolve_from_workspace(run, workspace_root),
        workspace_root / "BatteryProject" / "output" / "runs",
        "run 目录",
    )
    if not task_dir.is_dir() or not (task_dir / "task_manifest.json").is_file():
        raise ValueError(f"不是标准任务目录: {task_dir}")
    if not run_dir.is_dir():
        raise ValueError(f"run 目录不存在: {run_dir}")
    if mode not in {"selected", "full"}:
        raise ValueError("mode 必须为 selected 或 full")

    source_files = [path for path in run_dir.rglob("*") if path.is_file() and not path.is_symlink()]
    if mode == "selected":
        source_files = [path for path in source_files if path.suffix.lower() in SELECTED_SUFFIXES]
    if not source_files:
        raise ValueError(f"run 中没有符合 mode={mode} 的文件: {run_dir}")

    destination = task_dir / "04_输出结果" / run_dir.name
    if destination.exists():
        raise FileExistsError(f"该 run 已发布，禁止覆盖: {destination}")

    copied = []
    for source in source_files:
        relative = source.relative_to(run_dir)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(
            {
                "path": relative.as_posix(),
                "size": target.stat().st_size,
                "sha256": _sha256(target),
            }
        )

    manifest_path = task_dir / "05_复现说明" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("published_runs", []).append(
        {
            "run_id": run_dir.name,
            "source": run_dir.relative_to(workspace_root).as_posix(),
            "published_at": datetime.now().isoformat(timespec="seconds"),
            "mode": mode,
            "files": copied,
        }
    )
    _write_json(manifest_path, manifest)

    task_manifest_path = task_dir / "task_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["status"] = "published"
    task_manifest["latest_run_id"] = run_dir.name
    _write_json(task_manifest_path, task_manifest)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new-task", help="创建标准任务交付包")
    new_parser.add_argument("--cell", required=True)
    new_parser.add_argument("--name", required=True)
    new_parser.add_argument("--owner", default="何争")
    new_parser.add_argument("--month")
    new_parser.add_argument("--version", type=int, default=1)
    new_parser.add_argument("--template")
    new_parser.add_argument("--notebook-name")

    publish_parser = subparsers.add_parser("publish-task", help="发布 run 快照到任务包")
    publish_parser.add_argument("--task", required=True)
    publish_parser.add_argument("--run", required=True)
    publish_parser.add_argument("--mode", choices=("selected", "full"), default="selected")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "new-task":
        path = create_task(
            cell=args.cell,
            name=args.name,
            owner=args.owner,
            month=args.month,
            version=args.version,
            template=args.template,
            notebook_name=args.notebook_name,
            workspace_root=args.workspace_root,
        )
    else:
        path = publish_task(task=args.task, run=args.run, mode=args.mode, workspace_root=args.workspace_root)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
