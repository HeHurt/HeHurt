import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V2.mph"
SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_104515_coin_geometry_fixed_v2\isolation_results.json")


def run_case(tag, use_charge_function):
    model = ModelUtil.load(tag, MODEL)
    try:
        comp = model.component("comp1")
        liion = comp.physics("liion")
        neg_function = "ocv_gr_charge" if use_charge_function else "ocv_gr_discharge"
        liion.feature("pce1").feature("per1").set(
            "Eeq", neg_function + "(liion.cs_surface/liion.csmax)"
        )
        liion.feature("init1").set("phil", "-mat1.def.Eeq(socini_neg)")
        liion.feature("init4").set("phil", "-mat1.def.Eeq(socini_neg)")
        liion.feature("init4").set("phis", "mat2.def.Eeq(socini_pos)-mat1.def.Eeq(socini_neg)")
        liion.feature("init3").set("phis", "mat2.def.Eeq(socini_pos)-0.04[V]-mat1.def.Eeq(socini_neg)")
        comp.variable("var1").set("C", "0.01")
        mesh = comp.mesh("mesh1")
        try:
            model.result().table("tbl1").clearTableData()
        except Exception:
            pass
        model.study("std1").feature("time").set("tlist", "range(0,1,10)")
        model.study("std1").run()
        rows = model.result().table("tbl1").getReal()
        return {
            "ok": True,
            "negative_ocv": neg_function,
            "elements": int(mesh.getNumElem()),
            "first": [float(value) for value in rows[0]],
            "last": [float(value) for value in rows[-1]],
        }
    except Exception as exc:
        return {
            "ok": False,
            "negative_ocv": neg_function,
            "error": str(exc),
        }
    finally:
        ModelUtil.remove(tag)


def run_original():
    tag = "coin_v2_isolate_original"
    model = ModelUtil.load(tag, SOURCE)
    try:
        try:
            model.result().table("tbl1").clearTableData()
        except Exception:
            pass
        model.study("std1").feature("time").set("tlist", "range(0,1,10)")
        model.study("std1").run()
        rows = model.result().table("tbl1").getReal()
        return {"ok": True, "case": "untouched_source", "first": [float(v) for v in rows[0]], "last": [float(v) for v in rows[-1]]}
    except Exception as exc:
        return {"ok": False, "case": "untouched_source", "error": str(exc)}
    finally:
        ModelUtil.remove(tag)


def run_rebuilt(path, tag, case):
    model = ModelUtil.load(tag, path)
    try:
        try:
            model.result().table("tbl1").clearTableData()
        except Exception:
            pass
        model.study("std1").feature("time").set("tlist", "range(0,1,10)")
        try:
            model.sol().remove("sol1")
        except Exception:
            pass
        model.study("std1").run()
        rows = model.result().table("tbl1").getReal()
        return {"ok": True, "case": case, "first": [float(v) for v in rows[0]], "last": [float(v) for v in rows[-1]]}
    except Exception as exc:
        return {"ok": False, "case": case, "error": str(exc)}
    finally:
        ModelUtil.remove(tag)


results = [
    run_original(),
    run_rebuilt(SOURCE, "coin_v2_rebuilt_source", "source_rebuilt_solver"),
    run_rebuilt(MODEL, "coin_v2_rebuilt_output", "v2_rebuilt_solver"),
    run_case("coin_v2_isolate_discharge", False),
    run_case("coin_v2_isolate_charge", True),
]
OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False))
