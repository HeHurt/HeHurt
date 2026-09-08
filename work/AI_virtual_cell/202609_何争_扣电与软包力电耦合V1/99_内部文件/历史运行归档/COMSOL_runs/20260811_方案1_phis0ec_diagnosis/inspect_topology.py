import json
from pathlib import Path
from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\topology_result.json")
tag = "plan1_topology"

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
try:
    comp = model.component("comp1")
    geom_tags = [str(v) for v in comp.geom().tags()]
    report = {"geometry_tags": geom_tags, "features": {}}
    geom = comp.geom(geom_tags[0])
    report["geometry"] = {
        "tag": geom_tags[0],
        "sdim": int(geom.getSDim()),
        "n_entities": [int(v) for v in geom.getNEntities()],
        "n_domains": int(geom.getNDomains()),
        "n_boundaries": int(geom.getNBoundaries()),
    }
    liion = comp.physics("liion")
    for feature_tag in ["cc1", "cc2", "egnd1", "ec1", "ins1", "nf1"]:
        feature = liion.feature(feature_tag)
        selection = feature.selection()
        entities = [int(v) for v in selection.entities()]
        dim = int(selection.dim())
        item = {
            "label": str(feature.label()),
            "type": str(feature.getType()),
            "selection_geom": str(selection.geom()),
            "selection_dim": dim,
            "selection_dimensions": [int(v) for v in selection.dimension()],
            "entities": entities,
        }
        if dim == 2:
            item["adjacent_domains"] = {
                str(boundary): [int(v) for v in geom.getAdj(2, 3, boundary)]
                for boundary in entities
            }
        report["features"][feature_tag] = item
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
finally:
    ModelUtil.remove(tag)
