import json

from com.comsol.model.util import ModelUtil


MODEL = r"D:\Users\hez\Desktop\mic\超大\Case1~41D电化学模型不同长度_CW501设计参数_事件循环二圈能效.mph"
TAG = "cw501_study_result_audit"


def tags(manager):
    try:
        return [str(value) for value in manager.tags()]
    except Exception:
        return []


def properties(node):
    output = {}
    try:
        names = [str(value) for value in node.properties()]
    except Exception:
        names = []
    for name in names:
        for method in ("getStringArray", "getString"):
            try:
                value = getattr(node, method)(name)
                if method == "getStringArray":
                    value = [str(item) for item in value]
                else:
                    value = str(value)
                output[name] = value
                break
            except Exception:
                pass
    return output


try:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    model = ModelUtil.load(TAG, MODEL)
    payload = {"study": {}, "solutions": {}, "datasets": {}, "numerical": {}}
    for tag in tags(model.study("std1").feature()):
        node = model.study("std1").feature(tag)
        payload["study"][tag] = {"label": str(node.label()), "properties": properties(node)}
    for tag in tags(model.sol()):
        node = model.sol(tag)
        payload["solutions"][tag] = {"label": str(node.label()), "study": properties(node).get("study")}
    for tag in tags(model.result().dataset()):
        node = model.result().dataset(tag)
        payload["datasets"][tag] = {"label": str(node.label()), "properties": properties(node)}
    for tag in tags(model.result().numerical()):
        node = model.result().numerical(tag)
        payload["numerical"][tag] = {"label": str(node.label()), "properties": properties(node)}
    print(json.dumps(payload, ensure_ascii=False))
finally:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
