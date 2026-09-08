import json
from collections import Counter
from pathlib import Path

from com.comsol.model.util import ModelUtil


SOURCE = Path(r"D:\Users\hez\Desktop\mic\长时储能CW363-极片增高对能效差异_CW363设计参数.mph")
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260818_cw363_mesh_rebuild\mesh_audit.json")
MODEL_TAG = "cw363_mesh_audit"


def tags(manager):
    try:
        return [str(value) for value in manager.tags()]
    except Exception:
        return []


def get_node(manager, tag):
    try:
        return manager.get(tag)
    except Exception:
        return manager(tag)


def to_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [to_jsonable(item) for item in value]
    except TypeError:
        return str(value)


def read_property(node, name):
    for method in ("getString", "getStringArray", "getStringMatrix", "getBoolean", "getDouble"):
        try:
            return to_jsonable(getattr(node, method)(name))
        except Exception:
            continue
    return None


def selection_info(node):
    try:
        selection = node.selection()
        return {
            "dim": int(selection.dim()),
            "entities": [int(value) for value in selection.entities()],
            "geom": str(selection.geom()),
        }
    except Exception:
        return None


def feature_tree(manager):
    report = {}
    for feature_tag in tags(manager):
        node = get_node(manager, feature_tag)
        item = {
            "type": str(node.getType()),
            "label": str(node.label()),
        }
        selection = selection_info(node)
        if selection is not None:
            item["selection"] = selection
        for method, key in (("status", "status"), ("message", "message")):
            try:
                item[key] = str(getattr(node, method)())
            except Exception:
                pass
        properties = {}
        try:
            property_names = [str(value) for value in node.properties()]
        except Exception:
            property_names = []
        for name in property_names:
            value = read_property(node, name)
            if value not in (None, "", []):
                properties[name] = value
        if properties:
            item["properties"] = properties
        try:
            children = feature_tree(node.feature())
            if children:
                item["features"] = children
        except Exception:
            pass
        report[feature_tag] = item
    return report


try:
    ModelUtil.remove(MODEL_TAG)
except Exception:
    pass

model = ModelUtil.load(MODEL_TAG, str(SOURCE))
try:
    report = {"source": str(SOURCE), "components": {}}
    for component_tag in tags(model.component()):
        component = model.component(component_tag)
        component_report = {"geometries": {}, "meshes": {}, "physics_selections": {}}
        for geometry_tag in tags(component.geom()):
            geometry = component.geom(geometry_tag)
            geometry_report = {"label": str(geometry.label())}
            for dim, name in ((0, "points"), (1, "edges"), (2, "boundaries"), (3, "domains")):
                try:
                    geometry_report[name] = int(geometry.getNEntities(dim))
                except Exception:
                    pass
            component_report["geometries"][geometry_tag] = geometry_report
        for physics_tag in tags(component.physics()):
            physics = component.physics(physics_tag)
            component_report["physics_selections"][physics_tag] = {
                "label": str(physics.label()),
                "selection": selection_info(physics),
            }
        for mesh_tag in tags(component.mesh()):
            mesh = component.mesh(mesh_tag)
            mesh_report = {
                "label": str(mesh.label()),
                "is_empty": bool(mesh.isEmpty()),
                "is_complete": bool(mesh.isComplete()),
                "has_problems": bool(mesh.hasProblems()),
                "problems": [str(value) for value in mesh.problems()],
                "features": feature_tree(mesh.feature()),
            }
            if not mesh.isEmpty():
                mesh_types = [str(value) for value in mesh.getTypes()]
                mesh_report["types"] = mesh_types
                mesh_report["num_elements"] = int(mesh.getNumElem())
                mesh_report["entity_counts"] = {}
                for mesh_type in mesh_types:
                    entities = [int(value) for value in mesh.getElemEntity(mesh_type)]
                    mesh_report["entity_counts"][mesh_type] = {
                        str(entity): int(count)
                        for entity, count in sorted(Counter(entities).items())
                    }
            component_report["meshes"][mesh_tag] = mesh_report
        report["components"][component_tag] = component_report
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(OUTPUT))
finally:
    ModelUtil.remove(MODEL_TAG)
