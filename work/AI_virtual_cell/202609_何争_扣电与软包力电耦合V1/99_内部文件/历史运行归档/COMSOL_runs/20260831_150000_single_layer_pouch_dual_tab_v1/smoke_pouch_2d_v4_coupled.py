import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_2d_cross_section_v4_mechanical_breathing.mph"
OUTPUT = RUN / "pouch_dual_tab_2d_cross_section_v5_mechanical_breathing_smoke_solved.mph"
RESULT = RUN / "smoke_pouch_2d_v4_coupled_result.json"
TAG = "smoke_pouch_2d_v4_coupled"


def last_value(values):
    try:
        return float(values[0][len(values[0]) - 1])
    except Exception:
        return float(values[len(values) - 1])


payload = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
try:
    model = ModelUtil.load(TAG, str(SOURCE))
    model.param().set("coupling_on", "1")
    model.param().set("breathing_mode", "2")
    model.param().set("F_ext", "100[N]")
    model.study("std_cycle").feature("time").set("tlist", "range(0,20,120)")
    model.study("std_cycle").run()

    values = {}
    for tag, expression, unit in (
        ("gev_voltage", "vol_loaded", "V"),
        ("gev_current", "I", "A"),
    ):
        model.result().numerical().create(tag, "EvalGlobal")
        node = model.result().numerical(tag)
        node.set("expr", expression)
        node.set("unit", unit)
        values[tag] = last_value(node.getReal())

    for tag, domain, expression, unit in (
        ("av_neg_pressure", [4], "p_comp_neg_v4", "Pa"),
        ("av_sep_pressure", [5], "p_comp_sep_v4", "Pa"),
        ("av_pos_pressure", [6], "p_comp_pos_v4", "Pa"),
        ("av_neg_porosity", [4], "epsl_neg_v4", "1"),
        ("av_sep_porosity", [5], "epsl_sep_v4", "1"),
        ("av_pos_porosity", [6], "epsl_pos_v4", "1"),
        ("av_uy", [4, 5, 6], "v", "m"),
    ):
        model.result().numerical().create(tag, "AvSurface")
        node = model.result().numerical(tag)
        node.selection().set(domain)
        node.set("expr", expression)
        node.set("unit", unit)
        values[tag] = last_value(node.getReal())

    model.label("Single-layer pouch 2D V5 - coupled 120 s smoke solved")
    model.save(str(OUTPUT))
    payload.update({"ok": True, "values_at_120s": values})
except Exception:
    payload["traceback"] = traceback.format_exc()
finally:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps(payload, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")
