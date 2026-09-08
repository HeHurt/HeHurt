import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL_PATH = r"D:\Users\hez\Desktop\mic\超大\Case1~51D电化学模型不同长度_CW501设计参数负载循环.mph"
OUTPUT_PATH = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260824_160826_cw501_loadcycle_diag3\current_state.json"
TAG = "cw501_diag3"


def tags(manager):
    try:
        return [str(tag) for tag in manager.tags()]
    except Exception:
        return []


def get(manager, tag):
    try:
        return manager.get(tag)
    except Exception:
        return manager(tag)


def prop(node, name):
    for method in ("getString", "getStringArray", "getDouble", "getBoolean"):
        try:
            value = getattr(node, method)(name)
            if value is not None:
                if isinstance(value, (str, int, float, bool)):
                    return value
                return [str(item) for item in value]
        except Exception:
            pass
    return None


try:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    model = ModelUtil.load(TAG, MODEL_PATH)
    lc = model.component("comp1").physics("liion").feature("lc1")
    payload = {
        "source": MODEL_PATH,
        "source_modified": False,
        "load_cycle": {
            "active": bool(lc.isActive()),
            "LoadType": prop(lc, "LoadType"),
            "phis0init": prop(lc, "phis0init"),
            "useTimeConditionsOnly": prop(lc, "useTimeConditionsOnly"),
        },
        "solvers": {},
    }
    for solver_tag in tags(model.sol()):
        solver = get(model.sol(), solver_tag)
        solver_info = {"label": str(solver.label()), "time_nodes": []}
        for feature_tag in tags(solver.feature()):
            feature = get(solver.feature(), feature_tag)
            if str(feature.getType()) != "Time":
                continue
            entry = {
                "tag": feature_tag,
                "rtol": prop(feature, "rtol"),
                "timemethod": prop(feature, "timemethod"),
                "maxorder": prop(feature, "maxorder"),
                "initialstepbdf": prop(feature, "initialstepbdf"),
                "stabcntrl": prop(feature, "stabcntrl"),
                "eventtol": prop(feature, "eventtol"),
                "children": {},
            }
            for child_tag in tags(feature.feature()):
                child = get(feature.feature(), child_tag)
                if str(child.getType()) == "FullyCoupled":
                    entry["children"][child_tag] = {
                        "maxiter": prop(child, "maxiter"),
                        "ntolfact": prop(child, "ntolfact"),
                    }
            solver_info["time_nodes"].append(entry)
        payload["solvers"][solver_tag] = solver_info
    Path(OUTPUT_PATH).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": OUTPUT_PATH}, ensure_ascii=False))
finally:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
