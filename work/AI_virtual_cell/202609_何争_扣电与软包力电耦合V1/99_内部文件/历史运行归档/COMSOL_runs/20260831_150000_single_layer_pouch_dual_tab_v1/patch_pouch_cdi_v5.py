"""Create a low-SOC pouch model with a controlled CDI-only tolerance relaxation."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v4_v9_ocv.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v5_cdi_relaxed.mph"
RESULT = RUN / "patch_pouch_cdi_v5_result.json"
TAG = "pouch_dual_tab_electrochem_v5"


def remove() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def main() -> None:
    result = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        stationary = model.sol("sol1").feature("s1")
        stationary.set("stol", "1e-2")
        model.study("std1").feature("time").set("rtol", "1e-3")
        model.label("Single-layer pouch 3D P2D V5: V9 OCV with CDI initialization tolerance")
        model.save(str(OUTPUT))
        result.update({"ok": True, "cdi_stationary_tolerance": "1e-2", "transient_tolerance": "1e-3"})
    except Exception:
        result["traceback"] = traceback.format_exc()
    finally:
        remove()
        RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(result, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
