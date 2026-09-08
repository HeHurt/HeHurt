import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity_solved.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_102725_coin_v7_local_porosity_full_sweep")
DATA = RUN / "exported_data"
OUTPUT = RUN / "postprocess_manifest.json"
TAG = "coin_v7_full_results_extract"
DATASET = "dset5"
FORCES = [0.0, 100.0, 250.0, 500.0]
TARGET_SOC = [0.01, 0.10, 0.30, 0.50, 0.70, 0.85]
REGIONS = {
    "negative": {"domain": [4], "pressure": "p_comp_neg_v7", "porosity": "epsl_neg_v7"},
    "separator": {"domain": [5], "pressure": "p_comp_sep_v7", "porosity": "epsl_sep_v7"},
    "positive": {"domain": [6], "pressure": "p_comp_pos_v7", "porosity": "epsl_pos_v7"},
}
INTERFACES = {"negative_Cu": 9, "negative_separator": 11, "positive_separator": 13, "positive_Al": 15}
SHELL_DOMAINS = [1, 2, 8, 9, 10]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def rows(values):
    return [[float(value) for value in row] for row in values]


def global_data(model, expressions):
    manager = model.result().numerical()
    tag = "__v7_global"
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", DATASET)
    node.set("expr", [item[0] for item in expressions])
    node.set("unit", [item[1] for item in expressions])
    values = rows(node.getReal())
    remove(manager, tag)
    return {item[2]: value for item, value in zip(expressions, values)}


def field(model, tag, expression, unit, dimension, entities, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", DATASET)
    node.set("solnum", str(solnum))
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().geom("geom1", dimension)
    node.selection().set(entities)
    values = [row[0] for row in rows(node.getReal())]
    coordinates = rows(node.getCoordinates())
    remove(manager, tag)
    return coordinates, values


def stats(values):
    ordered = sorted(values)
    count = len(ordered)
    mean = sum(ordered) / count
    variance = sum((value - mean) ** 2 for value in ordered) / count
    return {"min": ordered[0], "mean": mean, "max": ordered[-1], "std": variance ** 0.5, "span": ordered[-1] - ordered[0]}


def write_dicts(path, data):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


DATA.mkdir(parents=True, exist_ok=True)
model = ModelUtil.load(TAG, MODEL)
manifest = {"source": MODEL, "dataset": DATASET, "files": {}}
try:
    global_values = global_data(model, [
        ("F_ext", "N", "force_N"), ("t", "s", "time_s"),
        ("vol", "V", "cell_voltage_V"), ("vol_loaded", "V", "loaded_voltage_V"),
        ("I", "A", "current_A"), ("I/i_1C", "1", "current_Crate"),
        ("p_ext", "MPa", "nominal_pressure_MPa"),
        ("R_contact_eff", "ohm", "contact_resistance_ohm"),
    ])
    count = len(global_values["time_s"])
    records = [{**{key: global_values[key][index] for key in global_values}, "global_solnum": index + 1} for index in range(count)]
    groups = {force: [row for row in records if abs(row["force_N"] - force) < 1e-8] for force in FORCES}
    voltage_rows = []
    stage_rows = []
    stage_lookup = {}
    for force, group in groups.items():
        if len(group) != 363:
            raise RuntimeError(f"Expected 363 saved states for {force} N, got {len(group)}")
        group.sort(key=lambda item: item["time_s"])
        soc = [0.01]
        for index in range(1, len(group)):
            dt = group[index]["time_s"] - group[index - 1]["time_s"]
            soc.append(soc[-1] + 0.5 * (group[index - 1]["current_Crate"] + group[index]["current_Crate"]) * dt / 3600)
        for item, value in zip(group, soc):
            item["actual_SOC"] = value
            voltage_rows.append(item)
        active = [index for index, item in enumerate(group) if item["current_Crate"] > 0.25]
        cutoff_index = active[-1]
        requested = [(f"SOC{int(target * 100):02d}", target) for target in TARGET_SOC] + [("cutoff", soc[cutoff_index])]
        for label, target in requested:
            candidates = active if label != "SOC01" else list(range(len(group)))
            local_index = min(candidates, key=lambda idx: abs(soc[idx] - target))
            item = group[local_index]
            stage = {
                "force_N": force, "stage": label, "global_solnum": item["global_solnum"],
                "time_s": item["time_s"], "actual_SOC": item["actual_SOC"],
                "cell_voltage_V": item["cell_voltage_V"], "loaded_voltage_V": item["loaded_voltage_V"],
                "current_Crate": item["current_Crate"], "nominal_pressure_MPa": item["nominal_pressure_MPa"],
                "contact_resistance_mohm": item["contact_resistance_ohm"] * 1000,
            }
            stage_rows.append(stage)
            stage_lookup[(force, label)] = stage

    voltage_path = DATA / "v7_voltage_soc.csv"
    write_dicts(voltage_path, voltage_rows)
    stage_path = DATA / "v7_stage_summary.csv"
    write_dicts(stage_path, stage_rows)
    manifest["files"].update({"voltage_soc": str(voltage_path), "stage_summary": str(stage_path)})

    region_rows = []
    electrolyte_rows = []
    interface_rows = []
    shell_rows = []
    for force in FORCES:
        for label in ["SOC01", "SOC10", "SOC30", "SOC50", "SOC70", "SOC85", "cutoff"]:
            stage = stage_lookup[(force, label)]
            solnum = stage["global_solnum"]
            for region, item in REGIONS.items():
                _, pressure = field(model, "__v7_pressure", item["pressure"], "MPa", 2, item["domain"], solnum)
                _, porosity = field(model, "__v7_porosity", item["porosity"], "1", 2, item["domain"], solnum)
                _, concentration = field(model, "__v7_cl", "cl", "mol/m^3", 2, item["domain"], solnum)
                ps = stats(pressure)
                es = stats(porosity)
                cs = stats(concentration)
                region_rows.append({
                    "force_N": force, "stage": label, "actual_SOC": stage["actual_SOC"], "region": region,
                    **{f"pressure_{key}_MPa": value for key, value in ps.items()},
                    **{f"porosity_{key}": value for key, value in es.items()},
                })
                electrolyte_rows.append({
                    "force_N": force, "stage": label, "actual_SOC": stage["actual_SOC"], "region": region,
                    **{f"cl_{key}_mol_m3": value for key, value in cs.items()},
                })
            for interface, boundary in INTERFACES.items():
                coords, theta = field(model, "__v7_theta", "liion.cs_surface/liion.csmax", "1", 1, [boundary], solnum)
                theta_stats = stats(theta)
                interface_rows.append({
                    "force_N": force, "stage": label, "actual_SOC": stage["actual_SOC"], "interface": interface,
                    **{f"stoichiometry_{key}": value for key, value in theta_stats.items()},
                })
            _, shell_current = field(model, "__v7_shell", "sqrt(liion.Isr^2+liion.Isz^2)", "A/m^2", 2, SHELL_DOMAINS, solnum)
            shell_stats = stats(shell_current)
            shell_rows.append({
                "force_N": force, "stage": label, "actual_SOC": stage["actual_SOC"],
                **{f"shell_current_{key}_A_m2": value for key, value in shell_stats.items()},
            })

    for name, data in [
        ("v7_local_pressure_porosity.csv", region_rows),
        ("v7_electrolyte_summary.csv", electrolyte_rows),
        ("v7_interface_stoichiometry_summary.csv", interface_rows),
        ("v7_shell_current_summary.csv", shell_rows),
    ]:
        path = DATA / name
        write_dicts(path, data)
        manifest["files"][name.removesuffix(".csv")] = str(path)

    manifest["counts"] = {"saved_states": count, "states_per_force": {str(force): len(group) for force, group in groups.items()}}
    manifest["ok"] = True
except Exception as exc:
    manifest.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": manifest.get("ok"), "output": str(OUTPUT), "error": manifest.get("error")}, ensure_ascii=False))
