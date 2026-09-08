import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V2.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_112022_coin_v2_voltage_diagnostic\start_voltage_breakdown.json")
TAG = "coin_start_voltage_breakdown"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def properties(node):
    result = {}
    for name in [str(value) for value in node.properties()]:
        for method in ("getStringMatrix", "getStringArray", "getString", "getDouble", "getBoolean"):
            try:
                value = getattr(node, method)(name)
                if value is not None:
                    result[name] = jsonable(value)
                    break
            except Exception:
                continue
    return result


def value(model, kind, expression, selection):
    manager = model.result().numerical()
    tag = "__start_" + kind + "_" + str(selection[0])
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, kind)
        node.selection().set(selection)
        node.set("data", "dset1")
        node.set("solnum", "1")
        node.set("expr", expression)
        result = jsonable(node.getReal())
        while isinstance(result, list) and len(result) == 1:
            result = result[0]
        return float(result)
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


model = ModelUtil.load(TAG, MODEL)
try:
    comp = model.component("comp1")
    liion = comp.physics("liion")
    comp.variable("var1").set("C", "0.5")
    try:
        model.result().table("tbl1").clearTableData()
    except Exception:
        pass
    model.study("std1").feature("time").set("tlist", "range(0,1,1)")
    try:
        model.sol().remove("sol1")
    except Exception:
        pass
    model.study("std1").run()

    feature_data = {}
    for tag in ("cc1", "cc2", "pce1", "pce2", "ecd1", "egnd1"):
        node = liion.feature(tag)
        feature_data[tag] = {
            "label": str(node.label()),
            "selection": [int(entry) for entry in node.selection().entities()],
            "properties": properties(node),
        }

    materials = {}
    for tag in [str(value) for value in comp.material().tags()]:
        material = comp.material(tag)
        try:
            selection = [int(entry) for entry in material.selection().entities()]
        except Exception:
            selection = []
        materials[tag] = {"label": str(material.label()), "selection": selection}

    domains = {}
    for domain in (1, 2, 4, 5):
        domains[str(domain)] = {
            "avg": value(model, "AvSurface", "phis", [domain]),
            "min": value(model, "MinSurface", "phis", [domain]),
            "max": value(model, "MaxSurface", "phis", [domain]),
        }
    boundaries = {
        str(boundary): value(model, "AvLine", "phis", [boundary])
        for boundary in (2, 4, 6, 8, 10, 11)
    }
    payload = {
        "source": MODEL,
        "saved": False,
        "features": feature_data,
        "materials": materials,
        "domain_phis_V": domains,
        "boundary_phis_V": boundaries,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(OUTPUT), "domain_phis_V": domains, "boundary_phis_V": boundaries, "materials": materials}, ensure_ascii=False))
finally:
    ModelUtil.remove(TAG)
