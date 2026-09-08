import json
from pathlib import Path


SOURCE = r"E:\Downloads\coin_geometry_参数路径已切换.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\mesh_audit.json")
TAG = "coin_mesh_audit"


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


def properties(node):
    result = {}
    try:
        names = [str(name) for name in node.properties()]
    except Exception:
        names = []
    for name in names:
        for method in ("getStringMatrix", "getStringArray", "getString", "getDouble", "getBoolean"):
            try:
                value = getattr(node, method)(name)
                if value is not None:
                    result[name] = jsonable(value)
                    break
            except Exception:
                continue
    return result


def feature_tree(manager):
    result = {}
    for tag in tags(manager):
        node = manager.get(tag)
        try:
            selection = [int(value) for value in node.selection().entities()]
        except Exception:
            selection = []
        entry = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "selection": selection,
            "properties": properties(node),
        }
        try:
            entry["active"] = bool(node.isActive())
        except Exception:
            pass
        children = feature_tree(node.feature())
        if children:
            entry["features"] = children
        result[tag] = entry
    return result


def mesh_info(mesh):
    entry = {
        "automatic": bool(mesh.isAutomatic()),
        "complete": bool(mesh.isComplete()),
        "empty": bool(mesh.isEmpty()),
        "locked": bool(mesh.isLocked()),
        "has_problems": bool(mesh.hasProblems()),
        "num_elements": int(mesh.getNumElem()),
        "num_vertices": int(mesh.getNumVertex()),
        "element_types": {},
        "features": feature_tree(mesh.feature()),
        "build_time_s": int(mesh.buildTime()),
        "build_date": str(mesh.buildDate()),
        "build_version": str(mesh.buildComsolVersion()),
    }
    for element_type in [str(value) for value in mesh.getTypes()]:
        item = {"count": int(mesh.getNumElem(element_type))}
        for method, key in (("getMinQuality", "min_quality"), ("getMeanQuality", "mean_quality")):
            try:
                item[key] = float(getattr(mesh, method)(element_type))
            except Exception:
                pass
        entry["element_types"][element_type] = item
    return entry


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        components = {}
        for component_tag in tags(model.component()):
            component = model.component(component_tag)
            components[component_tag] = {
                mesh_tag: mesh_info(component.mesh(mesh_tag))
                for mesh_tag in tags(component.mesh())
            }
        payload = {"source": SOURCE, "components": components}
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
