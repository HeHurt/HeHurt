import json
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\materials_result.json")
tag = "plan1_materials"

def read_property(node, name):
    for method in ("getString", "getStringArray", "getStringMatrix"):
        try:
            value = getattr(node, method)(name)
            if value is not None:
                try:
                    return [list(row) if hasattr(row, "__iter__") and not isinstance(row, str) else row for row in value]
                except TypeError:
                    return str(value)
        except Exception:
            pass
    return None

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
try:
    comp = model.component("comp1")
    report = {}
    for material_tag in [str(v) for v in comp.material().tags()]:
        material = comp.material(material_tag)
        item = {
            "label": str(material.label()),
            "selection": [int(v) for v in material.selection().entities()],
            "property_groups": {},
        }
        for group_tag in [str(v) for v in material.propertyGroup().tags()]:
            group = material.propertyGroup(group_tag)
            props = {}
            for name in [str(v) for v in group.properties()]:
                value = read_property(group, name)
                if value not in (None, "", []):
                    props[name] = value
            item["property_groups"][group_tag] = {
                "label": str(group.label()),
                "properties": props,
            }
        report[material_tag] = item
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
finally:
    ModelUtil.remove(tag)
