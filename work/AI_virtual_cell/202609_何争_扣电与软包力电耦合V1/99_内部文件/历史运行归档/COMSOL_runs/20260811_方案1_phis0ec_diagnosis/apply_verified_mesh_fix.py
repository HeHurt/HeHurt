import json
from collections import Counter
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = Path(r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph")
output_model = Path(r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1_已修复.mph")
output_json = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\apply_fix_result.json")

patch_tag = "plan1_patch"
verify_tag = "plan1_verify"
result = {
    "source": str(source),
    "output_model": str(output_model),
    "saved_as": True,
    "operation": "mesh1/swe2 selection [1,8] -> [1,2,8,9]",
}

for tag in (patch_tag, verify_tag):
    try:
        ModelUtil.remove(tag)
    except Exception:
        pass

model = ModelUtil.load(patch_tag, str(source))
try:
    mesh = model.component("comp1").mesh("mesh1")
    swe2 = mesh.feature("swe2")
    result["selection_before"] = [int(v) for v in swe2.selection().entities()]
    swe2.selection().set([1, 2, 8, 9])
    mesh.run()
    result["mesh_complete_before_save"] = bool(mesh.isComplete())
    result["mesh_status_before_save"] = str(swe2.status())
    result["mesh_message_before_save"] = str(swe2.message())
    output_model.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(output_model))
finally:
    ModelUtil.remove(patch_tag)

saved = ModelUtil.load(verify_tag, str(output_model))
probe_tag = "__codex_verify_voltage"
try:
    mesh = saved.component("comp1").mesh("mesh1")
    swe2 = mesh.feature("swe2")
    result["selection_after_reload"] = [int(v) for v in swe2.selection().entities()]
    result["selection_assertion"] = result["selection_after_reload"] == [1, 2, 8, 9]
    if mesh.isEmpty() or not mesh.isComplete():
        mesh.run()
    result["mesh_complete_after_reload"] = bool(mesh.isComplete())
    result["volume_element_counts"] = {}
    for mesh_type in ("tet", "prism", "hex", "pyr"):
        if mesh_type in [str(v) for v in mesh.getTypes()]:
            domains = Counter(int(v) for v in mesh.getElemEntity(mesh_type))
            result["volume_element_counts"][mesh_type] = {
                str(i): int(domains.get(i, 0)) for i in range(1, 10)
            }

    study = saved.study("std1")
    study.feature("param").set("plistarr", ["580[mm]"])
    study.feature("time").set("tlist", "range(0,0.1,0.2)")
    study.run()
    result["smoke"] = {
        "ok": True,
        "saved": False,
        "L_JR_pos": "580[mm]",
        "tlist": "range(0,0.1,0.2)",
    }

    try:
        saved.result().numerical().remove(probe_tag)
    except Exception:
        pass
    evaluator = saved.result().numerical().create(probe_tag, "EvalGlobal")
    evaluator.set("expr", ["comp1.liion.phis0_ec1"])
    evaluator.set("unit", ["V"])
    for dataset in reversed([str(v) for v in saved.result().dataset().tags()]):
        try:
            evaluator.set("data", dataset)
            values = evaluator.getReal()
            if len(values):
                result["smoke"]["dataset"] = dataset
                result["smoke"]["terminal_potential_V"] = [float(v) for v in values[0]]
                break
        except Exception:
            continue
finally:
    try:
        saved.result().numerical().remove(probe_tag)
    except Exception:
        pass
    ModelUtil.remove(verify_tag)

output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(output_json))
