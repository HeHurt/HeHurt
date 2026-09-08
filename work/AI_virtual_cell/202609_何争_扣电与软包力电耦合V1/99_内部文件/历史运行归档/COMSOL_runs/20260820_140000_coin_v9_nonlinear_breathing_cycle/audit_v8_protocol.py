import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\audit_v8_protocol.json")
TAG = "coin_v9_protocol_audit"


def tags(manager):
    try:
        return [str(x) for x in manager.tags()]
    except Exception:
        return []


def props(node):
    out = {}
    try:
        names = [str(x) for x in node.properties()]
    except Exception as exc:
        return {"__error__": str(exc)}
    for name in names:
        for getter in ("getString", "getStringArray", "get"):
            try:
                value = getattr(node, getter)(name)
                if hasattr(value, "__iter__") and not isinstance(value, str):
                    value = [str(x) for x in value]
                else:
                    value = str(value)
                out[name] = value
                break
            except Exception:
                continue
    return out


def feature_tree(manager):
    out = {}
    for tag in tags(manager):
        node = manager(tag)
        try:
            node_type = str(node.getType())
        except Exception:
            node_type = ""
        item = {"type": node_type, "label": str(node.label()), "properties": props(node)}
        try:
            children = feature_tree(node.feature())
        except Exception:
            children = {}
        if children:
            item["children"] = children
        out[tag] = item
    return out


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL}
try:
    comp = model.component("comp1")
    payload["parameters"] = {str(k): str(model.param().get(str(k))) for k in model.param().varnames()}
    payload["variables"] = {}
    for tag in tags(comp.variable()):
        node = comp.variable(tag)
        values = {}
        try:
            for name in node.varnames():
                values[str(name)] = str(node.get(str(name)))
        except Exception as exc:
            values["__error__"] = str(exc)
        payload["variables"][tag] = values
    payload["physics"] = {}
    for tag in tags(comp.physics()):
        physics = comp.physics(tag)
        payload["physics"][tag] = {
            "type": str(physics.getType()),
            "label": str(physics.label()),
            "features": feature_tree(physics.feature),
        }
    payload["studies"] = {}
    for tag in tags(model.study()):
        study = model.study(tag)
        payload["studies"][tag] = {
            "label": str(study.label()),
            "features": feature_tree(study.feature),
        }
    payload["functions"] = feature_tree(model.func)
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
