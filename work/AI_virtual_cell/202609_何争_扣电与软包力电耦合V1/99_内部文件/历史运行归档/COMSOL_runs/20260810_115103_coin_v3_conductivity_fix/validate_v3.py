import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V3.mph"
RUN_DIR = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_115103_coin_v3_conductivity_fix")
OUTPUT = RUN_DIR / "validation.json"
CSV_OUTPUT = RUN_DIR / "exported_data" / "full_charge_series.csv"


def flatten(value):
    if isinstance(value, (str, bytes)):
        return float(value)
    try:
        items = list(value)
    except TypeError:
        return float(value)
    result = []
    for item in items:
        nested = flatten(item)
        result.extend(nested if isinstance(nested, list) else [nested])
    return result


def series(model, kind, expression, count, selection=None):
    manager = model.result().numerical()
    tag = "__v3_" + kind + "_" + str(abs(hash((expression, tuple(selection or [])))) % 100000)
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
            value = flatten(node.getReal())
            values.append(float(value[0] if isinstance(value, list) else value))
        return values
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def run_case(tag, rate, end_time, output_step, keep_series=False):
    model = ModelUtil.load(tag, MODEL)
    try:
        comp = model.component("comp1")
        comp.variable("var1").set("C", str(rate))
        model.study("std1").feature("time").set("tlist", f"range(0,{output_step},{end_time})")
        try:
            model.result().table("tbl1").clearTableData()
        except Exception:
            pass
        try:
            model.sol().remove("sol1")
        except Exception:
            pass
        solve_error = None
        try:
            model.study("std1").run()
        except Exception as exc:
            solve_error = str(exc)

        times = [float(value) for value in model.sol("sol1").getPVals()]
        count = len(times)
        values = {
            "terminal_voltage_V": series(model, "AvLine", "phis", count, [11]),
            "positive_phis_avg_V": series(model, "AvSurface", "phis", count, [4]),
            "positive_phis_min_V": series(model, "MinSurface", "phis", count, [4]),
            "positive_phis_max_V": series(model, "MaxSurface", "phis", count, [4]),
            "positive_surface_stoich_avg": series(model, "AvSurface", "liion.cs_surface/liion.csmax", count, [4]),
            "positive_surface_stoich_min": series(model, "MinSurface", "liion.cs_surface/liion.csmax", count, [4]),
            "positive_surface_stoich_max": series(model, "MaxSurface", "liion.cs_surface/liion.csmax", count, [4]),
            "negative_surface_stoich_avg": series(model, "AvSurface", "liion.cs_surface/liion.csmax", count, [2]),
            "negative_surface_stoich_min": series(model, "MinSurface", "liion.cs_surface/liion.csmax", count, [2]),
            "negative_surface_stoich_max": series(model, "MaxSurface", "liion.cs_surface/liion.csmax", count, [2]),
            "charge1": series(model, "EvalGlobal", "charge1", count),
            "charge_hold": series(model, "EvalGlobal", "charge_hold", count),
            "current_A": series(model, "EvalGlobal", "I", count),
        }
        voltage = values["terminal_voltage_V"]
        max_index = max(range(len(voltage)), key=voltage.__getitem__)
        transition_index = next((i for i, value in enumerate(values["charge1"]) if value < 0.5), None)
        result = {
            "rate_C": rate,
            "requested_end_s": end_time,
            "actual_end_s": times[-1],
            "solve_ok": solve_error is None,
            "solve_error": solve_error,
            "point_count": count,
            "terminal_voltage_first_V": voltage[0],
            "terminal_voltage_last_V": voltage[-1],
            "terminal_voltage_max_V": voltage[max_index],
            "terminal_voltage_max_time_s": times[max_index],
            "positive_solid_potential_span_first_V": values["positive_phis_max_V"][0] - values["positive_phis_min_V"][0],
            "charge_transition_time_s": None if transition_index is None else times[transition_index],
            "positive_surface_stoich_min_all": min(values["positive_surface_stoich_min"]),
            "positive_surface_stoich_max_all": max(values["positive_surface_stoich_max"]),
            "negative_surface_stoich_min_all": min(values["negative_surface_stoich_min"]),
            "negative_surface_stoich_max_all": max(values["negative_surface_stoich_max"]),
        }
        if keep_series:
            result["series"] = {"time_s": times, **values}
        return result
    finally:
        ModelUtil.remove(tag)


cases = [
    run_case("coin_v3_ocv", 0.0, 1, 1),
    run_case("coin_v3_start", 0.5, 1, 1),
    run_case("coin_v3_full_charge", 0.5, 7200, 10, True),
]

full = cases[-1]["series"]
columns = list(full)
with CSV_OUTPUT.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.writer(handle)
    writer.writerow(columns)
    writer.writerows(zip(*(full[column] for column in columns)))

OUTPUT.write_text(json.dumps({"source": MODEL, "saved": False, "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "output": str(OUTPUT), "summaries": [{k: v for k, v in case.items() if k != "series"} for case in cases]}, ensure_ascii=False))
