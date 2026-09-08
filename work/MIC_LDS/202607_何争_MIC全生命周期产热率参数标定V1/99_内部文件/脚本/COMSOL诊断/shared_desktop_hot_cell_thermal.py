"""Shared Desktop demo: add heat-transfer physics, solve, and create a 3D plot."""
import jpype


comp = model.component("comp1")
geom = comp.geom("geom1")

# Effective thermal material. Keep it simple and robust for a live demo.
mat = comp.material().create("mat1", "Common")
mat.label("Effective cell stack material")
mat.selection().all()
mat.propertyGroup("def").set("density", "2200[kg/m^3]")
mat.propertyGroup("def").set("heatcapacity", "950[J/(kg*K)]")
mat.propertyGroup("def").set(
    "thermalconductivity",
    jpype.JArray(str)([
        "1.5[W/(m*K)]", "0", "0",
        "0", "15[W/(m*K)]", "0",
        "0", "0", "1.5[W/(m*K)]",
    ]),
)

# Heat transfer physics.
ht = comp.physics().create("ht", "HeatTransfer", "geom1")
hs = ht.create("hs1", "HeatSource", 3)
hs.label("Agent-inserted volumetric heat generation")
hs.selection().all()
hs.set("Q0", "2e5[W/m^3]")

temp = ht.create("temp1", "TemperatureBoundary", 2)
temp.label("Ambient temperature boundary")
temp.selection().all()
temp.set("T0", "293.15[K]")

# Mesh and stationary study.
mesh = comp.mesh().create("mesh1")
mesh.autoMeshSize(4)
mesh.run()

model.study().create("std1")
model.study("std1").create("stat", "Stationary")
model.study("std1").run()

# Result: 3D temperature surface plot. The Desktop should show the result tree
# and can render it if the plot is selected.
model.result().create("pg_temp", "PlotGroup3D")
model.result("pg_temp").label("Agent generated 3D temperature field")
model.result("pg_temp").set("data", "dset1")
model.result("pg_temp").create("surf1", "Surface")
model.result("pg_temp").feature("surf1").set("expr", "T")
model.result("pg_temp").feature("surf1").set("unit", "K")
model.result("pg_temp").run()

model.save(r"D:\Users\hez\Desktop\hithium\COMSOL\reports\Agent_SharedDesktop_HotCell_Demo.mph")

_result = {
    "status": "ok",
    "stage": "thermal_solve",
    "message": "Added heat-transfer physics, meshed, solved stationary thermal model, and created a 3D temperature plot.",
    "physics": [str(x) for x in comp.physics().tags()],
    "studies": [str(x) for x in model.study().tags()],
    "results": [str(x) for x in model.result().tags()],
}
