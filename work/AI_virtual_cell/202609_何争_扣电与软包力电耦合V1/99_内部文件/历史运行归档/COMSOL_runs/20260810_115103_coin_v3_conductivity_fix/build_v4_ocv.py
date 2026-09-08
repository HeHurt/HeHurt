import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V3.mph"
OUTPUT = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
LFP_FILE = r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params\LFP.dat"
RESULT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_115103_coin_v3_conductivity_fix\v4_build_verify.json")
BUILD_TAG = "coin_v4_ocv_build"
VERIFY_TAG = "coin_v4_ocv_verify"


def feature_text(node, name):
    return str(node.getString(name))


model = ModelUtil.load(BUILD_TAG, SOURCE)
try:
    lfp = model.func().get("ocv_lfp_base")
    lfp.set("filename", LFP_FILE)
    lfp.importData()
    lfp.set("funcname", "ocv_lfp_base")

    liion = model.component("comp1").physics("liion")
    positive_eeq = "ocv_lfp_base(liion.cs_surface/liion.csmax)+0.02[V]"
    positive_init = "ocv_lfp_base(socini_pos)+0.02[V]-ocv_gr_charge(socini_neg)"
    liion.feature("pce2").feature("per1").set("Eeq", positive_eeq)
    liion.feature("init4").set("phis", positive_init)
    liion.feature("init3").set("phis", positive_init)
    model.save(OUTPUT)
finally:
    ModelUtil.remove(BUILD_TAG)

model = ModelUtil.load(VERIFY_TAG, OUTPUT)
try:
    liion = model.component("comp1").physics("liion")
    checks = {
        "lfp_filename": feature_text(model.func().get("ocv_lfp_base"), "filename") == LFP_FILE,
        "lfp_funcname": feature_text(model.func().get("ocv_lfp_base"), "funcname") == "ocv_lfp_base",
        "positive_Eeq": feature_text(liion.feature("pce2").feature("per1"), "Eeq")
        == "ocv_lfp_base(liion.cs_surface/liion.csmax)+0.02[V]",
        "positive_electrode_init": feature_text(liion.feature("init4"), "phis")
        == "ocv_lfp_base(socini_pos)+0.02[V]-ocv_gr_charge(socini_neg)",
        "positive_collector_init": feature_text(liion.feature("init3"), "phis")
        == "ocv_lfp_base(socini_pos)+0.02[V]-ocv_gr_charge(socini_neg)",
        "negative_conductivity": feature_text(liion.feature("pce1"), "sigma") == "sigma_neg",
        "positive_conductivity": feature_text(liion.feature("pce2"), "sigma") == "sigma_pos",
    }
    if not all(checks.values()):
        raise AssertionError(json.dumps(checks, ensure_ascii=False))
    payload = {
        "source": SOURCE,
        "output": OUTPUT,
        "lfp_file": LFP_FILE,
        "checks": checks,
        "source_unchanged": True,
    }
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, **payload}, ensure_ascii=False))
finally:
    ModelUtil.remove(VERIFY_TAG)
