"""Check where the validated coin V9 model defines OCV functions."""

from __future__ import annotations

import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\model_snapshot.mph")
TAG = "audit_coin_v9_ocv_scope"


def describe_global(model):
    out = {}
    for tag in model.func().tags():
        node = model.func(tag)
        try:
            name = node.getString("funcname")
        except Exception:
            name = ""
        out[tag] = name
    return out


def main() -> None:
    result = {"ok": False}
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
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
        result = {
            "ok": True,
            "global_functions": describe_global(model),
            "materials": materials,
        }
    except Exception as exc:
        result = {"ok": False, "error": repr(exc)}
    finally:
        try:
            ModelUtil.remove(TAG)
        except Exception:
            pass
        (RUN / "audit_coin_v9_ocv_function_scope_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(result, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
