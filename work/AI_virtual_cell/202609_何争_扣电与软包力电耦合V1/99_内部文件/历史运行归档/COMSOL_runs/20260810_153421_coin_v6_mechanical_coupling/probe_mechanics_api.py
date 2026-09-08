import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_final.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\mechanics_api_probe.json")
TAG = "coin_v5_mechanics_probe"


def strings(values):
    try:
        return [str(value) for value in values]
    except Exception:
        return []


def read_property(node, prop):
    for method in ("getString", "getStringArray", "getStringMatrix", "getDouble", "getBoolean"):
        try:
            value = getattr(node, method)(prop)
            if isinstance(value, (str, int, float, bool)):
                return value
            try:
                return [str(item) for item in value]
            except TypeError:
                return str(value)
        except Exception:
            continue
    return None


def properties(node):
    return {prop: read_property(node, prop) for prop in strings(node.properties())}


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL}
try:
    comp = model.component("comp1")
    payload["parameters"] = {
        name: str(model.param().get(name))
        for name in strings(model.param().varnames())
    }
    payload["variables"] = {}
    for group_tag in strings(comp.variable().tags()):
        group = comp.variable(group_tag)
        payload["variables"][group_tag] = {
            name: str(group.get(name))
            for name in strings(group.varnames())
        }
    liion = comp.physics("liion")
    payload["electrochem_features"] = {
        tag: properties(liion.feature(tag))
        for tag in ("pce1", "sep1", "pce2", "cc1", "ecd1")
    }
    ecd = liion.feature("ecd1")
    ecd.set("IncludeContactResistance", "1")
    payload["electrode_current_with_contact"] = properties(ecd)
    ecd.set("IncludeContactResistance", "0")

    comp.physics().create("solid", "SolidMechanics", "geom1")
    solid = comp.physics("solid")
    solid.feature().create("fix_probe", "Fixed", 1)
    solid.feature("fix_probe").selection().set([2])
    solid.feature().create("load_probe", "BoundaryLoad", 1)
    solid.feature("load_probe").selection().set([20])
    solid.feature("load_probe").set("forceType", "FollowerPressure")
    solid.feature("load_probe").set("pressure", "1[MPa]")
    payload["solid_created"] = {
        "type": str(solid.getType()),
        "features": {},
    }
    for feature_tag in strings(solid.feature().tags()):
        feature = solid.feature(feature_tag)
        payload["solid_created"]["features"][feature_tag] = {
            "label": str(feature.label()),
            "type": str(feature.getType()),
            "properties": properties(feature),
        }
    comp.physics().remove("solid")
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
