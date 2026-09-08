"""Create a coarser, short-horizon 3D P2D pouch smoke model."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v5_cdi_relaxed.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v6_fast_smoke.mph"
RESULT = RUN / "build_pouch_electrochem_v6_fast_smoke_result.json"
TAG = "pouch_dual_tab_electrochem_v6"


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
        comp = model.component("comp1")
        size = comp.mesh("mesh1").feature("size")
        size.set("hauto", "7")
        size.set("hmax", "25[mm]")
        size.set("hmin", "5[mm]")
        size.set("hgrad", "1.3")
        comp.mesh("mesh1").run()

        model.study("std1").feature("time").set("tlist", "range(0,5,60)")
        time_solver = model.sol("sol1").feature("t1")
        time_solver.set("initialstepbdf", "0.1[s]")
        time_solver.set("maxstepbdf", "5[s]")
        model.label("Single-layer pouch 3D P2D V6: coarse mesh 60 s smoke")
        model.save(str(OUTPUT))
        result.update(
            {
                "ok": True,
                "mesh": {"hauto": 7, "hmax": "25[mm]", "hmin": "5[mm]", "through_thickness": "structured sweep retained"},
                "time": {"tlist": "range(0,5,60)", "max_internal_step": "5[s]", "rtol": "1e-3"},
            }
        )
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
