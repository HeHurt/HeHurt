import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
OUTPUT_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding\patch_result.json")
TAG = "coin_v5_patch"


EXPECTED = {
    "sigmal_mat": "userdef",
    "sigmal": "ely_sigma(cl)",
    "Dl_mat": "userdef",
    "Dl": "ely_D(cl)",
    "transpNum_mat": "userdef",
    "transpNum": "ely_tplus(cl)",
}


def read_properties(model):
    liion = model.component("comp1").physics("liion")
    return {
        tag: {prop: str(liion.feature(tag).getString(prop)) for prop in EXPECTED}
        for tag in ("pce1", "sep1", "pce2")
    }


model = ModelUtil.load(TAG, SOURCE)
try:
    liion = model.component("comp1").physics("liion")
    before = read_properties(model)
    for feature_tag in ("pce1", "sep1", "pce2"):
        node = liion.feature(feature_tag)
        for prop, value in EXPECTED.items():
            node.set(prop, value)
    after_in_memory = read_properties(model)
    model.save(OUTPUT_MODEL)
finally:
    ModelUtil.remove(TAG)

verify_tag = TAG + "_verify"
reloaded = ModelUtil.load(verify_tag, OUTPUT_MODEL)
try:
    after_reload = read_properties(reloaded)
    assertions = {
        feature_tag: {prop: after_reload[feature_tag][prop] == value for prop, value in EXPECTED.items()}
        for feature_tag in ("pce1", "sep1", "pce2")
    }
    ok = all(all(values.values()) for values in assertions.values())
finally:
    ModelUtil.remove(verify_tag)

payload = {
    "ok": ok,
    "source": SOURCE,
    "output_model": OUTPUT_MODEL,
    "before": before,
    "after_in_memory": after_in_memory,
    "after_reload": after_reload,
    "assertions": assertions,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
