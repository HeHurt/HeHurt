"""Build a review-first 2D length-thickness pouch-cell cross-section."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
OUTPUT = RUN / "pouch_dual_tab_2d_cross_section_v1_geometry_mesh.mph"
RESULT = RUN / "build_pouch_2d_cross_section_v1_result.json"
TAG = "pouch_2d_cross_section_v1"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def create_rectangle(geom, tag: str, label: str, pos: list[str], size: list[str]) -> None:
    geom.feature().create(tag, "Rectangle")
    feature = geom.feature(tag)
    feature.label(label)
    feature.set("pos", pos)
    feature.set("size", size)
    feature.set("selresult", "on")


def entities(selection, dimension: int) -> list[int]:
    return sorted(int(item) for item in selection.entities(dimension))


def main() -> None:
    payload: dict[str, object] = {"output": str(OUTPUT), "ok": False}
    remove_model()
    try:
        model = ModelUtil.create(TAG)
        model.label("Single-layer pouch 2D cross-section V1 - geometry and structured mesh")

        parameters = {
            "H_cell": ("86[mm]", "Coated active length"),
            "W_cell": ("52[mm]", "Out-of-plane coated width for later 2D physics"),
            "H_neg_cc_ext": ("14.5[mm]", "Negative bare-current-collector extension"),
            "H_pos_cc_ext": ("12.5[mm]", "Positive bare-current-collector extension"),
            "H_tab": ("35[mm]", "Tab length in this cross-section"),
            "W_tab": ("30[mm]", "Out-of-plane tab width for later 2D physics"),
            "L_neg_cc": ("8[um]", "Negative current collector full nominal thickness"),
            "L_neg": ("61.5[um]", "Graphite electrode thickness"),
            "L_sep": ("9[um]", "Separator thickness"),
            "L_pos": ("84[um]", "LFP electrode thickness"),
            "L_pos_cc": ("13[um]", "Positive current collector full nominal thickness"),
            "L_tab": ("0.20[mm]", "Tab thickness"),
            "x_neg_header": ("-H_neg_cc_ext", "Negative header start"),
            "x_neg_tab": ("-H_neg_cc_ext-H_tab", "Negative tab start"),
            "x_pos_header": ("H_cell", "Positive header start"),
            "x_pos_tab": ("H_cell+H_pos_cc_ext", "Positive tab start"),
            "z_pos_cc": ("L_neg_cc/2+L_neg+L_sep+L_pos", "Positive collector lower coordinate"),
        }
        for name, (expression, description) in parameters.items():
            model.param().set(name, expression, description)

        model.component().create("comp1", True)
        comp = model.component("comp1")
        comp.geom().create("geom1", 2)
        geom = comp.geom("geom1")
        geom.lengthUnit("mm")
        geom.axisymmetric(False)

        # Active stack, from negative collector to positive collector.
        create_rectangle(geom, "r_neg_cc", "Negative current collector - coated region", ["0", "0"], ["H_cell", "L_neg_cc/2"])
        create_rectangle(geom, "r_neg", "Graphite electrode", ["0", "L_neg_cc/2"], ["H_cell", "L_neg"])
        create_rectangle(geom, "r_sep", "Separator", ["0", "L_neg_cc/2+L_neg"], ["H_cell", "L_sep"])
        create_rectangle(geom, "r_pos", "LFP electrode", ["0", "L_neg_cc/2+L_neg+L_sep"], ["H_cell", "L_pos"])
        create_rectangle(geom, "r_pos_cc", "Positive current collector - coated region", ["0", "z_pos_cc"], ["H_cell", "L_pos_cc/2"])

        # Bare collector extensions between the coated stack and each tab.
        create_rectangle(geom, "r_neg_header", "Negative bare collector extension", ["x_neg_header", "0"], ["H_neg_cc_ext", "L_neg_cc/2"])
        create_rectangle(geom, "r_pos_header", "Positive bare collector extension", ["x_pos_header", "z_pos_cc"], ["H_pos_cc_ext", "L_pos_cc/2"])

        # Tabs are attached to the outer ends of the extensions and thicken away from the stack.
        create_rectangle(geom, "r_neg_tab", "Negative tab", ["x_neg_tab", "L_neg_cc/2-L_tab"], ["H_tab", "L_tab"])
        create_rectangle(geom, "r_pos_tab", "Positive tab", ["x_pos_tab", "z_pos_cc"], ["H_tab", "L_tab"])

        geom.run()
        domain_count = int(geom.getNDomains())
        if domain_count != 9:
            raise RuntimeError(f"Expected 9 rectangular domains, got {domain_count}")

        comp.mesh().create("mesh1")
        mesh = comp.mesh("mesh1")
        size = mesh.feature("size")
        size.set("custom", "on")
        size.set("hmax", "2[mm]")
        size.set("hmin", "1[um]")
        size.set("hgrad", "1.25")
        size.set("hcurve", "0.25")
        mesh.feature().create("map1", "Map")
        mesh.run()

        generated_selections = {
            name: entities(comp.selection(f"geom1_{tag}_dom"), 2)
            for name, tag in {
                "negative_cc": "r_neg_cc",
                "graphite": "r_neg",
                "separator": "r_sep",
                "lfp": "r_pos",
                "positive_cc": "r_pos_cc",
                "negative_header": "r_neg_header",
                "positive_header": "r_pos_header",
                "negative_tab": "r_neg_tab",
                "positive_tab": "r_pos_tab",
            }.items()
        }
        if any(len(value) != 1 for value in generated_selections.values()):
            raise RuntimeError(f"Generated domain selections are not one-to-one: {generated_selections}")

        model.save(str(OUTPUT))
        payload.update({
            "ok": True,
            "domain_count": domain_count,
            "parameters": {name: expression for name, (expression, _) in parameters.items()},
            "selections": generated_selections,
            "mesh": {"type": "Mapped quadrilateral", "hmax": "2[mm]", "hmin": "1[um]", "hgrad": "1.25"},
            "scope": "Geometry, generated selections and mesh only; physics intentionally not added before review.",
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
