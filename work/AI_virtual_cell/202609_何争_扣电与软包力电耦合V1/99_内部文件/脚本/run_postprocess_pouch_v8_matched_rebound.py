"""Run matched 100 N breathing controls for the 2D pouch cross-section."""

from __future__ import annotations

import csv
import json
import time as clock
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


TASK = Path(r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V1")
SOURCE = TASK / "02_模型" / "软包_V8_0p13Ah_0p5C_100N完整耦合.mph"
MODEL_NO_BREATH = TASK / "02_模型" / "软包_V8_0p13Ah_0p5C_100N无呼吸完整循环.mph"
INTERNAL = TASK / "99_内部文件" / "中间数据" / "软包V8_100N呼吸前后匹配对照"
RESULT = TASK / "99_内部文件" / "JSON" / "pouch_v8_100N_matched_rebound_comparison.json"


def tags(manager):
    return [str(item) for item in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def numerical_series(model, dataset, kind, expression, unit, selection=None, named=None):
    manager = model.result().numerical()
    tag = "__v9_series"
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    if named is not None:
        node.selection().named(named)
    elif selection is not None:
        node.selection().set(selection)
    try:
        return [float(item) for item in node.getReal()[0]]
    finally:
        remove(manager, tag)


def global_series(model, dataset, expression, unit):
    return numerical_series(model, dataset, "EvalGlobal", expression, unit)


def domain_average(model, dataset, expression, unit, domains):
    return numerical_series(model, dataset, "AvSurface", expression, unit, domains)


def domain_max(model, dataset, expression, unit, domains):
    return numerical_series(model, dataset, "MaxSurface", expression, unit, domains)


def boundary_average(model, dataset, expression, unit, named):
    return numerical_series(model, dataset, "AvLine", expression, unit, named=named)


def boundary_integral(model, dataset, expression, unit, named):
    return numerical_series(model, dataset, "IntLine", expression, unit, named=named)


def choose_dataset(model):
    candidates = []
    for dataset in tags(model.result().dataset()):
        try:
            times = global_series(model, dataset, "t", "s")
            if times:
                candidates.append((dataset, times))
        except Exception:
            continue
    if not candidates:
        raise RuntimeError("No readable transient dataset")
    return max(candidates, key=lambda item: (max(item[1]), len(item[1])))


def integrate_phase(time_s, current_a, voltage_v, charging):
    capacity_ah = 0.0
    energy_wh = 0.0
    for index in range(1, len(time_s)):
        i0, i1 = current_a[index - 1], current_a[index]
        active0 = i0 > 1e-12 if charging else i0 < -1e-12
        active1 = i1 > 1e-12 if charging else i1 < -1e-12
        if not (active0 or active1):
            continue
        dt_h = (time_s[index] - time_s[index - 1]) / 3600.0
        a0 = abs(i0) if active0 else 0.0
        a1 = abs(i1) if active1 else 0.0
        capacity_ah += 0.5 * (a0 + a1) * dt_h
        energy_wh += 0.5 * (a0 * voltage_v[index - 1] + a1 * voltage_v[index]) * dt_h
    return capacity_ah, energy_wh


def export_domain_field(model, dataset, expression, unit, domains, solnum, output):
    manager = model.result().numerical()
    tag = "__v9_field"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", dataset)
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    try:
        values = [float(row[0]) for row in node.getReal()]
        coords = [[float(item) for item in row] for row in node.getCoordinates()]
        with output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["x", "y", "value"])
            writer.writerows(zip(coords[0], coords[1], values))
        return len(values)
    finally:
        remove(manager, tag)


def extract_case(model, label):
    dataset, time_s = choose_dataset(model)
    voltage = global_series(model, dataset, "vol_loaded", "V")
    current = global_series(model, dataset, "I", "A")
    top_v = boundary_average(model, dataset, "v", "um", "sel_mech_top")
    bottom_v = boundary_average(model, dataset, "v", "um", "sel_mech_bottom")
    signed_thickness = [top - bottom for top, bottom in zip(top_v, bottom_v)]
    relative_thickness = [value - signed_thickness[0] for value in signed_thickness]
    series = {
        "time_s": time_s,
        "voltage_V": voltage,
        "terminal_voltage_V": global_series(model, dataset, "V_terminal", "V"),
        "current_A": current,
        "theta_neg": domain_average(model, dataset, "theta_neg_v4", "1", [4]),
        "theta_pos": domain_average(model, dataset, "theta_pos_v4", "1", [6]),
        "breathing_neg_pct": [100 * value for value in domain_average(model, dataset, "eps_breath_neg_v4", "1", [4])],
        "breathing_pos_pct": [100 * value for value in domain_average(model, dataset, "eps_breath_pos_v4", "1", [6])],
        "pressure_neg_kPa": domain_average(model, dataset, "p_comp_neg_v4", "kPa", [4]),
        "pressure_sep_kPa": domain_average(model, dataset, "p_comp_sep_v4", "kPa", [5]),
        "pressure_pos_kPa": domain_average(model, dataset, "p_comp_pos_v4", "kPa", [6]),
        "pressure_stack_max_kPa": domain_max(model, dataset, "max(0[Pa],-solid.sy)", "kPa", [4, 5, 6]),
        "mises_stack_max_kPa": domain_max(model, dataset, "solid.mises", "kPa", [4, 5, 6]),
        "porosity_neg": domain_average(model, dataset, "epsl_neg_v4", "1", [4]),
        "porosity_sep": domain_average(model, dataset, "epsl_sep_v4", "1", [5]),
        "porosity_pos": domain_average(model, dataset, "epsl_pos_v4", "1", [6]),
        "top_v_um": top_v,
        "bottom_v_um": bottom_v,
        "relative_thickness_change_um": relative_thickness,
    }
    series["actual_SOC"] = [
        0.5 * ((negative - 0.05) / 0.91 + (1.0 - positive) / 0.98)
        for negative, positive in zip(series["theta_neg"], series["theta_pos"])
    ]
    charge_ah, charge_wh = integrate_phase(time_s, current, voltage, True)
    discharge_ah, discharge_wh = integrate_phase(time_s, current, voltage, False)
    charge_indices = [i for i, value in enumerate(current) if value > 1e-6]
    discharge_indices = [i for i, value in enumerate(current) if value < -1e-6]
    discharge_end = max(discharge_indices)
    first_rest = min(discharge_end + 1, len(time_s) - 1)
    pressure_peak_index = max(range(len(time_s)), key=lambda i: series["pressure_stack_max_kPa"][i])
    metrics = {
        "charge_capacity_Ah": charge_ah,
        "discharge_capacity_Ah": discharge_ah,
        "charge_energy_Wh": charge_wh,
        "discharge_energy_Wh": discharge_wh,
        "charge_end_time_s": time_s[max(charge_indices)],
        "discharge_start_time_s": time_s[min(discharge_indices)],
        "discharge_end_time_s": time_s[discharge_end],
        "maximum_SOC_pct": 100 * max(series["actual_SOC"]),
        "cutoff_loaded_voltage_V": voltage[discharge_end],
        "immediate_rest_voltage_V": voltage[first_rest],
        "settled_voltage_V": voltage[-1],
        "instantaneous_rebound_mV": 1000 * (voltage[first_rest] - voltage[discharge_end]),
        "total_rebound_mV": 1000 * (voltage[-1] - voltage[discharge_end]),
        "pressure_stack_peak_kPa": max(series["pressure_stack_max_kPa"]),
        "pressure_peak_time_s": time_s[pressure_peak_index],
        "pressure_peak_SOC_pct": 100 * series["actual_SOC"][pressure_peak_index],
        "mises_stack_peak_kPa": max(series["mises_stack_max_kPa"]),
        "minimum_porosity": min(min(series["porosity_neg"]), min(series["porosity_sep"]), min(series["porosity_pos"])),
        "maximum_graphite_breathing_pct": max(series["breathing_neg_pct"]),
        "thickness_change_peak_um": max(relative_thickness),
        "top_edge_length_m": boundary_integral(model, dataset, "1", "m", "sel_mech_top")[0],
        "bottom_edge_length_m": boundary_integral(model, dataset, "1", "m", "sel_mech_bottom")[0],
        "top_effective_loaded_area_m2": boundary_integral(model, dataset, "1", "m", "sel_mech_top")[0] * 0.052,
        "top_normal_xy": [
            boundary_average(model, dataset, "nx", "1", "sel_mech_top")[0],
            boundary_average(model, dataset, "ny", "1", "sel_mech_top")[0],
        ],
    }
    path = INTERNAL / f"timeseries_{label}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        keys = list(series)
        writer.writerow(keys)
        writer.writerows(zip(*(series[key] for key in keys)))
    field_counts = {}
    for name, expression, unit, domains in (
        ("pressure_thickness", "max(0[Pa],-solid.sy)", "kPa", [4, 5, 6]),
        ("mises", "solid.mises", "kPa", [4, 5, 6]),
        ("porosity_neg", "epsl_neg_v4", "1", [4]),
        ("porosity_sep", "epsl_sep_v4", "1", [5]),
        ("porosity_pos", "epsl_pos_v4", "1", [6]),
    ):
        output = INTERNAL / f"field_{label}_pressure_peak_{name}.csv"
        field_counts[name] = export_domain_field(model, dataset, expression, unit, domains, pressure_peak_index + 1, output)
    return {"dataset": dataset, "series": series, "metrics": metrics, "timeseries_csv": str(path), "field_counts": field_counts}


def run_case(label, breathing_mode, output_model=None, reuse_source_solution=False):
    tag = f"pouch_v8_{label}"
    reuse_saved_solution = reuse_source_solution or (output_model is not None and output_model.exists())
    load_path = SOURCE if reuse_source_solution else (output_model if reuse_saved_solution else SOURCE)
    model = ModelUtil.load(tag, str(load_path))
    try:
        model.param().set("F_ext", "100[N]")
        model.param().set("coupling_on", "1")
        model.param().set("breathing_mode", str(breathing_mode))
        if reuse_saved_solution:
            elapsed = 0.0
        else:
            started = clock.time()
            model.study("std_cycle").run()
            elapsed = clock.time() - started
            model.label(f"Single-layer pouch V8 - 100 N {label} full cycle")
            model.save(str(output_model))
        return {"solve_elapsed_s": elapsed, "reused_saved_solution": reuse_saved_solution, "output_model": str(output_model or SOURCE), **extract_case(model, label)}
    finally:
        ModelUtil.remove(tag)


def main():
    INTERNAL.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": False,
        "source": str(SOURCE),
        "protocol": {"rated_capacity_Ah": 0.13, "C_rate": 0.5, "current_A": 0.065, "force_N": 100},
        "geometry_interpretation": {
            "space_dimension": "2D",
            "thickness_axis": "y",
            "display_scale": "y direction enlarged 100x",
            "pressure": "max(0,-solid.sy)",
            "thickness_displacement": "v",
        },
        "cases": {},
    }
    try:
        payload["cases"]["pressure_only_100N"] = run_case("pressure_only_100N", 0, MODEL_NO_BREATH)
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["cases"]["pressure_breathing_100N"] = run_case("pressure_breathing_100N", 2, reuse_source_solution=True)
        payload["ok"] = True
    except Exception as exc:
        payload["error"] = str(exc)
        payload["traceback"] = traceback.format_exc()
        raise
    finally:
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "result": str(RESULT), "metrics": {k: v["metrics"] for k, v in payload["cases"].items()}}, ensure_ascii=False))


main()
