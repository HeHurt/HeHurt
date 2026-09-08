"""Add mechanics, local pressure-porosity feedback, nonlinear breathing and a full cycle."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_2d_cross_section_v2_coin_v9_electrochem.mph"
OUTPUT = RUN / "pouch_dual_tab_2d_cross_section_v4_mechanical_breathing.mph"
RESULT = RUN / "build_pouch_2d_v4_mechanical_breathing_result.json"
TAG = "pouch_2d_v4_mechanical_breathing"


GRAPHITE_SHAPE = [
    (0.00, 0.000), (0.05, 0.035), (0.10, 0.085), (0.20, 0.170),
    (0.30, 0.255), (0.40, 0.385), (0.50, 0.500), (0.60, 0.515),
    (0.70, 0.535), (0.80, 0.600), (0.90, 0.705), (0.96, 0.840),
    (1.00, 1.000),
]

LFP_SHAPE = [
    (0.00, 0.000), (0.03, 0.005), (0.07, 0.020), (0.12, 0.055),
    (0.20, 0.130), (0.30, 0.260), (0.40, 0.420), (0.50, 0.610),
    (0.60, 0.770), (0.70, 0.885), (0.80, 0.950), (0.90, 0.985),
    (0.97, 0.997), (1.00, 1.000),
]


def safe_remove(manager, tag: str) -> None:
    try:
        manager.remove(tag)
    except Exception:
        pass


def entities(selection, dimension: int) -> list[int]:
    return sorted(int(item) for item in selection.entities(dimension))


def create_interpolation(comp, tag: str, name: str, table, label: str) -> None:
    safe_remove(comp.func(), tag)
    comp.func().create(tag, "Interpolation")
    fn = comp.func(tag)
    fn.label(label)
    fn.set("funcname", name)
    fn.set("source", "table")
    fn.set("table", [[f"{x:.8g}", f"{y:.8g}"] for x, y in table])
    fn.set("interp", "piecewisecubic")
    fn.set("extrap", "const")
    fn.set("argunit", [""])
    fn.set("fununit", [""])


def create_domain_variables(comp, tag: str, label: str, domain: list[int], entries: dict[str, str]) -> None:
    safe_remove(comp.variable(), tag)
    comp.variable().create(tag)
    group = comp.variable(tag)
    group.label(label)
    group.selection().geom("geom1", 2)
    group.selection().set(domain)
    for name, expression in entries.items():
        group.set(name, expression)


def create_box_boundary(comp, tag: str, label: str, xmin: str, xmax: str, ymin: str, ymax: str) -> None:
    safe_remove(comp.selection(), tag)
    comp.selection().create(tag, "Box")
    selection = comp.selection(tag)
    selection.label(label)
    selection.set("entitydim", "1")
    selection.set("condition", "inside")
    selection.set("xmin", xmin)
    selection.set("xmax", xmax)
    selection.set("ymin", ymin)
    selection.set("ymax", ymax)


def build() -> dict[str, object]:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    safe_remove(ModelUtil, TAG)
    model = ModelUtil.load(TAG, str(SOURCE))
    try:
        model.label("Single-layer pouch 2D V4 - electrochemistry-mechanics-breathing")
        model.comments(
            "Cartesian 2D single-layer pouch. Coin-V9 electrochemistry plus through-thickness mechanics, "
            "local pressure-porosity transport feedback and nonlinear graphite/LFP lithiation breathing."
        )
        comp = model.component("comp1")
        geom = comp.geom("geom1")

        domains = {
            "negative_tab": entities(comp.selection("geom1_r_neg_tab_dom"), 2),
            "negative_header": entities(comp.selection("geom1_r_neg_header_dom"), 2),
            "negative_cc": entities(comp.selection("geom1_r_neg_cc_dom"), 2),
            "graphite": entities(comp.selection("geom1_r_neg_dom"), 2),
            "separator": entities(comp.selection("geom1_r_sep_dom"), 2),
            "lfp": entities(comp.selection("geom1_r_pos_dom"), 2),
            "positive_cc": entities(comp.selection("geom1_r_pos_cc_dom"), 2),
            "positive_header": entities(comp.selection("geom1_r_pos_header_dom"), 2),
            "positive_tab": entities(comp.selection("geom1_r_pos_tab_dom"), 2),
        }
        all_domains = sorted(item for values in domains.values() for item in values)

        parameters = {
            "F_ext": ("100[N]", "External through-thickness compressive force"),
            "A_load": ("Ac", "Loaded coated area"),
            "p_ext": ("F_ext/A_load", "Nominal external pressure"),
            "p_ref": ("0.5[MPa]", "Contact-resistance reference pressure"),
            "p_floor": ("0.05[MPa]", "Contact-resistance pressure floor"),
            "beta_neg": ("0.03[1/MPa]", "Graphite porosity pressure coefficient"),
            "beta_sep": ("0.08[1/MPa]", "Separator porosity pressure coefficient"),
            "beta_pos": ("0.03[1/MPa]", "LFP porosity pressure coefficient"),
            "epsl_floor": ("0.15", "Porosity lower bound"),
            "p_local_cap": ("2[MPa]", "Local pressure cap used by the empirical feedback"),
            "R_contact_ref": ("10[mohm]", "Equivalent contact resistance at p_ref"),
            "m_contact": ("0.5", "Contact-resistance pressure exponent"),
            "R_contact_eff": ("R_contact_ref*(p_ref/max(p_ext,p_floor))^m_contact", "Pressure-dependent equivalent contact resistance"),
            "coupling_on": ("1", "0=electrochemical baseline, 1=mechanical feedback and breathing"),
            "breathing_mode": ("2", "0=off, 2=nonlinear literature-shaped breathing"),
            "eps_sw_neg_lit": ("0.07", "Graphite electrode through-thickness strain amplitude"),
            "eps_sw_pos_lit": ("0.006", "LFP electrode through-thickness strain amplitude"),
            "theta_neg_ref": ("0.05910024", "Initial graphite lithiation ratio from coin V9"),
            "theta_pos_ref": ("0.99019973", "Initial LFP lithiation ratio from coin V9"),
            "cycle_rest": ("600[s]", "Rest between charge and discharge"),
            "V_charge_cut": ("3.65[V]", "Loaded-voltage charge cutoff"),
            "V_discharge_cut": ("2.50[V]", "Loaded-voltage discharge cutoff"),
            "E_cu": ("110[GPa]", "Copper Young modulus"),
            "nu_cu": ("0.34", "Copper Poisson ratio"),
            "rho_cu_mech": ("8960[kg/m^3]", "Copper density"),
            "E_al": ("70[GPa]", "Aluminum Young modulus"),
            "nu_al": ("0.33", "Aluminum Poisson ratio"),
            "rho_al_mech": ("2700[kg/m^3]", "Aluminum density"),
            "E_neg_mech": ("0.5[GPa]", "Graphite composite Young modulus"),
            "nu_neg_mech": ("0.30", "Graphite composite Poisson ratio"),
            "rho_neg_mech": ("1800[kg/m^3]", "Graphite composite density"),
            "E_sep_mech": ("0.1[GPa]", "Separator Young modulus"),
            "nu_sep_mech": ("0.40", "Separator Poisson ratio"),
            "rho_sep_mech": ("900[kg/m^3]", "Separator density"),
            "E_pos_mech": ("0.7[GPa]", "LFP composite Young modulus"),
            "nu_pos_mech": ("0.30", "LFP composite Poisson ratio"),
            "rho_pos_mech": ("2200[kg/m^3]", "LFP composite density"),
        }
        for name, (expression, description) in parameters.items():
            model.param().set(name, expression, description)

        create_interpolation(comp, "sw_gr_v9_fn", "sw_gr_v9", GRAPHITE_SHAPE, "Graphite nonlinear SOC-strain shape")
        create_interpolation(comp, "sw_lfp_v9_fn", "sw_lfp_v9", LFP_SHAPE, "LFP nonlinear SOC-strain shape")

        mechanical_groups = {
            "mech_cu": ("Copper mechanics", domains["negative_tab"] + domains["negative_header"] + domains["negative_cc"], "E_cu", "nu_cu", "rho_cu_mech"),
            "mech_neg": ("Graphite mechanics", domains["graphite"], "E_neg_mech", "nu_neg_mech", "rho_neg_mech"),
            "mech_sep": ("Separator mechanics", domains["separator"], "E_sep_mech", "nu_sep_mech", "rho_sep_mech"),
            "mech_pos": ("LFP mechanics", domains["lfp"], "E_pos_mech", "nu_pos_mech", "rho_pos_mech"),
            "mech_al": ("Aluminum mechanics", domains["positive_cc"] + domains["positive_header"] + domains["positive_tab"], "E_al", "nu_al", "rho_al_mech"),
        }
        for tag, (label, selection, young, poisson, density) in mechanical_groups.items():
            create_domain_variables(comp, tag, label, selection, {
                "E_mech": young, "nu_mech": poisson, "rho_mech": density,
            })

        create_domain_variables(comp, "var_v4_neg", "Graphite breathing-pressure-porosity", domains["graphite"], {
            "theta_neg_v4": "liion.cs_average/liion.csmax",
            "eps_breath_neg_v4": "coupling_on*if(breathing_mode<0.5,0,eps_sw_neg_lit*(sw_gr_v9(theta_neg_v4)-sw_gr_v9(theta_neg_ref)))",
            "p_comp_neg_v4": "min(p_local_cap,max(0[Pa],-solid.sy))",
            "epsl_neg_v4": "epsl_neg+coupling_on*(max(epsl_floor,epsl_neg*(1-beta_neg*p_comp_neg_v4))-epsl_neg)",
        })
        create_domain_variables(comp, "var_v4_sep", "Separator pressure-porosity", domains["separator"], {
            "p_comp_sep_v4": "min(p_local_cap,max(0[Pa],-solid.sy))",
            "epsl_sep_v4": "epsl_sep+coupling_on*(max(epsl_floor,epsl_sep*(1-beta_sep*p_comp_sep_v4))-epsl_sep)",
        })
        create_domain_variables(comp, "var_v4_pos", "LFP breathing-pressure-porosity", domains["lfp"], {
            "theta_pos_v4": "liion.cs_average/liion.csmax",
            "eps_breath_pos_v4": "coupling_on*if(breathing_mode<0.5,0,eps_sw_pos_lit*(sw_lfp_v9(theta_pos_v4)-sw_lfp_v9(theta_pos_ref)))",
            "p_comp_pos_v4": "min(p_local_cap,max(0[Pa],-solid.sy))",
            "epsl_pos_v4": "epsl_pos+coupling_on*(max(epsl_floor,epsl_pos*(1-beta_pos*p_comp_pos_v4))-epsl_pos)",
        })

        liion = comp.physics("liion")
        liion.feature("pce1").set("epsl", "epsl_neg_v4")
        liion.feature("sep1").set("epsl", "epsl_sep_v4")
        liion.feature("pce2").set("epsl", "epsl_pos_v4")

        create_box_boundary(comp, "sel_mech_bottom", "Bottom support on coated stack", "-1[um]", "H_cell+1[um]", "-1[um]", "1[um]")
        create_box_boundary(comp, "sel_mech_top", "Top pressure on coated stack", "-1[um]", "H_cell+1[um]", "z_pos_cc+L_pos_cc/2-1[um]", "z_pos_cc+L_pos_cc/2+1[um]")

        safe_remove(comp.physics(), "solid")
        comp.physics().create("solid", "SolidMechanics", "geom1")
        solid = comp.physics("solid")
        solid.label("2D pouch solid mechanics")
        solid.selection().set(all_domains)
        elastic = solid.feature("lemm1")
        elastic.set("E_mat", "userdef")
        elastic.set("E", "E_mech")
        elastic.set("nu_mat", "userdef")
        elastic.set("nu", "nu_mech")
        elastic.set("rho_mat", "userdef")
        elastic.set("rho", "rho_mech")

        elastic.feature().create("breath_neg_v4", "ExternalStrain", 2)
        breath_neg = elastic.feature("breath_neg_v4")
        breath_neg.label("Graphite nonlinear lithiation breathing")
        breath_neg.selection().set(domains["graphite"])
        breath_neg.set("StrainInput", "StrainTensor")
        breath_neg.set("eext_src", "userdef")
        breath_neg.set("eext", ["0", "eps_breath_neg_v4", "0"])

        elastic.feature().create("breath_pos_v4", "ExternalStrain", 2)
        breath_pos = elastic.feature("breath_pos_v4")
        breath_pos.label("LFP nonlinear lithiation breathing")
        breath_pos.selection().set(domains["lfp"])
        breath_pos.set("StrainInput", "StrainTensor")
        breath_pos.set("eext_src", "userdef")
        breath_pos.set("eext", ["0", "eps_breath_pos_v4", "0"])

        solid.feature().create("fix_bottom", "Fixed", 1)
        solid.feature("fix_bottom").selection().named("sel_mech_bottom")
        solid.feature().create("load_top", "BoundaryLoad", 1)
        solid.feature("load_top").selection().named("sel_mech_top")
        solid.feature("load_top").set("forceType", "FollowerPressure")
        solid.feature("load_top").set("pressure", "coupling_on*p_ext")

        # Average terminal operators make the cutoff voltage a true global scalar.
        for tag in ("aveop_neg_terminal", "aveop_pos_terminal"):
            safe_remove(comp.cpl(), tag)
            comp.cpl().create(tag, "Average", "geom1")
            comp.cpl(tag).selection().geom("geom1", 1)
        comp.cpl("aveop_neg_terminal").selection().named("sel_neg_terminal_2d")
        comp.cpl("aveop_pos_terminal").selection().named("sel_pos_terminal_2d")

        var1 = comp.variable("var1")
        var1.set("I", "i_1C*C_rate*(charge1-discharge1)")
        var1.set("I_app", "I")
        var1.set("V_terminal", "aveop_pos_terminal(liion.phis)-aveop_neg_terminal(liion.phis)")
        var1.set("V_contact_drop", "coupling_on*I*R_contact_eff")
        var1.set("vol_loaded", "V_terminal+V_contact_drop")
        liion.feature("ecd1").set("Its", "I_app")

        # One charge-rest-discharge cycle with the same event protocol as coin V9.
        safe_remove(comp.physics(), "ev")
        comp.physics().create("ev", "Events", "geom1")
        ev = comp.physics("ev")
        ev.feature().create("ds1", "DiscreteStates", -1)
        ev.feature("ds1").set("dim", [["charge1"], ["discharge1"], ["charge_hold"], ["idle_to_charge_time"], ["idle_to_discharge_time"], ["discharge_hold"]])
        ev.feature("ds1").set("dimInit", [["1"], ["0"], ["0"], ["0"], ["0"], ["0"]])
        ev.feature("ds1").set("dimDescr", [[""], [""], [""], [""], [""], [""]])
        ev.feature().create("is1", "IndicatorStates", -1)
        ev.feature("is1").set("indDim", [["discharge_end"], ["charge_end"], ["charge_idle_end"], ["discharge_idle_end"]])
        ev.feature("is1").set("g", [
            ["V_discharge_cut-vol_loaded"], ["vol_loaded-V_charge_cut"],
            ["t-idle_to_charge_time-cycle_rest"], ["t-idle_to_discharge_time-cycle_rest"],
        ])
        ev.feature("is1").set("dimInit", [["0"], ["0"], ["0"], ["0"]])
        ev.feature("is1").set("dimDescr", [[""], [""], [""], [""]])
        for tag, condition, values in (
            ("impl2", "(charge_end>0)&&(charge1==1)", ["0", "0", "1", "root.t", "0", "0"]),
            ("impl3", "(charge_idle_end>0)&&(charge_hold==1)", ["0", "1", "0", "0", "0", "0"]),
            ("impl5", "(discharge_end>0)&&(discharge1==1)", ["0", "0", "0", "0", "root.t", "1"]),
        ):
            ev.feature().create(tag, "ImplicitEvent", -1)
            node = ev.feature(tag)
            node.set("condition", condition)
            node.set("useConsistentInit", "1")
            node.set("reInitName", ["charge1", "discharge1", "charge_hold", "idle_to_charge_time", "idle_to_discharge_time", "discharge_hold"])
            node.set("reInitValue", values)

        for tag in [str(item) for item in model.sol().tags()]:
            safe_remove(model.sol(), tag)
        for tag in [str(item) for item in model.study().tags()]:
            safe_remove(model.study(), tag)
        model.study().create("std_cycle")
        study = model.study("std_cycle")
        study.label("0.5C charge-rest-discharge coupled cycle")
        study.feature().create("cdi", "CurrentDistributionInitialization")
        study.feature("cdi").activate("solid", False)
        study.feature("cdi").activate("ev", False)
        study.feature().create("time", "Transient")
        time = study.feature("time")
        time.activate("liion", True)
        time.activate("solid", True)
        time.activate("ev", True)
        time.set("tlist", "range(0,60,18000)")
        time.set("rtol", "1e-3")
        for tag in [str(item) for item in ev.feature().tags()]:
            ev.feature(tag).set("StudyStep", "std_cycle/time")

        model.save(str(OUTPUT))
        payload.update({
            "ok": True,
            "domains": domains,
            "mechanical_boundaries": {
                "bottom": entities(comp.selection("sel_mech_bottom"), 1),
                "top": entities(comp.selection("sel_mech_top"), 1),
            },
            "coupling": {
                "pressure_direction": "-solid.sy",
                "porosity": ["epsl_neg_v4", "epsl_sep_v4", "epsl_pos_v4"],
                "breathing": ["eps_breath_neg_v4", "eps_breath_pos_v4"],
                "force": "100[N]",
            },
            "protocol": "0.5C charge to 3.65 V, rest 600 s, 0.5C discharge to 2.50 V",
        })
    finally:
        ModelUtil.remove(TAG)
    return payload


def verify(payload: dict[str, object]) -> None:
    verify_tag = TAG + "_verify"
    model = ModelUtil.load(verify_tag, str(OUTPUT))
    try:
        comp = model.component("comp1")
        payload["reload"] = {
            "physics": [str(item) for item in comp.physics().tags()],
            "studies": [str(item) for item in model.study().tags()],
            "neg_porosity": str(comp.physics("liion").feature("pce1").getString("epsl")),
            "sep_porosity": str(comp.physics("liion").feature("sep1").getString("epsl")),
            "pos_porosity": str(comp.physics("liion").feature("pce2").getString("epsl")),
            "neg_external_strain": [str(item) for item in comp.physics("solid").feature("lemm1").feature("breath_neg_v4").getStringArray("eext")],
            "pos_external_strain": [str(item) for item in comp.physics("solid").feature("lemm1").feature("breath_pos_v4").getStringArray("eext")],
            "event_g": [str(item) for item in comp.physics("ev").feature("is1").getStringArray("g")],
        }
    finally:
        ModelUtil.remove(verify_tag)


def main() -> None:
    payload: dict[str, object]
    try:
        payload = build()
        verify(payload)
    except Exception:
        payload = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False, "traceback": traceback.format_exc()}
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MPH_TOOL_RESULT_BEGIN")
    print(json.dumps(payload, ensure_ascii=False))
    print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
