import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
OUTPUT = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5.mph"
RESULT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_115103_coin_v3_conductivity_fix\v5_build_verify.json")
BUILD_TAG = "coin_v5_current_density_build"
VERIFY_TAG = "coin_v5_current_density_verify"


model = ModelUtil.load(BUILD_TAG, SOURCE)
try:
    terminal = model.component("comp1").physics("liion").feature("ecd1")
    terminal.set("ElectronicCurrentType", "AverageCurrentDensity")
    terminal.set("Ias", "I/Ac")
    model.save(OUTPUT)
finally:
    ModelUtil.remove(BUILD_TAG)

model = ModelUtil.load(VERIFY_TAG, OUTPUT)
try:
    terminal = model.component("comp1").physics("liion").feature("ecd1")
    checks = {
        "current_type": str(terminal.getString("ElectronicCurrentType")) == "AverageCurrentDensity",
        "current_density": str(terminal.getString("Ias")) == "I/Ac",
        "terminal_boundary": [int(value) for value in terminal.selection().entities()] == [11],
    }
    if not all(checks.values()):
        raise AssertionError(json.dumps(checks, ensure_ascii=False))
    payload = {"source": SOURCE, "output": OUTPUT, "checks": checks}
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, **payload}, ensure_ascii=False))
finally:
    ModelUtil.remove(VERIFY_TAG)
