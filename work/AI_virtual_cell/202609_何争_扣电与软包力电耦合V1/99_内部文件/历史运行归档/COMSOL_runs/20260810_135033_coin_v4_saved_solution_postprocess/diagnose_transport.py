import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_135033_coin_v4_saved_solution_postprocess\transport_diagnosis.json")
TAG = "coin_v4_transport_diagnosis"
STAGES = [("SOC01", 1), ("SOC50", 177), ("SOC70", 249), ("cutoff_SOC89", 319)]


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


def selected_properties(node):
    result = {}
    keywords = ("sigma", "cond", "brug", "eps", "por", "diff", "ds", "dl", "radius", "rp", "kappa", "trans", "electro")
    for prop in [str(value) for value in node.properties()]:
        if not any(key in prop.lower() for key in keywords):
            continue
        for method in ("getString", "getStringArray", "getStringMatrix", "getDouble", "getBoolean"):
            try:
                value = getattr(node, method)(prop)
                result[prop] = jsonable(value)
                break
            except Exception:
                continue
    return result


def field_range(model, tag, expr, domains, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    values = [float(row[0]) for row in node.getReal()]
    remove(manager, tag)
    return {"min": min(values), "max": max(values), "span": max(values) - min(values)}


model = ModelUtil.load(TAG, MODEL)
result = {"source": MODEL, "parameters": {}, "parameter_values": {}, "features": {}, "materials": {}, "fields": {}}
try:
    liion = model.component("comp1").physics("liion")
    nodes = {
        "separator": liion.feature("sep1"),
        "negative_electrode": liion.feature("pce1"),
        "negative_particle": liion.feature("pce1").feature("pin1"),
        "negative_reaction": liion.feature("pce1").feature("per1"),
        "positive_electrode": liion.feature("pce2"),
        "positive_particle": liion.feature("pce2").feature("pin1"),
        "positive_reaction": liion.feature("pce2").feature("per1"),
    }
    for name, node in nodes.items():
        result["features"][name] = selected_properties(node)

    for name in [str(value) for value in model.param().varnames()]:
        if any(key in name.lower() for key in ("epsl", "epss", "brug", "sigma", "diff", "dl", "tplus", "electro")):
            try:
                result["parameters"][name] = str(model.param().get(name))
            except Exception:
                pass
    for name in ("epsl_neg", "epsl_sep", "epsl_pos", "epss_neg", "epss_pos", "sigma_neg", "sigma_pos"):
        try:
            result["parameter_values"][name] = float(model.param().evaluate(name))
        except Exception as exc:
            result["parameter_values"][name] = {"error": str(exc)}

    materials = model.component("comp1").material()
    for material_tag in [str(value) for value in materials.tags()]:
        material = model.component("comp1").material(material_tag)
        item = {"label": str(material.label()), "groups": {}}
        groups = material.propertyGroup()
        for group_tag in [str(value) for value in groups.tags()]:
            group = material.propertyGroup(group_tag)
            props = {}
            for prop in [str(value) for value in group.properties()]:
                if not any(key in prop.lower() for key in ("sigma", "cond", "diff", "dl", "electro", "trans")):
                    continue
                for method in ("getString", "getStringArray", "getStringMatrix"):
                    try:
                        props[prop] = jsonable(getattr(group, method)(prop))
                        break
                    except Exception:
                        continue
            if props:
                item["groups"][group_tag] = props
        if item["groups"]:
            result["materials"][material_tag] = item

    for stage, solnum in STAGES:
        result["fields"][stage] = {}
        for domain_name, domains in {"negative": [4], "separator": [5], "positive": [6]}.items():
            item = {}
            for expr in ("cl", "phil"):
                try:
                    item[expr] = field_range(model, "__field", expr, domains, solnum)
                except Exception as exc:
                    item[expr] = {"error": str(exc)}
            if domain_name != "separator":
                item["phis"] = field_range(model, "__field", "phis", domains, solnum)
            result["fields"][stage][domain_name] = item
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT), "fields": result["fields"]}, ensure_ascii=False))
