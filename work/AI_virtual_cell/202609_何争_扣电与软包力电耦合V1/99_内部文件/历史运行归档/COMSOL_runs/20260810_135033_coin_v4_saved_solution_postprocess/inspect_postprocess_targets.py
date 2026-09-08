import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_135033_coin_v4_saved_solution_postprocess\targets.json")
TAG = "coin_v4_postprocess_targets"
SHELL_DOMAINS = [1, 2, 8, 9, 10]


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


def properties(node):
    result = {}
    try:
        names = [str(value) for value in node.properties()]
    except Exception:
        names = []
    for name in names:
        if name not in {"expr", "descr", "unit", "data", "solnum", "title", "titletype", "exprunit", "expression"}:
            continue
        for method in ("getStringMatrix", "getStringArray", "getString", "getDouble", "getBoolean"):
            try:
                value = getattr(node, method)(name)
                if value is not None:
                    result[name] = jsonable(value)
                    break
            except Exception:
                continue
    return result


def feature_tree(node):
    result = {}
    try:
        manager = node.feature()
    except Exception:
        return result
    for feature_tag in tags(manager):
        child = node.feature(feature_tag)
        try:
            selected = [int(value) for value in child.selection().entities()]
        except Exception:
            selected = []
        item = {
            "label": str(child.label()),
            "type": str(child.getType()),
            "selection": selected,
            "properties": properties(child),
        }
        grandchildren = feature_tree(child)
        if grandchildren:
            item["children"] = grandchildren
        result[feature_tag] = item
    return result


def scalar_series(model, kind, expression, count, selection=None):
    manager = model.result().numerical()
    tag = "__target_" + kind + "_" + str(abs(hash(expression)) % 100000)
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, kind)
        if selection is not None:
            node.selection().set(selection)
        node.set("data", "dset1")
        node.set("expr", expression)
        values = []
        for solnum in range(1, count + 1):
            node.set("solnum", str(solnum))
            value = jsonable(node.getReal())
            while isinstance(value, list) and len(value) == 1:
                value = value[0]
            values.append(float(value))
        return values
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


model = ModelUtil.load(TAG, MODEL)
try:
    physics = {}
    comp = model.component("comp1")
    for physics_tag in tags(comp.physics()):
        node = comp.physics(physics_tag)
        physics[physics_tag] = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "features": feature_tree(node),
        }

    plots = {}
    for plot_tag in tags(model.result()):
        node = model.result(plot_tag)
        try:
            node_type = str(node.getType())
        except Exception:
            continue
        plots[plot_tag] = {
            "label": str(node.label()),
            "type": node_type,
            "properties": properties(node),
            "features": feature_tree(node),
        }

    sol = model.sol("sol1")
    times = [float(value) for value in sol.getPVals()]
    count = len(times)
    global_series = {
        "terminal_voltage_V": scalar_series(model, "AvLine", "phis", count, [15]),
        "current_A": scalar_series(model, "EvalGlobal", "I", count),
        "current_Crate": scalar_series(model, "EvalGlobal", "I/i_1C", count),
        "charge1": scalar_series(model, "EvalGlobal", "charge1", count),
        "charge_hold": scalar_series(model, "EvalGlobal", "charge_hold", count),
        "positive_surface_stoich_avg": scalar_series(model, "AvSurface", "liion.cs_surface/liion.csmax", count, [6]),
        "negative_surface_stoich_avg": scalar_series(model, "AvSurface", "liion.cs_surface/liion.csmax", count, [4]),
    }

    current_density_candidates = {}
    candidates = [
        "liion.normIs",
        "liion.normJ",
        "liion.normJs",
        "sqrt(liion.Isr^2+liion.Isz^2)",
        "sqrt(liion.Isx^2+liion.Isy^2)",
        "sqrt(liion.Jsr^2+liion.Jsz^2)",
        "sqrt(liion.Jx^2+liion.Jy^2)",
        "liion.Isz",
        "liion.Jz",
    ]
    mid = max(1, count // 2)
    for expression in candidates:
        try:
            current_density_candidates[expression] = {
                "ok": True,
                "max_at_mid": scalar_series(model, "MaxSurface", expression, mid, SHELL_DOMAINS)[-1],
            }
        except Exception as exc:
            current_density_candidates[expression] = {"ok": False, "error": str(exc)}

    payload = {
        "source": MODEL,
        "times_s": times,
        "physics": physics,
        "plots": plots,
        "global_series": global_series,
        "current_density_candidates": current_density_candidates,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ok_candidates = {key: value for key, value in current_density_candidates.items() if value.get("ok")}
    print(json.dumps({"ok": True, "output": str(OUTPUT), "valid_current_density": ok_candidates}, ensure_ascii=False))
finally:
    ModelUtil.remove(TAG)
