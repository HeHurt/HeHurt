import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\audit_v8_events_exact.json")
TAG = "coin_v9_events_exact"


def read_all(node, name):
    result = {}
    for getter in ("getString", "getStringArray", "getStringMatrix"):
        try:
            value = getattr(node, getter)(name)
            if getter == "getString":
                result[getter] = str(value)
            else:
                result[getter] = [[str(y) for y in x] for x in value] if getter.endswith("Matrix") else [str(x) for x in value]
        except Exception as exc:
            result[getter] = {"error": str(exc)}
    return result


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "events": {}, "variables": {}, "study": {}}
try:
    comp = model.component("comp1")
    ev = comp.physics("ev")
    for tag in [str(x) for x in ev.feature().tags()]:
        node = ev.feature(tag)
        item = {"label": str(node.label()), "type": str(node.getType()), "properties": {}}
        for prop in [str(x) for x in node.properties()]:
            item["properties"][prop] = read_all(node, prop)
        payload["events"][tag] = item
    for group_tag in [str(x) for x in comp.variable().tags()]:
        group = comp.variable(group_tag)
        payload["variables"][group_tag] = {str(x): str(group.get(str(x))) for x in group.varnames()}
    for study_tag in [str(x) for x in model.study().tags()]:
        study = model.study(study_tag)
        item = {"label": str(study.label()), "features": {}}
        for ft in [str(x) for x in study.feature().tags()]:
            node = study.feature(ft)
            item["features"][ft] = {
                "type": str(node.getType()),
                "properties": {str(p): read_all(node, str(p)) for p in node.properties()},
            }
        payload["study"][study_tag] = item
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
