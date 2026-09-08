"""Parameter registry for Hithium cell parameter files.

The existing ``paramsXXX.py`` modules remain the source of truth. This module
adds a small registry so notebooks can use stable names such as ``MIC`` or
``587`` instead of importing the concrete module directly.
"""

from __future__ import annotations

from collections.abc import Callable
import importlib
from pathlib import Path
import sys


PARAMS_ROOT = Path(__file__).resolve().parent


def _ensure_params_root() -> None:
    params_root = str(PARAMS_ROOT)
    if params_root not in sys.path:
        sys.path.insert(0, params_root)


def _normalize_cell_key(cell: str) -> str:
    key = str(cell).strip().upper()
    for token in (" ", "_", "-", "."):
        key = key.replace(token, "")
    if key.endswith("AH"):
        key = key[:-2]
    return key


_CELL_PARAM_MODULES: dict[str, str] = {
    "MIC": "paramsMIC",
    "MIC1175": "paramsMIC",
    "1175": "paramsMIC",
    "280": "params280",
    "314": "params314",
    "314BASE": "params314",
    "3145PLUS3": "params314_5plus3",
    "3145+3": "params314_5plus3",
    "587": "params587",
    "587CALANDER": "params587calander",
    "650": "params650",
    "650310": "params650",
    "64150": "params64150",
    "50": "params50方壳",
    "50FANGKE": "params50方壳",
    "50方壳": "params50方壳",
    "CW362": "paramsCW362_pouch",
    "CW362POUCH": "paramsCW362_pouch",
    "CW391": "paramsCW391_pouch",
    "CW391POUCH": "paramsCW391_pouch",
    "1300CW363": "params1300CW363",
    "CW363": "params1300CW363",
    "LDSCW368": "paramsLDSCW368",
    "CW368": "paramsLDSCW368",
    "LDSCW501": "paramsLDSCW501",
    "CW501": "paramsLDSCW501",
    "NA": "paramsNa",
    "SODIUM": "paramsNa",
}


def list_cell_params() -> dict[str, str]:
    """Return the normalized cell-key to module-name registry."""
    return dict(_CELL_PARAM_MODULES)


def get_cell_params_module_name(cell: str) -> str:
    """Resolve a cell alias to its concrete ``paramsXXX`` module name."""
    key = _normalize_cell_key(cell)
    try:
        return _CELL_PARAM_MODULES[key]
    except KeyError as exc:
        known = ", ".join(sorted(_CELL_PARAM_MODULES))
        raise KeyError(f"Unknown cell parameter set {cell!r}. Known keys: {known}") from exc


def load_cell_params(cell: str, *, reload_module: bool = False) -> Callable[..., dict]:
    """Load ``get_hithium_params`` for a registered cell.

    Parameters
    ----------
    cell:
        Cell alias, for example ``"MIC"``, ``"280"``, ``"314"``, or ``"587"``.
    reload_module:
        Reload the concrete params module before returning the function. This is
        useful in notebooks after editing a params file.
    """
    _ensure_params_root()
    module_name = get_cell_params_module_name(cell)
    module = importlib.import_module(module_name)
    if reload_module:
        module = importlib.reload(module)
    try:
        return module.get_hithium_params
    except AttributeError as exc:
        raise AttributeError(f"{module_name} does not export get_hithium_params") from exc


def get_hithium_params(t_factor=1, temperature=298.15) -> dict:
    """Legacy 314 Ah params wrapper for ``from params import get_hithium_params``."""
    return load_cell_params("314")(t_factor, temperature)


__all__ = [
    "PARAMS_ROOT",
    "get_cell_params_module_name",
    "get_hithium_params",
    "list_cell_params",
    "load_cell_params",
]
