"""Finish the corrected pouch model by rebinding material domains explicitly."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v8_corrected_geometry_mesh.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v9_corrected_geometry_mesh.mph"
RESULT = RUN / "fix_pouch_v9_material_selections_result.json"
TAG = "pouch_dual_tab_v9"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def entities(selection, dimension: int) -> list[int]:
    return [int(item) for item in selection.entities(dimension)]


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove_model()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        domains = {
            "neg_cc": entities(comp.selection("box_neg_cc_active_v8"), 3),
            "neg_electrode": entities(comp.selection("box_neg_electrode_v8"), 3),
            "separator": entities(comp.selection("box_separator_v8"), 3),
            "pos_electrode": entities(comp.selection("box_pos_electrode_v8"), 3),
            "pos_cc": entities(comp.selection("box_pos_cc_active_v8"), 3),
            "neg_header": entities(comp.selection("geom1_blk_neg_header_dom"), 3),
            "pos_header": entities(comp.selection("geom1_blk_pos_header_dom"), 3),
            "neg_tab": entities(comp.selection("geom1_blk1_dom"), 3),
            "pos_tab": entities(comp.selection("geom1_blk2_dom"), 3),
        }

        expected_materials = {
            "mat1": sorted(domains["pos_cc"] + domains["pos_header"] + domains["pos_tab"]),
            "mat2": sorted(domains["neg_cc"] + domains["neg_header"] + domains["neg_tab"]),
            "mat3": domains["neg_electrode"],
            "mat4": domains["pos_electrode"],
            "mat5": domains["separator"],
        }
        for material_tag, selected_domains in expected_materials.items():
            comp.material(material_tag).selection().set(selected_domains)

        actual_materials = {
            material_tag: entities(comp.material(material_tag).selection(), 3)
            for material_tag in expected_materials
        }
        for material_tag, expected_domains in expected_materials.items():
            if sorted(actual_materials[material_tag]) != sorted(expected_domains):
                raise RuntimeError(
                    f"Material assertion failed for {material_tag}: "
                    f"{actual_materials[material_tag]} != {expected_domains}"
                )

        liion = comp.physics("liion")
        physics = {
            "negative_electrode": entities(liion.feature("pce1").selection(), 3),
            "separator": entities(liion.feature("sep1").selection(), 3),
            "positive_electrode": entities(liion.feature("pce2").selection(), 3),
            "conductors": entities(liion.feature("cc1").selection(), 3),
            "negative_terminal": entities(liion.feature("egnd1").selection(), 2),
            "positive_terminal": entities(liion.feature("ec1").selection(), 2),
        }
        expected_conductors = sorted(expected_materials["mat1"] + expected_materials["mat2"])
        if physics["negative_electrode"] != domains["neg_electrode"]:
            raise RuntimeError(f"Negative electrode physics mismatch: {physics}")
        if physics["separator"] != domains["separator"]:
            raise RuntimeError(f"Separator physics mismatch: {physics}")
        if physics["positive_electrode"] != domains["pos_electrode"]:
            raise RuntimeError(f"Positive electrode physics mismatch: {physics}")
        if sorted(physics["conductors"]) != expected_conductors:
            raise RuntimeError(f"Current conductor physics mismatch: {physics}")
        if len(physics["negative_terminal"]) != 1 or len(physics["positive_terminal"]) != 1:
            raise RuntimeError(f"Terminal selection mismatch: {physics}")

        model.label("Single-layer pouch V9 - corrected geometry, materials, physics and mesh")
        model.save(str(OUTPUT))
        payload.update(
            {
                "ok": True,
                "domains": domains,
                "materials": actual_materials,
                "physics": physics,
                "mesh": {"hmax": "5[mm]", "hmin": "1[mm]", "sequence": "Mapped 1 + Swept 1"},
            }
        )
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
