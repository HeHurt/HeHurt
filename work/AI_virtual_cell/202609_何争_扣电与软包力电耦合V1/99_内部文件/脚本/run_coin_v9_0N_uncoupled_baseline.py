"""Create and solve the matched 0 N / uncoupled / no-breathing coin-cell baseline."""

from __future__ import annotations

import csv
import json
import time as clock
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


TASK = Path(r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V1")
SOURCE = (
    TASK
    / "99_内部文件"
    / "历史运行归档"
    / "COMSOL_runs"
    / "20260820_140000_coin_v9_nonlinear_breathing_cycle"
    / "model_snapshot.mph"
)
OUTPUT_MODEL = TASK / "02_模型" / "扣电_V9_0N_无耦合无呼吸_完整循环.mph"
OUTPUT_JSON = TASK / "99_内部文件" / "JSON" / "coin_v9_0N_uncoupled_no_breath_baseline.json"
OUTPUT_CSV = TASK / "99_内部文件" / "中间数据" / "扣电V9_0N无耦合无呼吸基线时序.csv"
TAG = "coin_v9_0n_uncoupled_baseline"


def tags(manager):
    return [str(item) for item in manager.tags()]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def numerical_series(model, dataset, kind, expression, unit, selection=None):
    manager = model.result().numerical()
    tag = "__coin_baseline_series"
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


def solution_of(model, dataset):
    try:
        return str(model.result().dataset(dataset).getString("solution"))
    except Exception:
        return ""


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


def readback(model):
    comp = model.component("comp1")
    return {
        "parameters": {
            name: str(model.param().get(name))
            for name in ("F_ext", "coupling_on", "breathing_mode")
        },
        "variables": {
            "V_contact_drop": str(comp.variable("var1").get("V_contact_drop")),
            "vol_loaded": str(comp.variable("var1").get("vol_loaded")),
            "eps_breath_neg_v8": str(comp.variable("var_v8_neg").get("eps_breath_neg_v8")),
            "epsl_neg_v8": str(comp.variable("var_v8_neg").get("epsl_neg_v8")),
            "epsl_sep_v8": str(comp.variable("var_v8_sep").get("epsl_sep_v8")),
            "eps_breath_pos_v8": str(comp.variable("var_v8_pos").get("eps_breath_pos_v8")),
            "epsl_pos_v8": str(comp.variable("var_v8_pos").get("epsl_pos_v8")),
        },
        "load_pressure": str(comp.physics("solid").feature("load_top").getString("pressure")),
        "porosity_consumers": {
            "negative": str(comp.physics("liion").feature("pce1").getString("epsl")),
            "separator": str(comp.physics("liion").feature("sep1").getString("epsl")),
            "positive": str(comp.physics("liion").feature("pce2").getString("epsl")),
        },
        "study_tlist": str(model.study("std_v9").feature("time").getString("tlist")),
    }


payload = {
    "ok": False,
    "source": str(SOURCE),
    "output_model": str(OUTPUT_MODEL),
    "protocol": {
        "force_N": 0,
        "coupling_on": 0,
        "breathing_mode": 0,
        "C_rate": 0.5,
        "rest_s": 600,
        "t_end_s": 18000,
    },
}

if SOURCE.resolve() == OUTPUT_MODEL.resolve():
    raise RuntimeError("Refusing to overwrite source model")

model = ModelUtil.load(TAG, str(SOURCE))
try:
    comp = model.component("comp1")
    model.param().set("F_ext", "0[N]", "Baseline external force")
    model.param().set("coupling_on", "0", "0=electrochemical baseline, 1=mechanical feedback")
    model.param().set("breathing_mode", "0")

    comp.variable("var1").set("V_contact_drop", "coupling_on*I*R_contact_eff")
    comp.variable("var_v8_neg").set(
        "eps_breath_neg_v8",
        "coupling_on*if(breathing_mode<0.5,0,if(breathing_mode<1.5,eps_breath_neg_linear_v9,eps_breath_neg_lit_v9))",
    )
    comp.variable("var_v8_neg").set(
        "epsl_neg_v8",
        "epsl_neg+coupling_on*(max(epsl_floor,epsl_neg*(1-beta_neg*p_comp_neg_v8))-epsl_neg)",
    )
    comp.variable("var_v8_sep").set(
        "epsl_sep_v8",
        "epsl_sep+coupling_on*(max(epsl_floor,epsl_sep*(1-beta_sep*p_comp_sep_v8))-epsl_sep)",
    )
    comp.variable("var_v8_pos").set(
        "eps_breath_pos_v8",
        "coupling_on*if(breathing_mode<0.5,0,if(breathing_mode<1.5,eps_breath_pos_linear_v9,eps_breath_pos_lit_v9))",
    )
    comp.variable("var_v8_pos").set(
        "epsl_pos_v8",
        "epsl_pos+coupling_on*(max(epsl_floor,epsl_pos*(1-beta_pos*p_comp_pos_v8))-epsl_pos)",
    )
    comp.physics("solid").feature("load_top").set("pressure", "coupling_on*p_ext")

    step = model.study("std_v9").feature("time")
    step.set("tlist", "range(0,60,18000)")
    step.set("useparam", "off")
    payload["before_solve"] = readback(model)

    solutions_before = set(tags(model.sol()))
    started = clock.time()
    model.study("std_v9").run()
    payload["solve_elapsed_s"] = clock.time() - started
    new_solutions = [item for item in tags(model.sol()) if item not in solutions_before]
    candidates = []
    for dataset in tags(model.result().dataset()):
        if new_solutions and solution_of(model, dataset) not in new_solutions:
            continue
        try:
            times = global_series(model, dataset, "t", "s")
            if times:
                candidates.append((dataset, times))
        except Exception:
            continue
    if not candidates:
        raise RuntimeError(f"No readable transient dataset for new solutions: {new_solutions}")
    dataset, time_s = max(candidates, key=lambda item: (max(item[1]), len(item[1])))

    series = {
        "time_s": time_s,
        "voltage_V": global_series(model, dataset, "vol_loaded", "V"),
        "terminal_voltage_V": global_series(model, dataset, "vol", "V"),
        "current_A": global_series(model, dataset, "I", "A"),
        "current_Crate": global_series(model, dataset, "I/i_1C", "1"),
        "theta_neg": domain_average(model, dataset, "theta_neg_v8", "1", 4),
        "theta_pos": domain_average(model, dataset, "theta_pos_v8", "1", 6),
        "porosity_neg": domain_average(model, dataset, "epsl_neg_v8", "1", 4),
        "porosity_sep": domain_average(model, dataset, "epsl_sep_v8", "1", 5),
        "porosity_pos": domain_average(model, dataset, "epsl_pos_v8", "1", 6),
        "pressure_neg_MPa": domain_average(model, dataset, "p_comp_neg_v8", "MPa", 4),
        "pressure_sep_MPa": domain_average(model, dataset, "p_comp_sep_v8", "MPa", 5),
        "pressure_pos_MPa": domain_average(model, dataset, "p_comp_pos_v8", "MPa", 6),
    }
    charge_indices = [i for i, value in enumerate(series["current_A"]) if value > 1e-8]
    discharge_indices = [i for i, value in enumerate(series["current_A"]) if value < -1e-8]
    if not charge_indices or not discharge_indices:
        raise RuntimeError("Solved series does not contain both charge and discharge")
    discharge_end = max(discharge_indices)
    first_rest = min(discharge_end + 1, len(time_s) - 1)
    charge_ah, charge_wh = integrate_phase(time_s, series["current_A"], series["voltage_V"], True)
    discharge_ah, discharge_wh = integrate_phase(time_s, series["current_A"], series["voltage_V"], False)
    metrics = {
        "dataset": dataset,
        "new_solutions": new_solutions,
        "time_count": len(time_s),
        "tmax_s": max(time_s),
        "charge_capacity_Ah": charge_ah,
        "discharge_capacity_Ah": discharge_ah,
        "charge_energy_Wh": charge_wh,
        "discharge_energy_Wh": discharge_wh,
        "charge_end_time_s": time_s[max(charge_indices)],
        "discharge_start_time_s": time_s[min(discharge_indices)],
        "discharge_end_time_s": time_s[discharge_end],
        "cutoff_loaded_voltage_V": series["voltage_V"][discharge_end],
        "immediate_rest_voltage_V": series["voltage_V"][first_rest],
        "settled_voltage_V": series["voltage_V"][-1],
        "instantaneous_rebound_mV": 1000 * (
            series["voltage_V"][first_rest] - series["voltage_V"][discharge_end]
        ),
        "total_rebound_mV": 1000 * (
            series["voltage_V"][-1] - series["voltage_V"][discharge_end]
        ),
        "final_theta_neg": series["theta_neg"][-1],
        "final_theta_pos": series["theta_pos"][-1],
        "maximum_absolute_pressure_MPa": max(
            abs(value)
            for name in ("pressure_neg_MPa", "pressure_sep_MPa", "pressure_pos_MPa")
            for value in series[name]
        ),
        "porosity_ranges": {
            name: [min(series[name]), max(series[name])]
            for name in ("porosity_neg", "porosity_sep", "porosity_pos")
        },
    }
    payload["metrics"] = metrics

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        columns = list(series)
        writer.writerow(columns)
        writer.writerows(zip(*(series[name] for name in columns)))
    payload["timeseries_csv"] = str(OUTPUT_CSV)

    model.label("Coin V9 - 0 N uncoupled no-breathing full cycle")
    model.save(str(OUTPUT_MODEL))
finally:
    ModelUtil.remove(TAG)

verify_tag = TAG + "_verify"
verified = ModelUtil.load(verify_tag, str(OUTPUT_MODEL))
try:
    payload["after_reload"] = readback(verified)
    payload["reload_checks"] = {
        "force_is_0N": payload["after_reload"]["parameters"]["F_ext"] == "0[N]",
        "coupling_is_off": payload["after_reload"]["parameters"]["coupling_on"] == "0",
        "breathing_is_off": payload["after_reload"]["parameters"]["breathing_mode"] == "0",
        "contact_feedback_is_switched": payload["after_reload"]["variables"]["V_contact_drop"]
        == "coupling_on*I*R_contact_eff",
        "load_is_switched": payload["after_reload"]["load_pressure"] == "coupling_on*p_ext",
        "reached_18000s": payload["metrics"]["tmax_s"] >= 17999.9,
        "full_charge_discharge": (
            payload["metrics"]["charge_capacity_Ah"] > 0
            and payload["metrics"]["discharge_capacity_Ah"] > 0
            and payload["metrics"]["discharge_end_time_s"] < payload["metrics"]["tmax_s"]
        ),
    }
    payload["ok"] = all(payload["reload_checks"].values())
finally:
    ModelUtil.remove(verify_tag)

OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload["ok"], "output_model": str(OUTPUT_MODEL), "metrics": payload["metrics"]}, ensure_ascii=False))
