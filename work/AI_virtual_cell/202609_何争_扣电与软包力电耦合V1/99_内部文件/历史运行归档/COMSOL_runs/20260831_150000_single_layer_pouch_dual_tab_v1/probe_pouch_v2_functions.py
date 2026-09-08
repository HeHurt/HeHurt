"""Probe function scope and registration in the migrated 2D model."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_2d_cross_section_v2_coin_v9_electrochem.mph"
RESULT = RUN / "probe_pouch_v2_functions_result.json"
TAG = "pouch_v2_function_probe"


def remove() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def inspect(container, getter) -> dict[str, object]:
    output: dict[str, object] = {}
    for tag_obj in container.tags():
        tag = str(tag_obj)
        feature = getter(tag)
        item: dict[str, object] = {"type": str(feature.getType())}
        for prop in ("funcname", "source", "filename", "interp", "extrap"):
            try:
                item[prop] = str(feature.getString(prop))
            except Exception:
                pass
        output[tag] = item
    return output


def main() -> None:
    payload: dict[str, object] = {"ok": False}
    remove()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        payload.update({
            "ok": True,
            "global": inspect(model.func(), model.func),
            "component": inspect(comp.func(), comp.func),
        })
        for expression in ("ocv_gr_charge(0.05)", "ocv_lfp_base(0.99)", "ely_sigma(1000[mol/m^3])"):
            try:
                payload[expression] = float(model.param().evaluate(expression))
            except Exception:
                payload[expression] = traceback.format_exc()
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
