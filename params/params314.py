"""314 Ah cell parameter alias.

The historical file name ``params.py`` is kept for compatibility. New notebooks
should use this explicit module name, or the registry:

    from params import load_cell_params
    get_hithium_params = load_cell_params("314")
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

try:
    from .params import get_hithium_params
except ImportError:  # Supports top-level imports when params/ is on sys.path.
    _legacy_path = Path(__file__).with_name("params.py")
    _spec = importlib.util.spec_from_file_location("_hithium_params314_legacy", _legacy_path)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Cannot load legacy 314 params from {_legacy_path}")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules.setdefault("_hithium_params314_legacy", _module)
    _spec.loader.exec_module(_module)
    get_hithium_params = _module.get_hithium_params


__all__ = ["get_hithium_params"]
