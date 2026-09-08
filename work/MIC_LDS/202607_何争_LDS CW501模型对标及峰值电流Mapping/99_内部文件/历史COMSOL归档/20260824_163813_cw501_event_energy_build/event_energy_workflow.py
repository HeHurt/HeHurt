import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


SOURCE = r"D:\Users\hez\Desktop\mic\超大\Case1~41D电化学模型不同长度_CW501设计参数.mph"
OUTPUT = r"C:\HithiumSSD\hithium\COMSOL\runs\20260824_163813_cw501_event_energy_build\event_detail_audit.json"
TAG = "cw501_event_energy_workflow"


def tags(manager):
    try:
        return [str(tag) for tag in manager.tags()]
    except Exception:
        return []


def get_node(manager, tag):
    try:
        return manager.get(tag)
    except Exception:
        return manager(tag)


def values(node, name):
    result = {}
    for method in ("getStringArray", "getStringMatrix", "getString"):
        try:
            value = getattr(node, method)(name)
            if value is not None:
                if method == "getStringMatrix":
                    value = [[str(item) for item in row] for row in value]
                elif method == "getStringArray":
                    value = [str(item) for item in value]
                else:
                    value = str(value)
                result[method] = value
        except Exception:
            pass
    return result


def node_properties(node):
    try:
        names = [str(name) for name in node.properties()]
    except Exception:
        names = []
    return {name: values(node, name) for name in names}


def variable_groups(manager):
    result = {}
    for tag in tags(manager):
        node = get_node(manager, tag)
        try:
            names = [str(name) for name in node.varnames()]
        except Exception:
            names = []
        result[tag] = {
            "label": str(node.label()),
            "variables": {name: str(node.get(name)) for name in names},
        }
    return result


try:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    model = ModelUtil.load(TAG, SOURCE)
    comp = model.component("comp1")
    event = comp.physics("ev")
    payload = {
        "source": SOURCE,
        "source_modified": False,
        "events": {},
        "global_equations": {},
        "global_variables": variable_groups(model.variable()),
        "component_variables": variable_groups(comp.variable()),
        "electrode_current": node_properties(comp.physics("liion").feature("ec1")),
    }
    for feature_tag in tags(event.feature()):
        node = event.feature(feature_tag)
        payload["events"][feature_tag] = {
            "label": str(node.label()),
            "active": bool(node.isActive()),
            "properties": node_properties(node),
        }
    ge = comp.physics("ge")
    for feature_tag in tags(ge.feature()):
        node = ge.feature(feature_tag)
        payload["global_equations"][feature_tag] = {
            "label": str(node.label()),
            "properties": node_properties(node),
        }
    Path(OUTPUT).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": OUTPUT}, ensure_ascii=False))
finally:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
