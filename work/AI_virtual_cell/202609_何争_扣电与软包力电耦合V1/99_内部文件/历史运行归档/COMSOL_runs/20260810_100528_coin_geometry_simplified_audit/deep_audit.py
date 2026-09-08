import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_100528_coin_geometry_simplified_audit\deep_audit.json")
TAG = "coin_simplified_deep_audit"


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


def selection(node):
    result = {}
    try:
        result["entities"] = [int(value) for value in node.selection().entities()]
    except Exception:
        result["entities"] = []
    try:
        result["named"] = str(node.selection().named())
    except Exception:
        pass
    return result


def physics_feature(comp, physics_tag, *path):
    node = comp.physics(physics_tag).feature(path[0])
    for tag in path[1:]:
        node = node.feature(tag)
    return {
        "label": str(node.label()),
        "type": str(node.getType()),
        "selection": selection(node),
        "properties": properties(node),
    }


def function_tree(manager):
    result = {}
    for tag in tags(manager):
        node = manager.get(tag)
        result[tag] = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "properties": properties(node),
        }
    return result


def mesh_info(mesh):
    features = {}
    for tag in tags(mesh.feature()):
        node = mesh.feature(tag)
        features[tag] = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "selection": selection(node),
            "properties": properties(node),
        }
    types = {}
    for element_type in [str(value) for value in mesh.getTypes()]:
        types[element_type] = {
            "count": int(mesh.getNumElem(element_type)),
            "min_quality": float(mesh.getMinQuality(element_type)),
            "mean_quality": float(mesh.getMeanQuality(element_type)),
        }
    return {
        "automatic": bool(mesh.isAutomatic()),
        "complete": bool(mesh.isComplete()),
        "elements": int(mesh.getNumElem()),
        "vertices": int(mesh.getNumVertex()),
        "types": types,
        "features": features,
    }


def table_data(model):
    table = model.result().table("tbl1")
    result = {}
    for method, key in (("getColumnHeaders", "headers"), ("getReal", "real")):
        try:
            result[key] = jsonable(getattr(table, method)())
        except Exception as exc:
            result[key + "_error"] = str(exc)
    return result


def solution_info(model):
    result = {}
    for tag in tags(model.sol()):
        sol = model.sol(tag)
        try:
            result[tag] = {
                "pvals": jsonable(sol.getPVals()),
                "default_solnum": int(sol.getDefaultSolnum()),
            }
        except Exception as exc:
            result[tag] = {"error": str(exc)}
    return result


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        comp = model.component("comp1")
        feature_paths = {
            "event_states": ("ev", "ds1"),
            "event_indicators": ("ev", "is1"),
            "negative_particle": ("liion", "pce1", "pin1"),
            "negative_reaction": ("liion", "pce1", "per1"),
            "positive_particle": ("liion", "pce2", "pin1"),
            "positive_reaction": ("liion", "pce2", "per1"),
            "terminal_current": ("liion", "ecd1"),
            "ground": ("liion", "egnd1"),
            "init_negative": ("liion", "init1"),
            "init_positive": ("liion", "init4"),
            "init_al": ("liion", "init2"),
            "init_cu": ("liion", "init3"),
        }
        features = {
            name: physics_feature(comp, path[0], *path[1:])
            for name, path in feature_paths.items()
        }
        meshes = {}
        for component_tag in tags(model.component()):
            component = model.component(component_tag)
            for mesh_tag in tags(component.mesh()):
                meshes[component_tag + "/" + mesh_tag] = mesh_info(component.mesh(mesh_tag))
        payload = {
            "source": SOURCE,
            "functions": function_tree(model.func()),
            "features": features,
            "meshes": meshes,
            "solutions": solution_info(model),
            "probe_table": table_data(model),
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
