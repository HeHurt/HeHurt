import json
import math
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_090000_coin_v7_local_porosity\smoke_result.json")
TAG = "coin_v7_local_porosity_smoke"
REGIONS = {
    "negative": {"domain": [4], "pressure": "p_comp_neg_v7", "porosity": "epsl_neg_v7", "uniform": "epsl_neg_mech"},
    "separator": {"domain": [5], "pressure": "p_comp_sep_v7", "porosity": "epsl_sep_v7", "uniform": "epsl_sep_mech"},
    "positive": {"domain": [6], "pressure": "p_comp_pos_v7", "porosity": "epsl_pos_v7", "uniform": "epsl_pos_mech"},
}


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


def field(model, dataset, solnum, expression, unit, domains):
    manager = model.result().numerical()
    tag = "__v7_smoke_field"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", dataset)
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    try:
        return [float(row[0]) for row in node.getReal()]
    finally:
        remove(manager, tag)


def scalar(model, dataset, solnum, expression, unit):
    manager = model.result().numerical()
    tag = "__v7_smoke_global"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.set("unit", [unit])
    try:
        values = node.getReal()
        return float(values[0][0])
    finally:
        remove(manager, tag)


def series(model, dataset, expression, unit):
    manager = model.result().numerical()
    tag = "__v7_smoke_series"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    try:
        return [float(value) for value in node.getReal()[0]]
    finally:
        remove(manager, tag)


def summarize(values):
    mean = sum(values) / len(values)
    return {"min": min(values), "mean": mean, "max": max(values), "span": max(values) - min(values), "count": len(values)}


def correlation(x, y):
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    cov = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - x_mean) ** 2 for a in x))
    sy = math.sqrt(sum((b - y_mean) ** 2 for b in y))
    return cov / (sx * sy) if sx and sy else None


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "case": {"F_ext_N": 100.0, "local_porosity_on": 1, "t_end_s": 200.0}}
try:
    model.param().set("F_ext", "100[N]")
    model.param().set("local_porosity_on", "1")
    study = model.study("std_local")
    time = study.feature("time")
    time.set("useparam", "off")
    time.set("tlist", "range(0,20,200)")
    before_solutions = set(tags(model.sol()))
    before_datasets = set(tags(model.result().dataset()))
    study.run()
    after_solutions = tags(model.sol())
    after_datasets = tags(model.result().dataset())
    new_solutions = [tag for tag in after_solutions if tag not in before_solutions]
    new_datasets = [tag for tag in after_datasets if tag not in before_datasets]
    payload["solutions"] = {"before": sorted(before_solutions), "after": after_solutions, "new": new_solutions}
    payload["datasets"] = {
        "before": sorted(before_datasets),
        "after": after_datasets,
        "new": new_datasets,
        "solution_map": {tag: dataset_solution(model.result().dataset(tag)) for tag in after_datasets},
    }
    time_probes = {}
    for candidate in new_datasets:
        try:
            candidate_times = series(model, candidate, "t", "s")
            time_probes[candidate] = candidate_times
        except Exception as exc:
            time_probes[candidate] = {"error": str(exc)}
    valid_time_datasets = [(tag, values) for tag, values in time_probes.items() if isinstance(values, list) and values]
    if not valid_time_datasets:
        raise RuntimeError(f"No new dataset exposes the transient time axis: {time_probes}")
    dataset, times = max(valid_time_datasets, key=lambda item: (max(item[1]), len(item[1])))
    payload["dataset_used"] = dataset
    payload["time_probes"] = time_probes
    final_solnum = len(times)
    payload["final_solnum"] = final_solnum
    payload["times_s"] = times
    payload["voltage"] = {
        "cell_V": scalar(model, dataset, final_solnum, "vol", "V"),
        "loaded_V": scalar(model, dataset, final_solnum, "vol_loaded", "V"),
        "current_Crate": scalar(model, dataset, final_solnum, "I/i_1C", "1"),
    }
    payload["regions"] = {}
    for name, item in REGIONS.items():
        pressure = field(model, dataset, final_solnum, item["pressure"], "MPa", item["domain"])
        porosity = field(model, dataset, final_solnum, item["porosity"], "1", item["domain"])
        uniform = field(model, dataset, final_solnum, item["uniform"], "1", item["domain"])
        payload["regions"][name] = {
            "pressure_MPa": summarize(pressure),
            "local_porosity": summarize(porosity),
            "uniform_porosity": summarize(uniform),
            "pressure_porosity_correlation": correlation(pressure, porosity),
        }
    checks = {
        "finite_voltage": all(math.isfinite(value) for value in payload["voltage"].values()),
        "spatial_porosity_variation": all(item["local_porosity"]["span"] > 1e-6 for item in payload["regions"].values()),
        "higher_pressure_lower_porosity": all((item["pressure_porosity_correlation"] or 0) < -0.95 for item in payload["regions"].values()),
        "porosity_in_bounds": all(0.1499 <= item["local_porosity"]["min"] and item["local_porosity"]["max"] <= 0.5001 for item in payload["regions"].values()),
    }
    payload["checks"] = checks
    payload["ok"] = all(checks.values())
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
