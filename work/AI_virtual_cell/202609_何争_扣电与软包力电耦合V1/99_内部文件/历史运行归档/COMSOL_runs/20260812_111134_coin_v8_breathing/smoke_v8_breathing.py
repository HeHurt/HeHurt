import json
import math
import time as clock
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\smoke_result.json")
SOLVED_MODEL = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\model_smoke_solved.mph"
TAG = "coin_v8_breathing_smoke"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def tags(manager):
    return [str(value) for value in manager.tags()]


def dataset_solution(dataset):
    try:
        return str(dataset.getString("solution"))
    except Exception:
        return ""


def global_series(model, dataset, expression, unit):
    manager = model.result().numerical()
    tag = "__v8_smoke_global"
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
    tag = "__v8_smoke_avg"
    remove(manager, tag)
    node = manager.create(tag, "AvSurface")
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().set([domain])
    try:
        values = node.getReal()
        return [float(value) for value in values[0]]
    finally:
        remove(manager, tag)


def boundary_max(model, dataset, expression, unit, boundary):
    manager = model.result().numerical()
    tag = "__v8_smoke_max"
    remove(manager, tag)
    node = manager.create(tag, "MaxLine")
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().set([boundary])
    try:
        values = node.getReal()
        return [float(value) for value in values[0]]
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {
    "source": MODEL,
    "case": {"F_ext_N": 100.0, "breathing_on": 1, "eps_sw_neg_full": 0.20, "t_end_s": 200.0},
}
try:
    model.param().set("F_ext", "100[N]")
    model.param().set("breathing_on", "1")
    model.param().set("eps_sw_neg_full", "0.20")
    step = model.study("std_breath").feature("time")
    step.set("useparam", "off")
    step.set("tlist", "range(0,20,200)")
    before_solutions = set(tags(model.sol()))
    before_datasets = set(tags(model.result().dataset()))
    started = clock.time()
    model.study("std_breath").run()
    payload["solve_elapsed_s"] = clock.time() - started
    after_solutions = tags(model.sol())
    after_datasets = tags(model.result().dataset())
    new_solutions = [tag for tag in after_solutions if tag not in before_solutions]
    new_datasets = [tag for tag in after_datasets if tag not in before_datasets]
    payload["solutions"] = {"new": new_solutions}
    payload["datasets"] = {
        "new": new_datasets,
        "solution_map": {tag: dataset_solution(model.result().dataset(tag)) for tag in after_datasets},
    }
    candidates = []
    probes = {}
    solution_map = payload["datasets"]["solution_map"]
    solution_datasets = [
        dataset for dataset in after_datasets if solution_map.get(dataset) in new_solutions
    ]
    for dataset in solution_datasets:
        try:
            times = global_series(model, dataset, "t", "s")
            theta_probe = domain_average(model, dataset, "theta_neg_v8", "1", 4)
            probes[dataset] = {"times": times, "theta_count": len(theta_probe)}
            if times:
                candidates.append((dataset, times))
        except Exception as exc:
            probes[dataset] = {"error": str(exc)}
    if not candidates:
        raise RuntimeError(f"No new transient dataset found: {probes}")
    dataset, times = max(candidates, key=lambda item: (max(item[1]), len(item[1])))
    payload["dataset_used"] = dataset
    payload["times_s"] = times
    series = {
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
    payload["initial"] = {name: values[0] for name, values in series.items()}
    payload["final"] = {name: values[-1] for name, values in series.items()}
    payload["series"] = series
    checks = {
        "reached_200s": max(times) >= 199.9,
        "all_finite": all(math.isfinite(value) for values in series.values() for value in values),
        "negative_lithiation_increases": series["theta_neg"][-1] > series["theta_neg"][0],
        "negative_breathing_increases": series["eps_breath_neg"][-1] > series["eps_breath_neg"][0],
        "positive_breathing_increases": series["eps_breath_pos"][-1] >= series["eps_breath_pos"][0],
    }
    payload["checks"] = checks
    payload["ok"] = all(checks.values())
    model.save(SOLVED_MODEL)
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
