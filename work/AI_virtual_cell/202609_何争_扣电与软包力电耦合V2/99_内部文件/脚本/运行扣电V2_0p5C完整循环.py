from com.comsol.model.util import ModelUtil

SOURCE = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_0p5C_100N完整耦合_可计算.mph"
OUTPUT = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_0p5C_100N完整耦合_已计算.mph"
PROGRESS = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\99_内部文件\运行记录\扣电V2_0p5C完整循环进度.log"
TAG = "coin_full_cycle"

try: ModelUtil.remove(TAG)
except Exception: pass
ModelUtil.showProgress(PROGRESS)
model = ModelUtil.load(TAG, SOURCE)
model.study("std_v9").feature("time").set("tlist", "range(0,60,18000)")
model.sol("sol3").feature("t1").set("tlist", "range(0,60,18000)")
model.sol("sol3").feature("t1").set("initialstepbdf", "0.1[s]")
model.sol("sol3").feature("t1").set("initialstepbdfactive", "on")
model.study("std_v9").run()
times = list(model.sol("sol3").getPVals())
print("full_cycle", "success", "n_times", len(times), "t_first", times[0], "t_last", times[-1])
model.save(OUTPUT)
print("saved", OUTPUT)
ModelUtil.remove(TAG)
ModelUtil.showProgress(False)
