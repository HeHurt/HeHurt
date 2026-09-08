import json
from pathlib import Path


MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_final.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\geometry_entities.json")
TAG = "coin_v5_geometry_entities"


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def bbox(model, entity_dim, entity_id):
    manager = model.result().numerical()
    tag = f"__bbox_{entity_dim}_{entity_id}"
    remove(manager, tag)
    node = manager.create(tag, "Eval")
    node.set("data", "dset1")
    node.set("solnum", "1")
    node.set("expr", ["r", "z"])
    node.selection().geom("geom1", entity_dim)
    node.selection().set([entity_id])
    raw = node.getReal()
    rows = []
    try:
        for row in raw:
            rows.append([float(value) for value in row])
    finally:
        remove(manager, tag)
    if not rows:
        return None
    # COMSOL may return point-major or expression-major arrays.
    if len(rows) == 2 and len(rows[0]) > 2:
        r_values, z_values = rows[0], rows[1]
    else:
        r_values = [row[0] for row in rows]
        z_values = [row[1] for row in rows]
    return {
        "r_min": min(r_values), "r_max": max(r_values),
        "z_min": min(z_values), "z_max": max(z_values),
        "points": len(r_values),
    }


model = ModelUtil.load(TAG, MODEL)
payload = {"source": MODEL, "boundaries": {}, "domains": {}}
try:
    for boundary in range(1, 49):
        try:
            value = bbox(model, 1, boundary)
            if value:
                payload["boundaries"][str(boundary)] = value
        except Exception as exc:
            payload["boundaries"][str(boundary)] = {"error": str(exc)}
    for domain in range(1, 12):
        try:
            value = bbox(model, 2, domain)
            if value:
                payload["domains"][str(domain)] = value
        except Exception as exc:
            payload["domains"][str(domain)] = {"error": str(exc)}
    payload["ok"] = True
except Exception as exc:
    payload.update({"ok": False, "error": str(exc)})
finally:
    ModelUtil.remove(TAG)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload.get("ok"), "output": str(OUTPUT), "error": payload.get("error")}, ensure_ascii=False))
