import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5.mph"
SOLVED_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_final.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding")
OUTPUT = RUN / "full_result_final.json"
CSV_PATH = RUN / "exported_data" / "voltage_soc_v5_final.csv"
TAG = "coin_v5_full"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def scalar_series(model, tag, kind, expr, selection, count):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", "dset1")
    node.set("expr", expr)
    if selection is not None:
        node.selection().set(selection)
    values = []
    for solnum in range(1, count + 1):
        node.set("solnum", str(solnum))
        value = node.getReal()
        while hasattr(value, "__len__") and len(value) == 1:
            value = value[0]
        values.append(float(value))
    remove(manager, tag)
    return values


def field_range(model, tag, expr, domains, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    values = [float(row[0]) for row in node.getReal()]
    remove(manager, tag)
    return {"min": min(values), "max": max(values)}


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "solved_model": SOLVED_MODEL}
try:
    time_feature = model.study("std1").feature("time")
    time_feature.set("tlist", "range(0,20,7200)")
    model.sol("sol1").feature("t1").set("eventtol", "1e-4")
    model.study("std1").run()

    times = [float(value) for value in model.sol("sol1").getPVals()]
    count = len(times)
    voltage = scalar_series(model, "__voltage", "AvLine", "phis", [20], count)
    current_c = scalar_series(model, "__crate", "EvalGlobal", "I/i_1C", None, count)
    negative_avg = scalar_series(model, "__negavg", "AvSurface", "liion.cs_surface/liion.csmax", [4], count)
    positive_avg = scalar_series(model, "__posavg", "AvSurface", "liion.cs_surface/liion.csmax", [6], count)

    actual_soc = [0.01]
    for index in range(1, count):
        dt = times[index] - times[index - 1]
        actual_soc.append(actual_soc[-1] + 0.5 * (current_c[index - 1] + current_c[index]) * dt / 3600.0)

    transition_index = next(
        (index for index in range(1, count) if current_c[index - 1] > 0.25 and current_c[index] < 0.25),
        count - 1,
    )
    cutoff_index = transition_index - 1 if transition_index > 0 else transition_index
    cutoff_solnum = cutoff_index + 1

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["solnum", "time_s", "actual_SOC", "current_Crate", "terminal_voltage_V", "negative_surface_stoich_avg", "positive_surface_stoich_avg"])
        for index in range(count):
            writer.writerow([index + 1, times[index], actual_soc[index], current_c[index], voltage[index], negative_avg[index], positive_avg[index]])

    payload.update({
        "ok": True,
        "event_tolerance": str(model.sol("sol1").feature("t1").getString("eventtol")),
        "solution_count": count,
        "time_end_s": times[-1],
        "cutoff": {
            "solnum": cutoff_solnum,
            "time_s": times[cutoff_index],
            "actual_SOC": actual_soc[cutoff_index],
            "terminal_voltage_V": voltage[cutoff_index],
            "negative_surface_stoich_avg": negative_avg[cutoff_index],
            "positive_surface_stoich_avg": positive_avg[cutoff_index],
            "electrolyte_concentration_mol_m3": field_range(model, "__field", "cl", [4, 5, 6], cutoff_solnum),
            "negative_surface_stoichiometry": field_range(model, "__field", "liion.cs_surface/liion.csmax", [4], cutoff_solnum),
            "positive_surface_stoichiometry": field_range(model, "__field", "liion.cs_surface/liion.csmax", [6], cutoff_solnum),
            "negative_solid_potential_V": field_range(model, "__field", "phis", [4], cutoff_solnum),
            "positive_solid_potential_V": field_range(model, "__field", "phis", [6], cutoff_solnum),
            "electrolyte_potential_V": field_range(model, "__field", "phil", [4, 5, 6], cutoff_solnum),
        },
        "csv": str(CSV_PATH),
    })
    model.save(SOLVED_MODEL)
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
