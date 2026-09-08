import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V2.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_112022_coin_v2_voltage_diagnostic\diagnostic.json")


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def vector(value):
    value = jsonable(value)
    while isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list):
        return [float(value)]
    result = []
    for item in value:
        if isinstance(item, list):
            result.extend(float(entry) for entry in item)
        else:
            result.append(float(item))
    return result


def numerical_series(model, kind, expression, count, selection=None):
    manager = model.result().numerical()
    tag = "__diag_" + str(len(expression)) + "_" + kind
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, kind)
        if selection is not None:
            node.selection().set(selection)
        node.set("data", "dset1")
        node.set("expr", expression)
        values = []
        for solnum in range(1, count + 1):
            node.set("solnum", str(solnum))
            values.append(vector(node.getReal())[0])
        return values
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def first_last(series):
    return {"first": series[0], "last": series[-1], "count": len(series)}


def run_case(tag, rate, contact, end_time, keep_series=False):
    model = ModelUtil.load(tag, MODEL)
    try:
        comp = model.component("comp1")
        liion = comp.physics("liion")
        comp.variable("var1").set("C", str(rate))
        liion.feature("ecd1").set("IncludeContactResistance", "1" if contact else "0")
        try:
            model.result().table("tbl1").clearTableData()
        except Exception:
            pass
        model.study("std1").feature("time").set("tlist", f"range(0,1,{end_time})")
        try:
            model.sol().remove("sol1")
        except Exception:
            pass
        solve_error = None
        try:
            model.study("std1").run()
        except Exception as exc:
            solve_error = str(exc)

        sol = model.sol("sol1")
        times = [float(value) for value in sol.getPVals()]
        count = len(times)
        series = {
            "terminal_voltage": numerical_series(model, "AvLine", "phis", count, [11]),
            "positive_phis": numerical_series(model, "AvSurface", "phis", count, [4]),
            "negative_phis": numerical_series(model, "AvSurface", "phis", count, [2]),
            "positive_phil": numerical_series(model, "AvSurface", "phil", count, [4]),
            "negative_phil": numerical_series(model, "AvSurface", "phil", count, [2]),
            "positive_surface_stoich_avg": numerical_series(
                model, "AvSurface", "liion.cs_surface/liion.csmax", count, [4]
            ),
            "positive_surface_stoich_min": numerical_series(
                model, "MinSurface", "liion.cs_surface/liion.csmax", count, [4]
            ),
            "positive_surface_stoich_max": numerical_series(
                model, "MaxSurface", "liion.cs_surface/liion.csmax", count, [4]
            ),
            "negative_surface_stoich_avg": numerical_series(
                model, "AvSurface", "liion.cs_surface/liion.csmax", count, [2]
            ),
            "charge1": numerical_series(model, "EvalGlobal", "charge1", count),
            "charge_hold": numerical_series(model, "EvalGlobal", "charge_hold", count),
            "discharge1": numerical_series(model, "EvalGlobal", "discharge1", count),
            "current": numerical_series(model, "EvalGlobal", "I", count),
        }
        voltage = series["terminal_voltage"]
        usable = min(len(times), len(voltage))
        max_index = max(range(usable), key=lambda index: voltage[index])
        transition = next(
            (index for index in range(min(usable, len(series["charge1"]))) if series["charge1"][index] < 0.5),
            None,
        )
        result = {
            "rate": rate,
            "contact_resistance": contact,
            "requested_end_s": end_time,
            "solve_ok": solve_error is None,
            "solve_error": solve_error,
            "actual_end_s": times[-1],
            "terminal_voltage": first_last(voltage),
            "positive_phis": first_last(series["positive_phis"]),
            "positive_collector_minus_electrode_start_V": voltage[0] - series["positive_phis"][0],
            "max_voltage_V": voltage[max_index],
            "max_voltage_time_s": times[max_index],
            "charge_transition_time_s": None if transition is None else times[transition],
            "positive_surface_stoich_avg": first_last(series["positive_surface_stoich_avg"]),
            "positive_surface_stoich_min": first_last(series["positive_surface_stoich_min"]),
            "positive_surface_stoich_max": first_last(series["positive_surface_stoich_max"]),
            "negative_surface_stoich_avg": first_last(series["negative_surface_stoich_avg"]),
            "current": first_last(series["current"]),
        }
        if keep_series:
            result["series"] = {"time_s": times, **series}
        return result
    finally:
        ModelUtil.remove(tag)


cases = [
    run_case("coin_diag_ocv", 0.0, False, 1),
    run_case("coin_diag_load_no_contact", 0.5, False, 1),
    run_case("coin_diag_load_contact", 0.5, True, 1),
    run_case("coin_diag_event", 0.5, True, 420, True),
]
OUTPUT.write_text(json.dumps({"source": MODEL, "saved": False, "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT), "summaries": [{k: v for k, v in case.items() if k != "series"} for case in cases]}, ensure_ascii=False))
