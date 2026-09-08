import json
import math
import time as clock
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V9_nonlinear_breathing_cycle.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\smoke_result.json")
TAG = "coin_v9_smoke"


def tags(manager):
    return [str(x) for x in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def solution_of(model, dataset):
    try:
        return str(model.result().dataset(dataset).getString("solution"))
    except Exception:
        return ""


def global_series(model, dataset, expr, unit):
    manager = model.result().numerical()
    tag = "__v9_smoke_global"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("expr", [expr])
    node.set("unit", [unit])
    try:
        return [float(x) for x in node.getReal()[0]]
    finally:
        remove(manager, tag)


def domain_average(model, dataset, expr, unit, domain):
    manager = model.result().numerical()
    tag = "__v9_smoke_avg"
    remove(manager, tag)
    node = manager.create(tag, "AvSurface")
    node.set("data", dataset)
    node.set("expr", [expr])
    node.set("unit", [unit])
    node.selection().set([domain])
    try:
        return [float(x) for x in node.getReal()[0]]
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "case": {"F_ext_N": 100, "breathing_mode": 2, "t_end_s": 240}}
try:
    model.param().set("F_ext", "100[N]")
    model.param().set("breathing_mode", "2")
    step = model.study("std_v9").feature("time")
    step.set("tlist", "range(0,20,240)")
    step.set("useparam", "off")
    before = set(tags(model.sol()))
    start = clock.time()
    model.study("std_v9").run()
    payload["solve_elapsed_s"] = clock.time() - start
    new_solutions = [x for x in tags(model.sol()) if x not in before]
    candidates = []
    for dataset in tags(model.result().dataset()):
        if solution_of(model, dataset) not in new_solutions:
            continue
        try:
            times = global_series(model, dataset, "t", "s")
            candidates.append((dataset, times))
        except Exception:
            continue
    if not candidates:
        raise RuntimeError(f"No readable transient dataset for solutions {new_solutions}")
    dataset, times = max(candidates, key=lambda item: (max(item[1]), len(item[1])))
    series = {
        "time_s": times,
        "voltage_V": global_series(model, dataset, "vol_loaded", "V"),
        "current_Crate": global_series(model, dataset, "I/i_1C", "1"),
        "theta_neg": domain_average(model, dataset, "theta_neg_v8", "1", 4),
        "eps_breath_neg": domain_average(model, dataset, "eps_breath_neg_v8", "1", 4),
        "eps_breath_pos": domain_average(model, dataset, "eps_breath_pos_v8", "1", 6),
    }
    payload.update({"dataset": dataset, "new_solutions": new_solutions, "series": series})
    payload["checks"] = {
        "reached_end": max(times) >= 239.9,
        "finite": all(math.isfinite(x) for values in series.values() for x in values),
        "charging": max(series["current_Crate"]) > 0.49,
        "graphite_expands": series["eps_breath_neg"][-1] > series["eps_breath_neg"][0],
        "lfp_contracts": series["eps_breath_pos"][-1] < series["eps_breath_pos"][0],
    }
    payload["ok"] = all(payload["checks"].values())
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
