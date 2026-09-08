import json
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\fresh_solver_result.json")
tag = "plan1_fresh_solver"

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
report = {}
try:
    study = model.study("std1")
    study.feature("param").set("plistarr", ["580[mm]"])
    study.feature("time").set("tlist", "range(0,0.1,0.2)")
    report["solutions_before"] = [str(v) for v in model.sol().tags()]
    study.showAutoSequences("sol")
    report["solutions_after"] = [str(v) for v in model.sol().tags()]
    fresh = report["solutions_after"][-1]
    report["fresh_solution"] = fresh
    try:
        model.sol(fresh).runAll()
        report["ok"] = True
    except Exception as exc:
        report["ok"] = False
        report["error"] = str(exc)
finally:
    ModelUtil.remove(tag)

output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(output))
