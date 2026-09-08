import csv
import json
import time as clock
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_2d_cross_section_v7_capacity_consistent_coupled_100N_full_cycle_solved.mph"
OUTPUT = RUN / "pouch_dual_tab_2d_cross_section_v8_rated_0p13Ah_coupled_100N_full_cycle_solved.mph"
RESULT_DIR = RUN / "postprocess_v8_rated_0p13Ah"
CSV_PATH = RESULT_DIR / "timeseries_v8_rated_0p13Ah.csv"
RESULT_PATH = RESULT_DIR / "v8_rated_0p13Ah_result.json"
TAG = "pouch_v8_rated_0p13Ah"


def tags(manager):
    return [str(item) for item in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def numerical_series(model, dataset, kind, expression, unit, selection=None, named_selection=None):
    manager = model.result().numerical()
    tag = "__v8_series"
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", dataset)
    node.set("expr", [expression])
    node.set("unit", [unit])
    if named_selection is not None:
        node.selection().named(named_selection)
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


def boundary_average(model, dataset, expression, unit, named_selection):
    return numerical_series(
        model, dataset, "AvLine", expression, unit, named_selection=named_selection
    )


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
        raise RuntimeError("No readable transient dataset in solved model")
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
        energy_wh += 0.5 * (
            a0 * voltage_v[index - 1] + a1 * voltage_v[index]
        ) * dt_h
    return capacity_ah, energy_wh


def main():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": False,
        "source": str(SOURCE),
        "output_model": str(OUTPUT),
        "protocol": {
            "rated_capacity_Ah": 0.13,
            "i_1C_A": 0.13,
            "C_rate": 0.5,
            "applied_current_A": 0.065,
            "charge_cutoff_V": 3.65,
            "rest_s": 600,
            "discharge_cutoff_V": 2.50,
            "end_time_s": 18000,
        },
    }
    model = ModelUtil.load(TAG, str(SOURCE))
    try:
        model.param().set("C_nom_pouch", "0.13[A*h]", "Rated pouch-cell capacity")
        model.param().set("i_1C", "C_nom_pouch/1[h]", "1C current from rated capacity")
        model.param().set("C_rate", "0.5", "Charge/discharge rate based on rated capacity")
        model.param().set("coupling_on", "1")
        model.param().set("breathing_mode", "2")
        model.param().set("F_ext", "100[N]")
        variables = model.component("comp1").variable("var1")
        variables.set("I", "i_1C*C_rate*(charge1-discharge1)")
        variables.set("I_app", "I")

        started = clock.time()
        model.study("std_cycle").run()
        payload["solve_elapsed_s"] = clock.time() - started
        model.label("Single-layer pouch 2D V8 - rated 0.13 Ah, coupled 100 N, 0.5C full cycle")
        model.save(str(OUTPUT))

        dataset, time_s = choose_dataset(model)
        voltage_v = global_series(model, dataset, "vol_loaded", "V")
        current_a = global_series(model, dataset, "I", "A")
        charge_state = global_series(model, dataset, "charge1", "1")
        discharge_state = global_series(model, dataset, "discharge1", "1")
        theta_neg = domain_average(model, dataset, "theta_neg_v4", "1", 4)
        theta_pos = domain_average(model, dataset, "theta_pos_v4", "1", 6)
        top_v_um = boundary_average(model, dataset, "v", "um", "sel_mech_top")
        bottom_v_um = boundary_average(model, dataset, "v", "um", "sel_mech_bottom")
        signed_thickness_change_um = [
            top - bottom for top, bottom in zip(top_v_um, bottom_v_um)
        ]
        reference = signed_thickness_change_um[0]
        relative_thickness_change_um = [
            value - reference for value in signed_thickness_change_um
        ]
        relative_thickness_strain_pct = [
            100.0 * value / 0.3455 for value in relative_thickness_change_um
        ]
        electrode_soc_neg = [(value - 0.05) / 0.91 for value in theta_neg]
        electrode_soc_pos = [(1.0 - value) / 0.98 for value in theta_pos]
        electrode_soc = [
            0.5 * (negative + positive)
            for negative, positive in zip(electrode_soc_neg, electrode_soc_pos)
        ]

        charge_ah, charge_wh = integrate_phase(time_s, current_a, voltage_v, True)
        discharge_ah, discharge_wh = integrate_phase(time_s, current_a, voltage_v, False)
        charge_indices = [index for index, value in enumerate(current_a) if value > 1e-6]
        discharge_indices = [index for index, value in enumerate(current_a) if value < -1e-6]
        payload.update({
            "dataset": dataset,
            "reload_assertions": {
                "C_nom_pouch": str(model.param().get("C_nom_pouch")),
                "i_1C": str(model.param().get("i_1C")),
                "C_rate": str(model.param().get("C_rate")),
                "current_expression": str(variables.get("I")),
                "coupling_on": str(model.param().get("coupling_on")),
                "breathing_mode": str(model.param().get("breathing_mode")),
                "F_ext": str(model.param().get("F_ext")),
            },
            "metrics": {
                "time_end_s": max(time_s),
                "current_charge_peak_A": max(current_a),
                "current_discharge_peak_A": abs(min(current_a)),
                "charge_capacity_Ah": charge_ah,
                "discharge_capacity_Ah": discharge_ah,
                "charge_energy_Wh": charge_wh,
                "discharge_energy_Wh": discharge_wh,
                "coulombic_efficiency_pct": 100.0 * discharge_ah / charge_ah,
                "energy_efficiency_pct": 100.0 * discharge_wh / charge_wh,
                "charge_end_time_s": time_s[max(charge_indices)],
                "discharge_start_time_s": time_s[min(discharge_indices)],
                "discharge_end_time_s": time_s[max(discharge_indices)],
                "maximum_electrode_SOC_pct": 100.0 * max(electrode_soc),
                "voltage_min_V": min(voltage_v),
                "voltage_max_V": max(voltage_v),
                "relative_thickness_change_min_um": min(relative_thickness_change_um),
                "relative_thickness_change_max_um": max(relative_thickness_change_um),
                "relative_thickness_strain_min_pct": min(relative_thickness_strain_pct),
                "relative_thickness_strain_max_pct": max(relative_thickness_strain_pct),
            },
        })

        with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "time_s", "voltage_V", "current_A", "charge_state", "discharge_state",
                "theta_neg", "theta_pos", "electrode_SOC", "top_v_um", "bottom_v_um",
                "signed_thickness_change_um", "relative_thickness_change_um",
                "relative_thickness_strain_pct",
            ])
            writer.writerows(zip(
                time_s, voltage_v, current_a, charge_state, discharge_state,
                theta_neg, theta_pos, electrode_soc, top_v_um, bottom_v_um,
                signed_thickness_change_um, relative_thickness_change_um,
                relative_thickness_strain_pct,
            ))
        payload["timeseries_csv"] = str(CSV_PATH)
        payload["ok"] = True
    finally:
        ModelUtil.remove(TAG)

    verify_tag = TAG + "_reload"
    reloaded = ModelUtil.load(verify_tag, str(OUTPUT))
    try:
        dataset, times = choose_dataset(reloaded)
        current = global_series(reloaded, dataset, "I", "A")
        payload["reload_verification"] = {
            "dataset": dataset,
            "time_end_s": max(times),
            "C_nom_pouch": str(reloaded.param().get("C_nom_pouch")),
            "i_1C": str(reloaded.param().get("i_1C")),
            "C_rate": str(reloaded.param().get("C_rate")),
            "current_expression": str(reloaded.component("comp1").variable("var1").get("I")),
            "current_charge_peak_A": max(current),
            "current_discharge_peak_A": abs(min(current)),
        }
    finally:
        ModelUtil.remove(verify_tag)

    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps({
        "ok": payload["ok"],
        "output_model": str(OUTPUT),
        "result": str(RESULT_PATH),
        "metrics": payload.get("metrics"),
    }, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")


try:
    main()
except Exception:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    failure = {"ok": False, "traceback": traceback.format_exc()}
    RESULT_PATH.write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps(failure, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")
    raise
