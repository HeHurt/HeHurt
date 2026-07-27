from pathlib import Path


FILES = {
    "charge": r"D:\Users\hez\Desktop\mic\MICCW363-充电产热.mph",
    "discharge": r"D:\Users\hez\Desktop\mic\MICCW363-放电产热.mph",
}


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
    # COMSOL nodes expose different getters depending on the property type.
    for method in ("getString", "get", "getStringArray"):
        try:
            return jstr(getattr(node, method)(prop))
        except Exception:
            continue
    return {"error": "unreadable_property"}


def node_summary(node, max_props=200):
    props = safe("properties", lambda: [str(x) for x in node.properties()])
    out = {
        "type": safe("getType", lambda: str(node.getType())),
        "name": safe("name", lambda: str(node.name())),
        "properties": props,
    }
    if isinstance(props, list):
        values = {}
        for prop in props[:max_props]:
            values[prop] = get_prop(node, prop)
        out["property_values"] = values
    return out


def variable_summary(varnode):
    names = safe("varnames", lambda: [str(x) for x in varnode.varnames()])
    out = node_summary(varnode)
    out["varnames"] = names
    if isinstance(names, list):
        out["definitions"] = {}
        for name in names:
            out["definitions"][name] = safe(f"var:{name}", lambda name=name: jstr(varnode.get(name)))
            out["definitions"][name + ":descr"] = safe(
                f"descr:{name}", lambda name=name: jstr(varnode.descr(name))
            )
    return out


def table_summary(container):
    out = {}
    ts = tags(container)
    if not isinstance(ts, list):
        return ts
    for tag in ts:
        node = child(container, tag)
        out[tag] = node_summary(node)
    return out


def model_summary(model):
    out = {
        "tag": str(model.tag()),
        "label": safe("label", lambda: str(model.label())),
        "model_path": safe("modelPath", lambda: str(model.modelPath())),
        "parameters": {},
        "global_functions": {},
        "global_variables": {},
        "components": {},
        "studies": {},
        "results": {},
    }

    pnames = safe("param.varnames", lambda: [str(x) for x in model.param().varnames()])
    out["parameters"]["varnames"] = pnames
    if isinstance(pnames, list):
        vals = {}
        for name in pnames:
            vals[name] = {
                "expr": safe(f"param.get:{name}", lambda name=name: jstr(model.param().get(name))),
                "descr": safe(f"param.descr:{name}", lambda name=name: jstr(model.param().descr(name))),
            }
        out["parameters"]["values"] = vals

    out["global_functions"] = table_summary(model.func())
    out["global_variables"]["tags"] = safe("model.variable.tags", lambda: [str(x) for x in model.variable().tags()])
    if isinstance(out["global_variables"]["tags"], list):
        out["global_variables"]["nodes"] = {}
        for tag in out["global_variables"]["tags"]:
            out["global_variables"]["nodes"][tag] = variable_summary(model.variable(tag))

    ctags = tags(model.component())
    if isinstance(ctags, list):
        for ctag in ctags:
            comp = model.component(ctag)
            c = {
                "geom": tags(comp.geom()),
                "mesh": tags(comp.mesh()),
                "materials": {},
                "physics": {},
                "variables": {},
                "functions": {},
            }
            c["functions"] = table_summary(comp.func())
            mtags = tags(comp.material())
            if isinstance(mtags, list):
                for mtag in mtags:
                    c["materials"][mtag] = node_summary(comp.material(mtag))
            ptags = tags(comp.physics())
            if isinstance(ptags, list):
                for ptag in ptags:
                    phys = comp.physics(ptag)
                    ps = node_summary(phys)
                    ftags = tags(phys.feature())
                    ps["features"] = {}
                    if isinstance(ftags, list):
                        for ftag in ftags:
                            ps["features"][ftag] = node_summary(phys.feature(ftag))
                    c["physics"][ptag] = ps
            vtags = safe(f"{ctag}.variable.tags", lambda comp=comp: [str(x) for x in comp.variable().tags()])
            c["variables"]["tags"] = vtags
            if isinstance(vtags, list):
                c["variables"]["nodes"] = {}
                for vtag in vtags:
                    c["variables"]["nodes"][vtag] = variable_summary(comp.variable(vtag))
            out["components"][ctag] = c

    stags = tags(model.study())
    if isinstance(stags, list):
        for stag in stags:
            study = model.study(stag)
            ss = node_summary(study)
            ftags = tags(study.feature())
            ss["features"] = {}
            if isinstance(ftags, list):
                for ftag in ftags:
                    ss["features"][ftag] = node_summary(study.feature(ftag))
            out["studies"][stag] = ss

    rtags = tags(model.result())
    if isinstance(rtags, list):
        for rtag in rtags:
            out["results"][rtag] = node_summary(model.result(rtag))

    return out


def flatten(obj, prefix=""):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            rows.extend(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            rows.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        rows.append((prefix, str(obj)))
    return rows


def keyword_hits(summary):
    keywords = [
        "heat", "Heat", "Q", "q_", "q0", "Q0", "Qh", "qohm", "irreversible",
        "reversible", "rev", "dUdT", "dEdT", "entropy", "entropic", "T*d", "I*",
        "soc", "SOC", "ocv", "OCV", "eta", "overpotential", "liion", "ht",
        "产热", "热", "修正", "补偿", "charge", "discharge", "充", "放",
        "C_rate", "crate", "Crate", "scale", "factor", "corr", "offset",
    ]
    hits = []
    for path, value in flatten(summary):
        text = f"{path} = {value}"
        if any(k in text for k in keywords):
            hits.append(text)
    return hits[:1200]


result = {}
for key, path in FILES.items():
    tag = f"miccw363_{key}"
    if tag in [str(x) for x in ModelUtil.tags()]:
        safe("remove", lambda tag=tag: ModelUtil.remove(tag))
    m = ModelUtil.load(tag, path)
    summary = model_summary(m)
    result[key] = {
        "path": path,
        "size": Path(path).stat().st_size,
        "summary": summary,
        "keyword_hits": keyword_hits(summary),
    }

_result = result
