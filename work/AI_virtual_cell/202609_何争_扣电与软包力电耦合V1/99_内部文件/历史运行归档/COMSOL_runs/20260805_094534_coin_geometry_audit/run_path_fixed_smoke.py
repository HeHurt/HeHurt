import json
import time
from pathlib import Path


SOURCE = r"E:\Downloads\coin_geometry.mph"
PARAM_DIR = Path(r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params")
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\capacity_corrected_smoke.json")
RUN_LOG = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260805_094534_coin_geometry_audit\capacity_corrected_run.log")
TAG = "coin_path_fixed_smoke"


FUNCTION_FILES = {
    "ocv_lfp_base": "LFP_ocv.txt",
    "ocv_gr_discharge": "Gr_ocv.txt",
    "ely_sigma": "E_sigma.dat",
    "ely_D": "E_DL_int1.dat",
    "ely_tplus": "E_transpNm.dat",
}


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return [jsonable(item) for item in value]
    except TypeError:
        return str(value)


def solution_info(model):
    result = {}
    for tag in [str(value) for value in model.sol().tags()]:
        sol = model.sol(tag)
        entry = {}
        for method in ("getType", "getSize", "getSizeMulti", "getDefaultSolnum", "getPVals"):
            try:
                entry[method] = jsonable(getattr(sol, method)())
            except Exception as exc:
                entry[method + "_error"] = str(exc)
        result[tag] = entry
    return result


def evaluate_domain(model, domain, expression, solnum, tag_suffix):
    manager = model.result().numerical()
    tag = "__state_" + tag_suffix
    try:
        try:
            manager.remove(tag)
        except Exception:
            pass
        node = manager.create(tag, "AvSurface")
        node.selection().set([domain])
        node.set("data", "dset1")
        node.set("solnum", str(solnum))
        node.set("expr", expression)
        return {"value": jsonable(node.getReal()), "expression": expression}
    except Exception as exc:
        return {"error": str(exc), "expression": expression}
    finally:
        try:
            manager.remove(tag)
        except Exception:
            pass


def state_samples(model):
    result = {}
    expressions = {
        "surface_stoich": "liion.cs_surface/liion.csmax",
        "solid_potential": "phis",
        "electrolyte_potential": "phil",
    }
    for solnum in (1, 61, 121):
        sample = {}
        for side, domain in (("negative", 4), ("positive", 6)):
            sample[side] = {
                name: evaluate_domain(
                    model,
                    domain,
                    expression,
                    solnum,
                    side + "_" + name + "_" + str(solnum),
                )
                for name, expression in expressions.items()
            }
        result[str(solnum)] = sample
    return result


def main():
    started = time.time()
    log_lines = ["coin_geometry path-fixed smoke", "source=" + SOURCE]
    model = ModelUtil.load(TAG, SOURCE)
    try:
        mapped = {}
        for function_tag, filename in FUNCTION_FILES.items():
            path = PARAM_DIR / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            node = model.func().get(function_tag)
            node.set("filename", str(path))
            try:
                node.importData()
                imported = True
            except Exception as exc:
                imported = False
                log_lines.append(function_tag + " importData warning: " + str(exc))
            mapped[function_tag] = {"filename": str(path), "imported": imported}

        model.param().set("r_neg", "10.25[mm]")
        model.param().set("Ac", "pi*r_neg^2")
        model.param().set("i_1C", "min(ah_pos_soc1,ah_neg_soc1)")
        corrected_parameters = {
            name: {
                "expression": str(model.param().get(name)),
                "value": float(model.param().evaluate(name)),
            }
            for name in ("r_neg", "Ac", "ah_pos_soc1", "ah_neg_soc1", "i_1C")
        }

        try:
            model.result().table("tbl1").clearTableData()
        except Exception as exc:
            log_lines.append("clear probe table warning: " + str(exc))

        model.study("std1").feature("time").set("tlist", "range(0,5,600)")
        log_lines.append("study tlist=range(0,5,600)")
        model.study("std1").run()
        table = model.result().table("tbl1")
        payload = {
            "ok": True,
            "source": SOURCE,
            "saved": False,
            "mapped_functions": mapped,
            "corrected_parameters": corrected_parameters,
            "elapsed_s": time.time() - started,
            "probe_headers": jsonable(table.getColumnHeaders()),
            "probe_real": jsonable(table.getReal()),
            "solutions": solution_info(model),
            "state_samples": state_samples(model),
        }
        log_lines.append("solve=success")
    except Exception as exc:
        payload = {
            "ok": False,
            "source": SOURCE,
            "saved": False,
            "elapsed_s": time.time() - started,
            "error": str(exc),
            "solutions": solution_info(model),
        }
        log_lines.append("solve=failed")
        log_lines.append(str(exc))
    finally:
        ModelUtil.remove(TAG)

    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    RUN_LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "output": str(OUTPUT)}, ensure_ascii=False))


main()
