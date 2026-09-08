import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_135033_coin_v4_saved_solution_postprocess\audit.json")
TAG = "coin_v4_saved_solution_audit"


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


def selection(node):
    try:
        return [int(value) for value in node.selection().entities()]
    except Exception:
        return []


def properties(node):
    result = {}
    try:
        names = [str(value) for value in node.properties()]
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


def feature_tree(manager):
    result = {}
    for feature_tag in tags(manager):
        node = manager(feature_tag) if callable(manager) else manager.get(feature_tag)
        item = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "selection": selection(node),
        }
        children = feature_tree(node.feature)
        if children:
            item["children"] = children
        result[feature_tag] = item
    return result


def geometry_counts(geom):
    result = {}
    for name in ("getNPoints", "getNEdges", "getNBoundaries", "getNDomains"):
        try:
            result[name] = int(getattr(geom, name)())
        except Exception as exc:
            result[name + "_error"] = str(exc)
    try:
        result["bounding_box"] = jsonable(geom.getBoundingBox())
    except Exception as exc:
        result["bounding_box_error"] = str(exc)
    return result


def numerical_value(model, kind, expression, entity, solnum=1):
    manager = model.result().numerical()
    tag = "__audit_" + kind + "_" + str(entity) + "_" + str(abs(hash(expression)) % 10000)
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, kind)
        node.selection().set([entity])
        node.set("data", "dset1")
        node.set("solnum", str(solnum))
        node.set("expr", expression)
        value = jsonable(node.getReal())
        while isinstance(value, list) and len(value) == 1:
            value = value[0]
        return float(value)
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


model = ModelUtil.load(TAG, MODEL)
try:
    components = {}
    for component_tag in tags(model.component()):
        comp = model.component(component_tag)
        physics = {}
        for physics_tag in tags(comp.physics()):
            node = comp.physics(physics_tag)
            physics[physics_tag] = {
                "label": str(node.label()),
                "type": str(node.getType()),
                "selection": selection(node),
                "features": feature_tree(node.feature),
            }
        materials = {}
        for material_tag in tags(comp.material()):
            node = comp.material(material_tag)
            materials[material_tag] = {"label": str(node.label()), "selection": selection(node)}
        geometries = {tag: geometry_counts(comp.geom(tag)) for tag in tags(comp.geom())}
        components[component_tag] = {"physics": physics, "materials": materials, "geometries": geometries}

    solutions = {}
    for solution_tag in tags(model.sol()):
        node = model.sol(solution_tag)
        try:
            pvals = [float(value) for value in node.getPVals()]
            solutions[solution_tag] = {
                "count": len(pvals),
                "first": pvals[0],
                "last": pvals[-1],
                "default_solnum": int(node.getDefaultSolnum()),
            }
        except Exception as exc:
            solutions[solution_tag] = {"error": str(exc)}

    datasets = {}
    for dataset_tag in tags(model.result().dataset()):
        node = model.result().dataset(dataset_tag)
        datasets[dataset_tag] = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "properties": properties(node),
        }

    domain_bounds = {}
    boundary_bounds = {}
    if "sol1" in solutions and "error" not in solutions["sol1"]:
        comp = model.component("comp1")
        domain_count = components["comp1"]["geometries"].get("geom1", {}).get("getNDomains", 0)
        boundary_count = components["comp1"]["geometries"].get("geom1", {}).get("getNBoundaries", 0)
        for domain in range(1, domain_count + 1):
            try:
                domain_bounds[str(domain)] = {
                    "r_min": numerical_value(model, "MinSurface", "r", domain),
                    "r_max": numerical_value(model, "MaxSurface", "r", domain),
                    "z_min": numerical_value(model, "MinSurface", "z", domain),
                    "z_max": numerical_value(model, "MaxSurface", "z", domain),
                }
            except Exception as exc:
                domain_bounds[str(domain)] = {"error": str(exc)}
        for boundary in range(1, boundary_count + 1):
            try:
                boundary_bounds[str(boundary)] = {
                    "r_min": numerical_value(model, "MinLine", "r", boundary),
                    "r_max": numerical_value(model, "MaxLine", "r", boundary),
                    "z_min": numerical_value(model, "MinLine", "z", boundary),
                    "z_max": numerical_value(model, "MaxLine", "z", boundary),
                }
            except Exception as exc:
                boundary_bounds[str(boundary)] = {"error": str(exc)}

    payload = {
        "source": MODEL,
        "model_label": str(model.label()),
        "SOC_parameter": str(model.param().get("SOC")),
        "components": components,
        "solutions": solutions,
        "datasets": datasets,
        "domain_bounds": domain_bounds,
        "boundary_bounds": boundary_bounds,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(OUTPUT), "SOC": payload["SOC_parameter"], "solutions": solutions, "components": list(components)}, ensure_ascii=False))
finally:
    ModelUtil.remove(TAG)
