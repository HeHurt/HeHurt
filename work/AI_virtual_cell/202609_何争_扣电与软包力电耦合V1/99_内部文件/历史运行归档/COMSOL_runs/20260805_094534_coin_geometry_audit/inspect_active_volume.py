import json
from pathlib import Path


SOURCE = r"E:\Downloads\coin_geometry.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\active_volume.json")
TAG = "coin_active_volume"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def integrate(model, domain, expression, name):
    manager = model.result().numerical()
    tag = "__int_" + name
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, "IntSurface")
        node.selection().set([domain])
        node.set("data", "dset2")
        node.set("solnum", "1")
        node.set("expr", expression)
        return jsonable(node.getReal())
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        payload = {"source": SOURCE, "domains": {}}
        for label, domain in (("negative", 4), ("positive", 6)):
            payload["domains"][label] = {
                "cross_section_m2": integrate(model, domain, "1", label + "_area"),
                "axisymmetric_volume_m3": integrate(
                    model, domain, "2*pi*r", label + "_volume"
                ),
            }
        payload["parameter_values"] = {
            name: float(model.param().evaluate(name))
            for name in ("Ac", "t_an", "t_ca", "r_neg", "L_cell")
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
