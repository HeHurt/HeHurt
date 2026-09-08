import json
from pathlib import Path
import jpype
import time


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260811_132326_coin_v6_force_postprocess\saved_sweep_probe.json")
TAG = "coin_v6_saved_sweep_probe"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def eval_global(model, data, outer):
    manager = model.result().numerical()
    tag = f"__probe_v4_{data}_{outer}_{int(time.time() * 1000) % 1000000}"
    node = manager.create(tag, "EvalGlobal")
    steps = []
    try:
        node.set("data", data)
        steps.append("data")
        node.set("expr", ["F_ext", "t", "vol", "vol_loaded", "I/i_1C"])
        steps.append("expr")
        node.set("unit", ["N", "s", "V", "V", "1"])
        steps.append("unit")
        return {"steps": steps, "values": jsonable(node.getReal())}
    except Exception as exc:
        return {"steps": steps, "error": str(exc)}
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "solutions": {}, "global_trials": {}}
try:
    for sol_tag in ("sol1", "sol2"):
        sol = model.sol(sol_tag)
        methods = sorted({
            str(method.getName())
            for method in sol.getClass().getMethods()
            if any(key in str(method.getName()).lower() for key in ("outer", "pval", "param"))
        })
        item = {"methods": methods}
        for method_name in ("getPVals", "getPNames", "getParametricSolutions"):
            try:
                item[method_name] = jsonable(getattr(sol, method_name)())
            except Exception as exc:
                item[method_name + "_error"] = str(exc)
        payload["solutions"][sol_tag] = item

    for data in ("dset1", "dset4"):
        payload["global_trials"][data] = {}
        for outer in range(1, 2):
            payload["global_trials"][data][str(outer)] = eval_global(model, data, outer)
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
