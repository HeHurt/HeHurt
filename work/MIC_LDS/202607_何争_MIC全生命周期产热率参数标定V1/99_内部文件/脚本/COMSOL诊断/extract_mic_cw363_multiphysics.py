import json
from pathlib import Path

OUT = r"D:\Users\hez\Desktop\hithium\COMSOL\reports\mic_cw363_multiphysics.json"
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
        out["values"] = {}
        for p in ps:
            val = None
            for meth in ("getString", "get", "getStringArray"):
                try:
                    val = jstr(getattr(node, meth)(p))
                    break
                except Exception:
                    pass
            out["values"][p] = val
    return out


data = {}
for key, tag in TAGS.items():
    m = ModelUtil.model(tag)
    model_mp = {}
    mtags = safe("model.multiphysics.tags", lambda: [str(x) for x in m.multiphysics().tags()])
    if isinstance(mtags, list):
        for t in mtags:
            model_mp[t] = props(m.multiphysics(t))
    comps = {}
    for ctag in [str(x) for x in m.component().tags()]:
        comp = m.component(ctag)
        ctags_mp = safe("comp.multiphysics.tags", lambda comp=comp: [str(x) for x in comp.multiphysics().tags()])
        cobj = {}
        if isinstance(ctags_mp, list):
            for t in ctags_mp:
                cobj[t] = props(comp.multiphysics(t))
        comps[ctag] = cobj
    data[key] = {"model_multiphysics": model_mp, "component_multiphysics": comps}

Path(OUT).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
_result = {"ok": True, "out": OUT}
