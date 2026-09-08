import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V9_nonlinear_breathing_cycle_solved_100N.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\verify_saved_result.json")
TAG = "coin_v9_saved_verify"


def tags(manager):
    return [str(x) for x in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def series(model, dataset, expr, unit):
    manager = model.result().numerical()
    tag = "__v9_verify"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("expr", [expr])
    node.set("unit", [unit])
    try:
        return [float(x) for x in node.getReal()[0]]
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "datasets": {}, "checks": {}}
try:
    best = None
    for dataset in tags(model.result().dataset()):
        try:
            times = series(model, dataset, "t", "s")
            payload["datasets"][dataset] = {"count": len(times), "tmax": max(times)}
            if best is None or (max(times), len(times)) > (max(best[1]), len(best[1])):
                best = (dataset, times)
        except Exception as exc:
            payload["datasets"][dataset] = {"error": str(exc)}
    if best is None:
        raise RuntimeError("No saved transient dataset")
    dataset, times = best
    current = series(model, dataset, "I/i_1C", "1")
    voltage = series(model, dataset, "vol_loaded", "V")
    payload["dataset_used"] = dataset
    payload["summary"] = {
        "tmax_s": max(times),
        "current_min_C": min(current),
        "current_max_C": max(current),
        "current_final_C": current[-1],
        "minimum_discharge_voltage_V": min(v for v, c in zip(voltage, current) if c < -0.1),
        "maximum_charge_voltage_V": max(v for v, c in zip(voltage, current) if c > 0.1),
        "study_tlist": str(model.study("std_v9").feature("time").getString("tlist")),
        "breathing_mode": str(model.param().get("breathing_mode")),
    }
    payload["checks"] = {
        "reached_18000s": max(times) >= 17999.9,
        "contains_charge": max(current) > 0.49,
        "contains_discharge": min(current) < -0.49,
        "ends_at_rest": abs(current[-1]) < 0.01,
        "reaches_lower_cutoff": payload["summary"]["minimum_discharge_voltage_V"] <= 2.51,
        "reaches_upper_cutoff": payload["summary"]["maximum_charge_voltage_V"] >= 3.64,
        "nonlinear_mode_saved": payload["summary"]["breathing_mode"] == "2",
    }
    payload["ok"] = all(payload["checks"].values())
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload["ok"], "summary": payload["summary"], "output": str(OUTPUT)}, ensure_ascii=False))
