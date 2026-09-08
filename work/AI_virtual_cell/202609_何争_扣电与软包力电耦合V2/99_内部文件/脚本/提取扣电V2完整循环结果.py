import csv
import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_0p5C_100N完整耦合_已计算.mph"
TASK = Path(r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2")
DATA = TASK / "99_内部文件" / "中间数据"
JSON_DIR = TASK / "99_内部文件" / "JSON"
DATASET = "dset5"

REGIONS = {"正极": 4, "隔膜": 5, "负极": 6}
INTERFACES = {
    "正极-铝箔": 9,
    "正极-隔膜": 11,
    "负极-隔膜": 13,
    "负极-铜箔": 15,
}
CURRENT_DOMAINS = [1, 2, 3, 7, 8, 9, 10]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def numerical_series(model, kind, expr, unit, selection=None):
    manager = model.result().numerical()
    tag = "__coin_v2_series"
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", DATASET)
    node.set("expr", [expr])
    node.set("unit", [unit])
    if selection is not None:
        node.selection().set(selection)
    try:
        return [float(x) for x in node.getReal()[0]]
    finally:
        remove(manager, tag)


def global_series(model, expr, unit="1"):
    return numerical_series(model, "EvalGlobal", expr, unit)


def domain_average(model, expr, unit, domain):
    return numerical_series(model, "AvSurface", expr, unit, [domain])


def domain_min(model, expr, unit, domains):
    return numerical_series(model, "MinSurface", expr, unit, domains)


def domain_max(model, expr, unit, domains):
    return numerical_series(model, "MaxSurface", expr, unit, domains)


def boundary_max(model, expr, unit, boundary):
    return numerical_series(model, "MaxLine", expr, unit, [boundary])


def eval_field(model, expr, entity_dim, entities, solnum):
    manager = model.result().numerical()
    tag = "__coin_v2_field"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", DATASET)
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.selection().geom("geom1", entity_dim)
    node.selection().set(entities)
    try:
        raw = node.getReal()
        values = [float(row[0]) for row in raw]
        coords = [[float(x) for x in row] for row in node.getCoordinates()]
        return coords, values
    finally:
        remove(manager, tag)


def integrate_phase(time_s, current_a, voltage_v, positive):
    capacity_ah = 0.0
    energy_wh = 0.0
    for i in range(1, len(time_s)):
        i0, i1 = current_a[i - 1], current_a[i]
        active0 = i0 > 1e-10 if positive else i0 < -1e-10
        active1 = i1 > 1e-10 if positive else i1 < -1e-10
        if not (active0 or active1):
            continue
        dt_h = (time_s[i] - time_s[i - 1]) / 3600.0
        a0 = abs(i0) if active0 else 0.0
        a1 = abs(i1) if active1 else 0.0
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
    sign = 1 if phase == "充电" else -1
    candidates = [i for i, value in enumerate(current_c) if value * sign > 0.1]
    return min(candidates, key=lambda i: abs(soc[i] - target))


def nearest_time_index(time_s, target):
    return min(range(len(time_s)), key=lambda i: abs(time_s[i] - target))


DATA.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)
try:
    ModelUtil.remove("coin_v2_extract")
except Exception:
    pass
m = ModelUtil.load("coin_v2_extract", MODEL)

series = {
    "time_s": global_series(m, "t", "s"),
    "terminal_voltage_V": global_series(m, "vol_loaded", "V"),
    "cell_voltage_V": global_series(m, "vol", "V"),
    "current_A": global_series(m, "I", "A"),
    "current_Crate": global_series(m, "I/i_1C", "1"),
    "charge_state": global_series(m, "charge1", "1"),
    "discharge_state": global_series(m, "discharge1", "1"),
    "charge_hold_state": global_series(m, "charge_hold", "1"),
    "discharge_hold_state": global_series(m, "discharge_hold", "1"),
    "theta_negative": domain_average(m, "theta_neg_v8", "1", 6),
    "theta_positive": domain_average(m, "theta_pos_v8", "1", 4),
    "breathing_strain_negative": domain_average(m, "eps_breath_neg_v8", "1", 6),
    "breathing_strain_positive": domain_average(m, "eps_breath_pos_v8", "1", 4),
    "pressure_negative_MPa": domain_average(m, "p_comp_neg_v8", "MPa", 6),
    "pressure_separator_MPa": domain_average(m, "p_comp_sep_v8", "MPa", 5),
    "pressure_positive_MPa": domain_average(m, "p_comp_pos_v8", "MPa", 4),
    "porosity_negative": domain_average(m, "epsl_neg_v8", "1", 6),
    "porosity_separator": domain_average(m, "epsl_sep_v8", "1", 5),
    "porosity_positive": domain_average(m, "epsl_pos_v8", "1", 4),
    "electrolyte_c_negative_mol_m3": domain_average(m, "cl", "mol/m^3", 6),
    "electrolyte_c_separator_mol_m3": domain_average(m, "cl", "mol/m^3", 5),
    "electrolyte_c_positive_mol_m3": domain_average(m, "cl", "mol/m^3", 4),
    "electrolyte_c_min_mol_m3": domain_min(m, "cl", "mol/m^3", [4, 5, 6]),
    "electrolyte_c_max_mol_m3": domain_max(m, "cl", "mol/m^3", [4, 5, 6]),
    "loaded_boundary_displacement_um": boundary_max(m, "solid.disp", "um", 2),
    "contact_voltage_drop_mV": global_series(m, "V_contact_drop", "mV"),
}
series["actual_SOC"] = actual_soc(series["time_s"], series["current_Crate"])
series["electrolyte_span_mol_m3"] = [
    hi - lo for lo, hi in zip(series["electrolyte_c_min_mol_m3"], series["electrolyte_c_max_mol_m3"])
]

charge_indices = [i for i, x in enumerate(series["current_Crate"]) if x > 0.1]
discharge_indices = [i for i, x in enumerate(series["current_Crate"]) if x < -0.1]
charge_last = max(charge_indices)
discharge_first = min(discharge_indices)
discharge_last = max(discharge_indices)
after_discharge = [i for i in range(discharge_last + 1, len(series["time_s"]))]
rest_60_index = nearest_time_index(series["time_s"], series["time_s"][discharge_last] + 60.0)

charge_ah, charge_wh = integrate_phase(
    series["time_s"], series["current_A"], series["terminal_voltage_V"], True
)
discharge_ah, discharge_wh = integrate_phase(
    series["time_s"], series["current_A"], series["terminal_voltage_V"], False
)

metrics = {
    "rated_capacity_Ah": 0.016398503865463064,
    "i_1C_A": 0.016398503865463064,
    "applied_current_A": 0.008199251932731532,
    "force_N": 100.0,
    "charge_capacity_Ah": charge_ah,
    "discharge_capacity_Ah": discharge_ah,
    "charge_energy_Wh": charge_wh,
    "discharge_energy_Wh": discharge_wh,
    "coulombic_efficiency_pct": 100.0 * discharge_ah / charge_ah,
    "energy_efficiency_pct": 100.0 * discharge_wh / charge_wh,
    "charge_end_time_s": series["time_s"][charge_last],
    "discharge_start_time_s": series["time_s"][discharge_first],
    "discharge_end_time_s": series["time_s"][discharge_last],
    "maximum_actual_SOC_pct": 100.0 * max(series["actual_SOC"]),
    "final_actual_SOC_pct": 100.0 * series["actual_SOC"][-1],
    "voltage_at_last_discharge_output_V": series["terminal_voltage_V"][discharge_last],
    "voltage_60s_after_discharge_V": series["terminal_voltage_V"][rest_60_index],
    "final_rest_voltage_V": series["terminal_voltage_V"][-1],
    "rebound_60s_mV": 1000.0 * (
        series["terminal_voltage_V"][rest_60_index] - series["terminal_voltage_V"][discharge_last]
    ),
    "rebound_final_mV": 1000.0 * (
        series["terminal_voltage_V"][-1] - series["terminal_voltage_V"][discharge_last]
    ),
    "theta_negative_range": [min(series["theta_negative"]), max(series["theta_negative"])],
    "theta_positive_range": [min(series["theta_positive"]), max(series["theta_positive"])],
    "maximum_graphite_breathing_pct": 100.0 * max(series["breathing_strain_negative"]),
    "maximum_lfp_breathing_abs_pct": 100.0 * max(abs(x) for x in series["breathing_strain_positive"]),
    "pressure_peak_MPa": max(
        max(series["pressure_negative_MPa"]),
        max(series["pressure_separator_MPa"]),
        max(series["pressure_positive_MPa"]),
    ),
    "minimum_porosity": min(
        min(series["porosity_negative"]),
        min(series["porosity_separator"]),
        min(series["porosity_positive"]),
    ),
    "maximum_electrolyte_span_mol_m3": max(series["electrolyte_span_mol_m3"]),
    "loaded_boundary_displacement_range_um": [
        min(series["loaded_boundary_displacement_um"]),
        max(series["loaded_boundary_displacement_um"]),
    ],
    "maximum_abs_contact_drop_mV": max(abs(x) for x in series["contact_voltage_drop_mV"]),
}

series_csv = DATA / "扣电V2_0p5C_完整循环时序.csv"
with series_csv.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.writer(handle)
    headers = list(series.keys())
    writer.writerow(headers)
    for row in zip(*(series[key] for key in headers)):
        writer.writerow(row)

stages = []
for phase in ("充电", "放电"):
    for target in (0.10, 0.30, 0.50, 0.70, 0.90):
        idx = closest_index(series["actual_SOC"], series["current_Crate"], target, phase)
        stages.append({
            "phase": phase,
            "target_SOC": target,
            "index": idx,
            "solnum": idx + 1,
            "time_s": series["time_s"][idx],
            "actual_SOC": series["actual_SOC"][idx],
        })

spatial_files = []
for stage in stages:
    phase = stage["phase"]
    soc_label = int(round(stage["target_SOC"] * 100))
    solnum = stage["solnum"]

    shell_coords, shell_values = eval_field(
        m, "sqrt(liion.Isr^2+liion.Isz^2)", 2, CURRENT_DOMAINS, solnum
    )
    shell_path = DATA / f"集流构件电流密度_{phase}_SOC{soc_label:02d}.csv"
    with shell_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["r_um", "z_um", "current_density_A_m2"])
        for j, value in enumerate(shell_values):
            writer.writerow([shell_coords[0][j], shell_coords[1][j], value])
    spatial_files.append(str(shell_path))

    interface_path = DATA / f"界面嵌锂状态_{phase}_SOC{soc_label:02d}.csv"
    with interface_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["interface", "boundary", "r_um", "z_um", "electrode_stoichiometry"])
        for interface, boundary in INTERFACES.items():
            theta_expr = "theta_pos_v8" if interface.startswith("正极") else "theta_neg_v8"
            coords, values = eval_field(m, theta_expr, 1, [boundary], solnum)
            order = sorted(range(len(values)), key=lambda k: coords[0][k])
            for j in order:
                writer.writerow([interface, boundary, coords[0][j], coords[1][j], values[j]])
    spatial_files.append(str(interface_path))

    layer_path = DATA / f"局部压力孔隙率_{phase}_SOC{soc_label:02d}.csv"
    with layer_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["region", "domain", "r_um", "z_um", "pressure_Pa", "porosity", "stoichiometry"])
        for region, domain in REGIONS.items():
            p_expr = {"正极": "p_comp_pos_v8", "隔膜": "p_comp_sep_v8", "负极": "p_comp_neg_v8"}[region]
            e_expr = {"正极": "epsl_pos_v8", "隔膜": "epsl_sep_v8", "负极": "epsl_neg_v8"}[region]
            coords, pressure = eval_field(m, p_expr, 2, [domain], solnum)
            _, porosity = eval_field(m, e_expr, 2, [domain], solnum)
            if region == "隔膜":
                stoich = [float("nan")] * len(pressure)
            else:
                theta_expr = "theta_pos_v8" if region == "正极" else "theta_neg_v8"
                _, stoich = eval_field(m, theta_expr, 2, [domain], solnum)
            for j in range(len(pressure)):
                writer.writerow([
                    region, domain, coords[0][j], coords[1][j], pressure[j], porosity[j], stoich[j]
                ])
    spatial_files.append(str(layer_path))

payload = {
    "ok": True,
    "source_model": MODEL,
    "dataset": DATASET,
    "protocol": {
        "force_N": 100,
        "C_rate": 0.5,
        "rest_s": 600,
        "t_end_s": 18000,
        "coupling_on": 1,
        "local_porosity_on": 1,
        "breathing_on": 1,
        "breathing_mode": 2,
    },
    "domain_map": REGIONS,
    "interface_map": INTERFACES,
    "metrics": metrics,
    "stages": stages,
    "series_csv": str(series_csv),
    "spatial_files": spatial_files,
}
summary_path = JSON_DIR / "扣电V2_0p5C_完整循环后处理汇总.json"
summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "metrics": metrics, "summary": str(summary_path)}, ensure_ascii=False))
ModelUtil.remove("coin_v2_extract")
_result = {"ok": True, "summary": str(summary_path), "series_csv": str(series_csv)}
