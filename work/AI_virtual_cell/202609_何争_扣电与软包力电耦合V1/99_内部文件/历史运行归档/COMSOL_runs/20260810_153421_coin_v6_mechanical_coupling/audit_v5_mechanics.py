import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_final.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\audit_v5_mechanics.json")
TAG = "coin_v5_mechanics_audit"


def strings(values):
    try:
        return [str(value) for value in values]
    except Exception:
        return []


def entities(selection, dim):
    try:
        return [int(value) for value in selection.entities(dim)]
    except Exception:
        try:
            return [int(value) for value in selection.entities()]
        except Exception:
            return []


def selection_info(node):
    result = {}
    try:
        result["named"] = str(node.selection().named())
    except Exception:
        pass
    for dim in (2, 1, 0):
        found = entities(node.selection(), dim)
        if found:
            result[f"entities_dim_{dim}"] = found
    return result


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL}
try:
    comp = model.component("comp1")
    geom = comp.geom("geom1")
    payload["geometry"] = {
        "dimension": int(geom.getSDim()),
        "features": [],
    }
    for feature_tag in strings(geom.feature().tags()):
        node = geom.feature(feature_tag)
        payload["geometry"]["features"].append({
            "tag": feature_tag,
            "label": str(node.label()),
            "type": str(node.getType()),
        })

    payload["physics"] = []
    for physics_tag in strings(comp.physics().tags()):
        physics = comp.physics(physics_tag)
        entry = {
            "tag": physics_tag,
            "label": str(physics.label()),
            "type": str(physics.getType()),
            "selection": selection_info(physics),
            "features": [],
        }
        for feature_tag in strings(physics.feature().tags()):
            feature = physics.feature(feature_tag)
            entry["features"].append({
                "tag": feature_tag,
                "label": str(feature.label()),
                "type": str(feature.getType()),
                "selection": selection_info(feature),
            })
        payload["physics"].append(entry)

    payload["materials"] = []
    for material_tag in strings(comp.material().tags()):
        material = comp.material(material_tag)
        payload["materials"].append({
            "tag": material_tag,
            "label": str(material.label()),
            "type": str(material.getType()),
            "selection": selection_info(material),
        })

    payload["selections"] = []
    for selection_tag in strings(comp.selection().tags()):
        selection = comp.selection(selection_tag)
        item = {
            "tag": selection_tag,
            "label": str(selection.label()),
            "type": str(selection.getType()),
        }
        for dim in (2, 1, 0):
            found = entities(selection, dim)
            if found:
                item[f"entities_dim_{dim}"] = found
        payload["selections"].append(item)

    payload["parameters"] = {}
    for name in strings(model.param().varnames()):
        lowered = name.lower()
        if any(key in lowered for key in ("por", "eps", "contact", "res", "thick", "diam", "radius", "force", "press")):
            try:
                payload["parameters"][name] = str(model.param().get(name))
            except Exception:
                pass
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
