from pathlib import Path
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ROOT = WORKSPACE_ROOT / "BatteryProject"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.plotting import subplot


__all__ = ["subplot"]