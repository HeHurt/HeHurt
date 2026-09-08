import json
import time
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


TASK = Path(r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包统一极片设计力电耦合V1")
SOURCE = TASK / "02_模型" / "扣电_统一极片设计_0p5C_同名义压力_完整耦合_待计算.mph"
OUTPUT = TASK / "02_模型" / "扣电_统一极片设计_0p5C_同名义压力_完整耦合_已计算.mph"
RESULT = TASK / "99_内部文件" / "JSON" / "扣电_完整循环计算结果.json"
PROGRESS = TASK / "99_内部文件" / "运行记录" / "扣电_完整循环.log"
TAG = "coin_unified_full_cycle"

payload = {"ok": False, "source": str(SOURCE), "output_model": str(OUTPUT)}
try:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    ModelUtil.showProgress(str(PROGRESS))
    model = ModelUtil.load(TAG, str(SOURCE))
    model.param().set("SOC", "0.01")
    model.param().set("F_ext", "p_compare*Ac")
    model.param().set("coupling_on", "1")
    model.param().set("local_porosity_on", "1")
    model.param().set("breathing_on", "1")
    model.param().set("breathing_mode", "2")
    model.param().set("cycle_rest", "600[s]")
    model.param().set("V_charge_cut", "3.65[V]")
    model.param().set("V_discharge_cut", "2.5[V]")
    model.component("comp1").variable("var1").set("C", "0.5")
    model.study("std_v9").feature("time").set("tlist", "range(0,60,18000)")
    model.sol("sol3").feature("t1").set("tlist", "range(0,60,18000)")
    model.sol("sol3").feature("t1").set("initialstepbdf", "0.1[s]")
    model.sol("sol3").feature("t1").set("initialstepbdfactive", "on")
    model.sol("sol3").feature("t1").set("maxorder", "2")
    for soltag in model.sol().tags():
        model.sol(str(soltag)).clearSolutionData()
    started = time.time()
    model.study("std_v9").run()
    elapsed = time.time() - started
    times = list(model.sol("sol3").getPVals())
    model.save(str(OUTPUT))
    payload.update({
        "ok": True,
        "solve_elapsed_s": elapsed,
        "n_times": len(times),
        "time_end_s": max(times),
        "i_1C_A": float(model.param().evaluate("i_1C")),
        "current_0p5C_A": 0.5 * float(model.param().evaluate("i_1C")),
        "force_N": float(model.param().evaluate("F_ext")),
        "nominal_pressure_Pa": float(model.param().evaluate("F_ext")) / float(model.param().evaluate("Ac")),
    })
except Exception:
    payload["traceback"] = traceback.format_exc()
    raise
finally:
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    ModelUtil.showProgress(False)
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps(payload, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")

