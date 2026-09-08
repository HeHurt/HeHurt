/*
 * CW391PouchPurpleMechanism3D.java
 *
 * COMSOL 6.4 Java model for a 3D pouch-cell mechanism check.
 *
 * Purpose:
 *   Compare a high-SOC 90-100% cycling window against a same-throughput
 *   full-window reference using CW391 LFP/graphite pouch design inputs.
 *
 * Scope:
 *   This is a 3D mechanism/proxy model, not a full 3D P2D ageing model.
 *   The 3D domain represents the active pouch footprint. Local thermal
 *   accumulation, high-SOC exposure, current-density nonuniformity and
 *   graphite lithiation are expressed as spatial fields. A global ODE
 *   integrates the average side-reaction risk rate for both scenarios.
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

public class CW391PouchPurpleMechanism3D {

  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_pouch_3d_purple_mechanism";

  public static Model run() {
    Model model = ModelUtil.create("Model");
    model.modelPath(WORKDIR);
    model.label("CW391PouchPurpleMechanism3D.mph");
    model.comments(
        "CW391 LFP/graphite 3D pouch mechanism proxy. "
        + "The model tests whether high-SOC exposure plus center-biased "
        + "thermal/current fields can produce larger center-to-edge purple-risk "
        + "area at equal Ah throughput.");

    // ---------------------------------------------------------------------
    // CW391 geometry and design inputs from:
    // D:/Users/hez/Desktop/hithium/COMSOL/docx/
    // battery design input table, sheet 'simulation parameter table', CW391.
    // ---------------------------------------------------------------------
    model.param().set("Lx", "0.086", "CW391 active width, m");
    model.param().set("Ly", "0.682", "CW391 active length, m");
    model.param().set("L_pos", "215.47213784610315e-6", "Positive electrode thickness, m");
    model.param().set("L_sep", "12.8e-6", "Separator thickness, m");
    model.param().set("L_neg", "179.7082838568585e-6", "Negative electrode thickness, m");
    model.param().set("Lz", "L_pos+L_sep+L_neg", "Representative stack thickness, m");
    model.param().set("Vdom", "Lx*Ly*Lz", "Model domain volume, m3");

    model.param().set("Q_nom_Ah", "3.03", "CW391 design capacity, Ah");
    model.param().set("crate", "0.5", "Short-term comparison C-rate");
    model.param().set("I_app_A", "crate*Q_nom_Ah", "Applied current magnitude, A");
    model.param().set("t_end", "720", "One 10% SOC-window half-cycle at 0.5C, s");
    model.param().set("Ah_throughput", "I_app_A*t_end/3600", "Same-throughput dose, Ah");

    model.param().set("pos_areal_loading", "0.391/1540.25*1e6", "Positive loading, g/m2");
    model.param().set("neg_areal_loading", "0.201/1540.25*1e6", "Negative loading, g/m2");
    model.param().set("pos_active_fraction", "0.981", "LFP active material fraction");
    model.param().set("neg_active_fraction", "0.973", "Graphite active material fraction");
    model.param().set("pos_comp_density", "2.52e6", "Positive compacted density, g/m3");
    model.param().set("neg_comp_density", "1.52e6", "Negative compacted density, g/m3");
    model.param().set("rp_pos_m", "0.86e-6/2", "LFP Dv50 radius, m");
    model.param().set("rp_neg_m", "11.8e-6/2", "Graphite Dv50 radius, m");
    model.param().set("c_e0", "960", "Electrolyte salt concentration, mol/m3");
    model.param().set("sigma_e_input", "0.011", "Electrolyte conductivity from input table, S/m");

    // Mechanism parameters. These are explicit assumptions for the proxy model.
    model.param().set("TambK", "298.15", "Ambient temperature, K");
    model.param().set("tauT", "240", "Thermal response time, s");
    model.param().set("TrefK", "298.15", "Arrhenius reference temperature, K");
    model.param().set("Ea_over_R", "4500", "Effective ageing activation temperature, K");
    model.param().set("sigma_center", "0.46", "Center hot-zone normalized radius");
    model.param().set("tab_amp", "0.06", "Weak tab-direction current bias");
    model.param().set("j_center_amp_90", "0.34", "High-SOC center current-density amplification");
    model.param().set("j_center_amp_full", "0.18", "Reference center current-density amplification");
    model.param().set("dT_base_90", "1.6", "High-SOC uniform temperature rise, K");
    model.param().set("dT_center_90", "6.3", "High-SOC center temperature excess, K");
    model.param().set("dT_base_full", "1.1", "Reference uniform temperature rise, K");
    model.param().set("dT_center_full", "3.2", "Reference center temperature excess, K");
    model.param().set("high_soc_weight_90", "1.00", "Fraction of throughput spent near high SOC");
    model.param().set("high_soc_weight_full", "0.18", "Reference high-SOC residence fraction");
    model.param().set("dry_center_90", "0.22", "Center dryout/wetting amplification at high SOC");
    model.param().set("dry_center_full", "0.08", "Reference dryout/wetting amplification");
    model.param().set("risk_tau", "520", "Risk normalization time, s");
    model.param().set("risk_thr", "2.10", "Dimensionless purple-risk threshold");
    model.param().set("risk_smooth", "0.055", "Smooth threshold width");

    model.component().create("comp1", true);
    model.component("comp1").geom().create("geom1", 3);
    model.component("comp1").geom("geom1").create("blk1", "Block");
    model.component("comp1").geom("geom1").feature("blk1")
        .set("size", new String[]{"Lx", "Ly", "Lz"});
    model.component("comp1").geom("geom1").feature("blk1")
        .set("pos", new String[]{"0", "0", "0"});
    model.component("comp1").geom("geom1").run();

    model.component("comp1").cpl().create("intop1", "Integration");
    model.component("comp1").cpl("intop1").selection().all();

    model.component("comp1").variable().create("var1");
    model.component("comp1").variable("var1").label("3D local mechanism fields");
    model.component("comp1").variable("var1").set("xn", "(x-Lx/2)/(Lx/2)");
    model.component("comp1").variable("var1").set("yn", "(y-Ly/2)/(Ly/2)");
    model.component("comp1").variable("var1").set("rn", "sqrt(xn^2+yn^2)");
    model.component("comp1").variable("var1").set("center_shape", "exp(-rn^2/(2*sigma_center^2))");
    model.component("comp1").variable("var1").set("tab_shape", "1+tab_amp*(y/Ly-0.5)");
    model.component("comp1").variable("var1").set("thermal_ramp", "1-exp(-t/tauT)");

    model.component("comp1").variable("var1").set(
        "T90K", "TambK+thermal_ramp*(dT_base_90+dT_center_90*center_shape)");
    model.component("comp1").variable("var1").set(
        "TfullK", "TambK+thermal_ramp*(dT_base_full+dT_center_full*center_shape)");
    model.component("comp1").variable("var1").set(
        "arr90", "exp(Ea_over_R*(1/TrefK-1/T90K))");
    model.component("comp1").variable("var1").set(
        "arrfull", "exp(Ea_over_R*(1/TrefK-1/TfullK))");

    model.component("comp1").variable("var1").set(
        "jshape90", "(1+j_center_amp_90*center_shape)*tab_shape");
    model.component("comp1").variable("var1").set(
        "jshapefull", "(1+j_center_amp_full*center_shape)*tab_shape");
    model.component("comp1").variable("var1").set(
        "wet90", "1+dry_center_90*center_shape");
    model.component("comp1").variable("var1").set(
        "wetfull", "1+dry_center_full*center_shape");

    model.component("comp1").variable("var1").set(
        "xLi_gr_90", "0.955+0.025*center_shape*tab_shape");
    model.component("comp1").variable("var1").set(
        "xLi_gr_full", "0.600+0.012*center_shape*tab_shape");
    model.component("comp1").variable("var1").set(
        "soc_gate90", "1/(1+exp(-(xLi_gr_90-0.90)/0.018))");
    model.component("comp1").variable("var1").set(
        "soc_gatefull", "1/(1+exp(-(xLi_gr_full-0.90)/0.018))");

    model.component("comp1").variable("var1").set(
        "risk_rate90", "high_soc_weight_90*arr90*jshape90*wet90*(0.85+0.15*soc_gate90)/risk_tau");
    model.component("comp1").variable("var1").set(
        "risk_ratefull", "high_soc_weight_full*arrfull*jshapefull*wetfull*(0.85+0.15*soc_gatefull)/risk_tau");
    model.component("comp1").variable("var1").set("risk90", "risk_rate90*t");
    model.component("comp1").variable("var1").set("riskfull", "risk_ratefull*t");
    model.component("comp1").variable("var1").set(
        "mask90", "0.5*(1+tanh((risk90-risk_thr)/risk_smooth))");
    model.component("comp1").variable("var1").set(
        "maskfull", "0.5*(1+tanh((riskfull-risk_thr)/risk_smooth))");
    model.component("comp1").variable("var1").set(
        "center_mask", "0.5*(1+tanh((0.45-rn)/0.04))");
    model.component("comp1").variable("var1").set(
        "edge_mask", "0.5*(1+tanh((rn-0.82)/0.04))");

    model.component("comp1").physics().create("ge", "GlobalEquations", "geom1");
    model.component("comp1").physics("ge").feature("ge1").set("DependentVariableQuantity", "none");
    model.component("comp1").physics("ge").feature("ge1").set("SourceTermQuantity", "none");
    model.component("comp1").physics("ge").feature("ge1")
        .setIndex("name", "Dose90", 0, 0)
        .setIndex("equation", "Dose90t-intop1(risk_rate90)/Vdom", 0, 0)
        .setIndex("initialValueU", "0", 0, 0)
        .setIndex("initialValueUt", "0", 0, 0)
        .setIndex("description", "Average integrated high-SOC purple-risk dose", 0, 0);
    model.component("comp1").physics("ge").feature("ge1")
        .setIndex("name", "DoseFull", 1, 0)
        .setIndex("equation", "DoseFullt-intop1(risk_ratefull)/Vdom", 1, 0)
        .setIndex("initialValueU", "0", 1, 0)
        .setIndex("initialValueUt", "0", 1, 0)
        .setIndex("description", "Average integrated full-window reference purple-risk dose", 1, 0);

    model.component("comp1").mesh().create("mesh1");
    model.component("comp1").mesh("mesh1").autoMeshSize(8);

    model.study().create("std1");
    model.study("std1").create("time", "Transient");
    model.study("std1").feature("time").set("tlist", "range(0,20,t_end)");
    model.study("std1").feature("time").set("rtol", "1e-6");

    model.sol().create("sol1");
    model.sol("sol1").study("std1");
    model.sol("sol1").attach("std1");
    model.sol("sol1").create("st1", "StudyStep");
    model.sol("sol1").feature("st1").set("study", "std1");
    model.sol("sol1").feature("st1").set("studystep", "time");
    model.sol("sol1").create("v1", "Variables");
    model.sol("sol1").create("t1", "Time");
    model.sol("sol1").feature("t1").set("tlist", "range(0,20,t_end)");
    model.sol("sol1").feature("t1").set("plot", "off");
    model.sol("sol1").feature("t1").set("rtol", "1e-6");
    model.sol("sol1").feature("t1").set("maxorder", 2);
    model.sol("sol1").feature("t1").create("fc1", "FullyCoupled");
    model.sol("sol1").feature("t1").feature("fc1").set("linsolver", "dDef");

    model.result().table().create("tbl_metrics", "Table");
    model.result().table("tbl_metrics").comments("Final comparison metrics");
    model.result().numerical().create("gev_metrics", "EvalGlobal");
    model.result().numerical("gev_metrics").set("data", "dset1");
    model.result().numerical("gev_metrics").set("table", "tbl_metrics");
    model.result().numerical("gev_metrics").set("expr", new String[]{
        "Ah_throughput",
        "Dose90", "DoseFull", "Dose90/DoseFull",
        "100*intop1(mask90)/Vdom", "100*intop1(maskfull)/Vdom",
        "intop1(risk90)/Vdom", "intop1(riskfull)/Vdom",
        "(intop1(risk90*center_mask)/intop1(center_mask))/(intop1(risk90*edge_mask)/intop1(edge_mask))",
        "(intop1(riskfull*center_mask)/intop1(center_mask))/(intop1(riskfull*edge_mask)/intop1(edge_mask))",
        "intop1(T90K*center_mask)/intop1(center_mask)-273.15",
        "intop1(T90K*edge_mask)/intop1(edge_mask)-273.15",
        "intop1(TfullK*center_mask)/intop1(center_mask)-273.15",
        "intop1(TfullK*edge_mask)/intop1(edge_mask)-273.15",
        "intop1(xLi_gr_90*center_mask)/intop1(center_mask)",
        "intop1(xLi_gr_90*edge_mask)/intop1(edge_mask)",
        "intop1(xLi_gr_full*center_mask)/intop1(center_mask)",
        "intop1(xLi_gr_full*edge_mask)/intop1(edge_mask)"
    });
    model.result().numerical("gev_metrics").set("descr", new String[]{
        "same_Ah_throughput",
        "dose_90_100", "dose_full_reference", "dose_ratio_90_to_reference",
        "purple_area_90_pct", "purple_area_reference_pct",
        "avg_risk_90", "avg_risk_reference",
        "center_edge_risk_ratio_90", "center_edge_risk_ratio_reference",
        "center_temp_90_C", "edge_temp_90_C",
        "center_temp_reference_C", "edge_temp_reference_C",
        "center_graphite_lithiation_90", "edge_graphite_lithiation_90",
        "center_graphite_lithiation_reference", "edge_graphite_lithiation_reference"
    });

    model.result().table().create("tbl_timeseries", "Table");
    model.result().table("tbl_timeseries").comments("Time evolution of scenario-level metrics");
    model.result().numerical().create("gev_timeseries", "EvalGlobal");
    model.result().numerical("gev_timeseries").set("data", "dset1");
    model.result().numerical("gev_timeseries").set("table", "tbl_timeseries");
    model.result().numerical("gev_timeseries").set("expr", new String[]{
        "Dose90", "DoseFull", "Dose90/DoseFull",
        "100*intop1(mask90)/Vdom", "100*intop1(maskfull)/Vdom",
        "intop1(T90K*center_mask)/intop1(center_mask)-273.15",
        "intop1(T90K*edge_mask)/intop1(edge_mask)-273.15",
        "intop1(TfullK*center_mask)/intop1(center_mask)-273.15",
        "intop1(TfullK*edge_mask)/intop1(edge_mask)-273.15"
    });
    model.result().numerical("gev_timeseries").set("descr", new String[]{
        "dose_90_100", "dose_full_reference", "dose_ratio_90_to_reference",
        "purple_area_90_pct", "purple_area_reference_pct",
        "center_temp_90_C", "edge_temp_90_C",
        "center_temp_reference_C", "edge_temp_reference_C"
    });

    model.result().export().create("exp_metrics", "Table");
    model.result().export("exp_metrics").set("table", "tbl_metrics");
    model.result().export("exp_metrics").set("filename", WORKDIR + "/metrics.csv");
    model.result().export("exp_metrics").set("header", true);

    model.result().export().create("exp_timeseries", "Table");
    model.result().export("exp_timeseries").set("table", "tbl_timeseries");
    model.result().export("exp_timeseries").set("filename", WORKDIR + "/timeseries.csv");
    model.result().export("exp_timeseries").set("header", true);

    return model;
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(true);
    Model model = run();
    model.component("comp1").mesh("mesh1").run();
    model.study("std1").run();
    model.result().numerical("gev_metrics").set("looplevelinput", new String[]{"last"});
    model.result().numerical("gev_metrics").setResult();
    model.result().numerical("gev_timeseries").setResult();
    model.result().export("exp_metrics").run();
    model.result().export("exp_timeseries").run();
    model.save(WORKDIR + "/CW391PouchPurpleMechanism3D.mph");
    ModelUtil.remove("Model");
  }
}
