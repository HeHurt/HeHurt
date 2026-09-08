import json
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\mesh_features_result.json")
tag = "plan1_mesh_features"

def read_property(node, name):
    for method in ("getString", "getStringArray", "getStringMatrix", "getBoolean", "getDouble"):
        try:
            value = getattr(node, method)(name)
            if isinstance(value, str) or value is None:
                return value
            try:
                return [read_array(v) for v in value]
            except TypeError:
                return str(value)
        except Exception:
            pass
    return None

def read_array(value):
    if isinstance(value, str):
        return value
    try:
        return [read_array(v) for v in value]
    except TypeError:
        return str(value)

def tree(manager):
    result = {}
    for feature_tag in [str(v) for v in manager.tags()]:
        try:
            node = manager.get(feature_tag)
        except Exception:
            node = manager(feature_tag)
        item = {"type": str(node.getType()), "label": str(node.label())}
        try:
            sel = node.selection()
            item["selection"] = {
                "dim": int(sel.dim()),
                "entities": [int(v) for v in sel.entities()],
                "geom": str(sel.geom()),
            }
        except Exception:
            pass
        props = {}
        try:
            names = [str(v) for v in node.properties()]
        except Exception:
            names = []
        for name in names:
            value = read_property(node, name)
            if value not in (None, "", []):
                props[name] = value
        if props:
            item["properties"] = props
        try:
            children = tree(node.feature())
            if children:
                item["features"] = children
        except Exception:
            pass
        result[feature_tag] = item
    return result

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
try:
    mesh = model.component("comp1").mesh("mesh1")
    report = tree(mesh.feature())
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
finally:
    ModelUtil.remove(tag)
