import csv
import json
import time as clock
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
MODEL = RUN / "pouch_dual_tab_2d_cross_section_v4_mechanical_breathing.mph"
DATA_DIR = RUN / "exported_data_v4"
OUTPUT = RUN / "pouch_2d_v4_full_cycle_comparison.json"
CASES = [
    ("baseline", "0", "0", "0[N]"),
    ("coupled_100N", "1", "2", "100[N]"),
]


def tags(manager):
    return [str(item) for item in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def solution_of(model, dataset):
    try:
        return str(model.result().dataset(dataset).getString("solution"))
    except Exception:
        return ""


def numerical_series(model, dataset, kind, expression, unit, selection=None):
    manager = model.result().numerical()
    tag = "__pouch_v4_series"
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    if selection is not None:
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


def boundary_max(model, dataset, expression, unit, boundary):
    return numerical_series(model, dataset, "MaxLine", expression, unit, [boundary])


def integrate_phase(time_s, current_a, voltage_v, charging):
    capacity_ah = 0.0
    energy_wh = 0.0
    for index in range(1, len(time_s)):
        current0, current1 = current_a[index - 1], current_a[index]
        active0 = current0 > 1e-12 if charging else current0 < -1e-12
        active1 = current1 > 1e-12 if charging else current1 < -1e-12
        if not (active0 or active1):
            continue
        dt_h = (time_s[index] - time_s[index - 1]) / 3600.0
        magnitude0 = abs(current0) if active0 else 0.0
        magnitude1 = abs(current1) if active1 else 0.0
        capacity_ah += 0.5 * (magnitude0 + magnitude1) * dt_h
        energy_wh += 0.5 * (
            magnitude0 * voltage_v[index - 1] + magnitude1 * voltage_v[index]
        ) * dt_h
    return capacity_ah, energy_wh


def actual_soc(time_s, current_c):
    values = [0.01]
    for index in range(1, len(time_s)):
        dt_h = (time_s[index] - time_s[index - 1]) / 3600.0
        values.append(values[-1] + 0.5 * (current_c[index - 1] + current_c[index]) * dt_h)
    return values


def write_timeseries(label, series):
    path = DATA_DIR / f"timeseries_{label}.csv"
    keys = list(series)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(keys)
        for row in zip(*(series[key] for key in keys)):
            writer.writerow(row)
    return str(path)


DATA_DIR.mkdir(exist_ok=True)
payload = {
    "source": str(MODEL),
    "protocol": {
        "C_rate": 0.5,
        "charge_cutoff_V": 3.65,
        "rest_s": 600,
        "discharge_cutoff_V": 2.50,
        "t_end_s": 18000,
    },
    "cases": {},
    "ok": False,
}

for label, coupling_on, breathing_mode, force in CASES:
    tag = f"pouch_v4_cycle_{label}"
    case = {"label": label, "ok": False}
    model = None
    try:
        model = ModelUtil.load(tag, str(MODEL))
        model.param().set("coupling_on", coupling_on)
        model.param().set("breathing_mode", breathing_mode)
        model.param().set("F_ext", force)
        model.study("std_cycle").feature("time").set("tlist", "range(0,60,18000)")

        before = set(tags(model.sol()))
        started = clock.time()
        model.study("std_cycle").run()
        case["solve_elapsed_s"] = clock.time() - started
        new_solutions = [item for item in tags(model.sol()) if item not in before]
        candidates = []
        for dataset in tags(model.result().dataset()):
            if solution_of(model, dataset) not in new_solutions:
                continue
            try:
                time_s = global_series(model, dataset, "t", "s")
                candidates.append((dataset, time_s))
            except Exception:
                continue
        if not candidates:
            raise RuntimeError(f"No transient dataset found for {new_solutions}")
        dataset, time_s = max(candidates, key=lambda item: (max(item[1]), len(item[1])))

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
            "breathing_neg_pct": [100 * item for item in domain_average(model, dataset, "eps_breath_neg_v4", "1", 4)],
            "breathing_pos_pct": [100 * item for item in domain_average(model, dataset, "eps_breath_pos_v4", "1", 6)],
            "pressure_neg_kPa": domain_average(model, dataset, "p_comp_neg_v4", "kPa", 4),
            "pressure_sep_kPa": domain_average(model, dataset, "p_comp_sep_v4", "kPa", 5),
            "pressure_pos_kPa": domain_average(model, dataset, "p_comp_pos_v4", "kPa", 6),
            "porosity_neg": domain_average(model, dataset, "epsl_neg_v4", "1", 4),
            "porosity_sep": domain_average(model, dataset, "epsl_sep_v4", "1", 5),
            "porosity_pos": domain_average(model, dataset, "epsl_pos_v4", "1", 6),
            "electrolyte_min_mol_m3": domain_min(model, dataset, "cl", "mol/m^3", [4, 5, 6]),
            "electrolyte_max_mol_m3": domain_max(model, dataset, "cl", "mol/m^3", [4, 5, 6]),
            "top_displacement_um": boundary_max(model, dataset, "v", "um", 18),
            "collector_current_density_max_A_m2": domain_max(
                model, dataset, "sqrt(liion.Isx^2+liion.Isy^2)", "A/m^2", [1, 2, 3, 7, 8, 9]
            ),
        }
        series["actual_SOC"] = actual_soc(time_s, series["current_Crate"])
        charge_ah, charge_wh = integrate_phase(time_s, series["current_A"], series["voltage_V"], True)
        discharge_ah, discharge_wh = integrate_phase(time_s, series["current_A"], series["voltage_V"], False)
        charge_indices = [index for index, value in enumerate(series["current_Crate"]) if value > 0.1]
        discharge_indices = [index for index, value in enumerate(series["current_Crate"]) if value < -0.1]
        discharge_finished = bool(
            discharge_indices
            and max(discharge_indices) < len(time_s) - 1
            and abs(series["current_Crate"][-1]) < 0.1
            and min(series["voltage_V"][index] for index in discharge_indices) <= 2.51
        )
        electrolyte_span = [high - low for low, high in zip(
            series["electrolyte_min_mol_m3"], series["electrolyte_max_mol_m3"]
        )]
        metrics = {
            "charge_capacity_Ah": charge_ah,
            "discharge_capacity_Ah": discharge_ah,
            "charge_energy_Wh": charge_wh,
            "discharge_energy_Wh": discharge_wh,
            "coulombic_efficiency_pct": 100 * discharge_ah / charge_ah if charge_ah else None,
            "energy_efficiency_pct": 100 * discharge_wh / charge_wh if charge_wh else None,
            "charge_end_time_s": time_s[max(charge_indices)] if charge_indices else None,
            "discharge_start_time_s": time_s[min(discharge_indices)] if discharge_indices else None,
            "discharge_end_time_s": time_s[max(discharge_indices)] if discharge_indices else None,
            "maximum_SOC_pct": 100 * max(series["actual_SOC"]),
            "pressure_peak_kPa": max(
                max(series["pressure_neg_kPa"]), max(series["pressure_sep_kPa"]), max(series["pressure_pos_kPa"])
            ),
            "minimum_porosity": min(
                min(series["porosity_neg"]), min(series["porosity_sep"]), min(series["porosity_pos"])
            ),
            "maximum_graphite_breathing_pct": max(series["breathing_neg_pct"]),
            "top_displacement_range_um": [min(series["top_displacement_um"]), max(series["top_displacement_um"])],
            "maximum_electrolyte_span_mol_m3": max(electrolyte_span),
            "maximum_collector_current_density_A_m2": max(series["collector_current_density_max_A_m2"]),
        }
        solved_model = RUN / f"pouch_dual_tab_2d_cross_section_v4_{label}_full_cycle_solved.mph"
        model.label(f"Single-layer pouch 2D V4 - {label} full cycle solved")
        model.save(str(solved_model))
        case.update({
            "ok": bool(charge_indices and discharge_finished and max(time_s) >= 17999.9),
            "discharge_finished": discharge_finished,
            "dataset": dataset,
            "new_solutions": new_solutions,
            "series": series,
            "metrics": metrics,
            "timeseries_csv": write_timeseries(label, series),
            "solved_model": str(solved_model),
        })
    except Exception:
        case["traceback"] = traceback.format_exc()
    finally:
        if model is not None:
            try:
                ModelUtil.remove(tag)
            except Exception:
                pass
    payload["cases"][label] = case
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"case": label, "ok": case.get("ok"), "elapsed_s": case.get("solve_elapsed_s")}, ensure_ascii=False), flush=True)

payload["ok"] = all(case.get("ok") for case in payload["cases"].values())
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("MPH_TOOL_RESULT_BEGIN")
print(json.dumps({"ok": payload["ok"], "output": str(OUTPUT)}, ensure_ascii=False))
print("MPH_TOOL_RESULT_END")
