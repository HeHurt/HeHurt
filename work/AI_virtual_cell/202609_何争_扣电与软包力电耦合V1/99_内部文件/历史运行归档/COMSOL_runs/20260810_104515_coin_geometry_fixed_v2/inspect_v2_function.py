import json


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V2.mph"
TAG = "inspect_coin_v2_function"


model = ModelUtil.load(TAG, MODEL)
try:
    node = model.func().get("ocv_gr_charge")
    values = {}
    for name in ("funcname", "funcs", "filename", "source"):
        for method in ("getStringMatrix", "getStringArray", "getString"):
            try:
                value = getattr(node, method)(name)
                if value is not None:
                    values[name] = str(value)
                    break
            except Exception:
                continue
    comp = model.component("comp1")
    probes = {}
    for probe_tag in [str(value) for value in comp.probe().tags()]:
        probe = comp.probe(probe_tag)
        item = {"properties": {}, "selection": {}}
        try:
            item["selection"]["named"] = str(probe.selection().named())
        except Exception:
            pass
        try:
            item["selection"]["entities"] = [int(value) for value in probe.selection().entities()]
        except Exception:
            item["selection"]["entities"] = []
        for name in [str(value) for value in probe.properties()]:
            for method in ("getStringMatrix", "getStringArray", "getString"):
                try:
                    value = getattr(probe, method)(name)
                    if value is not None:
                        item["properties"][name] = str(value)
                        break
                except Exception:
                    continue
        probes[probe_tag] = item
    for feature_tag in ("ecd1", "egnd1"):
        feature = comp.physics("liion").feature(feature_tag)
        probes[feature_tag] = {"selection": {}}
        try:
            probes[feature_tag]["selection"]["named"] = str(feature.selection().named())
        except Exception:
            pass
        try:
            probes[feature_tag]["selection"]["entities"] = [int(value) for value in feature.selection().entities()]
        except Exception:
            probes[feature_tag]["selection"]["entities"] = []
    mesh = comp.mesh("mesh1")
    mesh.run()
    vertices = [[float(value) for value in row] for row in mesh.getVertex()]
    edges = [[int(value) for value in row] for row in mesh.getElem("edg")]
    entities = [int(value) for value in mesh.getElemEntity("edg")]
    boundary_points = {}
    for index, entity in enumerate(entities):
        points = boundary_points.setdefault(str(entity), [])
        for row in edges:
            vertex_index = row[index]
            points.append([vertices[0][vertex_index], vertices[1][vertex_index]])
    boundary_extents = {}
    for entity, points in boundary_points.items():
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        boundary_extents[entity] = [min(xs), max(xs), min(ys), max(ys)]
    print(json.dumps({"function": values, "probes_and_terminals": probes, "boundary_extents": boundary_extents}, ensure_ascii=False))
finally:
    ModelUtil.remove(TAG)
