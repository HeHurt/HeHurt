import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V5_final.mph"
RUN_MODEL = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\model_snapshot.mph"
DELIVERY_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V6_mechanical.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_153421_coin_v6_mechanical_coupling\patch_result.json")
TAG = "coin_v6_mechanical_patch"


PARAMETERS = {
    "F_ext": "250[N]",
    "R_load": "12.205[mm]",
    "A_load": "pi*R_load^2",
    "p_ext": "F_ext/A_load",
    "p_ref": "0.5[MPa]",
    "p_floor": "0.05[MPa]",
    "beta_neg": "0.03[1/MPa]",
    "beta_sep": "0.08[1/MPa]",
    "beta_pos": "0.03[1/MPa]",
    "epsl_floor": "0.15",
    "epsl_neg_mech": "max(epsl_floor,epsl_neg*(1-beta_neg*p_ext))",
    "epsl_sep_mech": "max(epsl_floor,epsl_sep*(1-beta_sep*p_ext))",
    "epsl_pos_mech": "max(epsl_floor,epsl_pos*(1-beta_pos*p_ext))",
    "R_contact_ref": "10[mohm]",
    "m_contact": "0.5",
    "R_contact_eff": "R_contact_ref*(p_ref/max(p_ext,p_floor))^m_contact",
    "E_steel": "200[GPa]",
    "nu_steel": "0.30",
    "rho_steel": "7850[kg/m^3]",
    "E_cu": "110[GPa]",
    "nu_cu": "0.34",
    "rho_cu_mech": "8960[kg/m^3]",
    "E_al": "70[GPa]",
    "nu_al": "0.33",
    "rho_al_mech": "2700[kg/m^3]",
    "E_pp": "1.5[GPa]",
    "nu_pp": "0.42",
    "rho_pp": "900[kg/m^3]",
    "E_neg_mech": "0.5[GPa]",
    "nu_neg_mech": "0.30",
    "rho_neg_mech": "1800[kg/m^3]",
    "E_sep_mech": "0.1[GPa]",
    "nu_sep_mech": "0.40",
    "rho_sep_mech": "900[kg/m^3]",
    "E_pos_mech": "0.7[GPa]",
    "nu_pos_mech": "0.30",
    "rho_pos_mech": "2200[kg/m^3]",
}


MECHANICAL_VARIABLE_GROUPS = {
    "mech_steel": ("壳体钢力学参数", [1, 2, 8, 9, 10], "E_steel", "nu_steel", "rho_steel"),
    "mech_cu": ("铜箔力学参数", [3], "E_cu", "nu_cu", "rho_cu_mech"),
    "mech_neg": ("负极多孔层力学参数", [4], "E_neg_mech", "nu_neg_mech", "rho_neg_mech"),
    "mech_sep": ("隔膜力学参数", [5], "E_sep_mech", "nu_sep_mech", "rho_sep_mech"),
    "mech_pos": ("正极多孔层力学参数", [6], "E_pos_mech", "nu_pos_mech", "rho_pos_mech"),
    "mech_al": ("铝箔力学参数", [7], "E_al", "nu_al", "rho_al_mech"),
    "mech_pp": ("PP 密封件力学参数", [11], "E_pp", "nu_pp", "rho_pp"),
}


def create_mechanical_variable_group(comp, tag, label, domains, young, poisson, density):
    comp.variable().create(tag)
    group = comp.variable(tag)
    group.label(label)
    group.selection().geom("geom1", 2)
    group.selection().set(domains)
    group.set("E_mech", young)
    group.set("nu_mech", poisson)
    group.set("rho_mech", density)


def readback(model):
    comp = model.component("comp1")
    solid = comp.physics("solid")
    liion = comp.physics("liion")
    result = {
        "parameters": {name: str(model.param().get(name)) for name in PARAMETERS},
        "variables": {
            "V_contact_drop": str(comp.variable("var1").get("V_contact_drop")),
            "vol_loaded": str(comp.variable("var1").get("vol_loaded")),
        },
        "porosity_consumers": {
            "pce1": str(liion.feature("pce1").getString("epsl")),
            "sep1": str(liion.feature("sep1").getString("epsl")),
            "pce2": str(liion.feature("pce2").getString("epsl")),
        },
        "event_g": [str(value) for value in comp.physics("ev").feature("is1").getStringArray("g")],
        "solid_features": {},
        "mechanical_variable_groups": {},
        "studies": [str(value) for value in model.study().tags()],
        "force_sweeps": {},
    }
    elastic = solid.feature("lemm1")
    result["solid_features"]["lemm1"] = {
        "type": str(elastic.getType()),
        "E": str(elastic.getString("E")),
        "nu": str(elastic.getString("nu")),
        "rho": str(elastic.getString("rho")),
    }
    for group_tag in MECHANICAL_VARIABLE_GROUPS:
        group = comp.variable(group_tag)
        result["mechanical_variable_groups"][group_tag] = {
            "E_mech": str(group.get("E_mech")),
            "nu_mech": str(group.get("nu_mech")),
            "rho_mech": str(group.get("rho_mech")),
        }
    for feature_tag in ("fix_bottom", "load_top"):
        feature = solid.feature(feature_tag)
        result["solid_features"][feature_tag] = {
            "type": str(feature.getType()),
        }
        if feature_tag == "load_top":
            result["solid_features"][feature_tag].update({
                "forceType": str(feature.getString("forceType")),
                "pressure": str(feature.getString("pressure")),
            })
    for study_tag, step_tag in (("std1", "time"), ("std_mech", "stat")):
        step = model.study(study_tag).feature(step_tag)
        result["force_sweeps"][f"{study_tag}/{step_tag}"] = {
            "useparam": str(step.getString("useparam")),
            "pname": [str(value) for value in step.getStringArray("pname")],
            "plistarr": [str(value) for value in step.getStringArray("plistarr")],
            "punit": [str(value) for value in step.getStringArray("punit")],
        }
    return result


model = ModelUtil.load(TAG, SOURCE)
payload = {"source": SOURCE, "run_model": RUN_MODEL, "delivery_model": DELIVERY_MODEL}
try:
    for name, expression in PARAMETERS.items():
        model.param().set(name, expression)

    comp = model.component("comp1")
    variables = comp.variable("var1")
    variables.set("V_contact_drop", "I*R_contact_eff")
    variables.set("vol_loaded", "vol+V_contact_drop")

    liion = comp.physics("liion")
    liion.feature("pce1").set("epsl", "epsl_neg_mech")
    liion.feature("sep1").set("epsl", "epsl_sep_mech")
    liion.feature("pce2").set("epsl", "epsl_pos_mech")

    event = comp.physics("ev").feature("is1")
    event.set("g", [
        "2.5-vol_loaded",
        "vol_loaded-3.65",
        "t-idle_to_charge_time-1800[s]",
        "t-idle_to_discharge_time-1800[s]",
    ])

    comp.physics().create("solid", "SolidMechanics", "geom1")
    solid = comp.physics("solid")
    solid.label("固体力学（外力耦合）")
    solid.selection().set(list(range(1, 12)))

    for group_tag, values in MECHANICAL_VARIABLE_GROUPS.items():
        create_mechanical_variable_group(comp, group_tag, *values)

    elastic = solid.feature("lemm1")
    elastic.label("分域线弹性材料")
    elastic.set("E_mat", "userdef")
    elastic.set("E", "E_mech")
    elastic.set("nu_mat", "userdef")
    elastic.set("nu", "nu_mech")
    elastic.set("rho_mat", "userdef")
    elastic.set("rho", "rho_mech")

    solid.feature().create("fix_bottom", "Fixed", 1)
    solid.feature("fix_bottom").label("底部固定")
    solid.feature("fix_bottom").selection().set([2])

    solid.feature().create("load_top", "BoundaryLoad", 1)
    solid.feature("load_top").label("顶部轴向外压")
    solid.feature("load_top").selection().set([20])
    solid.feature("load_top").set("forceType", "FollowerPressure")
    solid.feature("load_top").set("pressure", "p_ext")

    model.study().create("std_mech")
    model.study("std_mech").label("外力静力学")
    model.study("std_mech").create("stat", "Stationary")
    model.study("std_mech").feature("stat").activate("ev", False)
    model.study("std_mech").feature("stat").activate("liion", False)
    model.study("std_mech").feature("stat").activate("solid", True)
    model.study("std1").feature("cdi").activate("solid", False)
    model.study("std1").feature("time").activate("solid", False)

    for study_tag, step_tag in (("std1", "time"), ("std_mech", "stat")):
        step = model.study(study_tag).feature(step_tag)
        step.set("useparam", "on")
        step.set("pname", ["F_ext"])
        step.set("plistarr", ["0 100 250 500"])
        step.set("punit", ["N"])

    payload["before_save"] = readback(model)
    model.save(RUN_MODEL)
    model.save(DELIVERY_MODEL)
finally:
    ModelUtil.remove(TAG)

verify_tag = TAG + "_verify"
reloaded = ModelUtil.load(verify_tag, DELIVERY_MODEL)
try:
    payload["after_reload"] = readback(reloaded)
    payload["ok"] = payload["before_save"] == payload["after_reload"]
finally:
    ModelUtil.remove(verify_tag)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload["ok"], "output": str(OUTPUT), "delivery_model": DELIVERY_MODEL}, ensure_ascii=False))
