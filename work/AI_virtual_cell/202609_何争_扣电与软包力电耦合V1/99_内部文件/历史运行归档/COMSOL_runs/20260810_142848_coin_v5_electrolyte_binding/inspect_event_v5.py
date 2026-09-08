import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_solved.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding\event_audit.json")
TAG = "coin_v5_event_audit"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def all_properties(node):
    result = {}
    for prop in [str(value) for value in node.properties()]:
        for method in ("getString", "getStringArray", "getStringMatrix", "getDouble", "getBoolean"):
            try:
                result[prop] = jsonable(getattr(node, method)(prop))
                break
            except Exception:
                continue
    return result


def solver_tree(node):
    result = {}
    try:
        manager = node.feature()
        tags = [str(value) for value in manager.tags()]
    except Exception:
        return result
    for tag in tags:
        child = node.feature(tag)
        props = {
            key: value for key, value in all_properties(child).items()
            if any(word in key.lower() for word in ("tol", "step", "event", "time", "control", "strict"))
        }
        result[tag] = {"label": str(child.label()), "type": str(child.getType()), "properties": props, "children": solver_tree(child)}
    return result


model = ModelUtil.load(TAG, MODEL)
result = {"source": MODEL, "event_features": {}, "variables": {}}
try:
    events = model.component("comp1").physics("ev")
    for feature_tag in [str(value) for value in events.feature().tags()]:
        node = events.feature(feature_tag)
        result["event_features"][feature_tag] = {
            "label": str(node.label()), "type": str(node.getType()), "properties": all_properties(node)
        }
    indicator = events.feature("is1")
    result["indicator_raw"] = {}
    for prop in ("indDim", "g", "dimInit", "dimtInit", "dimDescr"):
        methods = {}
        for method in ("getString", "getStringArray", "getStringMatrix"):
            try:
                methods[method] = jsonable(getattr(indicator, method)(prop))
            except Exception as exc:
                methods[method] = {"error": str(exc)}
        result["indicator_raw"][prop] = methods

    variables = model.component("comp1").variable()
    for group_tag in [str(value) for value in variables.tags()]:
        group = model.component("comp1").variable(group_tag)
        selected = {}
        for name in [str(value) for value in group.varnames()]:
            try:
                expr = str(group.get(name))
            except Exception:
                continue
            if any(key in name.lower() or key in expr.lower() for key in ("vol", "volt", "charge", "3.65", "i/", "cut")):
                selected[name] = expr
        if selected:
            result["variables"][group_tag] = selected

    result["event_values"] = {}
    numerical = model.result().numerical()
    for expr in ("vol", "charge_end", "charge1", "I/i_1C"):
        tag = "__event_value"
        try:
            numerical.remove(tag)
        except Exception:
            pass
        node = numerical.create(tag, "EvalGlobal")
        node.set("data", "dset1")
        node.set("expr", expr)
        values = {}
        for solnum in (355, 356, 357, 358, 359):
            node.set("solnum", str(solnum))
            value = node.getReal()
            while hasattr(value, "__len__") and len(value) == 1:
                value = value[0]
            values[str(solnum)] = float(value)
        result["event_values"][expr] = values
        numerical.remove(tag)
    result["study_time"] = all_properties(model.study("std1").feature("time"))
    result["solver_tree"] = solver_tree(model.sol("sol1"))
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
