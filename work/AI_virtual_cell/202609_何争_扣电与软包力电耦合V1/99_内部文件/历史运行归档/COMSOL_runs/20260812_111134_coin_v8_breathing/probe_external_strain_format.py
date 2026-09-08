import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\external_strain_format_probe.json")
TAG = "coin_v8_external_strain_format"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "trials": {}}
try:
    parent = model.component("comp1").physics("solid").feature("lemm1")
    tests = {
        "scalar": "0.01",
        "vector3": ["0", "0", "0.01"],
        "vector6": ["0", "0", "0.01", "0", "0", "0"],
        "matrix3": [["0", "0", "0"], ["0", "0", "0"], ["0", "0", "0.01"]],
    }
    for index, (name, value) in enumerate(tests.items()):
        tag = f"__v8_ext_{index}"
        remove(parent.feature(), tag)
        node = parent.feature().create(tag, "ExternalStrain", 2)
        node.selection().set([4])
        try:
            node.set("eext_src", "userdef")
            node.set("eext", value)
            payload["trials"][name] = {
                "ok": True,
                "getString": jsonable(node.getString("eext")),
                "getStringArray": jsonable(node.getStringArray("eext")),
                "getStringMatrix": jsonable(node.getStringMatrix("eext")),
            }
        except Exception as exc:
            payload["trials"][name] = {"ok": False, "error": str(exc)}
        finally:
            remove(parent.feature(), tag)
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
