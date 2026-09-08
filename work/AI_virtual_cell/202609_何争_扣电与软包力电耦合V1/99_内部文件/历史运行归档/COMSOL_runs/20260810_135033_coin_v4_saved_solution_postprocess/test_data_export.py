import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V4.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_135033_coin_v4_saved_solution_postprocess")
DATA = RUN / "exported_data"
OUTPUT = RUN / "postprocess_manifest.json"
TAG = "coin_v4_saved_solution_export"

SHELL_DOMAINS = [1, 2, 8, 9, 10]
INTERFACES = {
    "negative_Cu": 9,
    "negative_separator": 11,
    "positive_separator": 13,
    "positive_Al": 15,
}
STAGES = [
    ("SOC01", 1),
    ("SOC10", 33),
    ("SOC30", 105),
    ("SOC50", 177),
    ("SOC70", 249),
    ("SOC85", 303),
    ("cutoff_SOC89", 319),
]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def as_rows(java_array):
    return [[float(value) for value in row] for row in java_array]


def eval_field(model, tag, expr, entity_dim, entities, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.selection().geom("geom1", entity_dim)
    node.selection().set(entities)
    values = [row[0] for row in as_rows(node.getReal())]
    coordinates = as_rows(node.getCoordinates())
    elements = [[int(value) for value in row] for row in node.getElements()]
    remove(manager, tag)
    return coordinates, elements, values


def scalar(model, tag, kind, expr, selection, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, kind)
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", expr)
    if selection is not None:
        node.selection().set(selection)
    value = node.getReal()
    while hasattr(value, "__len__") and len(value) == 1:
        value = value[0]
    remove(manager, tag)
    return float(value)


DATA.mkdir(parents=True, exist_ok=True)
model = ModelUtil.load(TAG, MODEL)
manifest = {"source": MODEL, "dataset": "dset1", "files": {}, "stages": []}
try:
    times = [float(value) for value in model.sol("sol1").getPVals()]
    current_c = [scalar(model, "__crate", "EvalGlobal", "I/i_1C", None, i) for i in range(1, len(times) + 1)]
    actual_soc = [0.01]
    for index in range(1, len(times)):
        dt = times[index] - times[index - 1]
        actual_soc.append(actual_soc[-1] + 0.5 * (current_c[index - 1] + current_c[index]) * dt / 3600.0)

    voltage_rows = []
    for index, time_s in enumerate(times, start=1):
        voltage_terminal = scalar(model, "__v20", "AvLine", "phis", [20], index)
        voltage_pos_al = scalar(model, "__v15", "AvLine", "phis", [15], index)
        current_a = scalar(model, "__current", "EvalGlobal", "I", None, index)
        voltage_rows.append([
            index, time_s, actual_soc[index - 1], current_a, current_c[index - 1],
            voltage_terminal, voltage_pos_al, voltage_terminal - voltage_pos_al,
        ])
    voltage_path = DATA / "voltage_soc.csv"
    with voltage_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["solnum", "time_s", "actual_SOC", "current_A", "current_Crate", "terminal_b20_V", "positive_Al_b15_V", "shell_drop_V"])
        writer.writerows(voltage_rows)
    manifest["files"]["voltage_soc"] = str(voltage_path)

    shell_columns = []
    shell_coords = None
    shell_elements = None
    stage_metrics = []
    for label, solnum in STAGES:
        coords, elements, values = eval_field(
            model, "__shell", "sqrt(liion.Isr^2+liion.Isz^2)", 2, SHELL_DOMAINS, solnum
        )
        if shell_coords is None:
            shell_coords = coords
            shell_elements = elements
        shell_columns.append((label, values))
        row = voltage_rows[solnum - 1]
        stage = {
            "label": label,
            "solnum": solnum,
            "time_s": times[solnum - 1],
            "actual_SOC": actual_soc[solnum - 1],
            "terminal_b20_V": row[5],
            "positive_Al_b15_V": row[6],
            "shell_drop_V": row[7],
            "shell_current_density_min_A_m2": min(values),
            "shell_current_density_max_A_m2": max(values),
        }
        manifest["stages"].append(stage)
        stage_metrics.append(stage)

    shell_nodes_path = DATA / "shell_current_density_nodes.csv"
    with shell_nodes_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["node", "r_um", "z_um"] + [label + "_A_m2" for label, _ in shell_columns])
        for node_index in range(len(shell_coords[0])):
            writer.writerow([
                node_index, shell_coords[0][node_index], shell_coords[1][node_index],
                *[values[node_index] for _, values in shell_columns],
            ])
    shell_triangles_path = DATA / "shell_current_density_triangles.csv"
    with shell_triangles_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["triangle", "node_1", "node_2", "node_3"])
        for element_index in range(len(shell_elements[0])):
            writer.writerow([element_index, shell_elements[0][element_index], shell_elements[1][element_index], shell_elements[2][element_index]])
    manifest["files"]["shell_nodes"] = str(shell_nodes_path)
    manifest["files"]["shell_triangles"] = str(shell_triangles_path)

    interface_path = DATA / "interface_stoichiometry_profiles.csv"
    with interface_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["interface", "boundary", "stage", "solnum", "time_s", "actual_SOC", "r_um", "z_um", "surface_stoichiometry"])
        for interface, boundary in INTERFACES.items():
            for label, solnum in STAGES:
                coords, _, values = eval_field(
                    model, "__interface", "liion.cs_surface/liion.csmax", 1, [boundary], solnum
                )
                order = sorted(range(len(values)), key=lambda i: coords[0][i])
                for index in order:
                    writer.writerow([
                        interface, boundary, label, solnum, times[solnum - 1], actual_soc[solnum - 1],
                        coords[0][index], coords[1][index], values[index],
                    ])
    manifest["files"]["interface_profiles"] = str(interface_path)

    metrics_path = RUN / "metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stage_metrics[0].keys()))
        writer.writeheader()
        writer.writerows(stage_metrics)
    manifest["files"]["metrics"] = str(metrics_path)
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "manifest": str(OUTPUT), "stages": manifest["stages"]}, ensure_ascii=False))
