"""Runtime helpers for notebook and example entry points.

These helpers reduce PyBaMM log noise for long aging studies without catching
or suppressing solver exceptions.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pybamm


DEFAULT_MAX_Y_VALUE = 1e7
DEFAULT_LOGGING_LEVEL = "CRITICAL"


def apply_pybamm_runtime_limits(
    max_y_value: float = DEFAULT_MAX_Y_VALUE,
    logging_level: str = DEFAULT_LOGGING_LEVEL,
) -> None:
    """Apply the default PyBaMM runtime limits used by project notebooks.

    This only adjusts the large-state diagnostic threshold and logger
    verbosity. Solver and Python exceptions are left untouched.
    """
    pybamm.settings.max_y_value = float(max_y_value)
    pybamm.set_logging_level(logging_level)


def _ensure_sys_path(path: Path) -> None:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _resolve_project_root(search_root: Path) -> Path:
    for candidate in (search_root, *search_root.parents):
        if (candidate / "src").exists() and (candidate / "pyproject.toml").exists():
            return candidate
        if (candidate / "BatteryProject" / "src").exists():
            return candidate / "BatteryProject"
    raise FileNotFoundError("Cannot locate BatteryProject root from current working directory")


def configure_notebook_environment(
    project_root: Path | str | None = None,
    *,
    search_root: Path | str | None = None,
    include_workspace_root: bool = False,
    max_y_value: float = DEFAULT_MAX_Y_VALUE,
    logging_level: str = DEFAULT_LOGGING_LEVEL,
) -> tuple[Path, Path, Path]:
    """Add common paths and apply default PyBaMM runtime limits.

    Parameters
    ----------
    project_root : Path | str | None
        Explicit BatteryProject root. When omitted, the root is discovered by
        searching upward from ``search_root`` or the current working directory.
    search_root : Path | str | None
        Starting point for project-root discovery when ``project_root`` is not
        provided.
    include_workspace_root : bool, optional
        Whether to also add ``PROJECT_ROOT.parent`` to ``sys.path``.

    Returns
    -------
    tuple[Path, Path, Path]
        ``(PROJECT_ROOT, WORKSPACE_ROOT, PARAMS_ROOT)``
    """
    if project_root is None:
        resolved_search_root = Path(search_root or Path.cwd()).resolve()
        resolved_project_root = _resolve_project_root(resolved_search_root)
    else:
        resolved_project_root = Path(project_root).resolve()

    workspace_root = resolved_project_root.parent
    params_root = workspace_root / "params"

    _ensure_sys_path(resolved_project_root)
    if include_workspace_root:
        _ensure_sys_path(workspace_root)
    _ensure_sys_path(params_root)

    apply_pybamm_runtime_limits(max_y_value=max_y_value, logging_level=logging_level)
    return resolved_project_root, workspace_root, params_root