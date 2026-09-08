import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
MODELS = {
    "baseline_new": RUN / "pouch_dual_tab_2d_cross_section_v4_baseline_full_cycle_solved.mph",
    "coupled_old": RUN / "pouch_dual_tab_2d_cross_section_v4_coupled_100N_full_cycle_solved.mph",
}
OUTPUT = RUN / "inspect_saved_pouch_solutions_result.json"


def tags(manager):
    return [str(item) for item in manager.tags()]


def read_properties(node):
    output = {}
    for prop in [str(item) for item in node.properties()]:
        values = {}
        for getter in ("getString", "getStringArray", "getStringMatrix"):
            try:
                raw = getattr(node, getter)(prop)
                if getter == "getString":
                    values[getter] = str(raw)
                elif getter == "getStringArray":
                    values[getter] = [str(item) for item in raw]
                else:
                    values[getter] = [[str(item) for item in row] for row in raw]
            except Exception:
                pass
        output[prop] = values
    return output


payload = {}
for label, path in MODELS.items():
    tag = f"inspect_{label}"
    model = ModelUtil.load(tag, str(path))
    try:
        comp = model.component("comp1")
        liion = comp.physics("liion")
        payload[label] = {
            "path": str(path),
            "size": path.stat().st_size,
            "parameters": {name: str(model.param().get(name)) for name in (
                "Ac", "W_cell", "H_cell", "i_1C", "C_rate", "coupling_on", "breathing_mode", "F_ext"
            )},
            "terminal": read_properties(liion.feature("ecd1")),
            "studies": tags(model.study()),
            "solutions": tags(model.sol()),
            "datasets": {
                dataset: {
                    "type": str(model.result().dataset(dataset).getType()),
                    "properties": read_properties(model.result().dataset(dataset)),
                }
                for dataset in tags(model.result().dataset())
            },
        }
    finally:
        ModelUtil.remove(tag)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
