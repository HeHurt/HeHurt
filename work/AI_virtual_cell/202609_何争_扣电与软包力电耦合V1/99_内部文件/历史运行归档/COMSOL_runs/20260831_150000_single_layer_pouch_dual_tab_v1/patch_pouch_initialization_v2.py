"""Create a transient-first variant that does not require a stationary CDI solve."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v1.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v2_transient_first.mph"
RESULT = RUN / "patch_pouch_initialization_v2_result.json"
TAG = "pouch_dual_tab_electrochem_v2"


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    try:
        try:
            ModelUtil.remove(TAG)
        except Exception:
            pass
        model = ModelUtil.load(TAG, str(SOURCE))
        model.study("std1").feature().remove("cdi")
        model.study("std1").feature("time").set("tlist", "range(0,10,600)")
        model.study("std1").feature("time").set("rtol", "1e-3")
        model.label("单层软包双侧出极耳：3D P2D 电化学基模 V2（低SOC瞬态优先）")
        model.save(str(OUTPUT))
        payload.update({"ok": True, "change": "Removed std1/cdi; retained time-dependent 0.5C study."})
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        try:
            ModelUtil.remove(TAG)
        except Exception:
            pass
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
