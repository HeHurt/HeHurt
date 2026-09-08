import json
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\isolation_result.json")

cases = [
    {"name": "baseline"},
    {"name": "no_contact_resistance", "contact": "0"},
    {"name": "boundary_43_only", "boundaries": [43]},
    {"name": "boundary_46_only", "boundaries": [46]},
]

results = []
for index, case in enumerate(cases):
    tag = f"plan1_case_{index}"
    try:
        ModelUtil.remove(tag)
    except Exception:
        pass
    model = ModelUtil.load(tag, source)
    try:
        ec1 = model.component("comp1").physics("liion").feature("ec1")
        if "contact" in case:
            ec1.set("IncludeContactResistance", case["contact"])
        if "boundaries" in case:
            ec1.selection().set(case["boundaries"])
        model.study("std1").feature("param").set("plistarr", ["580[mm]"])
        model.study("std1").feature("time").set("tlist", "range(0,0.1,0.2)")
        try:
            model.study("std1").run()
            results.append({"name": case["name"], "ok": True})
        except Exception as exc:
            results.append({"name": case["name"], "ok": False, "error": str(exc)})
    finally:
        ModelUtil.remove(tag)

output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(output))
