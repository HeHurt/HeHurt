import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding\binding_audit.json")
TAG = "coin_v4_binding_audit"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def read_property(node, prop):
    for method in ("getString", "getStringArray", "getStringMatrix", "getDouble", "getBoolean"):
        try:
            return jsonable(getattr(node, method)(prop))
        except Exception:
            continue
    return None


def inspect_function(node, tag):
    item = {"tag": tag, "label": str(node.label()), "type": str(node.getType()), "properties": {}}
    for prop in [str(value) for value in node.properties()]:
        if prop.lower() in {"funcname", "filename", "source", "argunit", "fununit", "interp", "extrap", "table", "struct"} or any(
            key in prop.lower() for key in ("func", "file", "unit")
        ):
            value = read_property(node, prop)
            if value is not None:
                item["properties"][prop] = value
    return item


model = ModelUtil.load(TAG, MODEL)
result = {"source": MODEL, "functions": {"global": [], "component": []}, "consumers": {}}
try:
    global_funcs = model.func()
    for function_tag in [str(value) for value in global_funcs.tags()]:
        result["functions"]["global"].append(inspect_function(model.func(function_tag), function_tag))
    comp_funcs = model.component("comp1").func()
    for function_tag in [str(value) for value in comp_funcs.tags()]:
        result["functions"]["component"].append(inspect_function(model.component("comp1").func(function_tag), function_tag))

    liion = model.component("comp1").physics("liion")
    for tag in ("pce1", "sep1", "pce2"):
        node = liion.feature(tag)
        result["consumers"][tag] = {
            prop: read_property(node, prop)
            for prop in ("ElectrolyteMaterial", "sigmal_mat", "sigmal", "Dl_mat", "Dl", "transpNum_mat", "transpNum", "fDl")
        }
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT), "functions": result["functions"], "consumers": result["consumers"]}, ensure_ascii=False))
