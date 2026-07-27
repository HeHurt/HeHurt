"""Run-directory helpers shared by headless canonical workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class WorkflowRunContext:
    """Resolved output locations for one workflow run."""

    workflow_id: str
    run_id: str
    run_dir: Path
    plots_dir: Path
    artifacts_dir: Path


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.")
    if not safe:
        raise ValueError("run name must contain at least one safe character")
    return safe


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write a UTF-8 JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def create_run_context(
    workflow_id: str,
    config: dict[str, Any],
    *,
    project_root: Path,
    run_id: str | None = None,
) -> WorkflowRunContext:
    """Create the standard output/runs directory and persist its config."""
    workflow_name = _safe_name(workflow_id)
    run_name = _safe_name(run_id or datetime.now().strftime("%Y%m%d_%H%M%S"))
    run_dir = project_root / "output" / "runs" / workflow_name / run_name
    plots_dir = run_dir / "plots"
    artifacts_dir = run_dir / "artifacts"
    plots_dir.mkdir(parents=True, exist_ok=False)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "config.json", config)
    return WorkflowRunContext(workflow_name, run_name, run_dir, plots_dir, artifacts_dir)
