import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\smoke_electrochem_result.json")
TAG = "coin_v6_electrochem_smoke"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def global_value(model, tag, expr, unit, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", expr)
    node.set("unit", unit)
    value = node.getReal()
    while hasattr(value, "__len__") and len(value) == 1:
        value = value[0]
    remove(manager, tag)
    return float(value)


def field_range(model, tag, expr, unit, domains, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.set("unit", [unit])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    rows = node.getReal()
    values = []
    for row in rows:
        try:
            values.extend(float(value) for value in row)
        except TypeError:
            values.append(float(row))
    remove(manager, tag)
    return {"min": min(values), "max": max(values)}


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "cases": []}
try:
    time_feature = model.study("std1").feature("time")
    payload["original_tlist"] = str(time_feature.getString("tlist"))
    time_feature.set("tlist", "range(0,20,200)")
    time_feature.set("useparam", "off")
    for index, force_N in enumerate((0.0, 500.0)):
        model.param().set("F_ext", f"{force_N}[N]")
        model.study("std1").run()
        times = [float(value) for value in model.sol("sol1").getPVals()]
        final_solnum = len(times)
        case = {
            "F_ext_N": force_N,
            "time_final_s": times[-1],
            "solution_points": final_solnum,
            "pressure_MPa": global_value(model, f"__p_{index}", "p_ext", "MPa", final_solnum),
            "epsl_neg": global_value(model, f"__en_{index}", "epsl_neg_mech", "1", final_solnum),
            "epsl_sep": global_value(model, f"__es_{index}", "epsl_sep_mech", "1", final_solnum),
            "epsl_pos": global_value(model, f"__ep_{index}", "epsl_pos_mech", "1", final_solnum),
            "R_contact_mohm": global_value(model, f"__rc_{index}", "R_contact_eff", "mohm", final_solnum),
            "vol_V": global_value(model, f"__v_{index}", "vol", "V", final_solnum),
            "vol_loaded_V": global_value(model, f"__vl_{index}", "vol_loaded", "V", final_solnum),
            "electrolyte_concentration_mol_m3": field_range(model, f"__cl_{index}", "cl", "mol/m^3", [4, 5, 6], final_solnum),
        }
        payload["cases"].append(case)
    payload["delta_500N_minus_0N"] = {
        "vol_V": payload["cases"][1]["vol_V"] - payload["cases"][0]["vol_V"],
        "vol_loaded_V": payload["cases"][1]["vol_loaded_V"] - payload["cases"][0]["vol_loaded_V"],
    }
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
