import json
from pathlib import Path


FILES = {
    "charge": r"D:\Users\hez\Desktop\mic\MICCW363-充电产热.mph",
    "discharge": r"D:\Users\hez\Desktop\mic\MICCW363-放电产热.mph",
}
OUT = r"D:\Users\hez\Desktop\hithium\COMSOL\reports\mic_cw363_heat_compare_extract.json"


def safe(label, fn):
    try:
        return fn()
    except Exception as exc:
        return {"error": label, "type": type(exc).__name__, "message": str(exc)}


def jstr(value):
    try:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
            try:
                return [jstr(x) for x in value]
            except Exception:
                pass
        return str(value)
    except Exception as exc:
        return {"convert_error": type(exc).__name__, "message": str(exc)}


def tags(container):
    return safe("tags", lambda: [str(x) for x in container.tags()])


def child(container, tag):
    try:
        return container(tag)
    except Exception:
        return container.get(tag)


def get_prop(node, prop):
    for method in ("getString", "get", "getStringArray"):
        try:
            return jstr(getattr(node, method)(prop))
        except Exception:
            continue
    return {"error": "unreadable_property"}


def node_type_name(node):
    return {
        "type": safe("getType", lambda: str(node.getType())),
        "name": safe("name", lambda: str(node.name())),
    }


def node_props(node):
    props = safe("properties", lambda: [str(x) for x in node.properties()])
    out = node_type_name(node)
    out["properties"] = props
    if isinstance(props, list):
        out["values"] = {p: get_prop(node, p) for p in props}
    return out


def variable_nodes(container):
    out = {}
    vtags = safe("variable.tags", lambda: [str(x) for x in container.variable().tags()])
    if not isinstance(vtags, list):
        return {"tags": vtags}
    for vtag in vtags:
        v = container.variable(vtag)
        names = safe("varnames", lambda v=v: [str(x) for x in v.varnames()])
        defs = {}
        if isinstance(names, list):
            for n in names:
                defs[n] = {
                    "expr": safe(f"{vtag}.{n}", lambda n=n, v=v: jstr(v.get(n))),
                    "descr": safe(f"{vtag}.{n}.descr", lambda n=n, v=v: jstr(v.descr(n))),
                }
        out[vtag] = {
            "name": safe("name", lambda v=v: str(v.name())),
            "varnames": names,
            "definitions": defs,
        }
    return out


def functions(container):
    out = {}
    ftags = tags(container.func())
    if not isinstance(ftags, list):
        return {"tags": ftags}
    for ftag in ftags:
        f = child(container.func(), ftag)
        out[ftag] = node_props(f)
    return out


def physics_nodes(comp):
    out = {}
    ptags = tags(comp.physics())
    if not isinstance(ptags, list):
        return {"tags": ptags}
    for ptag in ptags:
        phys = comp.physics(ptag)
        pobj = node_props(phys)
        ftags = tags(phys.feature())
        features = {}
        if isinstance(ftags, list):
            for ftag in ftags:
                features[ftag] = node_props(phys.feature(ftag))
        pobj["features"] = features
        out[ptag] = pobj
    return out


def couplings(comp):
    # Different COMSOL versions expose these lists under different names.
    out = {}
    for attr in ("cpl", "coupling", "selection"):
        out[attr] = safe(attr, lambda attr=attr: [str(x) for x in getattr(comp, attr)().tags()])
    return out


def parameters(model):
    names = safe("param.varnames", lambda: [str(x) for x in model.param().varnames()])
    vals = {}
    if isinstance(names, list):
        for n in names:
            vals[n] = {
                "expr": safe(n, lambda n=n: jstr(model.param().get(n))),
                "descr": safe(n + ".descr", lambda n=n: jstr(model.param().descr(n))),
            }
    return vals


def extract_model(key, path):
    tag = f"miccw363_{key}"
    current = [str(x) for x in ModelUtil.tags()]
    if tag not in current:
        ModelUtil.load(tag, path)
    m = ModelUtil.model(tag)
    out = {
        "tag": tag,
        "path": path,
        "label": safe("label", lambda: str(m.label())),
        "parameters": parameters(m),
        "global_functions": functions(m),
        "global_variables": variable_nodes(m),
        "components": {},
        "studies": {},
    }
    ctags = tags(m.component())
    if isinstance(ctags, list):
        for ctag in ctags:
            comp = m.component(ctag)
            out["components"][ctag] = {
                "variables": variable_nodes(comp),
                "functions": functions(comp),
                "physics": physics_nodes(comp),
                "couplings": couplings(comp),
            }
    stags = tags(m.study())
    if isinstance(stags, list):
        for stag in stags:
            study = m.study(stag)
            sobj = node_props(study)
            ftags = tags(study.feature())
            features = {}
            if isinstance(ftags, list):
                for ftag in ftags:
                    features[ftag] = node_props(study.feature(ftag))
            sobj["features"] = features
            out["studies"][stag] = sobj
    return out


data = {key: extract_model(key, path) for key, path in FILES.items()}
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
Path(OUT).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
_result = {"ok": True, "out": OUT, "models": list(data)}
