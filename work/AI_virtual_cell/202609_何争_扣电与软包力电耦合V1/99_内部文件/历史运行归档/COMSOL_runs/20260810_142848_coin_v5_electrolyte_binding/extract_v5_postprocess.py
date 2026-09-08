import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_final.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_142848_coin_v5_electrolyte_binding")
DATA = RUN / "exported_data"
VOLTAGE_CSV = DATA / "voltage_soc_v5_final.csv"
OUTPUT = RUN / "postprocess_v5_manifest.json"
TAG = "coin_v5_postprocess"

SHELL_DOMAINS = [1, 2, 8, 9, 10]
INTERFACES = {"negative_Cu": 9, "negative_separator": 11, "positive_separator": 13, "positive_Al": 15}
STAGES = [("SOC01", 1), ("SOC10", 33), ("SOC30", 105), ("SOC50", 177), ("SOC70", 249), ("SOC85", 303), ("cutoff_SOC99_9", 357)]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def rows(value):
    return [[float(item) for item in row] for row in value]


def eval_field(model, tag, expr, entity_dim, entities, solnum):
    manager = model.result().numerical()
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset1")
    node.set("solnum", str(solnum))
    node.set("expr", [expr])
    node.selection().geom("geom1", entity_dim)
    node.selection().set(entities)
    values = [row[0] for row in rows(node.getReal())]
    coordinates = rows(node.getCoordinates())
    elements = [[int(item) for item in row] for row in node.getElements()]
    remove(manager, tag)
    return coordinates, elements, values


with VOLTAGE_CSV.open(encoding="utf-8-sig") as handle:
    voltage_rows = {int(row["solnum"]): row for row in csv.DictReader(handle)}

model = ModelUtil.load(TAG, MODEL)
manifest = {"source": MODEL, "stages": [], "files": {}}
try:
    shell_coords = None
    shell_elements = None
    shell_columns = []
    for label, solnum in STAGES:
        coords, elements, values = eval_field(model, "__shell", "sqrt(liion.Isr^2+liion.Isz^2)", 2, SHELL_DOMAINS, solnum)
        if shell_coords is None:
            shell_coords = coords
            shell_elements = elements
        shell_columns.append((label, values))
        source_row = voltage_rows[solnum]
        manifest["stages"].append({
            "label": label,
            "solnum": solnum,
            "time_s": float(source_row["time_s"]),
            "actual_SOC": float(source_row["actual_SOC"]),
            "terminal_voltage_V": float(source_row["terminal_voltage_V"]),
            "current_density_max_A_m2": max(values),
        })

    shell_nodes = DATA / "shell_current_density_nodes_v5.csv"
    with shell_nodes.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["node", "r_um", "z_um"] + [label + "_A_m2" for label, _ in shell_columns])
        for index in range(len(shell_coords[0])):
            writer.writerow([index, shell_coords[0][index], shell_coords[1][index], *[values[index] for _, values in shell_columns]])
    shell_triangles = DATA / "shell_current_density_triangles_v5.csv"
    with shell_triangles.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["triangle", "node_1", "node_2", "node_3"])
        for index in range(len(shell_elements[0])):
            writer.writerow([index, shell_elements[0][index], shell_elements[1][index], shell_elements[2][index]])

    interface_csv = DATA / "interface_stoichiometry_profiles_v5.csv"
    with interface_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["interface", "boundary", "stage", "solnum", "time_s", "actual_SOC", "r_um", "z_um", "surface_stoichiometry"])
        for interface, boundary in INTERFACES.items():
            for label, solnum in STAGES:
                coords, _, values = eval_field(model, "__interface", "liion.cs_surface/liion.csmax", 1, [boundary], solnum)
                source_row = voltage_rows[solnum]
                for index in sorted(range(len(values)), key=lambda i: coords[0][i]):
                    writer.writerow([
                        interface, boundary, label, solnum, source_row["time_s"], source_row["actual_SOC"],
                        coords[0][index], coords[1][index], values[index],
                    ])
    manifest["files"] = {
        "voltage": str(VOLTAGE_CSV), "shell_nodes": str(shell_nodes),
        "shell_triangles": str(shell_triangles), "interfaces": str(interface_csv),
    }
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "manifest": str(OUTPUT), "stages": manifest["stages"]}, ensure_ascii=False))
