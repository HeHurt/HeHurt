"""Repair all layer/material selections after the corrected V7 geometry renumbered domains."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v7_corrected_geometry_mesh.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v8_corrected_geometry_mesh.mph"
RESULT = RUN / "fix_pouch_v8_domain_selections_result.json"
TAG = "pouch_dual_tab_v8"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def entities(selection, dimension: int) -> list[int]:
    return [int(item) for item in selection.entities(dimension)]


def create_domain_box(comp, tag: str, label: str, zmin: str, zmax: str) -> list[int]:
    try:
        comp.selection().remove(tag)
    except Exception:
        pass
    comp.selection().create(tag, "Box")
    selection = comp.selection(tag)
    selection.label(label)
    selection.set("entitydim", "3")
    selection.set("condition", "inside")
    selection.set("xmin", "-0.1[mm]")
    selection.set("xmax", "W_cell+0.1[mm]")
    selection.set("ymin", "-0.1[mm]")
    selection.set("ymax", "H_cell+0.1[mm]")
    selection.set("zmin", zmin)
    selection.set("zmax", zmax)
    selected = entities(selection, 3)
    if len(selected) != 1:
        raise RuntimeError(f"{tag} expected one active-stack domain, got {selected}")
    return selected


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove_model()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        geom = comp.geom("geom1")

        neg_cc = create_domain_box(comp, "box_neg_cc_active_v8", "Negative Cu collector under coating", "-0.1[um]", "L_neg_cc/2+0.1[um]")
        neg_electrode = create_domain_box(
            comp,
            "box_neg_electrode_v8",
            "Graphite coated active domain",
            "L_neg_cc/2-0.1[um]",
            "L_neg_cc/2+L_neg+0.1[um]",
        )
        separator = create_domain_box(
            comp,
            "box_separator_v8",
            "Separator active domain",
            "L_neg_cc/2+L_neg-0.1[um]",
            "L_neg_cc/2+L_neg+L_sep+0.1[um]",
        )
        pos_electrode = create_domain_box(
            comp,
            "box_pos_electrode_v8",
            "LFP coated active domain",
            "L_neg_cc/2+L_neg+L_sep-0.1[um]",
            "L_neg_cc/2+L_neg+L_sep+L_pos+0.1[um]",
        )
        pos_cc = create_domain_box(
            comp,
            "box_pos_cc_active_v8",
            "Positive Al collector under coating",
            "L_neg_cc/2+L_neg+L_sep+L_pos-0.1[um]",
            "L_neg_cc/2+L_neg+L_sep+L_pos+L_pos_cc/2+0.1[um]",
        )

        neg_tab = entities(comp.selection("geom1_blk1_dom"), 3)
        pos_tab = entities(comp.selection("geom1_blk2_dom"), 3)
        neg_header = entities(comp.selection("geom1_blk_neg_header_dom"), 3)
        pos_header = entities(comp.selection("geom1_blk_pos_header_dom"), 3)

        corrected_geometry_selections = {
            "sel1": pos_tab,
            "sel2": pos_cc + pos_header,
            "sel3": pos_electrode,
            "sel4": neg_tab,
            "sel5": neg_cc + neg_header,
            "sel6": neg_electrode,
            "sel7": separator,
        }
        for selection_tag, selected_domains in corrected_geometry_selections.items():
            selection = geom.feature(selection_tag).selection("selection")
            selection.clear()
            selection.set("fin", 3, selected_domains)
        geom.run()

        liion = comp.physics("liion")
        conductor_domains = sorted(neg_cc + pos_cc + neg_header + pos_header + neg_tab + pos_tab)
        negative_terminal_faces = entities(comp.selection("sel_neg_terminal_v7"), 2)
        positive_terminal_faces = entities(comp.selection("sel_pos_terminal_v7"), 2)
        liion.feature("pce1").selection().set(neg_electrode)
        liion.feature("pce2").selection().set(pos_electrode)
        liion.feature("cc1").selection().set(conductor_domains)
        liion.feature("egnd1").selection().set(negative_terminal_faces)
        liion.feature("ec1").selection().set(positive_terminal_faces)
        soc_feature = liion.feature("socicd1")
        soc_feature.feature("neges1").selection().set(neg_electrode)
        soc_feature.feature("poses1").selection().set(pos_electrode)
        # Separator 1 is a derived/non-editable selection in this official
        # template; it is recomputed from the electrode selections above.

        # Rebuild because updating the final geometry selections invalidates the
        # existing mesh sequence, even though the geometry solids are unchanged.
        all_domains = sorted(set(neg_cc + neg_electrode + separator + pos_electrode + pos_cc + neg_header + pos_header + neg_tab + pos_tab))
        mesh = comp.mesh("mesh1")
        mesh.feature("swe1").selection().set(all_domains)
        mesh.run()

        material_domains = {}
        for material_tag in comp.material().tags():
            material_domains[material_tag] = {
                "label": comp.material(material_tag).label(),
                "domains": entities(comp.material(material_tag).selection(), 3),
            }
        physics_domains = {
            "pce1_negative": entities(liion.feature("pce1").selection(), 3),
            "separator": entities(liion.feature("sep1").selection(), 3),
            "pce2_positive": entities(liion.feature("pce2").selection(), 3),
            "current_conductors": entities(liion.feature("cc1").selection(), 3),
            "negative_terminal": entities(liion.feature("egnd1").selection(), 2),
            "positive_terminal": entities(liion.feature("ec1").selection(), 2),
        }

        expected = {
            "pce1_negative": neg_electrode,
            "separator": separator,
            "pce2_positive": pos_electrode,
            "current_conductors": conductor_domains,
        }
        for key, expected_entities in expected.items():
            if sorted(physics_domains[key]) != sorted(expected_entities):
                raise RuntimeError(f"Selection assertion failed for {key}: {physics_domains[key]} != {expected_entities}")
        if len(physics_domains["negative_terminal"]) != 1 or len(physics_domains["positive_terminal"]) != 1:
            raise RuntimeError(f"Terminal assertion failed: {physics_domains}")

        model.label("Single-layer pouch V8 - corrected geometry, selections and mapped-swept mesh")
        model.save(str(OUTPUT))
        payload.update(
            {
                "ok": True,
                "layer_domains": {
                    "negative_collector_active": neg_cc,
                    "negative_electrode": neg_electrode,
                    "separator": separator,
                    "positive_electrode": pos_electrode,
                    "positive_collector_active": pos_cc,
                    "negative_header": neg_header,
                    "positive_header": pos_header,
                    "negative_tab": neg_tab,
                    "positive_tab": pos_tab,
                },
                "physics_domains": physics_domains,
                "material_domains": material_domains,
                "mesh_domains": all_domains,
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
