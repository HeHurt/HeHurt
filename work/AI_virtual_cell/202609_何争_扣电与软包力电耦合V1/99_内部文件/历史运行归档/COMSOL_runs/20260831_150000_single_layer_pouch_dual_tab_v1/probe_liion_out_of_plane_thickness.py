import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1\pouch_dual_tab_2d_cross_section_v4_baseline_full_cycle_solved.mph")
OUTPUT = MODEL.with_name("probe_liion_out_of_plane_thickness_result.json")
TAG = "probe_liion_out_of_plane_thickness"


model = ModelUtil.load(TAG, str(MODEL))
payload = {}
try:
    liion = model.component("comp1").physics("liion")
    payload["methods"] = sorted(set(str(method.getName()) for method in liion.getClass().getMethods()))
    for method_name in ("propertyGroup", "prop", "getString", "getStringArray"):
        payload[method_name] = method_name in payload["methods"]
    # Probe common COMSOL 2D thickness property-group and property names.
    probes = {}
    for group_name in ("d", "Thickness", "OutOfPlaneThickness", "PhysicalModelProperty"):
        try:
            group = liion.prop(group_name)
            item = {"ok": True, "methods": sorted(set(str(m.getName()) for m in group.getClass().getMethods()))}
            for name in ("d", "d0", "thickness", "Thickness"):
                try:
                    item[name] = str(group.getString(name))
                except Exception as exc:
                    item[name] = {"error": str(exc)}
            probes[group_name] = item
        except Exception as exc:
            probes[group_name] = {"ok": False, "error": str(exc)}
    payload["probes"] = probes
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
