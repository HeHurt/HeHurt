import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
RUN_MODEL = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_090000_coin_v7_local_porosity\model_snapshot.mph"
DELIVERY_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_090000_coin_v7_local_porosity\patch_result.json")
TAG = "coin_v7_local_porosity_patch"

REGIONS = {
    "var_v7_neg": {
        "label": "V7负极局部压力-孔隙率",
        "domain": 4,
        "pressure": "p_comp_neg_v7",
        "local": "epsl_neg_local_v7",
        "coupled": "epsl_neg_v7",
        "base": "epsl_neg",
        "uniform": "epsl_neg_mech",
        "beta": "beta_neg",
    },
    "var_v7_sep": {
        "label": "V7隔膜局部压力-孔隙率",
        "domain": 5,
        "pressure": "p_comp_sep_v7",
        "local": "epsl_sep_local_v7",
        "coupled": "epsl_sep_v7",
        "base": "epsl_sep",
        "uniform": "epsl_sep_mech",
        "beta": "beta_sep",
    },
    "var_v7_pos": {
        "label": "V7正极局部压力-孔隙率",
        "domain": 6,
        "pressure": "p_comp_pos_v7",
        "local": "epsl_pos_local_v7",
        "coupled": "epsl_pos_v7",
        "base": "epsl_pos",
        "uniform": "epsl_pos_mech",
        "beta": "beta_pos",
    },
}


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def tags(manager):
    try:
        return [str(value) for value in manager.tags()]
    except Exception:
        return []


def selection_entities(node):
    try:
        return [int(value) for value in node.selection().entities()]
    except Exception:
        return []


def readback(model):
    comp = model.component("comp1")
    result = {
        "parameters": {
            "local_porosity_on": str(model.param().get("local_porosity_on")),
            "p_local_cap": str(model.param().get("p_local_cap")),
        },
        "variables": {},
        "porosity_consumers": {
            "negative": str(comp.physics("liion").feature("pce1").getString("epsl")),
            "separator": str(comp.physics("liion").feature("sep1").getString("epsl")),
            "positive": str(comp.physics("liion").feature("pce2").getString("epsl")),
        },
        "studies": tags(model.study()),
    }
    for tag, item in REGIONS.items():
        group = comp.variable(tag)
        result["variables"][tag] = {
            "selection": selection_entities(group),
            item["pressure"]: str(group.get(item["pressure"])),
            item["local"]: str(group.get(item["local"])),
            item["coupled"]: str(group.get(item["coupled"])),
        }
    study = model.study("std_local")
    result["std_local"] = {
        "label": str(study.label()),
        "features": tags(study.feature()),
        "tlist": str(study.feature("time").getString("tlist")),
        "pname": [str(value) for value in study.feature("time").getStringArray("pname")],
        "plistarr": [str(value) for value in study.feature("time").getStringArray("plistarr")],
    }
    return result


for output in (RUN_MODEL, DELIVERY_MODEL):
    if Path(output).resolve() == Path(SOURCE).resolve():
        raise RuntimeError("Refusing to overwrite the V6 source model")

model = ModelUtil.load(TAG, SOURCE)
payload = {"source": SOURCE, "run_model": RUN_MODEL, "delivery_model": DELIVERY_MODEL}
try:
    comp = model.component("comp1")
    liion = comp.physics("liion")

    model.param().set("local_porosity_on", "0", "V7局部孔隙率开关：0=V6均匀孔隙率，1=局部压力孔隙率")
    model.param().set("p_local_cap", "2[MPa]", "局部压缩压力经验关系上限，待材料测试标定")

    for tag, item in REGIONS.items():
        remove(comp.variable(), tag)
        comp.variable().create(tag)
        group = comp.variable(tag)
        group.label(item["label"])
        group.selection().geom("geom1", 2)
        group.selection().set([item["domain"]])
        group.set(
            item["pressure"],
            "min(p_local_cap,max(0[Pa],withsol('sol2',-solid.sz,setval(F_ext,F_ext))))",
        )
        group.set(
            item["local"],
            f"max(epsl_floor,{item['base']}*(1-{item['beta']}*{item['pressure']}))",
        )
        group.set(
            item["coupled"],
            f"{item['uniform']}+local_porosity_on*({item['local']}-{item['uniform']})",
        )

    liion.feature("pce1").set("epsl", "epsl_neg_v7")
    liion.feature("sep1").set("epsl", "epsl_sep_v7")
    liion.feature("pce2").set("epsl", "epsl_pos_v7")

    remove(model.study(), "std_local")
    model.study().create("std_local")
    study = model.study("std_local")
    study.label("V7局部压力-孔隙率电化学")
    study.create("cdi", "CurrentDistributionInitialization")
    study.feature("cdi").label("电流分布初始化")
    study.feature("cdi").activate("solid", False)
    study.create("time", "Transient")
    time = study.feature("time")
    time.label("局部孔隙率瞬态")
    time.activate("solid", False)
    time.set("tlist", "range(0,20,7200)")
    time.set("useparam", "on")
    time.set("pname", ["F_ext", "local_porosity_on"])
    time.set("plistarr", ["0 100 250 500", "1"])
    time.set("punit", ["N", "1"])

    payload["before_save"] = readback(model)
    model.save(RUN_MODEL)
    model.save(DELIVERY_MODEL)
finally:
    ModelUtil.remove(TAG)

verify_tag = TAG + "_verify"
verified = ModelUtil.load(verify_tag, DELIVERY_MODEL)
try:
    payload["after_reload"] = readback(verified)
    payload["source_size_bytes"] = Path(SOURCE).stat().st_size
    payload["run_model_size_bytes"] = Path(RUN_MODEL).stat().st_size
    payload["delivery_model_size_bytes"] = Path(DELIVERY_MODEL).stat().st_size
    payload["ok"] = payload["before_save"] == payload["after_reload"]
finally:
    ModelUtil.remove(verify_tag)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload["ok"], "output": str(OUTPUT), "delivery_model": DELIVERY_MODEL}, ensure_ascii=False))
