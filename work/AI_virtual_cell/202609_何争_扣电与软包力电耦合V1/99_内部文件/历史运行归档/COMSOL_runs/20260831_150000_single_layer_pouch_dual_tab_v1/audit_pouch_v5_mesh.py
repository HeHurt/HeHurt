"""Inspect structured mesh features before controlled in-plane coarsening."""

from __future__ import annotations

import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v5_cdi_relaxed.mph"
TAG = "audit_pouch_v5_mesh"


def get(node, key):
    try:
        return node.getString(key)
    except Exception:
        return None


def main() -> None:
    result = {"ok": False}
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        mesh = model.component("comp1").mesh("mesh1")
        features = {}
        for tag in mesh.feature().tags():
            node = mesh.feature(tag)
            features[tag] = {"type": node.getType(), "hauto": get(node, "hauto"), "hmax": get(node, "hmax"), "hmin": get(node, "hmin"), "hgrad": get(node, "hgrad")}
        result = {"ok": True, "features": features}
    except Exception as exc:
        result = {"ok": False, "error": repr(exc)}
    finally:
        try:
            ModelUtil.remove(TAG)
        except Exception:
            pass
        (RUN / "audit_pouch_v5_mesh_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(result, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
