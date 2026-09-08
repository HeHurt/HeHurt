import csv
import json
import time as clock
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
COUPLED = RUN / "pouch_dual_tab_2d_cross_section_v8_rated_0p13Ah_coupled_100N_full_cycle_solved.mph"
BASELINE = RUN / "pouch_dual_tab_2d_cross_section_v8_rated_0p13Ah_baseline_full_cycle_solved.mph"
POST = RUN / "postprocess_v8_coin_comparison"
DATA_DIR = POST / "exported_data"
OUTPUT = POST / "pouch_v8_full_cycle_comparison.json"


def tags(manager):
    return [str(item) for item in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def numerical_series(model, dataset, kind, expression, unit, selection=None, named=None):
    manager = model.result().numerical()
    tag = "__v8_compare_series"
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


def domain_average(model, dataset, expression, unit, domain):
    return numerical_series(model, dataset, "AvSurface", expression, unit, [domain])


def domain_min(model, dataset, expression, unit, domains):
    return numerical_series(model, dataset, "MinSurface", expression, unit, domains)


def domain_max(model, dataset, expression, unit, domains):
    return numerical_series(model, dataset, "MaxSurface", expression, unit, domains)


def boundary_average(model, dataset, expression, unit, named):
    return numerical_series(model, dataset, "AvLine", expression, unit, named=named)


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


def closest_stage(series, phase, target):
    sign = 1 if phase == "charge" else -1
    indices = [index for index, value in enumerate(series["current_Crate"]) if value * sign > 0.1]
    if not indices:
        return None
    return min(indices, key=lambda index: abs(series["actual_SOC"][index] - target))


def eval_field(model, dataset, expression, entities, solnum):
    manager = model.result().numerical()
    tag = "__v8_compare_field"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", dataset)
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.selection().geom("geom1", 2)
    node.selection().set(entities)
    try:
        values = [float(row[0]) for row in node.getReal()]
        coords = [[float(item) for item in row] for row in node.getCoordinates()]
        return coords, values
    finally:
        remove(manager, tag)


def export_spatial(model, dataset, label, series):
    files = []
    stages = []
    for phase in ("charge", "discharge"):
        for target in (0.10, 0.50, 0.85):
            index = closest_stage(series, phase, target)
            stages.append({"phase": phase, "target_SOC": target, "index": index})
            if index is None:
                continue
            fields = {
                "pressure_neg_kPa": ("p_comp_neg_v4", [4]),
                "pressure_sep_kPa": ("p_comp_sep_v4", [5]),
                "pressure_pos_kPa": ("p_comp_pos_v4", [6]),
                "porosity_neg": ("epsl_neg_v4", [4]),
                "porosity_sep": ("epsl_sep_v4", [5]),
                "porosity_pos": ("epsl_pos_v4", [6]),
                "theta_neg": ("theta_neg_v4", [4]),
                "theta_pos": ("theta_pos_v4", [6]),
                "electrolyte_concentration": ("cl", [4, 5, 6]),
                "collector_current_density": ("sqrt(liion.Isx^2+liion.Isy^2)", [1, 2, 3, 7, 8, 9]),
            }
            for name, (expression, domains) in fields.items():
                coords, values = eval_field(model, dataset, expression, domains, index + 1)
                path = DATA_DIR / f"spatial_{label}_{phase}_SOC{int(target * 100):02d}_{name}.csv"
                with path.open("w", newline="", encoding="utf-8-sig") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["x_m", "y_m", name])
                    for point in range(len(values)):
                        writer.writerow([coords[0][point], coords[1][point], values[point]])
                files.append(str(path))
    return stages, files


def extract_case(model, label, export_fields):
    dataset, time_s = choose_dataset(model)
    top_v = boundary_average(model, dataset, "v", "um", "sel_mech_top")
    bottom_v = boundary_average(model, dataset, "v", "um", "sel_mech_bottom")
    signed_thickness = [top - bottom for top, bottom in zip(top_v, bottom_v)]
    relative_thickness = [value - signed_thickness[0] for value in signed_thickness]
    series = {
        "time_s": time_s,
        "voltage_V": global_series(model, dataset, "vol_loaded", "V"),
        "terminal_voltage_V": global_series(model, dataset, "V_terminal", "V"),
        "current_A": global_series(model, dataset, "I", "A"),
        "current_Crate": global_series(model, dataset, "I/i_1C", "1"),
        "charge_state": global_series(model, dataset, "charge1", "1"),
        "discharge_state": global_series(model, dataset, "discharge1", "1"),
        "theta_neg": domain_average(model, dataset, "theta_neg_v4", "1", 4),
        "theta_pos": domain_average(model, dataset, "theta_pos_v4", "1", 6),
        "breathing_neg_pct": [100 * value for value in domain_average(model, dataset, "eps_breath_neg_v4", "1", 4)],
        "breathing_pos_pct": [100 * value for value in domain_average(model, dataset, "eps_breath_pos_v4", "1", 6)],
        "pressure_neg_kPa": domain_average(model, dataset, "p_comp_neg_v4", "kPa", 4),
        "pressure_sep_kPa": domain_average(model, dataset, "p_comp_sep_v4", "kPa", 5),
        "pressure_pos_kPa": domain_average(model, dataset, "p_comp_pos_v4", "kPa", 6),
        "porosity_neg": domain_average(model, dataset, "epsl_neg_v4", "1", 4),
        "porosity_sep": domain_average(model, dataset, "epsl_sep_v4", "1", 5),
        "porosity_pos": domain_average(model, dataset, "epsl_pos_v4", "1", 6),
        "electrolyte_min_mol_m3": domain_min(model, dataset, "cl", "mol/m^3", [4, 5, 6]),
        "electrolyte_max_mol_m3": domain_max(model, dataset, "cl", "mol/m^3", [4, 5, 6]),
        "top_v_um": top_v,
        "bottom_v_um": bottom_v,
        "relative_thickness_change_um": relative_thickness,
        "relative_thickness_strain_pct": [100 * value / 345.5 for value in relative_thickness],
        "collector_current_density_max_A_m2": domain_max(
            model, dataset, "sqrt(liion.Isx^2+liion.Isy^2)", "A/m^2", [1, 2, 3, 7, 8, 9]
        ),
    }
    series["electrode_SOC_neg"] = [(value - 0.05) / 0.91 for value in series["theta_neg"]]
    series["electrode_SOC_pos"] = [(1.0 - value) / 0.98 for value in series["theta_pos"]]
    series["actual_SOC"] = [
        0.5 * (negative + positive)
        for negative, positive in zip(series["electrode_SOC_neg"], series["electrode_SOC_pos"])
    ]
    charge_ah, charge_wh = integrate_phase(time_s, series["current_A"], series["voltage_V"], True)
    discharge_ah, discharge_wh = integrate_phase(time_s, series["current_A"], series["voltage_V"], False)
    charge_indices = [index for index, value in enumerate(series["current_A"]) if value > 1e-6]
    discharge_indices = [index for index, value in enumerate(series["current_A"]) if value < -1e-6]
    electrolyte_span = [high - low for low, high in zip(
        series["electrolyte_min_mol_m3"], series["electrolyte_max_mol_m3"]
    )]
    metrics = {
        "charge_capacity_Ah": charge_ah,
        "discharge_capacity_Ah": discharge_ah,
        "charge_energy_Wh": charge_wh,
        "discharge_energy_Wh": discharge_wh,
        "coulombic_efficiency_pct": 100 * discharge_ah / charge_ah,
        "energy_efficiency_pct": 100 * discharge_wh / charge_wh,
        "charge_end_time_s": time_s[max(charge_indices)],
        "discharge_start_time_s": time_s[min(discharge_indices)],
        "discharge_end_time_s": time_s[max(discharge_indices)],
        "maximum_SOC_pct": 100 * max(series["actual_SOC"]),
        "pressure_peak_kPa": max(max(series["pressure_neg_kPa"]), max(series["pressure_sep_kPa"]), max(series["pressure_pos_kPa"])),
        "minimum_porosity": min(min(series["porosity_neg"]), min(series["porosity_sep"]), min(series["porosity_pos"])),
        "maximum_graphite_breathing_pct": max(series["breathing_neg_pct"]),
        "relative_thickness_change_range_um": [min(relative_thickness), max(relative_thickness)],
        "maximum_electrolyte_span_mol_m3": max(electrolyte_span),
        "maximum_collector_current_density_A_m2": max(series["collector_current_density_max_A_m2"]),
    }
    timeseries_path = DATA_DIR / f"timeseries_{label}.csv"
    with timeseries_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        keys = list(series)
        writer.writerow(keys)
        writer.writerows(zip(*(series[key] for key in keys)))
    stages, files = export_spatial(model, dataset, label, series) if export_fields else ([], [])
    return {
        "dataset": dataset,
        "series": series,
        "metrics": metrics,
        "timeseries_csv": str(timeseries_path),
        "spatial_stages": stages,
        "spatial_files": files,
    }


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": False,
        "coupled_model": str(COUPLED),
        "baseline_model": str(BASELINE),
        "protocol": {"rated_capacity_Ah": 0.13, "C_rate": 0.5, "current_A": 0.065},
        "cases": {},
    }

    tag = "pouch_v8_baseline_solve"
    model = ModelUtil.load(tag, str(COUPLED))
    try:
        model.param().set("coupling_on", "0")
        model.param().set("breathing_mode", "0")
        model.param().set("F_ext", "0[N]")
        started = clock.time()
        model.study("std_cycle").run()
        payload["baseline_solve_elapsed_s"] = clock.time() - started
        model.label("Single-layer pouch 2D V8 - rated 0.13 Ah baseline full cycle")
        model.save(str(BASELINE))
        payload["cases"]["baseline"] = extract_case(model, "baseline", False)
    finally:
        ModelUtil.remove(tag)

    tag = "pouch_v8_coupled_extract"
    model = ModelUtil.load(tag, str(COUPLED))
    try:
        payload["cases"]["coupled_100N"] = extract_case(model, "coupled_100N", True)
    finally:
        ModelUtil.remove(tag)

    tag = "pouch_v8_baseline_reload"
    model = ModelUtil.load(tag, str(BASELINE))
    try:
        dataset, times = choose_dataset(model)
        payload["baseline_reload"] = {
            "dataset": dataset,
            "time_end_s": max(times),
            "i_1C": str(model.param().get("i_1C")),
            "C_rate": str(model.param().get("C_rate")),
            "coupling_on": str(model.param().get("coupling_on")),
            "breathing_mode": str(model.param().get("breathing_mode")),
        }
    finally:
        ModelUtil.remove(tag)

    payload["ok"] = True
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps({"ok": True, "output": str(OUTPUT), "baseline_model": str(BASELINE)}, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")


try:
    main()
except Exception:
    POST.mkdir(parents=True, exist_ok=True)
    failure = {"ok": False, "traceback": traceback.format_exc()}
    OUTPUT.write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps(failure, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")
    raise
