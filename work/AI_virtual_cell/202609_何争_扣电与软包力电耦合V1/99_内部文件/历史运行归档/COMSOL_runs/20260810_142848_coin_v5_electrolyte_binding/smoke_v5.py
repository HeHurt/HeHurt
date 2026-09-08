import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding\smoke_result.json")
TAG = "coin_v5_smoke"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


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
    return {"min": min(values), "max": max(values)}


def boundary_average(model, tag, expr, boundary, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "AvLine")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", expr)
    node.selection().set([boundary])
    value = node.getReal()
    while hasattr(value, "__len__") and len(value) == 1:
        value = value[0]
    remove(manager, tag)
    return float(value)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL}
try:
    time_feature = model.study("std1").feature("time")
    payload["original_tlist"] = str(time_feature.getString("tlist"))
    time_feature.set("tlist", "range(0,20,200)")
    model.study("std1").run()
    times = [float(value) for value in model.sol("sol1").getPVals()]
    final_solnum = len(times)
    payload.update({
        "ok": True,
        "times_s": times,
        "terminal_voltage_V": boundary_average(model, "__voltage", "phis", 20, final_solnum),
        "electrolyte_concentration_mol_m3": field_range(model, "__field", "cl", [4, 5, 6], final_solnum),
        "negative_surface_stoichiometry": field_range(model, "__field", "liion.cs_surface/liion.csmax", [4], final_solnum),
        "positive_surface_stoichiometry": field_range(model, "__field", "liion.cs_surface/liion.csmax", [6], final_solnum),
    })
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
