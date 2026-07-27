"""Shared Desktop demo: live-update heat generation and rerun."""
comp = model.component("comp1")
ht = comp.physics("ht")

ht.feature("hs1").set("Q0", "8e5[W/m^3]")
ht.feature("hs1").label("Agent-updated heat generation: 4x")

model.study("std1").run()
model.result("pg_temp").label("Agent updated 3D temperature field - 4x heat")
model.result("pg_temp").run()
model.save(r"D:\Users\hez\Desktop\hithium\COMSOL\reports\Agent_SharedDesktop_HotCell_Demo_4xHeat.mph")

_result = {
    "status": "ok",
    "stage": "live_update",
    "message": "Updated volumetric heat generation from 2e5 to 8e5 W/m^3, reran the study, and refreshed the 3D temperature plot.",
    "heat_source": "8e5[W/m^3]",
}
