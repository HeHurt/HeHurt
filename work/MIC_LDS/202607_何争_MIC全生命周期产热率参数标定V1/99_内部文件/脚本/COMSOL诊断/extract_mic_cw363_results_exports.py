import json
from pathlib import Path

OUT = r"D:\Users\hez\Desktop\hithium\COMSOL\reports\mic_cw363_results_exports.json"
TAGS = {"charge": "miccw363_charge", "discharge": "miccw363_discharge"}


def safe(label, fn):
    try:
        return fn()
    except Exception as exc:
        return {"error": label, "type": type(exc).__name__, "message": str(exc)}


def jstr(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        try:
            return [jstr(x) for x in value]
        except Exception:
            pass
    return str(value)


def tags(container):
    return safe("tags", lambda: [str(x) for x in container.tags()])


def child(container, tag):
    try:
        return container(tag)
    except Exception:
        return container.get(tag)


def props(node):
    ps = safe("properties", lambda: [str(x) for x in node.properties()])
    out = {
        "type": safe("getType", lambda: str(node.getType())),
        "name": safe("name", lambda: str(node.name())),
        "properties": ps,
    }
    if isinstance(ps, list):
        vals = {}
        for p in ps:
            val = None
            for meth in ("getString", "get", "getStringArray"):
                try:
                    val = jstr(getattr(node, meth)(p))
                    break
                except Exception:
                    pass
            vals[p] = val
        out["values"] = vals
    return out


def list_nodes(container, depth=2):
    out = {}
    ts = tags(container)
    if not isinstance(ts, list):
        return {"tags": ts}
    for t in ts:
        n = child(container, t)
        d = props(n)
        if depth > 0:
            for sub in ("feature",):
                try:
                    subc = getattr(n, sub)()
                    d[sub] = list_nodes(subc, depth - 1)
                except Exception:
                    pass
        out[t] = d
    return out


data = {}
for key, tag in TAGS.items():
    m = ModelUtil.model(tag)
    data[key] = {
        "result": list_nodes(m.result(), depth=3),
        "dataset": list_nodes(m.result().dataset(), depth=1),
        "numerical": list_nodes(m.result().numerical(), depth=1),
        "export": list_nodes(m.result().export(), depth=1),
    }

Path(OUT).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
_result = {"ok": True, "out": OUT}
