import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_100528_coin_geometry_simplified_audit\mapped_mesh_test.json")
TAG = "coin_simplified_mapped_mesh"


def stats(mesh):
    result = {"elements": int(mesh.getNumElem()), "vertices": int(mesh.getNumVertex()), "types": {}}
    for kind in [str(value) for value in mesh.getTypes()]:
        result["types"][kind] = {
            "count": int(mesh.getNumElem(kind)),
            "min_quality": float(mesh.getMinQuality(kind)),
            "mean_quality": float(mesh.getMeanQuality(kind)),
        }
    return result


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        mesh = model.component("comp1").mesh("mesh1")
        mesh.run()
        baseline = stats(mesh)
        mesh.feature("ftri1").active(False)
        mapped = mesh.feature().create("map_audit", "Map")
        mapped.selection().geom("geom1", 2)
        mapped.selection().set([1, 2, 3, 4, 5])
        mesh.run()
        payload = {
            "source": SOURCE,
            "baseline_free_tri": baseline,
            "mapped_quad": stats(mesh),
            "saved": False,
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
