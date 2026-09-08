import json
from pathlib import Path


SOURCE = r"E:\Downloads\coin_geometry.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\ocp_probe.json")
TAG = "coin_ocp_probe"


def tags(manager):
    try:
        return [str(value) for value in manager.tags()]
    except Exception:
        return []


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def properties(node):
    result = {}
    try:
        names = [str(name) for name in node.properties()]
    except Exception:
        names = []
    for name in names:
        for method in ("getString", "getStringArray", "getStringMatrix", "getDouble", "getBoolean"):
            try:
                value = getattr(node, method)(name)
                if value is not None:
                    result[name] = jsonable(value)
                    break
            except Exception:
                continue
    return result


def feature(component, physics_tag, path):
    node = component.physics(physics_tag).feature(path[0])
    for tag in path[1:]:
        node = node.feature(tag)
    try:
        selection = [int(value) for value in node.selection().entities()]
    except Exception:
        selection = []
    return {
        "label": str(node.label()),
        "type": str(node.getType()),
        "selection": selection,
        "properties": properties(node),
    }


def event_feature(component, path):
    result = feature(component, "ev", path)
    node = component.physics("ev").feature(path[0])
    variants = {}
    for name in (
        "dim",
        "dimInit",
        "indDim",
        "g",
        "condition",
        "reInitName",
        "reInitValue",
    ):
        values = {}
        for method in ("getStringMatrix", "getStringArray", "getString"):
            try:
                value = getattr(node, method)(name)
                if value is not None:
                    values[method] = jsonable(value)
            except Exception:
                pass
        if values:
            variants[name] = values
    result["property_variants"] = variants
    return result


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


def variable_tree(component):
    result = {}
    for tag in tags(component.variable()):
        node = component.variable(tag)
        entries = {}
        try:
            names = [str(name) for name in node.varnames()]
        except Exception:
            names = []
        for name in names:
            try:
                entries[name] = str(node.get(name))
            except Exception:
                pass
        result[tag] = {"label": str(node.label()), "entries": entries}
    return result


def table_data(model, tag):
    table = model.result().table(tag)
    result = {"properties": properties(table)}
    for method, key in (("getColumnHeaders", "headers"), ("getReal", "real")):
        try:
            result[key] = jsonable(getattr(table, method)())
        except Exception as exc:
            result[key + "_error"] = str(exc)
    return result


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        comp = model.component("comp1")
        probes = {}
        for tag in tags(comp.probe()):
            node = comp.probe(tag)
            try:
                selection = [int(value) for value in node.selection().entities()]
            except Exception:
                selection = []
            probes[tag] = {
                "label": str(node.label()),
                "type": str(node.getType()),
                "selection": selection,
                "properties": properties(node),
            }

        payload = {
            "source": SOURCE,
            "global_functions": function_tree(model.func()),
            "component_functions": function_tree(comp.func()),
            "features": {
                "event_ds1": event_feature(comp, ["ds1"]),
                "event_is1": event_feature(comp, ["is1"]),
                "event_impl2": event_feature(comp, ["impl2"]),
                "event_impl3": event_feature(comp, ["impl3"]),
                "event_impl5": event_feature(comp, ["impl5"]),
                "event_impl6": event_feature(comp, ["impl6"]),
                "socicd1": feature(comp, "liion", ["socicd1"]),
                "pce1": feature(comp, "liion", ["pce1"]),
                "pce1_pin1": feature(comp, "liion", ["pce1", "pin1"]),
                "pce1_per1": feature(comp, "liion", ["pce1", "per1"]),
                "pce2": feature(comp, "liion", ["pce2"]),
                "pce2_pin1": feature(comp, "liion", ["pce2", "pin1"]),
                "pce2_per1": feature(comp, "liion", ["pce2", "per1"]),
                "ecd1": feature(comp, "liion", ["ecd1"]),
                "init1": feature(comp, "liion", ["init1"]),
                "init4": feature(comp, "liion", ["init4"]),
            },
            "variables": variable_tree(comp),
            "probes": probes,
            "table_tbl1": table_data(model, "tbl1"),
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
