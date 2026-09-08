import csv
import json
import math
import time as clock
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V9_nonlinear_breathing_cycle.mph"
SOLVED_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V9_nonlinear_breathing_cycle_solved_100N.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle")
DATA_DIR = RUN / "exported_data"
OUTPUT = RUN / "full_cycle_comparison.json"
MODES = [(0, "off"), (1, "legacy_linear_20pct"), (2, "literature_nonlinear")]
REGIONS = {"negative": 4, "separator": 5, "positive": 6}
INTERFACES = {
    "negative_Cu": 9,
    "negative_separator": 11,
    "positive_separator": 13,
    "positive_Al": 15,
}


def tags(manager):
    return [str(x) for x in manager.tags()]


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


def numerical_series(model, dataset, kind, expr, unit, selection=None):
    manager = model.result().numerical()
    tag = "__v9_series"
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", dataset)
    node.set("expr", [expr])
    node.set("unit", [unit])
    if selection is not None:
        node.selection().set(selection)
    try:
        return [float(x) for x in node.getReal()[0]]
    finally:
        remove(manager, tag)


def global_series(model, dataset, expr, unit):
    return numerical_series(model, dataset, "EvalGlobal", expr, unit)


def domain_average(model, dataset, expr, unit, domain):
    return numerical_series(model, dataset, "AvSurface", expr, unit, [domain])


def domain_min(model, dataset, expr, unit, domains):
    return numerical_series(model, dataset, "MinSurface", expr, unit, domains)


def domain_max(model, dataset, expr, unit, domains):
    return numerical_series(model, dataset, "MaxSurface", expr, unit, domains)


def boundary_max(model, dataset, expr, unit, boundary):
    return numerical_series(model, dataset, "MaxLine", expr, unit, [boundary])


def eval_field(model, dataset, expr, entity_dim, entities, solnum):
    manager = model.result().numerical()
    tag = "__v9_field"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", dataset)
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.selection().geom("geom1", entity_dim)
    node.selection().set(entities)
    try:
        values = [float(row[0]) for row in node.getReal()]
        coords = [[float(x) for x in row] for row in node.getCoordinates()]
        elements = [[int(x) for x in row] for row in node.getElements()]
        return coords, elements, values
    finally:
        remove(manager, tag)


def integrate_phase(time_s, current_a, voltage_v, positive):
    capacity_ah = 0.0
    energy_wh = 0.0
    for i in range(1, len(time_s)):
        i0, i1 = current_a[i - 1], current_a[i]
        active0 = i0 > 1e-12 if positive else i0 < -1e-12
        active1 = i1 > 1e-12 if positive else i1 < -1e-12
        if not (active0 or active1):
            continue
        dt_h = (time_s[i] - time_s[i - 1]) / 3600.0
        a0, a1 = abs(i0) if active0 else 0.0, abs(i1) if active1 else 0.0
        capacity_ah += 0.5 * (a0 + a1) * dt_h
        energy_wh += 0.5 * (a0 * voltage_v[i - 1] + a1 * voltage_v[i]) * dt_h
    return capacity_ah, energy_wh


def actual_soc(time_s, current_c):
    out = [0.01]
    for i in range(1, len(time_s)):
        dt_h = (time_s[i] - time_s[i - 1]) / 3600.0
        out.append(out[-1] + 0.5 * (current_c[i - 1] + current_c[i]) * dt_h)
    return out


def closest_index(soc, current_c, target, phase):
    sign = 1 if phase == "charge" else -1
    choices = [i for i, c in enumerate(current_c) if c * sign > 0.1]
    if not choices:
        return None
    return min(choices, key=lambda i: abs(soc[i] - target))


def write_spatial(model, dataset, mode_label, series, stages):
    files = []
    for phase, target, index in stages:
        if index is None:
            continue
        solnum = index + 1
        for region, domain in REGIONS.items():
            if region == "negative":
                fields = {
                    "pressure_Pa": "p_comp_neg_v8",
                    "porosity": "epsl_neg_v8",
                    "stoichiometry": "theta_neg_v8",
                    "breathing_strain": "eps_breath_neg_v8",
                    "electrolyte_concentration_mol_m3": "cl",
                }
            elif region == "separator":
                fields = {
                    "pressure_Pa": "p_comp_sep_v8",
                    "porosity": "epsl_sep_v8",
                    "electrolyte_concentration_mol_m3": "cl",
                }
            else:
                fields = {
                    "pressure_Pa": "p_comp_pos_v8",
                    "porosity": "epsl_pos_v8",
                    "stoichiometry": "theta_pos_v8",
                    "breathing_strain": "eps_breath_pos_v8",
                    "electrolyte_concentration_mol_m3": "cl",
                }
            coords = None
            values_by_name = {}
            for name, expr in fields.items():
                current_coords, _, values = eval_field(model, dataset, expr, 2, [domain], solnum)
                if coords is None:
                    coords = current_coords
                values_by_name[name] = values
            path = DATA_DIR / f"spatial_{mode_label}_{phase}_SOC{int(target*100):02d}_{region}.csv"
            with path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["r_um", "z_um", *values_by_name.keys()])
                for j in range(len(coords[0])):
                    writer.writerow([coords[0][j], coords[1][j], *[v[j] for v in values_by_name.values()]])
            files.append(str(path))

        interface_path = DATA_DIR / f"interfaces_{mode_label}_{phase}_SOC{int(target*100):02d}.csv"
        with interface_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["interface", "boundary", "r_um", "z_um", "surface_stoichiometry"])
            for interface, boundary in INTERFACES.items():
                coords, _, values = eval_field(
                    model, dataset, "liion.cs_surface/liion.csmax", 1, [boundary], solnum
                )
                for j in sorted(range(len(values)), key=lambda k: coords[0][k]):
                    writer.writerow([interface, boundary, coords[0][j], coords[1][j], values[j]])
        files.append(str(interface_path))

        shell_path = DATA_DIR / f"shell_current_{mode_label}_{phase}_SOC{int(target*100):02d}.csv"
        coords, elements, values = eval_field(
            model, dataset, "sqrt(liion.Isr^2+liion.Isz^2)", 2, [1, 2, 8, 9, 10], solnum
        )
        with shell_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["r_um", "z_um", "shell_current_density_A_m2"])
            for j in range(len(values)):
                writer.writerow([coords[0][j], coords[1][j], values[j]])
        files.append(str(shell_path))
    return files


DATA_DIR.mkdir(parents=True, exist_ok=True)
payload = {
    "source": MODEL,
    "solved_model": SOLVED_MODEL,
    "protocol": {"force_N": 100, "C_rate": 0.5, "rest_s": 600, "t_end_s": 18000},
    "cases": {},
}

for mode, mode_label in MODES:
    tag = f"coin_v9_cycle_mode_{mode}"
    model = ModelUtil.load(tag, MODEL)
    case = {"mode": mode, "label": mode_label}
    try:
        model.param().set("F_ext", "100[N]")
        model.param().set("breathing_mode", str(mode))
        step = model.study("std_v9").feature("time")
        step.set("tlist", "range(0,60,18000)")
        step.set("useparam", "off")
        before = set(tags(model.sol()))
        started = clock.time()
        model.study("std_v9").run()
        case["solve_elapsed_s"] = clock.time() - started
        new_solutions = [x for x in tags(model.sol()) if x not in before]
        candidates = []
        for dataset in tags(model.result().dataset()):
            if solution_of(model, dataset) not in new_solutions:
                continue
            try:
                times = global_series(model, dataset, "t", "s")
                candidates.append((dataset, times))
            except Exception:
                continue
        if not candidates:
            raise RuntimeError(f"No readable transient dataset for {new_solutions}")
        dataset, times = max(candidates, key=lambda item: (max(item[1]), len(item[1])))
        series = {
            "time_s": times,
            "voltage_V": global_series(model, dataset, "vol_loaded", "V"),
            "current_A": global_series(model, dataset, "I", "A"),
            "current_Crate": global_series(model, dataset, "I/i_1C", "1"),
            "charge_state": global_series(model, dataset, "charge1", "1"),
            "discharge_state": global_series(model, dataset, "discharge1", "1"),
            "theta_neg": domain_average(model, dataset, "theta_neg_v8", "1", 4),
            "theta_pos": domain_average(model, dataset, "theta_pos_v8", "1", 6),
            "eps_breath_neg": domain_average(model, dataset, "eps_breath_neg_v8", "1", 4),
            "eps_breath_pos": domain_average(model, dataset, "eps_breath_pos_v8", "1", 6),
            "p_neg_MPa": domain_average(model, dataset, "p_comp_neg_v8", "MPa", 4),
            "p_sep_MPa": domain_average(model, dataset, "p_comp_sep_v8", "MPa", 5),
            "p_pos_MPa": domain_average(model, dataset, "p_comp_pos_v8", "MPa", 6),
            "epsl_neg": domain_average(model, dataset, "epsl_neg_v8", "1", 4),
            "epsl_sep": domain_average(model, dataset, "epsl_sep_v8", "1", 5),
            "epsl_pos": domain_average(model, dataset, "epsl_pos_v8", "1", 6),
            "cl_min_mol_m3": domain_min(model, dataset, "cl", "mol/m^3", [4, 5, 6]),
            "cl_max_mol_m3": domain_max(model, dataset, "cl", "mol/m^3", [4, 5, 6]),
            "top_disp_um": boundary_max(model, dataset, "solid.disp", "um", 20),
        }
        series["actual_SOC"] = actual_soc(times, series["current_Crate"])
        charge_ah, charge_wh = integrate_phase(times, series["current_A"], series["voltage_V"], True)
        discharge_ah, discharge_wh = integrate_phase(times, series["current_A"], series["voltage_V"], False)
        charge_idx = [i for i, x in enumerate(series["current_Crate"]) if x > 0.1]
        discharge_idx = [i for i, x in enumerate(series["current_Crate"]) if x < -0.1]
        metrics = {
            "charge_capacity_Ah": charge_ah,
            "discharge_capacity_Ah": discharge_ah,
            "charge_energy_Wh": charge_wh,
            "discharge_energy_Wh": discharge_wh,
            "coulombic_efficiency_pct": 100 * discharge_ah / charge_ah if charge_ah else None,
            "energy_efficiency_pct": 100 * discharge_wh / charge_wh if charge_wh else None,
            "charge_end_time_s": times[max(charge_idx)] if charge_idx else None,
            "discharge_start_time_s": times[min(discharge_idx)] if discharge_idx else None,
            "discharge_end_time_s": times[max(discharge_idx)] if discharge_idx else None,
            "maximum_charge_SOC_pct": 100 * max(series["actual_SOC"]),
            "minimum_final_SOC_pct": 100 * min(series["actual_SOC"]),
            "maximum_graphite_breathing_pct": 100 * max(series["eps_breath_neg"]),
            "minimum_lfp_breathing_pct": 100 * min(series["eps_breath_pos"]),
            "pressure_peak_MPa": max(
                max(series["p_neg_MPa"]), max(series["p_sep_MPa"]), max(series["p_pos_MPa"])
            ),
            "minimum_porosity": min(min(series["epsl_neg"]), min(series["epsl_sep"]), min(series["epsl_pos"])),
            "maximum_electrolyte_span_mol_m3": max(
                hi - lo for lo, hi in zip(series["cl_min_mol_m3"], series["cl_max_mol_m3"])
            ),
            "top_displacement_range_um": [min(series["top_disp_um"]), max(series["top_disp_um"])],
        }
        stages = []
        for phase in ("charge", "discharge"):
            for target in (0.10, 0.50, 0.85):
                stages.append((phase, target, closest_index(series["actual_SOC"], series["current_Crate"], target, phase)))
        discharge_finished = bool(
            discharge_idx
            and max(discharge_idx) < len(times) - 1
            and abs(series["current_Crate"][-1]) < 0.1
            and min(series["voltage_V"][i] for i in discharge_idx) <= 2.51
        )
        case.update({
            "ok": bool(charge_idx and discharge_finished and max(times) >= 17999.9),
            "discharge_finished": discharge_finished,
            "dataset": dataset,
            "new_solutions": new_solutions,
            "series": series,
            "metrics": metrics,
            "stage_indices": [
                {"phase": phase, "target_SOC": target, "index": idx, "solnum": idx + 1 if idx is not None else None}
                for phase, target, idx in stages
            ],
        })
        if mode in (0, 2):
            case["spatial_files"] = write_spatial(model, dataset, mode_label, series, stages)
        if mode == 2:
            model.save(SOLVED_MODEL)
    except Exception as exc:
        case.update({"ok": False, "error": str(exc)})
    finally:
        ModelUtil.remove(tag)
    payload["cases"][mode_label] = case
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"case": mode_label, "ok": case.get("ok"), "error": case.get("error")}, ensure_ascii=False), flush=True)

payload["ok"] = all(case.get("ok") for case in payload["cases"].values())
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload["ok"], "output": str(OUTPUT), "solved_model": SOLVED_MODEL}, ensure_ascii=False))
