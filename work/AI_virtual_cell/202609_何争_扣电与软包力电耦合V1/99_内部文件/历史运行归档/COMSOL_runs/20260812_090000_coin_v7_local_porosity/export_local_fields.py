import csv
import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_090000_coin_v7_local_porosity")
OUTPUT = RUN / "local_field_export.json"
TAG = "coin_v7_local_field_export"
REGIONS = {
    "negative": {"domain": [4], "base": "epsl_neg", "beta": "beta_neg"},
    "separator": {"domain": [5], "base": "epsl_sep", "beta": "beta_sep"},
    "positive": {"domain": [6], "base": "epsl_pos", "beta": "beta_pos"},
}


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def evaluate(model, expression, unit, domains):
    manager = model.result().numerical()
    tag = "__v7_field_export"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset4")
    node.set("solnum", "2")
    node.set("expr", [expression])
    node.set("unit", [unit])
    node.selection().geom("geom1", 2)
    node.selection().set(domains)
    values = [float(row[0]) for row in node.getReal()]
    coordinates = [[float(value) for value in row] for row in node.getCoordinates()]
    remove(manager, tag)
    return coordinates, values


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "force_N": 100.0, "files": {}}
try:
    for region, item in REGIONS.items():
        pressure_expr = "min(2[MPa],max(0[Pa],-solid.sz))"
        porosity_expr = f"max(epsl_floor,{item['base']}*(1-{item['beta']}*({pressure_expr})))"
        pressure_coords, pressure = evaluate(model, pressure_expr, "MPa", item["domain"])
        porosity_coords, porosity = evaluate(model, porosity_expr, "1", item["domain"])
        if pressure_coords != porosity_coords:
            raise RuntimeError(f"Coordinate mismatch in {region}")
        path = RUN / "exported_data" / f"{region}_local_pressure_porosity_100N.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["r_um", "z_um", "pressure_MPa", "porosity"])
            for index in range(len(pressure)):
                writer.writerow([pressure_coords[0][index], pressure_coords[1][index], pressure[index], porosity[index]])
        payload["files"][region] = str(path)
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
