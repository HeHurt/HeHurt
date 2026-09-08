import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1\pouch_dual_tab_2d_cross_section_v7_capacity_consistent_coupled_100N_full_cycle_solved.mph")
OUTPUT = MODEL.with_name("verify_pouch_v7_capacity_consistent_result.json")
TAG = "verify_pouch_v7_capacity_consistent"


def tags(manager):
    return [str(item) for item in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def time_series(model, dataset):
    manager = model.result().numerical()
    tag = "__verify_time"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", dataset)
    node.set("expr", ["t"])
    node.set("unit", ["s"])
    try:
        return [float(item) for item in node.getReal()[0]]
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, str(MODEL))
payload = {"model": str(MODEL), "ok": False}
try:
    comp = model.component("comp1")
    candidates = []
    for dataset in tags(model.result().dataset()):
        try:
            times = time_series(model, dataset)
            if times:
                candidates.append((dataset, times))
        except Exception:
            pass
    dataset, times = max(candidates, key=lambda item: (max(item[1]), len(item[1])))
    payload.update({
        "out_of_plane_thickness": str(comp.physics("liion").prop("d").getString("d")),
        "i_1C_pouch_geom": str(model.param().get("i_1C_pouch_geom")),
        "current_expression": str(comp.variable("var1").get("I")),
        "coupling_on": str(model.param().get("coupling_on")),
        "breathing_mode": str(model.param().get("breathing_mode")),
        "force": str(model.param().get("F_ext")),
        "dataset": dataset,
        "max_time_s": max(times),
        "solution_count": len(tags(model.sol())),
        "size_bytes": MODEL.stat().st_size,
    })
    payload["ok"] = (
        payload["out_of_plane_thickness"] == "52[mm]"
        and "i_1C_pouch_geom*C_rate" in payload["current_expression"]
        and payload["coupling_on"] == "1"
        and payload["breathing_mode"] == "2"
        and payload["force"] == "100[N]"
        and payload["max_time_s"] >= 17999.9
    )
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
