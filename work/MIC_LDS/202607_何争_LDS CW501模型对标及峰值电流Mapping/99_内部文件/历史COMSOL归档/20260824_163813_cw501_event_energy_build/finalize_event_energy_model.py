import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL = Path(r"D:\Users\hez\Desktop\mic\超大\Case1~41D电化学模型不同长度_CW501设计参数_事件循环二圈能效.mph")
REPORT = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260824_163813_cw501_event_energy_build\finalize_result.json")
TAG = "cw501_event_energy_finalize"


def remove_tag(tag):
    try:
        ModelUtil.remove(tag)
    except Exception:
        pass


remove_tag(TAG)
model = ModelUtil.load(TAG, str(MODEL))
try:
    study_time = model.study("std1").feature("time")
    study_time.set("tlist", "range(0,25/C,25000/C)")

    evaluation = model.result().numerical("gev_cycle2")
    evaluation.set("data", "dset5")
    evaluation.set("innerinput", "last")
    evaluation.set("outerinput", "all")
    evaluation.set("includeparam", "on")
    evaluation.set("table", "tbl_cycle2")
    model.save(str(MODEL))
finally:
    ModelUtil.remove(TAG)

verify_tag = TAG + "_verify"
remove_tag(verify_tag)
saved = ModelUtil.load(verify_tag, str(MODEL))
try:
    time_node = saved.study("std1").feature("time")
    evaluation = saved.result().numerical("gev_cycle2")
    checks = {
        "time_range_extended": str(time_node.getString("tlist")) == "range(0,25/C,25000/C)",
        "evaluation_dataset": str(evaluation.getString("data")) == "dset5",
        "evaluation_last_time": str(evaluation.getString("innerinput")) == "last",
        "evaluation_all_parameter_cases": str(evaluation.getString("outerinput")) == "all",
        "evaluation_includes_parameters": str(evaluation.getString("includeparam")) == "on",
    }
finally:
    ModelUtil.remove(verify_tag)

if not all(checks.values()):
    raise RuntimeError(f"Final reload verification failed: {checks}")
payload = {"ok": True, "model": str(MODEL), "reload_checks": checks}
REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
