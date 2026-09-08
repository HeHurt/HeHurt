"""Reload and independently verify the corrected single-layer pouch model."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v9_corrected_geometry_mesh.mph"
RESULT = RUN / "verify_pouch_v9_corrected_geometry_mesh_result.json"
TAG = "pouch_dual_tab_v9_verify"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def entities(selection, dimension: int) -> list[int]:
    return sorted(int(item) for item in selection.entities(dimension))


def feature_tags(container) -> list[str]:
    return [str(item) for item in container.tags()]


def main() -> None:
    payload: dict[str, object] = {"model": str(SOURCE), "ok": False}
    remove_model()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        geom = comp.geom("geom1")
        mesh = comp.mesh("mesh1")
        liion = comp.physics("liion")

        parameters = {
            name: str(model.param().get(name))
            for name in ("W_cell", "H_cell", "W_tab", "H_tab", "H_neg_cc_ext", "H_pos_cc_ext", "L_tab", "X_tab")
        }
        expected_parameters = {
            "W_cell": "52[mm]",
            "H_cell": "86[mm]",
            "W_tab": "30[mm]",
            "H_tab": "35[mm]",
            "H_neg_cc_ext": "14.5[mm]",
            "H_pos_cc_ext": "12.5[mm]",
            "L_tab": "0.20[mm]",
            "X_tab": "(W_cell-W_tab)/2",
        }
        if parameters != expected_parameters:
            raise RuntimeError(f"Parameter assertion failed: {parameters}")

        geometry = {
            "negative_header_pos": [str(x) for x in geom.feature("blk_neg_header").getStringArray("pos")],
            "negative_header_size": [str(x) for x in geom.feature("blk_neg_header").getStringArray("size")],
            "positive_header_pos": [str(x) for x in geom.feature("blk_pos_header").getStringArray("pos")],
            "positive_header_size": [str(x) for x in geom.feature("blk_pos_header").getStringArray("size")],
            "negative_tab_pos": [str(x) for x in geom.feature("blk1").getStringArray("pos")],
            "negative_tab_size": [str(x) for x in geom.feature("blk1").getStringArray("size")],
            "positive_tab_pos": [str(x) for x in geom.feature("blk2").getStringArray("pos")],
            "positive_tab_size": [str(x) for x in geom.feature("blk2").getStringArray("size")],
        }
        expected_geometry = {
            "negative_header_pos": ["0", "H_cell", "0"],
            "negative_header_size": ["W_cell", "H_neg_cc_ext", "L_neg_cc/2"],
            "positive_header_pos": ["0", "-H_pos_cc_ext", "L_neg_cc/2+L_neg+L_sep+L_pos"],
            "positive_header_size": ["W_cell", "H_pos_cc_ext", "L_pos_cc/2"],
            "negative_tab_pos": ["X_tab", "H_cell+H_neg_cc_ext", "L_neg_cc/2-L_tab"],
            "negative_tab_size": ["W_tab", "H_tab", "L_tab"],
            "positive_tab_pos": ["X_tab", "-H_pos_cc_ext-H_tab", "L_neg_cc/2+L_neg+L_sep+L_pos"],
            "positive_tab_size": ["W_tab", "H_tab", "L_tab"],
        }
        if geometry != expected_geometry:
            raise RuntimeError(f"Geometry assertion failed: {geometry}")

        domains = {
            "positive_header": entities(comp.selection("geom1_blk_pos_header_dom"), 3),
            "negative_cc": entities(comp.selection("box_neg_cc_active_v8"), 3),
            "negative_electrode": entities(comp.selection("box_neg_electrode_v8"), 3),
            "separator": entities(comp.selection("box_separator_v8"), 3),
            "positive_electrode": entities(comp.selection("box_pos_electrode_v8"), 3),
            "positive_cc": entities(comp.selection("box_pos_cc_active_v8"), 3),
            "negative_header": entities(comp.selection("geom1_blk_neg_header_dom"), 3),
            "positive_tab": entities(comp.selection("geom1_blk2_dom"), 3),
            "negative_tab": entities(comp.selection("geom1_blk1_dom"), 3),
        }
        if sorted(value[0] for value in domains.values() if len(value) == 1) != list(range(1, 10)):
            raise RuntimeError(f"Domain partition assertion failed: {domains}")

        materials = {tag: entities(comp.material(tag).selection(), 3) for tag in ("mat1", "mat2", "mat3", "mat4", "mat5")}
        expected_materials = {"mat1": [1, 6, 8], "mat2": [2, 7, 9], "mat3": [3], "mat4": [5], "mat5": [4]}
        if materials != expected_materials:
            raise RuntimeError(f"Material assertion failed: {materials}")

        physics = {
            "negative_electrode": entities(liion.feature("pce1").selection(), 3),
            "separator": entities(liion.feature("sep1").selection(), 3),
            "positive_electrode": entities(liion.feature("pce2").selection(), 3),
            "conductors": entities(liion.feature("cc1").selection(), 3),
            "negative_terminal": entities(liion.feature("egnd1").selection(), 2),
            "positive_terminal": entities(liion.feature("ec1").selection(), 2),
        }
        expected_physics = {
            "negative_electrode": [3], "separator": [4], "positive_electrode": [5],
            "conductors": [1, 2, 6, 7, 8, 9], "negative_terminal": [41], "positive_terminal": [31],
        }
        if physics != expected_physics:
            raise RuntimeError(f"Physics assertion failed: {physics}")

        mesh.run()
        mesh_tags = feature_tags(mesh.feature())
        if "map1" not in mesh_tags or "swe1" not in mesh_tags or "dis1" in mesh_tags:
            raise RuntimeError(f"Mesh sequence assertion failed: {mesh_tags}")
        mesh_data = {
            "features": mesh_tags,
            "hmax": str(mesh.feature("size").getString("hmax")),
            "hmin": str(mesh.feature("size").getString("hmin")),
            "hauto": str(mesh.feature("size").getString("hauto")),
            "swept_domains": entities(mesh.feature("swe1").selection(), 3),
        }
        if mesh_data["hmax"] != "5[mm]" or mesh_data["hmin"] != "1[mm]" or mesh_data["hauto"] != "4":
            raise RuntimeError(f"Mesh size assertion failed: {mesh_data}")
        if mesh_data["swept_domains"] != list(range(1, 10)):
            raise RuntimeError(f"Swept-domain assertion failed: {mesh_data}")

        payload.update({
            "ok": True,
            "parameters": parameters,
            "geometry": geometry,
            "domains": domains,
            "materials": materials,
            "physics": physics,
            "mesh": mesh_data,
        })
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove_model()
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
