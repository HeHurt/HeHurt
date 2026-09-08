import json
from com.comsol.model.util import ModelUtil

MODEL = r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包统一极片设计力电耦合V1\02_模型\软包_统一极片设计_0p5C_同名义压力_完整耦合_待计算.mph"
TAG = "pouch_clear_old_solution"
try:
    ModelUtil.remove(TAG)
except Exception:
    pass
model = ModelUtil.load(TAG, MODEL)
states = {}
for soltag in model.sol().tags():
    soltag = str(soltag)
    model.sol(soltag).clearSolutionData()
    states[soltag] = bool(model.sol(soltag).isEmpty())
model.save(MODEL)
ModelUtil.remove(TAG)
print("MPH_TOOL_RESULT_BEGIN")
print(json.dumps({"ok": True, "model": MODEL, "solutions_empty": states}, ensure_ascii=False))
print("MPH_TOOL_RESULT_END")
