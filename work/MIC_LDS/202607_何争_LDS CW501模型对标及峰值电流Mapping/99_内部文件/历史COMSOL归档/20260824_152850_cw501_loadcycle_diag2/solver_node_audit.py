import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL_PATH = r"D:\Users\hez\Desktop\mic\超大\Case1~51D电化学模型不同长度_CW501设计参数负载循环.mph"
OUTPUT_PATH = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260824_152850_cw501_loadcycle_diag2\solver_node_properties.json"
MODEL_TAG = "cw501_solver_node_audit"


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


def read_property(node, name):
    for method in ("getString", "getStringArray", "getStringMatrix", "getDouble", "getBoolean"):
        try:
            value = getattr(node, method)(name)
            if value is not None:
                if isinstance(value, (str, int, float, bool)):
                    return value
                try:
                    return [list(row) if not isinstance(row, str) else row for row in value]
                except TypeError:
                    return str(value)
        except Exception:
            pass
    return None


def walk(manager):
    result = {}
    for tag in tags(manager):
        node = get_node(manager, tag)
        try:
            prop_names = [str(name) for name in node.properties()]
        except Exception:
            prop_names = []
        props = {}
        for name in prop_names:
            value = read_property(node, name)
            if value not in (None, "", []):
                props[name] = value
        item = {
            "label": str(node.label()),
            "type": str(node.getType()),
            "properties": props,
        }
        try:
            children = walk(node.feature())
        except Exception:
            children = {}
        if children:
            item["features"] = children
        result[tag] = item
    return result


try:
    try:
        ModelUtil.remove(MODEL_TAG)
    except Exception:
        pass
    model = ModelUtil.load(MODEL_TAG, MODEL_PATH)
    payload = {"source": MODEL_PATH, "source_modified": False, "solvers": {}, "physics": {}}
    for solver_tag in tags(model.sol()):
        solver = get_node(model.sol(), solver_tag)
        payload["solvers"][solver_tag] = {
            "label": str(solver.label()),
            "features": walk(solver.feature()),
        }
    for physics_tag in ("liion", "ev"):
        physics = model.component("comp1").physics(physics_tag)
        payload["physics"][physics_tag] = {
            "label": str(physics.label()),
            "features": walk(physics.feature()),
        }
    Path(OUTPUT_PATH).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": OUTPUT_PATH}, ensure_ascii=False))
finally:
    try:
        ModelUtil.remove(MODEL_TAG)
    except Exception:
        pass
