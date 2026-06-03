from __future__ import annotations

import sys
from pathlib import Path


BATTERY_PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BATTERY_PROJECT_ROOT.parent

for candidate in (BATTERY_PROJECT_ROOT, WORKSPACE_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)