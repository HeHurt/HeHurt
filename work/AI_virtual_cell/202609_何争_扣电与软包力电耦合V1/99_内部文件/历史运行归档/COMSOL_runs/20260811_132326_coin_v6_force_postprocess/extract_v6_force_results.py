import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260811_132326_coin_v6_force_postprocess")
DATA = RUN / "exported_data"
TAG = "coin_v6_force_saved_solution_export"
FORCES = [0.0, 100.0, 250.0, 500.0]
TARGET_SOC = [0.01, 0.10, 0.30, 0.50, 0.70, 0.85]
SHELL_DOMAINS = [1, 2, 8, 9, 10]
ELECTROLYTE_DOMAINS = {"negative": [4], "separator": [5], "positive": [6]}
INTERFACES = {
    "negative_Cu": 9,
    "negative_separator": 11,
    "positive_separator": 13,
    "positive_Al": 15,
}


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def rows(values):
    return [[float(value) for value in row] for row in values]


def flatten_single(values):
    result = []
    for row in values:
        try:
            result.extend(float(value) for value in row)
        except TypeError:
            result.append(float(row))
    return result


def eval_global(model, data, expressions):
    manager = model.result().numerical()
    tag = "__v6_global_" + data
    remove(manager, tag)
    node = manager.create(tag, "EvalGlobal")
    node.set("data", data)
    node.set("expr", [item[0] for item in expressions])
    node.set("unit", [item[1] for item in expressions])
    values = rows(node.getReal())
    remove(manager, tag)
    return {item[2]: value for item, value in zip(expressions, values)}


def eval_field(model, tag, data, expr, unit, dim, entities, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", data)
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.set("unit", [unit])
    node.selection().geom("geom1", dim)
    node.selection().set(entities)
    values = [row[0] for row in rows(node.getReal())]
    coordinates = rows(node.getCoordinates())
    elements = [[int(value) for value in row] for row in node.getElements()]
    remove(manager, tag)
    return coordinates, elements, values


def stats(values):
    ordered = sorted(values)
    count = len(ordered)
    mean = sum(ordered) / count
    variance = sum((value - mean) ** 2 for value in ordered) / count
    return {
        "min": ordered[0],
        "mean": mean,
        "max": ordered[-1],
        "std": variance ** 0.5,
        "p95": ordered[min(count - 1, int(0.95 * (count - 1)))],
    }


def write_csv(path, fieldnames, data_rows):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_rows)


DATA.mkdir(parents=True, exist_ok=True)
model = ModelUtil.load(TAG, MODEL)
manifest = {"source": MODEL, "datasets": {"electrochem": "dset1", "mechanics": "dset4"}, "files": {}}
try:
    global_data = eval_global(model, "dset1", [
        ("F_ext", "N", "force_N"),
        ("t", "s", "time_s"),
        ("vol", "V", "cell_voltage_V"),
        ("vol_loaded", "V", "loaded_voltage_V"),
        ("I", "A", "current_A"),
        ("I/i_1C", "1", "current_Crate"),
        ("p_ext", "MPa", "pressure_MPa"),
        ("R_contact_eff", "ohm", "contact_resistance_ohm"),
        ("epsl_neg_mech", "1", "epsl_negative"),
        ("epsl_sep_mech", "1", "epsl_separator"),
        ("epsl_pos_mech", "1", "epsl_positive"),
    ])
    count = len(global_data["time_s"])
    records = [{**{key: global_data[key][index] for key in global_data}, "global_solnum": index + 1} for index in range(count)]
    groups = {}
    for force in FORCES:
        groups[force] = [record for record in records if abs(record["force_N"] - force) < 1e-6]
        if not groups[force]:
            raise RuntimeError(f"No saved electrochemical solutions found for F_ext={force} N")

    voltage_rows = []
    stage_rows = []
    stage_indices = {}
    for force, group in groups.items():
        group.sort(key=lambda item: item["time_s"])
        soc = [0.01]
        for index in range(1, len(group)):
            dt = group[index]["time_s"] - group[index - 1]["time_s"]
            soc.append(soc[-1] + 0.5 * (group[index - 1]["current_Crate"] + group[index]["current_Crate"]) * dt / 3600.0)
        for item, value in zip(group, soc):
            item["actual_SOC"] = value
            voltage_rows.append(item)

        active = [index for index, item in enumerate(group) if item["current_Crate"] > 0.25]
        cutoff_index = active[-1]
        requested = [(f"SOC{int(target * 100):02d}", target) for target in TARGET_SOC]
        requested.append(("cutoff", soc[cutoff_index]))
        stage_indices[force] = {}
        for label, target in requested:
            candidates = active if label != "SOC01" else list(range(len(group)))
            local_index = min(candidates, key=lambda idx: abs(soc[idx] - target))
            item = group[local_index]
            stage_indices[force][label] = item["global_solnum"]
            stage_rows.append({
                "force_N": force,
                "stage": label,
                "global_solnum": item["global_solnum"],
                "time_s": item["time_s"],
                "actual_SOC": item["actual_SOC"],
                "cell_voltage_V": item["cell_voltage_V"],
                "loaded_voltage_V": item["loaded_voltage_V"],
                "current_Crate": item["current_Crate"],
                "pressure_MPa": item["pressure_MPa"],
                "contact_resistance_mohm": item["contact_resistance_ohm"] * 1000.0,
                "epsl_negative": item["epsl_negative"],
                "epsl_separator": item["epsl_separator"],
                "epsl_positive": item["epsl_positive"],
            })

    voltage_path = DATA / "force_voltage_soc.csv"
    voltage_fields = ["force_N", "global_solnum", "time_s", "actual_SOC", "cell_voltage_V", "loaded_voltage_V", "current_A", "current_Crate", "pressure_MPa", "contact_resistance_ohm", "epsl_negative", "epsl_separator", "epsl_positive"]
    write_csv(voltage_path, voltage_fields, [{key: row[key] for key in voltage_fields} for row in voltage_rows])
    manifest["files"]["voltage_soc"] = str(voltage_path)

    stage_path = DATA / "force_stage_summary.csv"
    write_csv(stage_path, list(stage_rows[0]), stage_rows)
    manifest["files"]["stage_summary"] = str(stage_path)

    interface_rows = []
    electrolyte_rows = []
    shell_files = {}
    for force in FORCES:
        stage_items = [(label, solnum) for label, solnum in stage_indices[force].items()]
        for label, solnum in stage_items:
            stage = next(row for row in stage_rows if row["force_N"] == force and row["stage"] == label)
            for interface, boundary in INTERFACES.items():
                coords, _, values = eval_field(model, f"__if_{int(force)}_{label}_{boundary}", "dset1", "liion.cs_surface/liion.csmax", "1", 1, [boundary], solnum)
                for index in sorted(range(len(values)), key=lambda idx: coords[0][idx]):
                    interface_rows.append({
                        "force_N": force, "stage": label, "actual_SOC": stage["actual_SOC"],
                        "interface": interface, "boundary": boundary,
                        "r_um": coords[0][index], "z_um": coords[1][index], "stoichiometry": values[index],
                    })
            for region, domains in ELECTROLYTE_DOMAINS.items():
                _, _, values = eval_field(model, f"__cl_{int(force)}_{label}_{region}", "dset1", "cl", "mol/m^3", 2, domains, solnum)
                item = stats(values)
                electrolyte_rows.append({
                    "force_N": force, "stage": label, "actual_SOC": stage["actual_SOC"], "region": region,
                    "cl_min_mol_m3": item["min"], "cl_mean_mol_m3": item["mean"], "cl_max_mol_m3": item["max"], "cl_std_mol_m3": item["std"],
                })

        for label in ("SOC50", "cutoff"):
            solnum = stage_indices[force][label]
            coords, elements, values = eval_field(model, f"__shell_{int(force)}_{label}", "dset1", "sqrt(liion.Isr^2+liion.Isz^2)", "A/m^2", 2, SHELL_DOMAINS, solnum)
            shell_path = DATA / f"shell_current_density_F{int(force)}N_{label}.csv"
            with shell_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["node", "r_um", "z_um", "current_density_A_m2"])
                for index, value in enumerate(values):
                    writer.writerow([index, coords[0][index], coords[1][index], value])
            triangle_path = DATA / f"shell_triangles_F{int(force)}N_{label}.csv"
            with triangle_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["triangle", "node_1", "node_2", "node_3"])
                for index in range(len(elements[0])):
                    writer.writerow([index, elements[0][index], elements[1][index], elements[2][index]])
            shell_files[f"F{int(force)}_{label}"] = {"nodes": str(shell_path), "triangles": str(triangle_path), "stats": stats(values)}

    interface_path = DATA / "force_interface_stoichiometry.csv"
    write_csv(interface_path, list(interface_rows[0]), interface_rows)
    manifest["files"]["interface_stoichiometry"] = str(interface_path)
    electrolyte_path = DATA / "force_electrolyte_summary.csv"
    write_csv(electrolyte_path, list(electrolyte_rows[0]), electrolyte_rows)
    manifest["files"]["electrolyte_summary"] = str(electrolyte_path)
    manifest["files"]["shell_current_density"] = shell_files

    mechanical_rows = []
    for solnum, force in enumerate(FORCES, start=1):
        _, _, disp = eval_field(model, f"__mech_disp_{solnum}", "dset4", "solid.disp", "m", 2, list(range(1, 12)), solnum)
        _, _, mises = eval_field(model, f"__mech_mises_{solnum}", "dset4", "solid.mises", "Pa", 2, list(range(1, 12)), solnum)
        _, _, sep_strain = eval_field(model, f"__mech_sep_{solnum}", "dset4", "solid.eZZ", "1", 2, [5], solnum)
        _, _, top_disp = eval_field(model, f"__mech_top_{solnum}", "dset4", "solid.disp", "m", 1, [20], solnum)
        mechanical_rows.append({
            "force_N": force,
            "pressure_MPa": force / (3.141592653589793 * (12.205e-3) ** 2) / 1e6,
            "max_displacement_um": max(disp) * 1e6,
            "mean_top_displacement_um": sum(top_disp) / len(top_disp) * 1e6,
            "max_von_mises_MPa": max(mises) / 1e6,
            "separator_eZZ_min": min(sep_strain),
            "separator_eZZ_mean": sum(sep_strain) / len(sep_strain),
            "separator_eZZ_max": max(sep_strain),
        })
    mechanical_path = DATA / "force_mechanical_summary.csv"
    write_csv(mechanical_path, list(mechanical_rows[0]), mechanical_rows)
    manifest["files"]["mechanical_summary"] = str(mechanical_path)
    manifest["ok"] = True
finally:
    ModelUtil.remove(TAG)

manifest_path = RUN / "postprocess_manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": manifest.get("ok", False), "manifest": str(manifest_path)}, ensure_ascii=False))
