import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\external_strain_axes_probe.json")
TAG = "coin_v8_external_strain_axes"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def boundary_average(model, dataset, expression, unit, boundary):
    manager = model.result().numerical()
    tag = "__v8_axis_avg"
    remove(manager, tag)
    node = manager.create(tag, "AvLine")
    node.set("data", dataset)
    node.set("expr", expression)
    node.set("unit", unit)
    node.selection().set([boundary])
    try:
        value = node.getReal()
        while hasattr(value, "__len__") and len(value) == 1:
            value = value[0]
        return float(value)
    finally:
        remove(manager, tag)


def dataset_for_solution(model, solution):
    for tag in [str(value) for value in model.result().dataset().tags()]:
        dataset = model.result().dataset(tag)
        try:
            if str(dataset.getString("solution")) == solution:
                return tag
        except Exception:
            pass
    raise RuntimeError(f"No dataset found for {solution}")


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "trials": {}}
try:
    model.param().set("F_ext", "0[N]")
    model.study("std_mech").feature("stat").set("useparam", "off")
    parent = model.component("comp1").physics("solid").feature("lemm1")
    tag = "__v8_axis_test"
    remove(parent.feature(), tag)
    node = parent.feature().create(tag, "ExternalStrain", 2)
    node.selection().set([4])
    node.set("StrainInput", "StrainTensor")
    node.set("eext_src", "userdef")
    tests = {
        "component_1": ["0.01", "0", "0"],
        "component_2": ["0", "0.01", "0"],
        "component_3": ["0", "0", "0.01"],
    }
    for name, strain in tests.items():
        node.set("eext", strain)
        before = set(str(value) for value in model.sol().tags())
        model.study("std_mech").run()
        after = [str(value) for value in model.sol().tags()]
        new_solutions = [value for value in after if value not in before]
        solution = new_solutions[-1] if new_solutions else after[-1]
        dataset = dataset_for_solution(model, solution)
        payload["trials"][name] = {
            "eext": strain,
            "solution": solution,
            "dataset": dataset,
            "top_u_um": boundary_average(model, dataset, "u", "um", 20),
            "top_v_um": boundary_average(model, dataset, "v", "um", 20),
            "top_disp_um": boundary_average(model, dataset, "solid.disp", "um", 20),
        }
    remove(parent.feature(), tag)
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
