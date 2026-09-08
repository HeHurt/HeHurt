import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1\pouch_dual_tab_2d_cross_section_v4_mechanical_breathing.mph")
OUTPUT = MODEL.with_name("inspect_pouch_v4_events_result.json")
TAG = "inspect_pouch_v4_events"


def read(node, prop):
    result = {}
    for getter in ("getString", "getStringArray", "getStringMatrix"):
        try:
            value = getattr(node, getter)(prop)
            if getter == "getString":
                result[getter] = str(value)
            elif getter == "getStringArray":
                result[getter] = [str(item) for item in value]
            else:
                result[getter] = [[str(item) for item in row] for row in value]
        except Exception as exc:
            result[getter] = {"error": str(exc)}
    return result


model = ModelUtil.load(TAG, str(MODEL))
payload = {}
try:
    ev = model.component("comp1").physics("ev")
    for tag in [str(item) for item in ev.feature().tags()]:
        node = ev.feature(tag)
        payload[tag] = {
            "type": str(node.getType()),
            "properties": {str(prop): read(node, str(prop)) for prop in node.properties()},
        }
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
