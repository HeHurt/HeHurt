import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


TASK = Path(r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包统一极片设计力电耦合V1")
SOURCE = TASK / "02_模型" / "软包_统一极片设计_0p5C_同名义压力_完整耦合_待计算.mph"
OUTPUT = TASK / "99_内部文件" / "JSON" / "软包_smoke结果.json"
PROGRESS = TASK / "99_内部文件" / "运行记录" / "软包_smoke_direct.log"
TAG = "pouch_unified_smoke"


def evaluate_series(model, expression, unit):
    manager = model.result().numerical()
    tag = "__smoke_eval"
    try:
        manager.remove(tag)
    except Exception:
        pass
    node = manager.create(tag, "EvalGlobal")
    node.set("data", "dset1")
    node.set("expr", [expression])
    node.set("unit", [unit])
    try:
        return [float(value) for value in node.getReal()[0]]
    finally:
        manager.remove(tag)


payload = {"ok": False, "source": str(SOURCE)}
try:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    ModelUtil.showProgress(str(PROGRESS))
    model = ModelUtil.load(TAG, str(SOURCE))
    model.study("std_cycle").feature("time").set("tlist", "range(0,30,300)")
    model.study("std_cycle").run()
    voltage = evaluate_series(model, "vol_loaded", "V")
    current = evaluate_series(model, "I", "A")
    payload.update({
        "ok": True,
        "time_end_s": 300.0,
        "n_times": len(voltage),
        "voltage_range_V": [min(voltage), max(voltage)],
        "current_range_A": [min(current), max(current)],
        "i_1C_A": float(model.param().evaluate("i_1C")),
        "force_N": float(model.param().evaluate("F_ext")),
        "area_m2": float(model.param().evaluate("Ac")),
        "nominal_pressure_Pa": float(model.param().evaluate("F_ext")) / float(model.param().evaluate("Ac")),
    })
except Exception:
    payload["traceback"] = traceback.format_exc()
    raise
finally:
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    ModelUtil.showProgress(False)
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps(payload, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")

