from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


TSD_HEADER = b"%TSD-Header-###%"
REPARSE_POINT = 0x400

ROOT_FILES = {
    ".gitattributes",
    ".gitignore",
    "AGENTS.md",
    "datasets.json",
    "pyproject.toml",
    "uv.lock",
}

TREE_RULES = {
    ".codex": "codex_project_config",
    ".plans": "plans",
    "BatteryProject/api": "batteryproject_api",
    "BatteryProject/deploy": "batteryproject_deploy",
    "BatteryProject/docs": "batteryproject_docs",
    "BatteryProject/examples": "canonical_examples",
    "BatteryProject/src": "pybamm_core_source",
    "BatteryProject/studio": "studio_frontend",
    "BatteryProject/tests": "tests",
    "docs": "project_docs",
    "params": "cell_parameters",
    "skills": "project_skills",
    "tools": "project_tools",
}

BATTERYPROJECT_FILES = {
    "BatteryProject/.gitignore",
    "BatteryProject/pyproject.toml",
    "BatteryProject/README.md",
    "BatteryProject/run_studio.py",
    "BatteryProject/run_studio_uv.bat",
    "BatteryProject/uv.lock",
}

WORKFLOW_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".cmd",
    ".css",
    ".html",
    ".ini",
    ".ipynb",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".pyi",
    ".rst",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}

SKIP_DIR_NAMES = {
    ".git",
    ".ipynb_checkpoints",
    ".pytest_cache",
    ".venv",
    ".venv-liionpack",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "output",
    "outputs",
    "release",
    "results",
    "runs",
    "scratch",
}


def is_reparse(entry: os.DirEntry[str]) -> bool:
    try:
        return bool(getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & REPARSE_POINT)
    except OSError:
        return True


def walk_files(root: Path):
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name.lower(), reverse=True)
        except OSError:
            continue
        for entry in entries:
            if is_reparse(entry):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in SKIP_DIR_NAMES:
                        stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    yield Path(entry.path)
            except OSError:
                continue


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_usable_bytes(path: Path, code_exe: Path, bridge: Path, temp_root: Path) -> tuple[bytes | None, str]:
    data = path.read_bytes()
    if not data.startswith(TSD_HEADER):
        return data, "python"
    if path.suffix.lower() not in WORKFLOW_EXTENSIONS:
        return None, "DLP ciphertext; binary Code.exe bridge intentionally not used"
    destination = temp_root / f"{hashlib.sha256(str(path).encode('utf-8')).hexdigest()}.codex_plain"
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    result = subprocess.run(
        [str(code_exe), str(bridge), str(path), str(destination)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not destination.exists():
        return None, f"Code.exe bridge failed: {result.stderr.strip()}"
    try:
        data = destination.read_bytes()
    finally:
        destination.unlink(missing_ok=True)
    if data.startswith(TSD_HEADER):
        return None, "Code.exe bridge still returned DLP ciphertext"
    return data, "code_exe_bridge"


def strip_notebook_outputs(data: bytes) -> tuple[bytes, bool]:
    try:
        notebook = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return data, False
    changed = False
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            if cell.get("outputs"):
                cell["outputs"] = []
                changed = True
            if cell.get("execution_count") is not None:
                cell["execution_count"] = None
                changed = True
    metadata = notebook.get("metadata", {})
    if "widgets" in metadata:
        metadata.pop("widgets")
        changed = True
    if not changed:
        return data, False
    return json.dumps(notebook, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), True


def git_state(root: Path) -> dict[str, str]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False
        )
        return result.stdout.strip()

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "status_short": run("status", "--short", "--untracked-files=all"),
    }


def collect(root: Path) -> dict[str, tuple[Path, str]]:
    selected: dict[str, tuple[Path, str]] = {}

    def add(path: Path, category: str) -> None:
        if path.is_file():
            selected.setdefault(path.relative_to(root).as_posix(), (path, category))

    for name in ROOT_FILES | BATTERYPROJECT_FILES:
        add(root / name, "root_and_environment")

    for relative, category in TREE_RULES.items():
        tree = root / relative
        if tree.is_dir():
            for path in walk_files(tree):
                if relative == "skills" and ".system" in path.relative_to(tree).parts:
                    continue
                add(path, category)

    work = root / "work"
    if work.is_dir():
        for path in walk_files(work):
            relative_parts = path.relative_to(work).parts
            if "04_输出结果" in relative_parts or "04_output" in relative_parts:
                continue
            if path.suffix.lower() in WORKFLOW_EXTENSIONS:
                add(path, "workflow_sources_and_manifests")

    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact Hithium PyBaMM core workspace archive.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--code-exe",
        type=Path,
        default=Path(r"D:\软件安装\Microsoft VS Code\Code.exe"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.workspace.resolve()
    output = args.output.resolve()
    selected = collect(root)
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path, category in selected.values():
        totals[category][0] += 1
        totals[category][1] += path.stat().st_size

    if args.dry_run:
        largest = sorted(
            (
                {"path": relative, "category": category, "bytes": path.stat().st_size}
                for relative, (path, category) in selected.items()
            ),
            key=lambda item: item["bytes"],
            reverse=True,
        )[:30]
        print(json.dumps({
            "file_count": len(selected),
            "source_bytes": sum(path.stat().st_size for path, _ in selected.values()),
            "categories": {key: {"files": value[0], "bytes": value[1]} for key, value in sorted(totals.items())},
            "largest_files": largest,
        }, ensure_ascii=False, indent=2))
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing archive: {output}")

    included = []
    skipped = []
    state = git_state(root)
    bridge = Path(__file__).with_name("export_plain_with_code.js")
    with tempfile.TemporaryDirectory(prefix="codex-hithium-core-") as temporary:
        temp_root = Path(temporary)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for relative, (path, category) in sorted(selected.items()):
                try:
                    data, read_route = read_usable_bytes(path, args.code_exe, bridge, temp_root)
                except OSError as exc:
                    skipped.append({"path": relative, "reason": f"read_error: {exc}"})
                    continue
                if data is None:
                    skipped.append({"path": relative, "reason": read_route})
                    continue
                if path.suffix.lower() == ".ipynb" and not data:
                    skipped.append({"path": relative, "reason": "source notebook is zero bytes"})
                    continue
                source_size = len(data)
                source_sha256 = sha256_bytes(data)
                notebook_outputs_stripped = False
                if path.suffix.lower() == ".ipynb":
                    data, notebook_outputs_stripped = strip_notebook_outputs(data)
                archive.writestr(relative, data)
                included.append({
                    "path": relative,
                    "category": category,
                    "source_size": source_size,
                    "source_sha256": source_sha256,
                    "packed_size": len(data),
                    "packed_sha256": sha256_bytes(data),
                    "read_route": read_route,
                    "notebook_outputs_stripped": notebook_outputs_stripped,
                })

            manifest = {
                "schema_version": 1,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_workspace": str(root),
                "scope": "PyBaMM core code, parameters, tests, canonical examples, workflow sources, project skills and docs",
                "notebook_policy": "keep code/markdown/metadata; strip cell outputs, execution_count and widget state in archive only",
                "excluded": [
                    ".git history",
                    "virtual environments and caches",
                    "data_raw and data_processed",
                    "BatteryProject/output and Studio runtime state",
                    "COMSOL, archive, outputs and generated results",
                    "work task result folders and binary experiment inputs",
                ],
                "git": state,
                "included_file_count": len(included),
                "included_source_bytes": sum(item["source_size"] for item in included),
                "included_packed_bytes": sum(item["packed_size"] for item in included),
                "skipped": skipped,
                "files": included,
            }
            archive.writestr("CORE_PACKAGE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
            archive.writestr(
                "README_CORE_PACKAGE.md",
                (
                    "# Hithium PyBaMM核心代码与工作流包\n\n"
                    "本包用于在新电脑恢复可运行代码、参数、测试、canonical examples、工作流源码、"
                    "项目规则、skills和数据registry。Notebook保留代码和Markdown，但归档副本已清空历史输出。"
                    "它不包含实验原始数据、仿真输出、虚拟环境、COMSOL或Git历史。\n\n"
                    "恢复后先阅读AGENTS.md，按BatteryProject/pyproject.toml与uv.lock重建环境，"
                    "再运行参数检查、单元测试和最小PyBaMM smoke test。需要实验对标时，"
                    "再依据datasets.json单独迁移对应data_raw/data_processed文件。\n"
                ).encode("utf-8"),
            )

    sidecar = output.with_suffix(".manifest.json")
    sidecar.write_text(json.dumps({
        "archive": output.name,
        "archive_size": output.stat().st_size,
        "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "included_file_count": len(included),
        "included_source_bytes": sum(item["source_size"] for item in included),
        "included_packed_bytes": sum(item["packed_size"] for item in included),
        "skipped_count": len(skipped),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
