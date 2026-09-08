import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\smoke_mechanics_result.json")
TAG = "coin_v6_mechanics_smoke"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def flatten(values):
    result = []
    for row in values:
        try:
            result.extend(float(value) for value in row)
        except TypeError:
            result.append(float(row))
    return result


def field_range(model, data, tag, expr, domains, unit):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", data)
    node.set("expr", [expr])
    node.set("unit", [unit])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    values = flatten(node.getReal())
    remove(manager, tag)
    return {"min": min(values), "max": max(values)}


def boundary_average(model, data, tag, expr, boundaries, unit):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "AvLine")
    node.set("data", data)
    node.set("expr", expr)
    node.set("unit", unit)
    node.selection().set(boundaries)
    value = node.getReal()
    while hasattr(value, "__len__") and len(value) == 1:
        value = value[0]
    remove(manager, tag)
    return float(value)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "F_ext_N": 250.0}
try:
    model.param().set("F_ext", "250[N]")
    model.study("std_mech").feature("stat").set("useparam", "off")
    model.study("std_mech").run()
    dataset_tags = [str(value) for value in model.result().dataset().tags()]
    payload["datasets"] = dataset_tags
    payload["dataset_info"] = {}
    for dataset_tag in dataset_tags:
        dataset = model.result().dataset(dataset_tag)
        item = {"label": str(dataset.label()), "type": str(dataset.getType())}
        for prop in ("solution", "data", "revdata"):
            try:
                item[prop] = str(dataset.getString(prop))
            except Exception:
                pass
        payload["dataset_info"][dataset_tag] = item
    data = dataset_tags[-1]
    payload["dataset_used"] = data
    payload["pressure_MPa"] = 250.0 / (3.141592653589793 * (12.205e-3) ** 2) / 1e6
    payload["von_mises_Pa"] = field_range(model, data, "__mises", "solid.mises", list(range(1, 12)), "Pa")
    payload["displacement_m"] = field_range(model, data, "__disp", "solid.disp", list(range(1, 12)), "m")
    payload["top_displacement_m"] = boundary_average(model, data, "__top_disp", "solid.disp", [20], "m")
    payload["separator_axial_strain"] = field_range(model, data, "__sep_ezz", "solid.eZZ", [5], "1")
    payload["stack_displacement_m"] = field_range(model, data, "__stack_disp", "solid.disp", [3, 4, 5, 6, 7], "m")
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
