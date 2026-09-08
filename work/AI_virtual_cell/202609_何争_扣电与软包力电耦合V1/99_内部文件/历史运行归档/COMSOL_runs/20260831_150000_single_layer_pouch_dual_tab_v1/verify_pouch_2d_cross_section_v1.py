"""Reload, remesh and verify the review-first 2D pouch model."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_2d_cross_section_v1_geometry_mesh.mph"
RESULT = RUN / "verify_pouch_2d_cross_section_v1_result.json"
TAG = "pouch_2d_cross_section_v1_verify"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def entities(selection, dimension: int) -> list[int]:
    return sorted(int(item) for item in selection.entities(dimension))


def main() -> None:
    payload: dict[str, object] = {"model": str(SOURCE), "ok": False}
    remove_model()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        geom = comp.geom("geom1")
        mesh = comp.mesh("mesh1")

        if int(geom.getNDomains()) != 9:
            raise RuntimeError(f"Expected 9 domains after reload, got {geom.getNDomains()}")

        tags = {
            "negative_cc": "r_neg_cc", "graphite": "r_neg", "separator": "r_sep",
            "lfp": "r_pos", "positive_cc": "r_pos_cc", "negative_header": "r_neg_header",
            "positive_header": "r_pos_header", "negative_tab": "r_neg_tab", "positive_tab": "r_pos_tab",
        }
        selections = {name: entities(comp.selection(f"geom1_{tag}_dom"), 2) for name, tag in tags.items()}
        if any(len(value) != 1 for value in selections.values()):
            raise RuntimeError(f"Domain selections are not one-to-one: {selections}")
        if sorted(value[0] for value in selections.values()) != list(range(1, 10)):
            raise RuntimeError(f"Domain coverage is not exactly 1..9: {selections}")

        mesh.run()
        mesh_tags = [str(item) for item in mesh.feature().tags()]
        mesh_data = {
            "features": mesh_tags,
            "hmax": str(mesh.feature("size").getString("hmax")),
            "hmin": str(mesh.feature("size").getString("hmin")),
            "hgrad": str(mesh.feature("size").getString("hgrad")),
        }
        if "map1" not in mesh_tags:
            raise RuntimeError(f"Mapped quadrilateral mesh missing: {mesh_data}")
        if mesh_data["hmax"] != "2[mm]" or mesh_data["hmin"] != "1[um]" or mesh_data["hgrad"] != "1.25":
            raise RuntimeError(f"Mesh settings changed after reload: {mesh_data}")

        payload.update({
            "ok": True,
            "domain_count": 9,
            "selections": selections,
            "mesh": mesh_data,
            "physics_count": len([str(item) for item in comp.physics().tags()]),
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
