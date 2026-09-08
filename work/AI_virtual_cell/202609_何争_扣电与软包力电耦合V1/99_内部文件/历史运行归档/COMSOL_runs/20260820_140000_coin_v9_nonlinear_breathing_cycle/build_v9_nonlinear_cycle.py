import json
from pathlib import Path


SOURCE = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V8_breathing.mph"
RUN_MODEL = r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\model_snapshot.mph"
DELIVERY_MODEL = r"C:\Users\hez\WorkBuddy\2026-08-05-16-49-35\runs\coin_geometry_fixed_V9_nonlinear_breathing_cycle.mph"
OUTPUT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\build_result.json")
TAG = "coin_v9_nonlinear_cycle_build"


# Representative graphite electrode thickness-change curve digitized from
# Rieger et al., Journal of Energy Storage 6 (2016) 213-221, Fig. 4/curve
# reproduced as Fig. 9 in Escher et al., Energy Technology 10 (2022) 2101120.
# The normalized ordinate keeps the staging-shaped curve; the dimensional
# amplitude is controlled by eps_sw_neg_lit=0.07.
GRAPHITE_SHAPE = [
    (0.00, 0.000), (0.05, 0.035), (0.10, 0.085), (0.20, 0.170),
    (0.30, 0.255), (0.40, 0.385), (0.50, 0.500), (0.60, 0.515),
    (0.70, 0.535), (0.80, 0.600), (0.90, 0.705), (0.96, 0.840),
    (1.00, 1.000),
]

# LFP composite-electrode strain is concentrated in the LFP/FP phase
# transformation region. The sigmoidal normalized shape follows the single
# strain-derivative peak reported by Zhang et al., Electrochimica Acta 353
# (2020) 136594. The 0.6% amplitude is kept separate from the normalized shape.
LFP_SHAPE = [
    (0.00, 0.000), (0.03, 0.005), (0.07, 0.020), (0.12, 0.055),
    (0.20, 0.130), (0.30, 0.260), (0.40, 0.420), (0.50, 0.610),
    (0.60, 0.770), (0.70, 0.885), (0.80, 0.950), (0.90, 0.985),
    (0.97, 0.997), (1.00, 1.000),
]


def remove(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def tags(manager):
    try:
        return [str(x) for x in manager.tags()]
    except Exception:
        return []


def create_interpolation(comp, tag, funcname, table, label):
    remove(comp.func(), tag)
    comp.func().create(tag, "Interpolation")
    fn = comp.func(tag)
    fn.label(label)
    fn.set("funcname", funcname)
    fn.set("source", "table")
    fn.set("table", [[f"{x:.8g}", f"{y:.8g}"] for x, y in table])
    fn.set("interp", "piecewisecubic")
    fn.set("extrap", "const")
    fn.set("argunit", [""])
    fn.set("fununit", [""])
    return fn


def readback(model):
    comp = model.component("comp1")
    ev = comp.physics("ev")
    return {
        "parameters": {
            key: str(model.param().get(key))
            for key in (
                "breathing_mode", "eps_sw_neg_lit", "eps_sw_pos_lit",
                "eps_sw_neg_full", "eps_sw_pos_full", "cycle_rest",
                "V_charge_cut", "V_discharge_cut",
            )
        },
        "function_tables": {
            "graphite": [
                [str(y) for y in row]
                for row in comp.func("sw_gr_v9_fn").getStringMatrix("table")
            ],
            "lfp": [
                [str(y) for y in row]
                for row in comp.func("sw_lfp_v9_fn").getStringMatrix("table")
            ],
        },
        "variables": {
            "negative": {
                name: str(comp.variable("var_v8_neg").get(name))
                for name in (
                    "theta_neg_v8", "eps_breath_neg_linear_v9",
                    "eps_breath_neg_lit_v9", "eps_breath_neg_v8",
                    "p_comp_neg_v8", "epsl_neg_v8",
                )
            },
            "positive": {
                name: str(comp.variable("var_v8_pos").get(name))
                for name in (
                    "theta_pos_v8", "eps_breath_pos_linear_v9",
                    "eps_breath_pos_lit_v9", "eps_breath_pos_v8",
                    "p_comp_pos_v8", "epsl_pos_v8",
                )
            },
        },
        "events": {
            tag: {
                "StudyStep": [str(x) for x in ev.feature(tag).getStringArray("StudyStep")],
                "condition": str(ev.feature(tag).getString("condition")) if tag.startswith("impl") else "",
            }
            for tag in tags(ev.feature())
        },
        "study": {
            "tags": tags(model.study()),
            "tlist": str(model.study("std_v9").feature("time").getString("tlist")),
        },
    }


for target in (RUN_MODEL, DELIVERY_MODEL):
    if Path(target).resolve() == Path(SOURCE).resolve():
        raise RuntimeError("Refusing to overwrite V8 source")

model = ModelUtil.load(TAG, SOURCE)
payload = {"source": SOURCE, "run_model": RUN_MODEL, "delivery_model": DELIVERY_MODEL}
try:
    params = {
        "breathing_mode": ("2", "0=off, 1=legacy linear, 2=literature nonlinear"),
        "eps_sw_neg_lit": ("0.07", "Graphite full-range electrode axial strain from dilatometry"),
        "eps_sw_pos_lit": ("0.006", "LFP full-range composite-electrode strain"),
        "cycle_rest": ("600[s]", "Rest between charge and discharge"),
        "V_charge_cut": ("3.65[V]", "Loaded-voltage charge cutoff"),
        "V_discharge_cut": ("2.5[V]", "Loaded-voltage discharge cutoff"),
    }
    for name, (expr, descr) in params.items():
        model.param().set(name, expr, descr)

    comp = model.component("comp1")
    create_interpolation(comp, "sw_gr_v9_fn", "sw_gr_v9", GRAPHITE_SHAPE, "V9石墨SOC-厚度变化（文献曲线）")
    create_interpolation(comp, "sw_lfp_v9_fn", "sw_lfp_v9", LFP_SHAPE, "V9 LFP嵌锂比例-应变（文献形状）")

    neg = comp.variable("var_v8_neg")
    neg.label("V9负极非线性呼吸-局部压力-孔隙率")
    neg.set("eps_breath_neg_linear_v9", "eps_sw_neg_full*max(0,min(1,(theta_neg_v8-theta_neg_ref)/(1-theta_neg_ref)))")
    neg.set("eps_breath_neg_lit_v9", "eps_sw_neg_lit*(sw_gr_v9(theta_neg_v8)-sw_gr_v9(theta_neg_ref))")
    neg.set(
        "eps_breath_neg_v8",
        "if(breathing_mode<0.5,0,if(breathing_mode<1.5,eps_breath_neg_linear_v9,eps_breath_neg_lit_v9))",
    )

    pos = comp.variable("var_v8_pos")
    pos.label("V9正极非线性呼吸-局部压力-孔隙率")
    pos.set("eps_breath_pos_linear_v9", "eps_sw_pos_full*max(0,min(1,(theta_pos_ref-theta_pos_v8)/theta_pos_ref))")
    pos.set("eps_breath_pos_lit_v9", "eps_sw_pos_lit*(sw_lfp_v9(theta_pos_v8)-sw_lfp_v9(theta_pos_ref))")
    pos.set(
        "eps_breath_pos_v8",
        "if(breathing_mode<0.5,0,if(breathing_mode<1.5,eps_breath_pos_linear_v9,eps_breath_pos_lit_v9))",
    )

    parent = comp.physics("solid").feature("lemm1")
    parent.feature("breath_neg_v8").label("V9石墨非线性嵌锂呼吸")
    parent.feature("breath_neg_v8").set("eext", ["0", "0", "eps_breath_neg_v8"])
    parent.feature("breath_pos_v8").label("V9 LFP非线性嵌锂呼吸")
    parent.feature("breath_pos_v8").set("eext", ["0", "0", "eps_breath_pos_v8"])

    remove(model.study(), "std_v9")
    model.study().create("std_v9")
    study = model.study("std_v9")
    study.label("V9完整充电-静置-放电：非线性呼吸耦合")
    study.create("time", "Transient")
    step = study.feature("time")
    step.label("完整充放电循环")
    step.activate("liion", True)
    step.activate("solid", True)
    step.activate("ev", True)
    step.set("tlist", "range(0,60,18000)")
    step.set("useparam", "off")

    ev = comp.physics("ev")
    for event_tag in tags(ev.feature()):
        ev.feature(event_tag).set("StudyStep", "std_v9/time")
    indicator = ev.feature("is1")
    indicator.set(
        "g",
        [
            "V_discharge_cut-vol_loaded",
            "vol_loaded-V_charge_cut",
            "t-idle_to_charge_time-cycle_rest",
            "t-idle_to_discharge_time-cycle_rest",
        ],
    )
    # One cycle only: after the lower-voltage event the model remains at rest.
    ev.feature("impl6").set("condition", "(discharge_idle_end>0)&&(discharge_hold==1)&&(t<0[s])")

    payload["before_save"] = readback(model)
    model.save(RUN_MODEL)
    model.save(DELIVERY_MODEL)
finally:
    ModelUtil.remove(TAG)

verify_tag = TAG + "_verify"
verified = ModelUtil.load(verify_tag, DELIVERY_MODEL)
try:
    payload["after_reload"] = readback(verified)
    payload["ok"] = payload["before_save"] == payload["after_reload"]
    payload["sizes_bytes"] = {
        "source": Path(SOURCE).stat().st_size,
        "run_model": Path(RUN_MODEL).stat().st_size,
        "delivery_model": Path(DELIVERY_MODEL).stat().st_size,
    }
finally:
    ModelUtil.remove(verify_tag)

OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": payload["ok"], "delivery_model": DELIVERY_MODEL, "output": str(OUTPUT)}, ensure_ascii=False))
