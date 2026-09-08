from com.comsol.model.util import ModelUtil

SOURCE = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_0p5C_100N完整耦合_计算版.mph"
OUTPUT = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_0p5C_100N完整耦合_可计算.mph"

for tag in ["probe_fix", "probe_verify"]:
    try: ModelUtil.remove(tag)
    except Exception: pass
model = ModelUtil.load("probe_fix", SOURCE)
c = model.component("comp1")
c.probe("bnd1").selection().set([2])
c.probe("bnd2").selection().set([2])
for soltag in model.sol().tags(): model.sol(soltag).clearSolutionData()
model.save(OUTPUT)
ModelUtil.remove("probe_fix")
check = ModelUtil.load("probe_verify", OUTPUT); cc=check.component("comp1")
print("saved",OUTPUT)
print("voltage_probe",list(cc.probe("bnd1").selection().entities()),cc.probe("bnd1").getString("expr"))
print("current_probe",list(cc.probe("bnd2").selection().entities()),cc.probe("bnd2").getString("expr"))
print("vol_loaded",cc.variable("var1").get("vol_loaded"))
print("mesh",cc.mesh("mesh1").getNumElem())
ModelUtil.remove("probe_verify")
