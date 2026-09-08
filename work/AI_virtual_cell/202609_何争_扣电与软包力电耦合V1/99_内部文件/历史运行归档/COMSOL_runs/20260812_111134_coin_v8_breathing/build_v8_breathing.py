import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V7_local_porosity.mph"
RUN_MODEL = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\model_snapshot.mph"
DELIVERY_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260812_111134_coin_v8_breathing\build_result.json")
TAG = "coin_v8_breathing_build"


PARAMETERS = {
    "breathing_on": ("0", "V8嵌锂呼吸开关：0=关闭，1=开启"),
    "eps_sw_neg_full": ("0.20", "石墨由初始嵌锂态到完全嵌锂的轴向膨胀应变"),
    "eps_sw_pos_full": ("0.01", "LFP由初始嵌锂态到完全脱锂的轴向膨胀应变"),
    "theta_neg_ref": ("0.05910024", "负极初始平均嵌锂比例，来自V7已保存初始解"),
    "theta_pos_ref": ("0.99019973", "正极初始平均嵌锂比例，来自V7已保存初始解"),
}


REGIONS = {
    "var_v8_neg": {
        "label": "V8负极嵌锂呼吸-局部压力-孔隙率",
        "domain": 4,
        "theta": "theta_neg_v8",
        "breathing": "eps_breath_neg_v8",
        "pressure": "p_comp_neg_v8",
        "porosity": "epsl_neg_v8",
        "base": "epsl_neg",
        "beta": "beta_neg",
    },
    "var_v8_sep": {
        "label": "V8隔膜局部压力-孔隙率",
        "domain": 5,
        "pressure": "p_comp_sep_v8",
        "porosity": "epsl_sep_v8",
        "base": "epsl_sep",
        "beta": "beta_sep",
    },
    "var_v8_pos": {
        "label": "V8正极嵌锂呼吸-局部压力-孔隙率",
        "domain": 6,
        "theta": "theta_pos_v8",
        "breathing": "eps_breath_pos_v8",
        "pressure": "p_comp_pos_v8",
        "porosity": "epsl_pos_v8",
        "base": "epsl_pos",
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
    solid = comp.physics("solid")
    liion = comp.physics("liion")
    result = {
        "parameters": {name: str(model.param().get(name)) for name in PARAMETERS},
        "porosity_consumers": {
            "negative": str(liion.feature("pce1").getString("epsl")),
            "separator": str(liion.feature("sep1").getString("epsl")),
            "positive": str(liion.feature("pce2").getString("epsl")),
        },
        "external_strain": {},
        "variables": {},
        "studies": tags(model.study()),
    }
    parent = solid.feature("lemm1")
    for tag in ("breath_neg_v8", "breath_pos_v8"):
        node = parent.feature(tag)
        result["external_strain"][tag] = {
            "selection": selection_entities(node),
            "StrainInput": str(node.getString("StrainInput")),
            "eext": [str(value) for value in node.getStringArray("eext")],
        }
    for tag, item in REGIONS.items():
        group = comp.variable(tag)
        entry = {"selection": selection_entities(group)}
        for key in ("theta", "breathing", "pressure", "porosity"):
            if key in item:
                entry[item[key]] = str(group.get(item[key]))
        result["variables"][tag] = entry
    step = model.study("std_breath").feature("time")
    result["std_breath"] = {
        "features": tags(model.study("std_breath").feature()),
        "tlist": str(step.getString("tlist")),
        "useparam": str(step.getString("useparam")),
    }
    return result


for output in (RUN_MODEL, DELIVERY_MODEL):
    if Path(output).resolve() == Path(SOURCE).resolve():
        raise RuntimeError("Refusing to overwrite the V7 source model")

model = ModelUtil.load(TAG, SOURCE)
payload = {"source": SOURCE, "run_model": RUN_MODEL, "delivery_model": DELIVERY_MODEL}
try:
    for name, (expression, description) in PARAMETERS.items():
        model.param().set(name, expression, description)

    comp = model.component("comp1")
    liion = comp.physics("liion")
    solid = comp.physics("solid")

    for tag, item in REGIONS.items():
        remove(comp.variable(), tag)
        comp.variable().create(tag)
        group = comp.variable(tag)
        group.label(item["label"])
        group.selection().geom("geom1", 2)
        group.selection().set([item["domain"]])
        if tag == "var_v8_neg":
            group.set(item["theta"], "liion.cs_average/liion.csmax")
            group.set(
                item["breathing"],
                "breathing_on*eps_sw_neg_full*max(0,min(1,(theta_neg_v8-theta_neg_ref)/(1-theta_neg_ref)))",
            )
        elif tag == "var_v8_pos":
            group.set(item["theta"], "liion.cs_average/liion.csmax")
            group.set(
                item["breathing"],
                "breathing_on*eps_sw_pos_full*max(0,min(1,(theta_pos_ref-theta_pos_v8)/theta_pos_ref))",
            )
        group.set(item["pressure"], "min(p_local_cap,max(0[Pa],-solid.sz))")
        group.set(
            item["porosity"],
            f"max(epsl_floor,{item['base']}*(1-{item['beta']}*{item['pressure']}))",
        )

    liion.feature("pce1").set("epsl", "epsl_neg_v8")
    liion.feature("sep1").set("epsl", "epsl_sep_v8")
    liion.feature("pce2").set("epsl", "epsl_pos_v8")

    parent = solid.feature("lemm1")
    for tag in ("breath_neg_v8", "breath_pos_v8"):
        remove(parent.feature(), tag)
    parent.feature().create("breath_neg_v8", "ExternalStrain", 2)
    neg = parent.feature("breath_neg_v8")
    neg.label("负极嵌锂轴向呼吸（20%满量程）")
    neg.selection().set([4])
    neg.set("StrainInput", "StrainTensor")
    neg.set("eext_src", "userdef")
    neg.set("eext", ["0", "0", "eps_breath_neg_v8"])

    parent.feature().create("breath_pos_v8", "ExternalStrain", 2)
    pos = parent.feature("breath_pos_v8")
    pos.label("正极脱锂轴向呼吸（1%满量程）")
    pos.selection().set([6])
    pos.set("StrainInput", "StrainTensor")
    pos.set("eext_src", "userdef")
    pos.set("eext", ["0", "0", "eps_breath_pos_v8"])

    remove(model.study(), "std_breath")
    model.study().create("std_breath")
    study = model.study("std_breath")
    study.label("V8电化学-力学-局部孔隙率全耦合")
    study.create("time", "Transient")
    time = study.feature("time")
    time.label("嵌锂呼吸全耦合瞬态")
    time.activate("liion", True)
    time.activate("solid", True)
    time.activate("ev", True)
    time.set("tlist", "range(0,20,7200)")
    time.set("useparam", "on")
    time.set("pname", ["F_ext", "breathing_on"])
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
