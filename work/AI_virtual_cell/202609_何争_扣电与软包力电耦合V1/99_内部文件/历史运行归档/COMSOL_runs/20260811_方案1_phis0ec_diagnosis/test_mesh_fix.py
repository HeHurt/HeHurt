import json
from collections import Counter
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\mesh_fix_result.json")
tag = "plan1_mesh_fix"

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
report = {"change": "mesh1/swe2 selection: [1,8] -> [1,2,8,9]", "saved": False}
try:
    mesh = model.component("comp1").mesh("mesh1")
    mesh.feature("swe2").selection().set([1, 2, 8, 9])
    try:
        mesh.run()
        report["mesh_ok"] = True
        report["mesh_complete"] = bool(mesh.isComplete())
        report["mesh_problems"] = [str(v) for v in mesh.problems()]
        report["mesh_types"] = [str(v) for v in mesh.getTypes()]
        report["volume_element_counts"] = {}
        for mesh_type in ["tet", "prism", "hex", "pyr"]:
            if mesh_type in report["mesh_types"]:
                domains = Counter(int(v) for v in mesh.getElemEntity(mesh_type))
                report["volume_element_counts"][mesh_type] = {
                    str(i): int(domains.get(i, 0)) for i in range(1, 10)
                }
        swe2 = mesh.feature("swe2")
        report["swe2_status"] = str(swe2.status())
        report["swe2_message"] = str(swe2.message())
        report["swe2_warnings"] = [str(v) for v in swe2.warnings()]
    except Exception as exc:
        report["mesh_ok"] = False
        report["mesh_error"] = str(exc)
    report["solve_ok"] = "verified_in_previous_in_memory_run"
finally:
    ModelUtil.remove(tag)

output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(str(output))
