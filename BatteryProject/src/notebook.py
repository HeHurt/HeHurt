"""Notebook-facing setup helpers.

This module centralizes the repeated first-cell boilerplate used by project
notebooks: path setup, PyBaMM runtime limits, matplotlib style, and parameter
registry access.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

from .runtime import (
    DEFAULT_LOGGING_LEVEL,
    DEFAULT_MAX_Y_VALUE,
    configure_notebook_environment,
)


@dataclass(frozen=True)
class NotebookContext:
    """Paths and options resolved by ``setup_notebook``."""

    project_root: Path
    workspace_root: Path
    params_root: Path
    cell: str | None = None
    style: str | list[str] | tuple[str, ...] | None = None
    autoreload_enabled: bool = False


def _prioritize_paths(*paths: Path) -> None:
    normalized = [str(path.resolve()) for path in paths]
    remaining = [item for item in sys.path if str(Path(item).resolve()) not in normalized]
    sys.path[:] = normalized + remaining


def _enable_autoreload() -> bool:
    try:
        ipython = get_ipython()  # type: ignore[name-defined]
    except NameError:
        return False
    if ipython is None:
        return False
    ipython.run_line_magic("load_ext", "autoreload")
    ipython.run_line_magic("autoreload", "2")
    return True


def _apply_plot_style(style: str | list[str] | tuple[str, ...] | None) -> None:
    if style is False or style is None:
        return

    import matplotlib.pyplot as plt

    plt.style.use("science")
    plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"
    plt.rcParams["axes.unicode_minus"] = False


def setup_notebook(
    *,
    cell: str | None = None,
    style: str | list[str] | tuple[str, ...] | None = "science",
    project_root: Path | str | None = None,
    search_root: Path | str | None = None,
    include_workspace_root: bool = True,
    autoreload: bool = True,
    max_y_value: float = DEFAULT_MAX_Y_VALUE,
    logging_level: str = DEFAULT_LOGGING_LEVEL,
) -> NotebookContext:
    """Configure a project notebook and return its resolved context.

    Parameters
    ----------
    cell:
        Optional cell alias, for example ``"MIC"`` or ``"587"``. It is stored in
        the returned context for downstream notebook code.
    style:
        Matplotlib style to apply. Defaults to ``"science"``. Use ``None`` to
        skip style setup.
    project_root, search_root, include_workspace_root:
        Passed through to ``configure_notebook_environment``.
    autoreload:
        Enable IPython autoreload when running inside a notebook kernel.
    max_y_value, logging_level:
        PyBaMM runtime controls.
    """
    project, workspace, params_root = configure_notebook_environment(
        project_root=project_root,
        search_root=search_root,
        include_workspace_root=include_workspace_root,
        max_y_value=max_y_value,
        logging_level=logging_level,
    )
    _prioritize_paths(project, workspace, params_root)

    autoreload_enabled = _enable_autoreload() if autoreload else False
    _apply_plot_style(style)

    return NotebookContext(
        project_root=project,
        workspace_root=workspace,
        params_root=params_root,
        cell=cell,
        style=style,
        autoreload_enabled=autoreload_enabled,
    )


def load_params(cell: str, *, reload_module: bool = False) -> Callable[..., dict[str, Any]]:
    """Return ``get_hithium_params`` for a registered cell alias."""
    from params import load_cell_params

    return load_cell_params(cell, reload_module=reload_module)


__all__ = ["NotebookContext", "load_params", "setup_notebook"]
