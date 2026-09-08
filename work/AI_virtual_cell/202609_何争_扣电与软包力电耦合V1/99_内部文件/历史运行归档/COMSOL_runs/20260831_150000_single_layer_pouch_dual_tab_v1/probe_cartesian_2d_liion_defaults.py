"""Probe COMSOL 6.4 default feature tree for a Cartesian 2D Li-ion interface."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RESULT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1\probe_cartesian_2d_liion_defaults_result.json")
TAG = "probe_liion_2d"


def remove() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def tree(liion) -> dict[str, object]:
    return {
        str(item): {
            "type": str(liion.feature(str(item)).getType()),
            "children": {
                str(child): str(liion.feature(str(item)).feature(str(child)).getType())
                for child in liion.feature(str(item)).feature().tags()
            },
        }
        for item in liion.feature().tags()
    }


def main() -> None:
    payload: dict[str, object] = {"ok": False}
    remove()
    try:
        model = ModelUtil.create(TAG)
        model.component().create("comp1", True)
        comp = model.component("comp1")
        comp.geom().create("geom1", 2)
        geom = comp.geom("geom1")
        geom.feature().create("r1", "Rectangle")
        geom.feature("r1").set("size", ["1[mm]", "1[mm]"])
        geom.run()
        comp.physics().create("liion", "LithiumIonBatteryMPH", "geom1")
        liion = comp.physics("liion")
        stages: dict[str, object] = {"root": tree(liion)}
        for tag, feature_type, dimension in (
            ("cc1", "CurrentConductor", 2),
            ("pce1", "PorousElectrode", 2),
            ("sep1", "Separator", 2),
            ("pce2", "PorousElectrode", 2),
            ("egnd1", "ElectricGround", 1),
            ("ecd1", "ElectrodeCurrent", 1),
        ):
            if tag not in [str(item) for item in liion.feature().tags()]:
                liion.feature().create(tag, feature_type, dimension)
            stages[tag] = tree(liion)
        payload.update({"ok": True, "stages": stages})
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove()
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps({"ok": payload.get("ok"), "result": str(RESULT)}, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
