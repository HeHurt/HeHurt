import json
from pathlib import Path


SOURCE = r"E:\Downloads\coin_geometry_参数路径已切换.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\coarse_mesh_test.json")
TAG = "coin_coarse_mesh_test"


def stats(mesh):
    return {
        "elements": int(mesh.getNumElem()),
        "vertices": int(mesh.getNumVertex()),
        "types": {
            str(element_type): int(mesh.getNumElem(str(element_type)))
            for element_type in mesh.getTypes()
        },
    }


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        comp = model.component("comp1")
        macro = comp.mesh("mesh1")
        baseline = {
            "macro": stats(macro),
            "negative_particle": stats(
                model.component("liion_pce1_pin1_xdim").mesh("liion_pce1_pin1_xdim")
            ),
            "positive_particle": stats(
                model.component("liion_pce2_pin1_xdim").mesh("liion_pce2_pin1_xdim")
            ),
        }

        macro.feature("size1").set("hauto", "5")
        macro.run()

        comp.physics("liion").feature("pce1").feature("pin1").set("Nel", "6")
        comp.physics("liion").feature("pce2").feature("pin1").set("Nel", "6")
        neg_mesh = model.component("liion_pce1_pin1_xdim").mesh("liion_pce1_pin1_xdim")
        pos_mesh = model.component("liion_pce2_pin1_xdim").mesh("liion_pce2_pin1_xdim")
        neg_mesh.feature("dis1").set("numelem", "6")
        pos_mesh.feature("dis1").set("numelem", "6")
        neg_mesh.run()
        pos_mesh.run()

        candidate = {
            "macro": stats(macro),
            "negative_particle": stats(neg_mesh),
            "positive_particle": stats(pos_mesh),
            "settings": {
                "mesh1.size1.hauto": "5",
                "negative_particle_elements": 6,
                "positive_particle_elements": 6,
            },
        }
        macro.feature("size").set("hauto", "7")
        macro.feature("size1").set("hauto", "7")
        macro.run()
        coarsest_automatic = {
            "macro": stats(macro),
            "settings": {
                "mesh1.size.hauto": "7",
                "mesh1.size1.hauto": "7",
            },
        }
        payload = {
            "source": SOURCE,
            "saved": False,
            "baseline": baseline,
            "candidate": candidate,
            "coarsest_automatic": coarsest_automatic,
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
