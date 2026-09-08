"""Inspect the exact V6 geometry and mesh feature tree before rebuilding it."""

from __future__ import annotations

import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v7_corrected_geometry_mesh.mph"
RESULT = RUN / "audit_pouch_v7_geometry_features_result.json"
TAG = "audit_pouch_v7_geometry_features"


def value(node, key):
    for getter in ("getString", "getStringArray", "getIntArray"):
        try:
            result = getattr(node, getter)(key)
            if isinstance(result, (str, int, float, bool)) or result is None:
                return result
            return [str(item) for item in result]
        except Exception:
            pass
    return None


def main() -> None:
    payload = {"ok": False}
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        geom = comp.geom("geom1")
        geometry = {}
        keys = (
            "pos", "size", "lx", "ly", "lz", "x", "y", "z", "distance",
            "workplane", "input", "selresult", "createselection", "intbnd",
        )
        for feature_tag in geom.feature().tags():
            feature = geom.feature(feature_tag)
            geometry[feature_tag] = {
                "type": feature.getType(),
                "label": feature.label(),
                "properties": {key: value(feature, key) for key in keys if value(feature, key) is not None},
            }

        workplane = {}
        wp_geom = geom.feature("wp1").geom()
        for feature_tag in wp_geom.feature().tags():
            feature = wp_geom.feature(feature_tag)
            workplane[feature_tag] = {
                "type": feature.getType(),
                "label": feature.label(),
                "pos": value(feature, "pos"),
                "size": value(feature, "size"),
                "lx": value(feature, "lx"),
                "ly": value(feature, "ly"),
            }

        selections = {}
        for selection_tag in comp.selection().tags():
            selection = comp.selection(selection_tag)
            item = {"label": selection.label()}
            for dim in (3, 2, 1, 0):
                try:
                    entities = list(selection.entities(dim))
                    if entities:
                        item[str(dim)] = entities
                except Exception:
                    pass
            selections[selection_tag] = item

        mesh = comp.mesh("mesh1")
        mesh_features = {}
        for feature_tag in mesh.feature().tags():
            feature = mesh.feature(feature_tag)
            selected = []
            for dim in (3, 2, 1, 0):
                try:
                    entities = list(feature.selection().entities(dim))
                    if entities:
                        selected.append({"dim": dim, "entities": entities})
                except Exception:
                    pass
            mesh_features[feature_tag] = {
                "type": feature.getType(),
                "label": feature.label(),
                "hauto": value(feature, "hauto"),
                "hmax": value(feature, "hmax"),
                "hmin": value(feature, "hmin"),
                "numelem": value(feature, "numelem"),
                "method": value(feature, "method"),
                "selection": selected,
            }
        materials = {}
        for material_tag in comp.material().tags():
            material = comp.material(material_tag)
            material_selection = []
            try:
                material_selection = list(material.selection().entities(3))
            except Exception:
                pass
            materials[material_tag] = {
                "label": material.label(),
                "selection": material_selection,
            }
        liion = comp.physics("liion")
        physics_selections = {}
        for feature_tag in ("pce1", "sep1", "pce2", "cc1", "egnd1", "ec1"):
            feature = liion.feature(feature_tag)
            selected = []
            for dimension in (3, 2):
                try:
                    current = list(feature.selection().entities(dimension))
                    if current:
                        selected.append({"dim": dimension, "entities": current})
                except Exception:
                    pass
            physics_selections[feature_tag] = selected
        payload = {
            "ok": True,
            "geometry": geometry,
            "workplane": workplane,
            "selections": selections,
            "materials": materials,
            "physics_selections": physics_selections,
            "mesh": mesh_features,
        }
    except Exception as exc:
        payload = {"ok": False, "error": repr(exc)}
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
