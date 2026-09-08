import json
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\solver_result.json")
tag = "plan1_solver"

def scalar(value):
    if isinstance(value, str):
        return value
    try:
        return [scalar(v) for v in value]
    except TypeError:
        return str(value)

def read_property(node, name):
    for method in ("getString", "getStringArray", "getStringMatrix", "getBoolean", "getDouble"):
        try:
            value = getattr(node, method)(name)
            if value is not None:
                return scalar(value)
        except Exception:
            pass
    return None

def feature_tree(manager):
    result = {}
    for feature_tag in [str(v) for v in manager.tags()]:
        try:
            node = manager.get(feature_tag)
        except Exception:
            node = manager(feature_tag)
        props = {}
        for name in [str(v) for v in node.properties()]:
            value = read_property(node, name)
            if value not in (None, "", []):
                props[name] = value
        item = {
            "type": str(node.getType()),
            "label": str(node.label()),
            "properties": props,
        }
        children = feature_tree(node.feature())
        if children:
            item["features"] = children
        result[feature_tag] = item
    return result

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
try:
    report = {"studies": {}, "solutions": {}}
    for study_tag in [str(v) for v in model.study().tags()]:
        study = model.study(study_tag)
        report["studies"][study_tag] = feature_tree(study.feature())
    for sol_tag in [str(v) for v in model.sol().tags()]:
        sol = model.sol(sol_tag)
        report["solutions"][sol_tag] = {
            "label": str(sol.label()),
            "study": read_property(sol, "study"),
            "features": feature_tree(sol.feature()),
        }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
finally:
    ModelUtil.remove(tag)
