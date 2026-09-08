import json
import time
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
RUN_MODEL = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_102725_coin_v7_local_porosity_full_sweep\model_snapshot_solved.mph"
DELIVERY_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity_solved.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_102725_coin_v7_local_porosity_full_sweep\solve_result.json")
TAG = "coin_v7_full_sweep"


def tags(manager):
    return [str(value) for value in manager.tags()]


def dataset_solution(dataset):
    try:
        return str(dataset.getString("solution"))
    except Exception:
        return ""


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def global_values(model, dataset, expressions):
    manager = model.result().numerical()
    tag = "__v7_solve_verify"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("expr", [expr for expr, _ in expressions])
    node.set("unit", [unit for _, unit in expressions])
    try:
        return [[float(value) for value in row] for row in node.getReal()]
    finally:
        remove(manager, tag)


for target in (RUN_MODEL, DELIVERY_MODEL):
    if Path(target).resolve() == Path(SOURCE).resolve():
        raise RuntimeError("Refusing to overwrite the V7 baseline model")

started = time.time()
model = ModelUtil.load(TAG, SOURCE)
payload = {
    "source": SOURCE,
    "run_model": RUN_MODEL,
    "delivery_model": DELIVERY_MODEL,
    "study": "std_local",
    "forces_N": [0, 100, 250, 500],
    "tlist": "range(0,20,7200)",
}
try:
    model.param().set("local_porosity_on", "1")
    step = model.study("std_local").feature("time")
    step.set("tlist", "range(0,20,7200)")
    step.set("useparam", "on")
    step.set("pname", ["F_ext"])
    step.set("plistarr", ["0 100 250 500"])
    step.set("punit", ["N"])
    before_solutions = set(tags(model.sol()))
    before_datasets = set(tags(model.result().dataset()))
    model.study("std_local").run()
    after_solutions = tags(model.sol())
    after_datasets = tags(model.result().dataset())
    payload["new_solutions"] = [tag for tag in after_solutions if tag not in before_solutions]
    payload["new_datasets"] = [tag for tag in after_datasets if tag not in before_datasets]
    payload["dataset_solution_map"] = {
        tag: dataset_solution(model.result().dataset(tag)) for tag in after_datasets
    }
    candidates = []
    for dataset in payload["new_datasets"]:
        try:
            values = global_values(model, dataset, [("F_ext", "N"), ("t", "s")])
            if values and len(values) == 2:
                candidates.append({
                    "dataset": dataset,
                    "count": len(values[0]),
                    "forces": sorted(set(round(value, 8) for value in values[0])),
                    "time_min": min(values[1]),
                    "time_max": max(values[1]),
                })
        except Exception as exc:
            candidates.append({"dataset": dataset, "error": str(exc)})
    payload["dataset_candidates"] = candidates
    valid = [item for item in candidates if "error" not in item and item["time_max"] >= 7200]
    if not valid:
        raise RuntimeError(f"No completed 7200 s transient dataset found: {candidates}")
    transient = max(valid, key=lambda item: (len(item["forces"]), item["count"]))
    if transient["forces"] != [0.0, 100.0, 250.0, 500.0]:
        raise RuntimeError(f"Unexpected force sweep in saved solution: {transient}")
    payload["transient_dataset"] = transient["dataset"]
    payload["transient_summary"] = transient
    model.save(RUN_MODEL)
    model.save(DELIVERY_MODEL)
    payload["elapsed_s"] = time.time() - started
    payload["source_size_bytes"] = Path(SOURCE).stat().st_size
    payload["run_model_size_bytes"] = Path(RUN_MODEL).stat().st_size
    payload["delivery_model_size_bytes"] = Path(DELIVERY_MODEL).stat().st_size
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc), "elapsed_s": time.time() - started})
finally:
    ModelUtil.remove(TAG)

if payload.get("ok"):
    verify_tag = TAG + "_reload"
    verified = ModelUtil.load(verify_tag, DELIVERY_MODEL)
    try:
        payload["reload"] = {
            "studies": tags(verified.study()),
            "solutions": tags(verified.sol()),
            "datasets": tags(verified.result().dataset()),
            "local_porosity_on": str(verified.param().get("local_porosity_on")),
        }
        payload["reload_ok"] = (
            "std_local" in payload["reload"]["studies"]
            and payload["transient_dataset"] in payload["reload"]["datasets"]
            and payload["reload"]["local_porosity_on"] == "1"
        )
    finally:
        ModelUtil.remove(verify_tag)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "reload_ok": payload.get("reload_ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
