"""Inspect the saved V3 OCV function and positive electrode expression."""

from __future__ import annotations

import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v4_v9_ocv.mph"
TAG = "audit_pouch_v4_ocv"


def main() -> None:
    payload = {"ok": False}
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        tags = list(model.func().tags())
        funcs = {}
        for tag in tags:
            node = model.func(tag)
            funcs[tag] = {"funcname": node.getString("funcname"), "source": node.getString("source")}
        comp = model.component("comp1")
        materials = {}
        for tag in comp.material().tags():
            mat = comp.material(tag)
            item = {"label": mat.label()}
            try:
                item["Eeq"] = mat.propertyGroup("ElectrodePotential").getString("Eeq")
            except Exception:
                pass
            materials[tag] = item
        payload = {
            "ok": True,
            "global_functions": funcs,
            "positive_Eeq": comp.material("mat4").propertyGroup("ElectrodePotential").getString("Eeq"),
            "materials": materials,
        }
    except Exception as exc:
        payload = {"ok": False, "error": repr(exc)}
    finally:
        try:
            ModelUtil.remove(TAG)
        except Exception:
            pass
        (RUN / "audit_pouch_v4_ocv_result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
