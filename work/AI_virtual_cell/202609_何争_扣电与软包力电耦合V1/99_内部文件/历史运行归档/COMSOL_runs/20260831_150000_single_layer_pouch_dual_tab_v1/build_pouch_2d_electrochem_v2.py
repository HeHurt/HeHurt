"""Migrate the validated coin-V9 electrochemistry onto the confirmed 2D pouch cross-section."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260820_140000_coin_v9_nonlinear_breathing_cycle\model_snapshot.mph")
PARAMS = Path(r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params")
OUTPUT = RUN / "pouch_dual_tab_2d_cross_section_v2_coin_v9_electrochem.mph"
RESULT = RUN / "build_pouch_2d_electrochem_v2_result.json"
TAG = "pouch_2d_electrochem_v2"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def create_rectangle(geom, tag: str, label: str, pos: list[str], size: list[str]) -> None:
    geom.feature().create(tag, "Rectangle")
    feature = geom.feature(tag)
    feature.label(label)
    feature.set("pos", pos)
    feature.set("size", size)
    feature.set("selresult", "on")


def entities(selection, dimension: int) -> list[int]:
    return sorted(int(item) for item in selection.entities(dimension))


def safe_remove(container, tag: str) -> None:
    try:
        container.remove(tag)
    except Exception:
        pass


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove_model()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        model.label("Single-layer pouch 2D V2 - coin V9 electrochemistry")
        model.comments(
            "Confirmed 2D length-thickness geometry with y display scale 100. "
            "LFP/graphite/electrolyte parameters and lookup functions migrated from coin V9."
        )
        comp = model.component("comp1")

        # Remove mechanics/breathing-only infrastructure while retaining the complete
        # coin-V9 parameters, material definitions and electrochemical functions.
        safe_remove(comp.physics(), "solid")
        safe_remove(comp.physics(), "ev")
        safe_remove(comp.physics(), "liion")
        for component_tag in [str(item) for item in model.component().tags()]:
            if component_tag != "comp1":
                safe_remove(model.component(), component_tag)
        for group in (
            "mech_steel", "mech_cu", "mech_neg", "mech_sep", "mech_pos", "mech_al", "mech_pp",
            "var_v7_neg", "var_v7_sep", "var_v7_pos", "var_v8_neg", "var_v8_sep", "var_v8_pos",
        ):
            safe_remove(comp.variable(), group)
        for material in ("mat6", "mat7"):
            safe_remove(comp.material(), material)
        for selection_tag in [str(item) for item in comp.selection().tags()]:
            safe_remove(comp.selection(), selection_tag)

        # Remove old studies, solutions, probes and results tied to the axisymmetric coin geometry.
        for tag in [str(item) for item in model.sol().tags()]:
            safe_remove(model.sol(), tag)
        for tag in [str(item) for item in model.study().tags()]:
            safe_remove(model.study(), tag)
        for tag in [str(item) for item in comp.probe().tags()]:
            safe_remove(comp.probe(), tag)
        for tag in [str(item) for item in model.result().numerical().tags()]:
            safe_remove(model.result().numerical(), tag)
        for tag in [str(item) for item in model.result().dataset().tags()]:
            safe_remove(model.result().dataset(), tag)
        for tag in [str(item) for item in model.result().table().tags()]:
            safe_remove(model.result().table(), tag)
        for tag in [str(item) for item in model.result().tags()]:
            safe_remove(model.result(), tag)

        p = model.param()
        geometry_parameters = {
            "H_cell": ("86[mm]", "Coated active length"),
            "W_cell": ("52[mm]", "Effective out-of-plane coated width"),
            "H_neg_cc_ext": ("14.5[mm]", "Negative bare collector extension"),
            "H_pos_cc_ext": ("12.5[mm]", "Positive bare collector extension"),
            "H_tab": ("35[mm]", "Tab length in the 2D section"),
            "W_tab": ("30[mm]", "Physical out-of-plane tab width"),
            "L_neg_cc": ("8[um]", "Negative collector full nominal thickness"),
            "L_neg": ("61.5[um]", "Graphite electrode thickness"),
            "L_sep": ("9[um]", "Separator thickness"),
            "L_pos": ("84[um]", "LFP electrode thickness"),
            "L_pos_cc": ("13[um]", "Positive collector full nominal thickness"),
            "L_tab": ("0.20[mm]", "Tab thickness"),
            "x_neg_header": ("-H_neg_cc_ext", "Negative header start"),
            "x_neg_tab": ("-H_neg_cc_ext-H_tab", "Negative tab start"),
            "x_pos_header": ("H_cell", "Positive header start"),
            "x_pos_tab": ("H_cell+H_pos_cc_ext", "Positive tab start"),
            "z_pos_cc": ("L_neg_cc/2+L_neg+L_sep+L_pos", "Positive collector lower coordinate"),
            "C_rate": ("0.5", "Short smoke-test charge rate"),
            "Ac": ("W_cell*H_cell", "Single-layer coated area used for capacity scaling"),
        }
        for name, (expression, description) in geometry_parameters.items():
            p.set(name, expression, description)
        p.set("SOC", ".01", "Initial SOC, identical to coin V9")

        # Point all external electrochemical tables to the user-confirmed parameter folder.
        function_files = {
            "ocv_lfp_base": "LFP.dat",
            "ocv_gr_discharge": "Gr_ocv.txt",
            "ocv_gr_charge": "Gr_charge.dat",
            "ely_sigma": "E_sigma.dat",
            "ely_D": "E_DL_int1.dat",
            "ely_tplus": "E_transpNm.dat",
        }
        function_units = {
            "ocv_lfp_base": ("", "V", "linear"),
            "ocv_gr_discharge": ("", "V", "const"),
            "ocv_gr_charge": ("", "V", "const"),
            "ely_sigma": ("mol/m^3", "S/m", "const"),
            "ely_D": ("mol/m^3", "m^2/s", "const"),
            "ely_tplus": ("mol/m^3", "1", "const"),
        }
        for function_tag, filename in function_files.items():
            safe_remove(model.func(), function_tag)
            model.func().create(function_tag, "Interpolation")
            function = model.func(function_tag)
            argument_unit, function_unit, extrapolation = function_units[function_tag]
            function.label(f"Coin V9: {function_tag}")
            function.set("funcname", function_tag)
            function.set("source", "file")
            function.set("filename", str(PARAMS / filename))
            function.set("argunit", [argument_unit])
            function.set("fununit", [function_unit])
            function.set("interp", "linear")
            function.set("extrap", extrapolation)
            function.importData()

        # Rebuild the confirmed Cartesian length-thickness geometry.
        geom = comp.geom("geom1")
        geom.axisymmetric(False)
        for feature_tag in reversed([str(item) for item in geom.feature().tags()]):
            if feature_tag != "fin":
                safe_remove(geom.feature(), feature_tag)
        create_rectangle(geom, "r_neg_cc", "Negative current collector - coated", ["0", "0"], ["H_cell", "L_neg_cc/2"])
        create_rectangle(geom, "r_neg", "Graphite electrode", ["0", "L_neg_cc/2"], ["H_cell", "L_neg"])
        create_rectangle(geom, "r_sep", "Separator", ["0", "L_neg_cc/2+L_neg"], ["H_cell", "L_sep"])
        create_rectangle(geom, "r_pos", "LFP electrode", ["0", "L_neg_cc/2+L_neg+L_sep"], ["H_cell", "L_pos"])
        create_rectangle(geom, "r_pos_cc", "Positive current collector - coated", ["0", "z_pos_cc"], ["H_cell", "L_pos_cc/2"])
        create_rectangle(geom, "r_neg_header", "Negative bare collector extension", ["x_neg_header", "0"], ["H_neg_cc_ext", "L_neg_cc/2"])
        create_rectangle(geom, "r_pos_header", "Positive bare collector extension", ["x_pos_header", "z_pos_cc"], ["H_pos_cc_ext", "L_pos_cc/2"])
        create_rectangle(geom, "r_neg_tab", "Negative tab", ["x_neg_tab", "L_neg_cc/2-L_tab"], ["H_tab", "L_tab"])
        create_rectangle(geom, "r_pos_tab", "Positive tab", ["x_pos_tab", "z_pos_cc"], ["H_tab", "L_tab"])
        geom.run()
        if int(geom.getNDomains()) != 9:
            raise RuntimeError(f"Expected 9 pouch domains, got {geom.getNDomains()}")

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
        if any(len(value) != 1 for value in domains.values()):
            raise RuntimeError(f"Generated geometry selections are not one-to-one: {domains}")

        # Robust terminal-edge selections independent of boundary numbering.
        for selection_tag in ("sel_neg_terminal_2d", "sel_pos_terminal_2d"):
            comp.selection().create(selection_tag, "Box")
            comp.selection(selection_tag).set("entitydim", "1")
            comp.selection(selection_tag).set("condition", "inside")
        neg_terminal = comp.selection("sel_neg_terminal_2d")
        neg_terminal.label("Negative tab outer terminal edge")
        neg_terminal.set("xmin", "x_neg_tab-1[um]")
        neg_terminal.set("xmax", "x_neg_tab+1[um]")
        neg_terminal.set("ymin", "L_neg_cc/2-L_tab-1[um]")
        neg_terminal.set("ymax", "L_neg_cc/2+1[um]")
        pos_terminal = comp.selection("sel_pos_terminal_2d")
        pos_terminal.label("Positive tab outer terminal edge")
        pos_terminal.set("xmin", "x_pos_tab+H_tab-1[um]")
        pos_terminal.set("xmax", "x_pos_tab+H_tab+1[um]")
        pos_terminal.set("ymin", "z_pos_cc-1[um]")
        pos_terminal.set("ymax", "z_pos_cc+L_tab+1[um]")

        # Rebind materials. The electrochemical material definitions themselves remain coin-V9 copies.
        comp.material("mat1").selection().set(domains["graphite"])
        comp.material("mat2").selection().set(domains["lfp"])
        comp.material("mat3").selection().set(domains["separator"])
        comp.material("mat4").selection().set(domains["positive_cc"] + domains["positive_header"] + domains["positive_tab"])
        comp.material("mat5").selection().set(domains["negative_cc"] + domains["negative_header"] + domains["negative_tab"])

        # Recreate the interface as Cartesian 2D. The coin interface itself was
        # axisymmetric and therefore could not be safely reused on this geometry.
        comp.physics().create("liion", "LithiumIonBatteryMPH", "geom1")
        liion = comp.physics("liion")
        liion.feature().create("cc1", "CurrentConductor", 2)
        liion.feature().create("pce1", "PorousElectrode", 2)
        liion.feature().create("pce2", "PorousElectrode", 2)
        liion.feature().create("egnd1", "ElectricGround", 1)
        liion.feature().create("ecd1", "ElectrodeCurrent", 1)
        liion.feature().create("init2", "init", 2)
        liion.feature().create("init3", "init", 2)
        liion.feature().create("init4", "init", 2)
        liion.selection().set(list(range(1, 10)))
        liion.feature("pce1").selection().set(domains["graphite"])
        liion.feature("pce2").selection().set(domains["lfp"])
        conductor_domains = sorted(
            domains["negative_tab"] + domains["negative_header"] + domains["negative_cc"]
            + domains["positive_cc"] + domains["positive_header"] + domains["positive_tab"]
        )
        liion.feature("cc1").selection().set(conductor_domains)

        socicd = liion.feature("socicd1")
        socicd.set("SOC_init", "SOC")
        socicd.set("Ecell_0SOC", "2.35[V]")
        socicd.set("Ecell_100SOC", "3.65[V]")
        socicd.set("Ecell_init", "2.37[V]")
        socicd.feature("neges1").selection().set(domains["graphite"])
        socicd.feature("poses1").selection().set(domains["lfp"])

        for electrode_tag, sigma, epsl, epss in (
            ("pce1", "sigma_neg", "epsl_neg", "epss_neg"),
            ("pce2", "sigma_pos", "epsl_pos", "epss_pos"),
        ):
            electrode = liion.feature(electrode_tag)
            electrode.set("ElectrolyteMaterial", "mat3")
            electrode.set("sigmal_mat", "userdef")
            electrode.set("sigmal", "ely_sigma(cl)")
            electrode.set("Dl_mat", "userdef")
            electrode.set("Dl", "ely_D(cl)")
            electrode.set("transpNum_mat", "userdef")
            electrode.set("transpNum", "ely_tplus(cl)")
            electrode.set("ElectrodeMaterial", "dommat")
            electrode.set("sigma_mat", "userdef")
            electrode.set("sigma", sigma)
            electrode.set("epsl", epsl)
            electrode.set("epss", epss)
            electrode.set("IonicCorrModel", "Bruggeman")
            electrode.set("ElectricCorrModel", "Bruggeman")
            electrode.set("DiffusionCorrModel", "Bruggeman")
            electrode.set("Migration", "Bruggeman")

        separator = liion.feature("sep1")
        separator.set("ElectrolyteMaterial", "dommat")
        separator.set("sigmal_mat", "userdef")
        separator.set("sigmal", "ely_sigma(cl)")
        separator.set("Dl_mat", "userdef")
        separator.set("Dl", "ely_D(cl)")
        separator.set("transpNum_mat", "userdef")
        separator.set("transpNum", "ely_tplus(cl)")
        separator.set("epsl", "epsl_sep")
        separator.set("IonicCorrModel", "Bruggeman")
        separator.set("DiffusionCorrModel", "Bruggeman")
        separator.set("Migration", "Bruggeman")

        for electrode_tag, ds, csmax, rp, c0, k_rate, ocv in (
            ("pce1", "Ds_neg", "csmax_neg", "rp_neg", "c0_neg", "k_neg", "ocv_gr_charge(liion.cs_surface/liion.csmax)"),
            ("pce2", "Ds_pos", "csmax_pos", "rp_pos", "c0_pos", "k_pos", "ocv_lfp_base(liion.cs_surface/liion.csmax)+0.02[V]"),
        ):
            particle = liion.feature(electrode_tag).feature("pin1")
            particle.set("ParticleConcentrationType", "SolveinExtraDimension")
            particle.set("Ds_mat", "userdef")
            particle.set("Ds", ds)
            particle.set("ParticleMaterial", "dommat")
            particle.set("cEeqref_mat", "userdef")
            particle.set("cEeqref", csmax)
            particle.set("rp", rp)
            particle.set("ParticleType", "Spheres")
            particle.set("SpeciesSettingsType", "InitialSpeciesConcentration")
            particle.set("csinit", c0)
            particle.set("Distribution", "CubicRoot")
            particle.set("Nel", "6")
            particle.set("Nord", "1")

            reaction = liion.feature(electrode_tag).feature("per1")
            reaction.set("MaterialOption", "dommat")
            reaction.set("Eeq_mat", "userdef")
            reaction.set("Eeq", ocv)
            reaction.set("ElectrodeKinetics", "LithiumInsertion")
            reaction.set("i0Type", "userdef")
            reaction.set("i0refType", "FromRateConstant")
            reaction.set("k", k_rate)
            reaction.set("alphaa", "0.5")
            reaction.set("alphac", "0.5")
            reaction.set("LinearizeConcentrationDependence", "1")
            reaction.set("ExtrapolateInsertionKinetics", "1")
            reaction.set("xpolsoc", "1e-3")
            reaction.set("ActiveSpecificSurfaceAreaType", "ParticleBasedArea")
            reaction.set("ParticleType", "Spheres")
            reaction.set("rp", rp)

        liion.feature("pce1").set("epsl", "epsl_neg")
        liion.feature("sep1").set("epsl", "epsl_sep")
        liion.feature("pce2").set("epsl", "epsl_pos")
        liion.feature("egnd1").selection().named("sel_neg_terminal_2d")
        liion.feature("ecd1").selection().named("sel_pos_terminal_2d")
        liion.feature("egnd1").set("IncludeContactResistance", "0")
        liion.feature("ecd1").set("IncludeContactResistance", "0")

        # Preserve the V9 OCV direction and explicit low-SOC initial state.
        liion.feature("pce1").feature("per1").set("Eeq", "ocv_gr_charge(liion.cs_surface/liion.csmax)")
        liion.feature("pce2").feature("per1").set("Eeq", "ocv_lfp_base(liion.cs_surface/liion.csmax)+0.02[V]")
        liion.feature("init1").set("phil", "-ocv_gr_charge(socini_neg)")
        liion.feature("init1").set("cl", "cl_0")
        liion.feature("init1").set("phis", "0")
        liion.feature("init2").selection().set(domains["negative_tab"] + domains["negative_header"] + domains["negative_cc"])
        liion.feature("init2").set("phis", "0[V]")
        liion.feature("init3").selection().set(domains["positive_cc"] + domains["positive_header"] + domains["positive_tab"])
        liion.feature("init3").set("phis", "ocv_lfp_base(socini_pos)+0.02[V]-ocv_gr_charge(socini_neg)")
        liion.feature("init4").selection().set(domains["lfp"])
        liion.feature("init4").set("phil", "-ocv_gr_charge(socini_neg)")
        liion.feature("init4").set("cl", "cl_0")
        liion.feature("init4").set("phis", "ocv_lfp_base(socini_pos)+0.02[V]-ocv_gr_charge(socini_neg)")

        # Default No Flux and Insulation nodes own non-editable applicable-boundary
        # selections and automatically update after the Cartesian geometry rebuild.

        var1 = comp.variable("var1")
        var1.set("I_app", "i_1C*C_rate", "Applied positive charging current")
        var1.set("I", "I_app", "Compatibility alias for the migrated terminal condition")
        var1.set("C", "C_rate", "C-rate compatibility alias")
        try:
            var1.remove("V_contact_drop")
            var1.remove("vol_loaded")
        except Exception:
            pass
        liion.feature("ecd1").set("ElectronicCurrentType", "TotalCurrent")
        liion.feature("ecd1").set("TotalCurrentType", "ExplicitValue")
        liion.feature("ecd1").set("Its", "I_app")
        liion.feature("ecd1").set(
            "phis0init", "ocv_lfp_base(socini_pos)+0.02[V]-ocv_gr_charge(socini_neg)"
        )

        # Replace the coin mesh with a mapped quadrilateral mesh for the thin 2D stack.
        safe_remove(comp.mesh(), "mesh1")
        comp.mesh().create("mesh1")
        mesh = comp.mesh("mesh1")
        size = mesh.feature("size")
        size.set("custom", "on")
        size.set("hmax", "2[mm]")
        size.set("hmin", "1[um]")
        size.set("hgrad", "1.25")
        size.set("hcurve", "0.25")
        mesh.feature().create("map1", "Map")
        mesh.run()

        # The user-confirmed display exaggeration is a view setting, not a physical thickness change.
        view = comp.view("view1")
        axis = view.axis()
        axis.set("viewscaletype", "manual")
        axis.set("xscale", "1")
        axis.set("yscale", "100")
        axis.set("xmin", "-58.65000534057617")
        axis.set("xmax", "142.64999389648438")
        axis.set("ymin", "-0.7509139776229858")
        axis.set("ymax", "0.9134140014648438")

        # Fresh electrochemical-only study; no stale coin/mechanics solver is retained.
        model.study().create("std1")
        study = model.study("std1")
        study.label("2D pouch electrochemical smoke")
        study.feature().create("cdi", "CurrentDistributionInitialization")
        study.feature("cdi").set("useinitsol", "off")
        study.feature().create("time", "Transient")
        study.feature("time").set("tlist", "range(0,5,60)")
        study.feature("time").set("rtol", "1e-3")

        model.save(str(OUTPUT))
        payload.update({
            "ok": True,
            "domains": domains,
            "terminals": {"negative": entities(neg_terminal, 1), "positive": entities(pos_terminal, 1)},
            "materials": {
                "graphite": domains["graphite"], "lfp": domains["lfp"], "electrolyte": domains["separator"],
                "copper": sorted(domains["negative_tab"] + domains["negative_header"] + domains["negative_cc"]),
                "aluminum": sorted(domains["positive_cc"] + domains["positive_header"] + domains["positive_tab"]),
            },
            "electrochemistry": {
                "SOC": str(p.get("SOC")), "Ac": str(p.get("Ac")), "C_rate": str(p.get("C_rate")),
                "functions": {tag: str(PARAMS / filename) for tag, filename in function_files.items()},
                "mechanics_removed": True, "pressure_porosity_feedback_removed": True,
            },
            "mesh": {"type": "Mapped quadrilateral", "hmax": "2[mm]", "hmin": "1[um]"},
            "view": {"xscale": 1, "yscale": 100},
            "study": "CDI + 0.5C charge, range(0,5,60) s",
        })
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove_model()
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
