import json
import math
import time as clock
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing.mph"
RUN_SOLVED = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\model_solved_100N.mph"
DELIVERY_SOLVED = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing_solved_100N.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\full_100N_result.json")
TAG = "coin_v8_breathing_full_100n"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def tags(manager):
    return [str(value) for value in manager.tags()]


def solution_of(model, dataset):
    try:
        return str(model.result().dataset(dataset).getString("solution"))
    except Exception:
        return ""


def global_series(model, dataset, expression, unit):
    manager = model.result().numerical()
    tag = "__v8_full_global"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    try:
        return [float(value) for value in node.getReal()[0]]
    finally:
        remove(manager, tag)


def domain_average(model, dataset, expression, unit, domain):
    manager = model.result().numerical()
    tag = "__v8_full_avg"
    remove(manager, tag)
    node = manager.create(tag, "AvSurface")
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().set([domain])
    try:
        return [float(value) for value in node.getReal()[0]]
    finally:
        remove(manager, tag)


def boundary_max(model, dataset, expression, unit, boundary):
    manager = model.result().numerical()
    tag = "__v8_full_max"
    remove(manager, tag)
    node = manager.create(tag, "MaxLine")
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().set([boundary])
    try:
        return [float(value) for value in node.getReal()[0]]
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {
    "source": MODEL,
    "solved_models": [RUN_SOLVED, DELIVERY_SOLVED],
    "case": {"F_ext_N": 100.0, "breathing_on": 1, "eps_sw_neg_full": 0.20, "t_end_s": 7200.0},
}
try:
    model.param().set("F_ext", "100[N]")
    model.param().set("breathing_on", "1")
    model.param().set("eps_sw_neg_full", "0.20")
    step = model.study("std_breath").feature("time")
    step.set("useparam", "off")
    step.set("tlist", "range(0,60,7200)")
    before_solutions = set(tags(model.sol()))
    started = clock.time()
    model.study("std_breath").run()
    payload["solve_elapsed_s"] = clock.time() - started
    new_solutions = [tag for tag in tags(model.sol()) if tag not in before_solutions]
    candidates = []
    probes = {}
    for dataset in tags(model.result().dataset()):
        if solution_of(model, dataset) not in new_solutions:
            continue
        try:
            times = global_series(model, dataset, "t", "s")
            theta = domain_average(model, dataset, "theta_neg_v8", "1", 4)
            probes[dataset] = {"tmax": max(times), "count": len(times), "theta_count": len(theta)}
            candidates.append((dataset, times))
        except Exception as exc:
            probes[dataset] = {"error": str(exc)}
    if not candidates:
        raise RuntimeError(f"No readable transient dataset: {probes}")
    dataset, times = max(candidates, key=lambda item: (max(item[1]), len(item[1])))
    series = {
        "time_s": times,
        "voltage_V": global_series(model, dataset, "vol_loaded", "V"),
        "current_Crate": global_series(model, dataset, "I/i_1C", "1"),
        "theta_neg": domain_average(model, dataset, "theta_neg_v8", "1", 4),
        "theta_pos": domain_average(model, dataset, "theta_pos_v8", "1", 6),
        "eps_breath_neg": domain_average(model, dataset, "eps_breath_neg_v8", "1", 4),
        "eps_breath_pos": domain_average(model, dataset, "eps_breath_pos_v8", "1", 6),
        "p_neg_MPa": domain_average(model, dataset, "p_comp_neg_v8", "MPa", 4),
        "p_sep_MPa": domain_average(model, dataset, "p_comp_sep_v8", "MPa", 5),
        "p_pos_MPa": domain_average(model, dataset, "p_comp_pos_v8", "MPa", 6),
        "epsl_neg": domain_average(model, dataset, "epsl_neg_v8", "1", 4),
        "epsl_sep": domain_average(model, dataset, "epsl_sep_v8", "1", 5),
        "epsl_pos": domain_average(model, dataset, "epsl_pos_v8", "1", 6),
        "top_disp_um": boundary_max(model, dataset, "solid.disp", "um", 20),
    }
    payload["new_solutions"] = new_solutions
    payload["dataset_used"] = dataset
    payload["dataset_probes"] = probes
    payload["initial"] = {name: values[0] for name, values in series.items()}
    payload["final"] = {name: values[-1] for name, values in series.items()}
    payload["extrema"] = {
        name: {"min": min(values), "max": max(values)} for name, values in series.items() if name != "time_s"
    }
    payload["series"] = series
    payload["checks"] = {
        "reached_7200s": max(times) >= 7199.9,
        "all_finite": all(math.isfinite(value) for values in series.values() for value in values),
        "negative_breathing_activated": max(series["eps_breath_neg"]) > 0.05,
        "negative_breathing_below_cap": max(series["eps_breath_neg"]) <= 0.200001,
        "porosity_above_floor": min(series["epsl_neg"] + series["epsl_sep"] + series["epsl_pos"]) >= 0.1499,
    }
    payload["ok"] = all(payload["checks"].values())
    model.save(RUN_SOLVED)
    model.save(DELIVERY_SOLVED)
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
