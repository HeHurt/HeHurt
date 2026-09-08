import json
from pathlib import Path


SOURCE = r"E:\Downloads\coin_geometry.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\solution_states.json")
TAG = "coin_solution_states"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def evaluate_domain_average(model, domain, expression, name):
    manager = model.result().numerical()
    errors = []
    for numerical_type in ("AvSurface", "AvVolume"):
        tag = "__" + name + "_" + numerical_type.lower()
        try:
            try:
                manager.remove(tag)
            except Exception:
                pass
            node = manager.create(tag, numerical_type)
            node.selection().set([domain])
            node.set("data", "dset2")
            node.set("expr", expression)
            values = jsonable(node.getReal())
            return {"type": numerical_type, "expression": expression, "values": values}
        except Exception as exc:
            errors.append(numerical_type + ": " + str(exc))
        finally:
            try:
                manager.remove(tag)
            except Exception:
                pass
    return {"expression": expression, "errors": errors}


def evaluate_global(model, expression, name):
    manager = model.result().numerical()
    tag = "__global_" + name
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, "EvalGlobal")
        node.set("data", "dset2")
        node.set("expr", expression)
        return {"expression": expression, "values": jsonable(node.getReal())}
    except Exception as exc:
        return {"expression": expression, "error": str(exc)}
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def main():
    model = ModelUtil.load(TAG, SOURCE)
    try:
        domain_expressions = {
            "surface_stoich": "liion.cs_surface/liion.csmax",
            "solid_potential": "phis",
            "electrolyte_potential": "phil",
            "equilibrium_potential": "liion.Eeq",
            "local_current": "liion.iloc",
        }
        domains = {}
        for label, domain in (("negative", 4), ("positive", 6)):
            domains[label] = {}
            for name, expression in domain_expressions.items():
                domains[label][name] = evaluate_domain_average(
                    model, domain, expression, label + "_" + name
                )

        global_expressions = {
            "probe_voltage": "vol",
            "applied_current": "I",
            "liion_cell_voltage": "liion.E_cell",
            "positive_ocp_from_state": "ocv_lfp_base(comp1.liion.cs_surface/comp1.liion.csmax)-0.02[V]",
            "negative_ocp_from_state": "ocv_gr_discharge(comp1.liion.cs_surface/comp1.liion.csmax)",
        }
        globals_result = {
            name: evaluate_global(model, expression, name)
            for name, expression in global_expressions.items()
        }
        OUTPUT.write_text(
            json.dumps(
                {"source": SOURCE, "domains": domains, "globals": globals_result},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(json.dumps({"ok": True, "output": str(OUTPUT)}, ensure_ascii=False))
    finally:
        ModelUtil.remove(TAG)


main()
