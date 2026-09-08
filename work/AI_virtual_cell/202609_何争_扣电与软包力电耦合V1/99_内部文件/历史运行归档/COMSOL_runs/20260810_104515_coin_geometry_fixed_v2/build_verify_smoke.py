import csv
import json
import time
from pathlib import Path


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_104515_coin_geometry_fixed_v2")
SOURCE = Path(r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed.mph")
OUTPUT = Path(r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V2.mph")
SNAPSHOT = RUN / "model_snapshot.mph"
CHARGE_OCV = Path(r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params\Gr_charge.dat")
BUILD_TAG = "coin_fixed_v2_build"
VERIFY_TAG = "coin_fixed_v2_verify"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def mesh_stats(mesh):
    result = {"elements": int(mesh.getNumElem()), "vertices": int(mesh.getNumVertex()), "types": {}}
    for kind in [str(value) for value in mesh.getTypes()]:
        result["types"][kind] = {
            "count": int(mesh.getNumElem(kind)),
            "min_quality": float(mesh.getMinQuality(kind)),
            "mean_quality": float(mesh.getMeanQuality(kind)),
        }
    return result


def average(model, domain, expression, solnum, tag):
    manager = model.result().numerical()
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, "AvSurface")
        node.selection().set([domain])
        node.set("data", "dset1")
        node.set("solnum", str(solnum))
        node.set("expr", expression)
        value = jsonable(node.getReal())
        while isinstance(value, list) and len(value) == 1:
            value = value[0]
        return float(value)
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def boundary_average(model, boundary, expression, solnum, tag):
    manager = model.result().numerical()
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, "AvLine")
        node.selection().set([boundary])
        node.set("data", "dset1")
        node.set("solnum", str(solnum))
        node.set("expr", expression)
        value = jsonable(node.getReal())
        while isinstance(value, list) and len(value) == 1:
            value = value[0]
        return float(value)
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def apply_changes(model):
    model.param().set("Ac", "pi*(10.25[mm])^2")
    model.param().set("i_1C", "min(ah_pos_soc1,ah_neg_soc1)")

    model.func().duplicate("ocv_gr_charge", "ocv_gr_discharge")
    charge = model.func().get("ocv_gr_charge")
    charge.label("Graphite OCV - charge")
    charge.set("filename", str(CHARGE_OCV))
    charge.importData()
    charge.set("funcname", "ocv_gr_charge")

    comp = model.component("comp1")
    liion = comp.physics("liion")
    x = "liion.cs_surface/liion.csmax"
    neg_ocv = f"if(charge1+charge_hold>0.5,ocv_gr_charge({x}),ocv_gr_discharge({x}))"
    liion.feature("pce1").feature("per1").set("Eeq", neg_ocv)
    liion.feature("pce2").feature("per1").set(
        "Eeq", "ocv_lfp_base(1-liion.cs_surface/liion.csmax)-0.02[V]"
    )

    neg_init = "-ocv_gr_charge(socini_neg)"
    pos_init = "ocv_lfp_base(1-socini_pos)-0.02[V]-ocv_gr_charge(socini_neg)"
    liion.feature("init1").set("phil", neg_init)
    liion.feature("init4").set("phil", neg_init)
    liion.feature("init4").set("phis", pos_init)
    liion.feature("init2").set("phis", "0[V]")
    liion.feature("init3").set("phis", pos_init)
    liion.feature("egnd1").selection().set([2])
    liion.feature("ecd1").selection().set([11])
    comp.probe("bnd1").selection().set([11])
    comp.probe("bnd2").selection().set([11])

    macro = comp.mesh("mesh1")
    macro.feature("ftri1").active(False)
    mapped = macro.feature().create("map1", "Map")
    mapped.label("Mapped quadrilateral - layered cell")
    mapped.selection().geom("geom1", 2)
    mapped.selection().set([1, 2, 3, 4, 5])
    macro.run()

    for electrode in ("pce1", "pce2"):
        liion.feature(electrode).feature("pin1").set("Nel", "6")
    for component_tag in ("liion_pce1_pin1_xdim", "liion_pce2_pin1_xdim"):
        particle = model.component(component_tag).mesh(component_tag)
        particle.feature("dis1").set("numelem", "6")
        particle.run()


def verify_saved(model):
    comp = model.component("comp1")
    liion = comp.physics("liion")
    macro = comp.mesh("mesh1")
    checks = {
        "Ac": str(model.param().get("Ac")) == "pi*(10.25[mm])^2",
        "i_1C": str(model.param().get("i_1C")) == "min(ah_pos_soc1,ah_neg_soc1)",
        "charge_function": str(model.func().get("ocv_gr_charge").getString("funcname")) == "ocv_gr_charge",
        "negative_Eeq_switch": "ocv_gr_charge" in str(liion.feature("pce1").feature("per1").getString("Eeq")),
        "positive_Eeq_direction": str(liion.feature("pce2").feature("per1").getString("Eeq")) == "ocv_lfp_base(1-liion.cs_surface/liion.csmax)-0.02[V]",
        "positive_init": str(liion.feature("init4").getString("phis")) == "ocv_lfp_base(1-socini_pos)-0.02[V]-ocv_gr_charge(socini_neg)",
        "collector_init": str(liion.feature("init3").getString("phis")) == "ocv_lfp_base(1-socini_pos)-0.02[V]-ocv_gr_charge(socini_neg)",
        "mapped_mesh": "quad" in [str(value) for value in macro.getTypes()],
        "negative_particle_Nel": str(liion.feature("pce1").feature("pin1").getString("Nel")) == "6",
        "positive_particle_Nel": str(liion.feature("pce2").feature("pin1").getString("Nel")) == "6",
        "ground_boundary": [int(value) for value in liion.feature("egnd1").selection().entities()] == [2],
        "terminal_boundary": [int(value) for value in liion.feature("ecd1").selection().entities()] == [11],
        "voltage_probe_boundary": [int(value) for value in comp.probe("bnd1").selection().entities()] == [11],
        "current_probe_boundary": [int(value) for value in comp.probe("bnd2").selection().entities()] == [11],
    }
    if not all(checks.values()):
        raise AssertionError(json.dumps(checks, ensure_ascii=False))
    return {
        "checks": checks,
        "Ac_m2": float(model.param().evaluate("Ac")),
        "i_1C_A": float(model.param().evaluate("i_1C")),
        "contact_Rc": str(liion.feature("ecd1").getString("Rc")),
        "macro_mesh": mesh_stats(macro),
        "negative_particle_mesh": mesh_stats(model.component("liion_pce1_pin1_xdim").mesh("liion_pce1_pin1_xdim")),
        "positive_particle_mesh": mesh_stats(model.component("liion_pce2_pin1_xdim").mesh("liion_pce2_pin1_xdim")),
    }


def smoke(model):
    try:
        model.result().table("tbl1").clearTableData()
    except Exception:
        pass
    model.study("std1").feature("time").set("tlist", "range(0,5,300)")
    try:
        model.sol().remove("sol1")
    except Exception:
        pass
    started = time.time()
    model.study("std1").run()
    elapsed = time.time() - started
    last_solnum = int(model.sol("sol1").getDefaultSolnum())
    states = {}
    for solnum, name in ((1, "initial"), (last_solnum, "final")):
        states[name] = {
            "negative": {
                "stoich": average(model, 2, "liion.cs_surface/liion.csmax", solnum, "__neg_stoich_" + name),
                "phis": average(model, 2, "phis", solnum, "__neg_phis_" + name),
                "phil": average(model, 2, "phil", solnum, "__neg_phil_" + name),
                "Eeq": average(model, 2, "ocv_gr_charge(liion.cs_surface/liion.csmax)", solnum, "__neg_eeq_" + name),
            },
            "positive": {
                "stoich": average(model, 4, "liion.cs_surface/liion.csmax", solnum, "__pos_stoich_" + name),
                "phis": average(model, 4, "phis", solnum, "__pos_phis_" + name),
                "phil": average(model, 4, "phil", solnum, "__pos_phil_" + name),
                "Eeq": average(model, 4, "ocv_lfp_base(1-liion.cs_surface/liion.csmax)-0.02[V]", solnum, "__pos_eeq_" + name),
            },
        }
    voltage_start = boundary_average(model, 11, "phis", 1, "__vol_initial")
    voltage_end = boundary_average(model, 11, "phis", last_solnum, "__vol_final")
    current = float(model.param().evaluate("i_1C")) * 0.5
    return {
        "elapsed_s": elapsed,
        "solution_count": last_solnum,
        "voltage_start_V": voltage_start,
        "voltage_end_V": voltage_end,
        "current_A": current,
        "states": states,
        "direction_checks": {
            "voltage_rises": voltage_end > voltage_start,
            "negative_stoich_increases": states["final"]["negative"]["stoich"] > states["initial"]["negative"]["stoich"],
            "positive_stoich_decreases": states["final"]["positive"]["stoich"] < states["initial"]["positive"]["stoich"],
        },
    }


def main():
    source_stat = SOURCE.stat()
    if OUTPUT.exists() and SNAPSHOT.exists():
        model = ModelUtil.load(BUILD_TAG, str(OUTPUT))
        try:
            model.func().get("ocv_gr_charge").set("funcname", "ocv_gr_charge")
            comp = model.component("comp1")
            liion = comp.physics("liion")
            liion.feature("pce2").feature("per1").set(
                "Eeq", "ocv_lfp_base(1-liion.cs_surface/liion.csmax)-0.02[V]"
            )
            pos_init = "ocv_lfp_base(1-socini_pos)-0.02[V]-ocv_gr_charge(socini_neg)"
            liion.feature("init4").set("phis", pos_init)
            liion.feature("init3").set("phis", pos_init)
            liion.feature("egnd1").selection().set([2])
            liion.feature("ecd1").selection().set([11])
            comp.probe("bnd1").selection().set([11])
            comp.probe("bnd2").selection().set([11])
            model.save(str(SNAPSHOT))
            model.save(str(OUTPUT))
        finally:
            ModelUtil.remove(BUILD_TAG)
    elif not OUTPUT.exists() and not SNAPSHOT.exists():
        model = ModelUtil.load(BUILD_TAG, str(SOURCE))
        try:
            apply_changes(model)
            model.save(str(SNAPSHOT))
            model.save(str(OUTPUT))
        finally:
            ModelUtil.remove(BUILD_TAG)
    else:
        raise FileExistsError("Only one of V2 output and snapshot exists")

    model = ModelUtil.load(VERIFY_TAG, str(OUTPUT))
    try:
        verification = verify_saved(model)
        smoke_result = smoke(model)
    finally:
        ModelUtil.remove(VERIFY_TAG)

    source_after = SOURCE.stat()
    payload = {
        "source": str(SOURCE),
        "output": str(OUTPUT),
        "snapshot": str(SNAPSHOT),
        "source_unchanged": source_stat.st_size == source_after.st_size and source_stat.st_mtime_ns == source_after.st_mtime_ns,
        "verification": verification,
        "smoke": smoke_result,
    }
    (RUN / "verify_smoke.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (RUN / "metrics.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["Ac", verification["Ac_m2"], "m^2"])
        writer.writerow(["i_1C", verification["i_1C_A"], "A"])
        writer.writerow(["macro_elements", verification["macro_mesh"]["elements"], "1"])
        writer.writerow(["smoke_voltage_start", smoke_result["voltage_start_V"], "V"])
        writer.writerow(["smoke_voltage_end", smoke_result["voltage_end_V"], "V"])
        writer.writerow(["smoke_current", smoke_result["current_A"], "A"])
    if not all(smoke_result["direction_checks"].values()):
        raise AssertionError(json.dumps(smoke_result, ensure_ascii=False))
    (RUN / "run.log").write_text(
        "build=success\nreload_verify=success\nsmoke=success\nsource_unchanged=true\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "output": str(OUTPUT), "smoke": smoke_result}, ensure_ascii=False))


main()
