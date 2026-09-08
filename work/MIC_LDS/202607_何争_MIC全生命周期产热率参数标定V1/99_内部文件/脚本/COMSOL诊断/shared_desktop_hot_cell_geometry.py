"""Shared Desktop demo: build a 3D pouch-cell-like hot-cell geometry."""
import jpype


def safe_remove(tag):
    try:
        model.component().remove(tag)
    except Exception:
        pass


model.label("Agent_SharedDesktop_HotCell_Demo.mph")
model.modelPath(r"D:\Users\hez\Desktop\hithium\COMSOL\reports")

safe_remove("comp1")
comp = model.component().create("comp1", True)
geom = comp.geom().create("geom1", 3)
geom.lengthUnit("mm")

# Main jelly-roll / electrode stack body.
body = geom.create("cell_body", "Block")
body.label("Pouch cell body / JR stack")
body.set("size", jpype.JArray(jpype.JDouble)([220.0, 120.0, 12.0]))
body.set("pos", jpype.JArray(jpype.JDouble)([0.0, 0.0, 0.0]))

# Visual layer stripes across thickness, useful in Desktop Model Builder/Graphics.
for i in range(8):
    layer = geom.create(f"layer_{i+1}", "Block")
    layer.label(f"Visual layer {i+1}")
    layer.set("size", jpype.JArray(jpype.JDouble)([220.0, 120.0, 0.45]))
    layer.set("pos", jpype.JArray(jpype.JDouble)([0.0, 0.0, 1.0 + i * 1.25]))

# Positive and negative tabs.
tab_p = geom.create("tab_pos", "Block")
tab_p.label("Positive Al tab")
tab_p.set("size", jpype.JArray(jpype.JDouble)([18.0, 42.0, 3.0]))
tab_p.set("pos", jpype.JArray(jpype.JDouble)([202.0, 78.0, 12.0]))

tab_n = geom.create("tab_neg", "Block")
tab_n.label("Negative Cu tab")
tab_n.set("size", jpype.JArray(jpype.JDouble)([18.0, 42.0, 3.0]))
tab_n.set("pos", jpype.JArray(jpype.JDouble)([0.0, 0.0, 12.0]))

# Hotspot marker on the surface, representing a local high current density zone.
hot = geom.create("hotspot", "Block")
hot.label("Agent-inserted local hotspot marker")
hot.set("size", jpype.JArray(jpype.JDouble)([35.0, 28.0, 1.0]))
hot.set("pos", jpype.JArray(jpype.JDouble)([92.0, 46.0, 15.3]))

geom.run()

_result = {
    "status": "ok",
    "stage": "geometry",
    "message": "Built pouch cell body, 8 visual layers, tabs, and hotspot marker in shared COMSOL Desktop.",
    "model_tag": str(model.tag()),
    "components": [str(x) for x in model.component().tags()],
    "geometry_features": [str(x) for x in geom.feature().tags()],
}
