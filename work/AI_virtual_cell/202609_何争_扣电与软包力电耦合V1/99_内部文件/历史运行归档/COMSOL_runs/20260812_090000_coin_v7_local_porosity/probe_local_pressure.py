import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_090000_coin_v7_local_porosity\local_pressure_probe.json")
TAG = "coin_v7_local_pressure_probe"
DOMAINS = {"negative": [4], "separator": [5], "positive": [6]}
STRESS_CANDIDATES = ["solid.sz", "solid.szz", "solid.sZZ", "solid.pm", "solid.p"]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def evaluate(model, dataset, solnum, expression, domains):
    manager = model.result().numerical()
    tag = "__pressure_probe"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", dataset)
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.set("unit", ["Pa"])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    try:
        values = [float(row[0]) for row in node.getReal()]
        return {"min": min(values), "max": max(values), "mean": sum(values) / len(values), "count": len(values)}
    finally:
        remove(manager, tag)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "mechanics": {}, "cross_solution": {}}
try:
    for expression in STRESS_CANDIDATES:
        payload["mechanics"][expression] = {}
        for region, domains in DOMAINS.items():
            try:
                payload["mechanics"][expression][region] = evaluate(model, "dset4", 2, expression, domains)
            except Exception as exc:
                payload["mechanics"][expression][region] = {"error": str(exc)}

    cross_candidates = [
        "withsol('sol2',solid.sz,setval(F_ext,F_ext))",
        "withsol('sol2',solid.szz,setval(F_ext,F_ext))",
        "withsol('sol2',solid.sZZ,setval(F_ext,F_ext))",
    ]
    for expression in cross_candidates:
        try:
            payload["cross_solution"][expression] = evaluate(model, "dset1", 364, expression, [4, 5, 6])
        except Exception as exc:
            payload["cross_solution"][expression] = {"error": str(exc)}
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT)}, ensure_ascii=False))
