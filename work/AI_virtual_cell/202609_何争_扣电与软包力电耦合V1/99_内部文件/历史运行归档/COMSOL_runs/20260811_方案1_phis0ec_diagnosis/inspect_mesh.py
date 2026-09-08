import json
from collections import Counter
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\mesh_result.json")
tag = "plan1_mesh"

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
try:
    mesh = model.component("comp1").mesh("mesh1")
    if mesh.isEmpty() or not mesh.isComplete():
        mesh.run()
    report = {
        "is_empty": bool(mesh.isEmpty()),
        "is_complete": bool(mesh.isComplete()),
        "has_problems": bool(mesh.hasProblems()),
        "problems": [str(v) for v in mesh.problems()],
        "types": [str(v) for v in mesh.getTypes()],
        "num_elements": int(mesh.getNumElem()),
        "entity_counts": {},
    }
    for mesh_type in report["types"]:
        entities = [int(v) for v in mesh.getElemEntity(mesh_type)]
        report["entity_counts"][mesh_type] = {
            str(k): int(v) for k, v in sorted(Counter(entities).items())
        }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
finally:
    ModelUtil.remove(tag)
