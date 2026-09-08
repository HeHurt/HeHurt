"""Inspect exact V9 electrochemical selections/materials before 2D migration."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
COIN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\model_snapshot.mph")
POUCH = RUN / "pouch_dual_tab_2d_cross_section_v1_geometry_mesh.mph"
RESULT = RUN / "inspect_coin_v9_for_2d_migration_result.json"


def remove(tag: str) -> None:
    try:
        ModelUtil.remove(tag)
    except Exception:
        pass


def entities(selection, dim: int) -> list[int]:
    try:
        return sorted(int(item) for item in selection.entities(dim))
    except Exception:
        return []


def properties(feature) -> dict[str, object]:
    data: dict[str, object] = {}
    try:
        for name in feature.properties():
            key = str(name)
            try:
                data[key] = str(feature.getString(key))
            except Exception:
                try:
                    data[key] = [str(item) for item in feature.getStringArray(key)]
                except Exception:
                    pass
    except Exception:
        pass
    return data


def main() -> None:
    payload: dict[str, object] = {"ok": False}
    remove("coin_inspect")
    remove("pouch_inspect")
    try:
        coin = ModelUtil.load("coin_inspect", str(COIN))
        comp = coin.component("comp1")
        liion = comp.physics("liion")
        material_data: dict[str, object] = {}
        for tag_obj in comp.material().tags():
            tag = str(tag_obj)
            material = comp.material(tag)
            groups: dict[str, object] = {}
            for group_obj in material.propertyGroup().tags():
                group = str(group_obj)
                groups[group] = properties(material.propertyGroup(group))
            material_data[tag] = {
                "label": str(material.label()),
                "selection": entities(material.selection(), 2),
                "groups": groups,
            }

        feature_data: dict[str, object] = {}
        for tag_obj in liion.feature().tags():
            tag = str(tag_obj)
            feature = liion.feature(tag)
            feature_data[tag] = {
                "type": str(feature.getType()),
                "active": bool(feature.isActive()),
                "domains": entities(feature.selection(), 2),
                "boundaries": entities(feature.selection(), 1),
                "properties": properties(feature),
                "children": [str(item) for item in feature.feature().tags()],
                "child_data": {
                    str(child_obj): {
                        "type": str(feature.feature(str(child_obj)).getType()),
                        "active": bool(feature.feature(str(child_obj)).isActive()),
                        "properties": properties(feature.feature(str(child_obj))),
                    }
                    for child_obj in feature.feature().tags()
                },
            }

        pouch = ModelUtil.load("pouch_inspect", str(POUCH))
        view_data: dict[str, object] = {}
        for tag_obj in pouch.component("comp1").view().tags():
            tag = str(tag_obj)
            view = pouch.component("comp1").view(tag)
            axis = view.axis()
            view_data[tag] = {"label": str(view.label()), "axis": properties(axis)}

        payload.update({
            "ok": True,
            "materials": material_data,
            "liion_features": feature_data,
            "liion_root_properties": properties(liion),
            "liion_root_type": str(liion.getType()),
            "var1": {
                str(name): str(comp.variable("var1").get(str(name)))
                for name in comp.variable("var1").varnames()
            },
            "pouch_views": view_data,
            "geometry_features": [str(item) for item in comp.geom("geom1").feature().tags()],
            "variable_groups": [str(item) for item in comp.variable().tags()],
            "physics": [str(item) for item in comp.physics().tags()],
            "studies": [str(item) for item in coin.study().tags()],
            "solutions": [str(item) for item in coin.sol().tags()],
        })
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove("coin_inspect")
        remove("pouch_inspect")
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps({"ok": payload.get("ok"), "result": str(RESULT)}, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
