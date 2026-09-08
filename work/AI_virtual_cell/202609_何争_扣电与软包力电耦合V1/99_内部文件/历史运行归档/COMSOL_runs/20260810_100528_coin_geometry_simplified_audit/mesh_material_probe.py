import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_100528_coin_geometry_simplified_audit\mesh_material_probe.json")
TAG = "coin_simplified_mesh_probe"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def tags(manager):
    try:
        return [str(value) for value in manager.tags()]
    except Exception:
        return []


def get_property(node, name):
    for method in ("getStringMatrix", "getStringArray", "getString", "getDouble", "getBoolean"):
        try:
            value = getattr(node, method)(name)
            if value is not None:
                return jsonable(value)
        except Exception:
            continue
    return None


def mesh_stats(mesh):
    result = {
        "elements": int(mesh.getNumElem()),
        "vertices": int(mesh.getNumVertex()),
        "types": {},
    }
    for kind in [str(value) for value in mesh.getTypes()]:
        result["types"][kind] = {
            "count": int(mesh.getNumElem(kind)),
            "min_quality": float(mesh.getMinQuality(kind)),
            "mean_quality": float(mesh.getMeanQuality(kind)),
        }
    return result


def material_info(comp):
    result = {}
    for tag in tags(comp.material()):
        material = comp.material(tag)
        groups = {}
        for group_tag in tags(material.propertyGroup()):
            group = material.propertyGroup(group_tag)
            values = {}
            for name in ("Eeq", "dEeqdT", "sigma", "conductivity"):
                value = get_property(group, name)
                if value is not None:
                    values[name] = value
            if values:
                groups[group_tag] = values
        result[tag] = {"label": str(material.label()), "groups": groups}
    return result


def geometry_info(comp):
    geom = comp.geom("geom1")
    result = {"dimension": int(geom.getSDim())}
    try:
        result["bounding_box"] = jsonable(geom.getBoundingBox())
    except Exception as exc:
        result["bounding_box_error"] = str(exc)
    domains = {}
    for domain in range(1, 6):
        try:
            measure = geom.measure()
            measure.selection().init(2)
            measure.selection().set([domain])
            domains[str(domain)] = {
                "area_m2": float(measure.getVolume()),
                "boundary_length_m": float(measure.getArea()),
            }
        except Exception as exc:
            domains[str(domain)] = {"error": str(exc)}
    result["domains"] = domains
    return result


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        comp = model.component("comp1")
        macro = comp.mesh("mesh1")
        macro.run()
        baseline = mesh_stats(macro)

        macro.feature("size").set("hmax", "200[um]")
        macro.feature("size").set("hmin", "40[um]")
        macro.feature("size1").set("hmax", "200[um]")
        macro.feature("size1").set("hmin", "40[um]")
        macro.run()
        conservative = mesh_stats(macro)

        particles = {}
        for component_tag in ("liion_pce1_pin1_xdim", "liion_pce2_pin1_xdim"):
            mesh = model.component(component_tag).mesh(component_tag)
            before = mesh_stats(mesh)
            mesh.feature("dis1").set("numelem", "6")
            mesh.run()
            particles[component_tag] = {"baseline": before, "six_elements": mesh_stats(mesh)}

        payload = {
            "source": SOURCE,
            "geometry": geometry_info(comp),
            "materials": material_info(comp),
            "macro_mesh": {
                "baseline": baseline,
                "conservative_200um_40um": conservative,
            },
            "particle_mesh": particles,
            "saved": False,
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
