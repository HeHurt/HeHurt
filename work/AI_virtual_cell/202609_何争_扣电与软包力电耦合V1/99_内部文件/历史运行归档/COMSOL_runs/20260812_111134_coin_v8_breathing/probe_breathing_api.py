import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity_solved.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\breathing_api_probe.json")
TAG = "coin_v8_breathing_probe"
CANDIDATES = [
    "liion.cs_average/liion.csmax", "liion.cs_avg/liion.csmax", "liion.csav/liion.csmax",
    "liion.cs_mean/liion.csmax", "liion.socloc", "liion.soc", "liion.cs_surface/liion.csmax",
]
FEATURE_TYPES = ["ExternalStrain", "InitialStressandStrain", "InitialStressStrain", "InelasticStrain"]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def properties(node):
    result = {}
    for prop in [str(value) for value in node.properties()]:
        for method in ("getStringMatrix", "getStringArray", "getString", "getDouble", "getBoolean"):
            try:
                result[prop] = jsonable(getattr(node, method)(prop))
                break
            except Exception:
                pass
    return result


def evaluate(model, expression, domain, solnum):
    manager = model.result().numerical()
    tag = "__v8_expr_probe"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset5")
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.set("unit", ["1"])
    node.selection().geom("geom1", 2)
    node.selection().set([domain])
    try:
        values = [float(row[0]) for row in node.getReal()]
        return {"min": min(values), "mean": sum(values) / len(values), "max": max(values), "count": len(values)}
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "expressions": {}, "features": {}, "liion_nodes": {}}
try:
    for expression in CANDIDATES:
        payload["expressions"][expression] = {}
        for domain in (4, 6):
            for solnum in (1, 177, 303):
                key = f"d{domain}_s{solnum}"
                try:
                    payload["expressions"][expression][key] = evaluate(model, expression, domain, solnum)
                except Exception as exc:
                    payload["expressions"][expression][key] = {"error": str(exc)}

    liion = model.component("comp1").physics("liion")
    for tag in ("socicd1", "pce1", "pce2", "init1", "init2", "init3", "init4"):
        try:
            payload["liion_nodes"][tag] = properties(liion.feature(tag))
        except Exception as exc:
            payload["liion_nodes"][tag] = {"error": str(exc)}

    parent = model.component("comp1").physics("solid").feature("lemm1")
    for index, feature_type in enumerate(FEATURE_TYPES):
        tag = f"__v8_probe_{index}"
        remove(parent.feature(), tag)
        try:
            parent.feature().create(tag, feature_type, 2)
            node = parent.feature(tag)
            payload["features"][feature_type] = {
                "created": True, "type": str(node.getType()), "properties": properties(node)
            }
        except Exception as exc:
            payload["features"][feature_type] = {"created": False, "error": str(exc)}
        finally:
            remove(parent.feature(), tag)
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
