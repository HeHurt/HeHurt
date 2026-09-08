"""Correct V6 pouch geometry and rebuild a useful structured mesh.

Geometry convention:
- 52 mm x 86 mm coated active rectangle.
- Negative Cu foil extends 14.5 mm beyond the +y short edge.
- Positive Al foil extends 12.5 mm beyond the -y short edge.
- 30 mm x 35 mm x 0.20 mm tabs are centred on the foil-extension ends.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v6_fast_smoke.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v7_corrected_geometry_mesh.mph"
RESULT = RUN / "build_pouch_v7_corrected_geometry_mesh_result.json"
TAG = "pouch_dual_tab_v7_geometry_mesh"


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
        model.label("Single-layer pouch V7 - corrected foil extensions, centred tabs, mapped-swept mesh")
        model.comments(
            "Corrected from V6 per electrode drawing: 52x86 mm coated area; "
            "14.5 mm negative and 12.5 mm positive uncoated collector extensions; "
            "30x35x0.20 mm tabs centred at opposite short-edge ends."
        )
        param = model.param()
        param.set("H_neg_cc_ext", "14.5[mm]", "Negative Cu uncoated collector extension beyond coating")
        param.set("H_pos_cc_ext", "12.5[mm]", "Positive Al uncoated collector extension beyond coating")
        param.set("L_tab", "0.20[mm]", "Physical tab thickness from electrode drawing")
        param.set("X_tab", "(W_cell-W_tab)/2", "Centred tab x position")

        comp = model.component("comp1")
        geom = comp.geom("geom1")
        z_pos_cc = "L_neg_cc/2+L_neg+L_sep+L_pos"

        # Reposition and thicken the existing tabs. They start only after the
        # full-width uncoated foil extensions, not directly at the coating edge.
        neg_tab = geom.feature("blk1")
        neg_tab.label("Negative tab - centred after Cu foil extension")
        neg_tab.set("pos", ["X_tab", "H_cell+H_neg_cc_ext", "L_neg_cc/2-L_tab"])
        neg_tab.set("size", ["W_tab", "H_tab", "L_tab"])
        neg_tab.set("selresult", "on")

        pos_tab = geom.feature("blk2")
        pos_tab.label("Positive tab - centred after Al foil extension")
        pos_tab.set("pos", ["X_tab", "-H_pos_cc_ext-H_tab", z_pos_cc])
        pos_tab.set("size", ["W_tab", "H_tab", "L_tab"])
        pos_tab.set("selresult", "on")

        # Add the missing uncoated current-collector extensions.
        if "blk_neg_header" not in list(geom.feature().tags()):
            geom.feature().create("blk_neg_header", "Block")
        neg_header = geom.feature("blk_neg_header")
        neg_header.label("Negative Cu foil extension - 14.5 mm")
        neg_header.set("pos", ["0", "H_cell", "0"])
        neg_header.set("size", ["W_cell", "H_neg_cc_ext", "L_neg_cc/2"])
        neg_header.set("selresult", "on")

        if "blk_pos_header" not in list(geom.feature().tags()):
            geom.feature().create("blk_pos_header", "Block")
        pos_header = geom.feature("blk_pos_header")
        pos_header.label("Positive Al foil extension - 12.5 mm")
        pos_header.set("pos", ["0", "-H_pos_cc_ext", z_pos_cc])
        pos_header.set("size", ["W_cell", "H_pos_cc_ext", "L_pos_cc/2"])
        pos_header.set("selresult", "on")

        geom.run()

        # Read generated domains from their source features. The five active
        # stack domains retain the V6 named selections; the new metal domains
        # are added to those selections without guessing domain numbers.
        neg_tab_domains = entities(comp.selection("geom1_blk1_dom"), 3)
        pos_tab_domains = entities(comp.selection("geom1_blk2_dom"), 3)
        neg_header_domains = entities(comp.selection("geom1_blk_neg_header_dom"), 3)
        pos_header_domains = entities(comp.selection("geom1_blk_pos_header_dom"), 3)
        neg_cc_base = entities(comp.selection("geom1_sel5"), 3)
        pos_cc_base = entities(comp.selection("geom1_sel2"), 3)

        geom.feature("sel1").selection("selection").set("fin", 3, pos_tab_domains)
        geom.feature("sel2").selection("selection").set("fin", 3, pos_cc_base + pos_header_domains)
        geom.feature("sel4").selection("selection").set("fin", 3, neg_tab_domains)
        geom.feature("sel5").selection("selection").set("fin", 3, neg_cc_base + neg_header_domains)
        geom.run()

        # Robust coordinate selections for the two outer tab terminal faces.
        for selection_tag in ("sel_neg_terminal_v7", "sel_pos_terminal_v7"):
            try:
                comp.selection().remove(selection_tag)
            except Exception:
                pass
            comp.selection().create(selection_tag, "Box")
            comp.selection(selection_tag).set("entitydim", "2")
            comp.selection(selection_tag).set("condition", "inside")

        neg_terminal = comp.selection("sel_neg_terminal_v7")
        neg_terminal.label("Negative tab outer terminal face")
        neg_terminal.set("xmin", "X_tab-1[um]")
        neg_terminal.set("xmax", "X_tab+W_tab+1[um]")
        neg_terminal.set("ymin", "H_cell+H_neg_cc_ext+H_tab-1[um]")
        neg_terminal.set("ymax", "H_cell+H_neg_cc_ext+H_tab+1[um]")
        neg_terminal.set("zmin", "L_neg_cc/2-L_tab-1[um]")
        neg_terminal.set("zmax", "L_neg_cc/2+1[um]")

        pos_terminal = comp.selection("sel_pos_terminal_v7")
        pos_terminal.label("Positive tab outer terminal face")
        pos_terminal.set("xmin", "X_tab-1[um]")
        pos_terminal.set("xmax", "X_tab+W_tab+1[um]")
        pos_terminal.set("ymin", "-H_pos_cc_ext-H_tab-1[um]")
        pos_terminal.set("ymax", "-H_pos_cc_ext-H_tab+1[um]")
        pos_terminal.set("zmin", z_pos_cc + "-1[um]")
        pos_terminal.set("zmax", z_pos_cc + "+L_tab+1[um]")

        liion = comp.physics("liion")
        liion.feature("egnd1").selection().named("sel_neg_terminal_v7")
        liion.feature("ec1").selection().named("sel_pos_terminal_v7")

        # Rebuild the mesh: regular mapped surface mesh, swept thin layers,
        # and one element through each physical layer. V6's 25 mm global size
        # and five subdivisions on selected edges are removed.
        mesh = comp.mesh("mesh1")
        size = mesh.feature("size")
        size.set("hauto", "4")
        size.set("hmax", "5[mm]")
        size.set("hmin", "1[mm]")
        size.set("hgrad", "1.25")
        size.set("hcurve", "0.3")
        size.set("hnarrow", "0.8")
        try:
            mesh.feature().remove("dis1")
        except Exception:
            pass

        stack_domains = []
        for selection_tag in (
            "geom1_sel1", "geom1_sel2", "geom1_sel3", "geom1_sel4",
            "geom1_sel5", "geom1_sel6", "geom1_sel7",
        ):
            stack_domains.extend(entities(comp.selection(selection_tag), 3))
        all_domains = sorted(set(stack_domains))
        mesh.feature("swe1").selection().set(all_domains)
        mesh.run()

        neg_terminal_faces = entities(neg_terminal, 2)
        pos_terminal_faces = entities(pos_terminal, 2)
        if len(neg_terminal_faces) != 1 or len(pos_terminal_faces) != 1:
            raise RuntimeError(
                f"Expected one terminal face per tab, got negative={neg_terminal_faces}, positive={pos_terminal_faces}"
            )

        model.save(str(OUTPUT))
        payload.update(
            {
                "ok": True,
                "geometry": {
                    "coated_area": "52[mm] x 86[mm]",
                    "negative_collector_extension": "14.5[mm]",
                    "positive_collector_extension": "12.5[mm]",
                    "tabs": "30[mm] x 35[mm] x 0.20[mm], centred on opposite short edges",
                    "negative_tab_domains": neg_tab_domains,
                    "positive_tab_domains": pos_tab_domains,
                    "negative_header_domains": neg_header_domains,
                    "positive_header_domains": pos_header_domains,
                    "negative_terminal_face": neg_terminal_faces,
                    "positive_terminal_face": pos_terminal_faces,
                },
                "mesh": {
                    "type": "mapped surface + swept 3D domains",
                    "hmax": "5[mm]",
                    "hmin": "1[mm]",
                    "through_thickness_distribution": "removed V6 five-edge distribution; one swept element per physical domain",
                    "domains": all_domains,
                },
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
