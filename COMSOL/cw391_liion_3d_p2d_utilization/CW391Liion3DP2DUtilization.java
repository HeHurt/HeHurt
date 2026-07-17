/*
 * CW391Liion3DP2DUtilization.java
 *
 * Builds a CW391 representative pouch-sheet model from COMSOL's official
 * 3D Lithium-Ion Battery pouch-cell utilization example.
 *
 * The retained COMSOL structure is a true 3D liion model with porous
 * electrodes, separator, current collectors/tabs and particle intercalation
 * extra dimensions, i.e. a pseudo-4D 3D-P2D model.
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

public class CW391Liion3DP2DUtilization {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";
  private static final String BASE = WORKDIR + "/pouch_cell_utilization_base.mph";

  private static void applyCW391Params(Model model, String scenario, String socStart) {
    model.modelPath(WORKDIR);
    model.label("CW391_3D_P2D_" + scenario + ".mph");
    model.comments(
        "CW391 representative 20 mm x 10 mm LFP/graphite pouch-sheet model. "
        + "Built by modifying COMSOL's pouch_cell_utilization 3D Lithium-Ion "
        + "Battery example. Geometry is a foil-to-foil unit cell with particle "
        + "intercalation extra dimensions.");

    // Representative sheet size with the official 1:2 mesh-safe tab topology.
    model.param().set("W_cell", "10[mm]", "Representative sheet short side in COMSOL x direction");
    model.param().set("H_cell", "20[mm]", "Representative sheet long side in COMSOL y direction");
    model.param().set("W_tab", "5[mm]", "Simplified tab width");
    model.param().set("H_tab", "1[mm]", "Simplified tab height");

    // CW391 foil-to-foil layer stack. Coating thicknesses use one side of the
    // double-sided electrode thickness from the design sheet.
    model.param().set("L_neg_cc", "8[um]", "CW391 Cu current collector thickness");
    model.param().set("L_pos_cc", "14[um]", "CW391 Al current collector thickness");
    model.param().set("L_neg", "85.85414192842925[um]", "CW391 single-side graphite coating thickness");
    model.param().set("L_sep", "12.8[um]", "CW391 separator thickness");
    model.param().set("L_pos", "100.73606892305158[um]", "CW391 single-side LFP coating thickness");
    model.component("comp1").geom("geom1").feature("blk2").set("lz", "L_pos_cc/2");
    model.component("comp1").geom("geom1").feature("blk2").set("size",
        new String[]{"W_tab", "H_tab", "L_pos_cc/2"});

    // CW391 LFP/graphite electrochemical design values.
    model.param().set("rp_pos", "0.43[um]", "CW391 LFP Dv50/2");
    model.param().set("rp_neg", "5.90[um]", "CW391 graphite Dv50/2");
    model.param().set("sigmas_pos", "4[S/m]", "Effective LFP composite conductivity");
    model.param().set("sigmas_neg", "100[S/m]", "Effective graphite composite conductivity");
    model.param().set("csmax_pos", "22806[mol/m^3]", "LFP maximum host concentration");
    model.param().set("csmax_neg", "31370[mol/m^3]", "Graphite maximum host concentration");
    model.param().set("epss_pos", "0.709", "CW391 LFP active volume fraction from loading/thickness");
    model.param().set("epss_neg", "0.664", "CW391 graphite active volume fraction from loading/thickness");
    model.param().set("i0ref_pos", "0.70[A/m^2]", "Reference exchange current density positive electrode");
    model.param().set("i0ref_neg", "0.96[A/m^2]", "Reference exchange current density negative electrode");

    // Area-scaled capacity requested by user: 3.03 Ah * (20*10)/(86*682).
    model.param().set("Q_CW391_full", "3.03[A*h]", "Original CW391 pouch design capacity");
    model.param().set("A_CW391_full", "86[mm]*682[mm]", "Original CW391 reference area");
    model.param().set("A_model", "W_cell*H_cell", "Representative model area");
    model.param().set("Q_model_target", "Q_CW391_full*A_model/A_CW391_full", "Area-scaled target capacity");

    // Short charge windows with equal SOC throughput. 4C is used to make
    // in-plane utilization differences observable in the small smoke model.
    model.param().set("SOC_start", socStart, "Initial cell SOC for " + scenario);
    model.param().set("SOC_window", "0.1", "Same 10% SOC throughput in both scenarios");
    model.param().set("C_rate", "4[1]", "High-rate short-window charge for utilization contrast");
    model.param().set("sim_time", "1[h]*SOC_window/C_rate", "Simulation time");

    // Drive the official liion terminal by the CW391 area-scaled target current.
    model.component("comp1").variable("var1").set("I_target", "Q_model_target*C_rate/1[h]");
    model.component("comp1").variable("var1").set("I_app", "I_target");

    // Positive electrode is changed from the COMSOL example's LMO material to
    // a smooth LFP-like equilibrium-potential law. This is intentionally smooth
    // to support Newton convergence in the first 3D P2D run.
    try {
      model.component("comp1").material("mat4").label("LFP, LiFePO4 (Positive, Li-ion Battery)");
      model.component("comp1").material("mat4").propertyGroup("ElectrodePotential")
          .set("Eeq", "3.43-0.10*doc+0.018*tanh((doc-0.08)/0.045)-0.018*tanh((doc-0.92)/0.045)");
      model.component("comp1").material("mat4").propertyGroup("ElectrodePotential")
          .set("dEeqdT", "0[V/K]");
      model.component("comp1").material("mat4").propertyGroup("ElectrodePotential")
          .set("cEeqref", "csmax_pos");
    } catch (Exception ex) {
      System.out.println("WARN: Could not override positive material OCV: " + ex.getMessage());
    }

    model.component("comp1").geom("geom1").run();
    // The official geometry assumed equal Cu/Al collector thicknesses. After
    // correcting the positive-tab block to L_pos_cc/2, the large positive
    // current-collector top face remains boundary 20.
    model.component("comp1").mesh("mesh1").feature("map1").selection().geom("geom1", 2);
    model.component("comp1").mesh("mesh1").feature("map1").selection().set(new int[]{20});
    model.component("comp1").mesh("mesh1").feature("swe1").selection().set(1, 2, 3, 4, 5, 6, 7);
    model.component("comp1").mesh("mesh1").run();
    model.study("std1").feature("time").set("tlist", "range(0,1,sim_time)");
    model.study("std1").feature("time").set("rtol", "1e-3");
  }

  private static void addMetrics(Model model, String scenario) {
    String tbl = "tbl_metrics_" + scenario;
    String gev = "gev_metrics_" + scenario;
    model.result().table().create(tbl, "Table");
    model.result().table(tbl).comments("Final scalar metrics for " + scenario);
    model.result().numerical().create(gev, "EvalGlobal");
    model.result().numerical(gev).set("data", "dset1");
    model.result().numerical(gev).set("table", tbl);
    model.result().numerical(gev).set("expr", new String[]{
        "Q_model_target/1[A*h]",
        "liion.I_1C_cell/1[A]",
        "I_target/1[A]",
        "I_app/1[A]",
        "liion.phis0_ec1",
        "liion.SOC_cell",
        "liion.soc_average_pce1",
        "liion.soc_average_pce2"
    });
    model.result().numerical(gev).set("descr", new String[]{
        "target_area_scaled_capacity_Ah",
        "comsol_auto_1C_current_A",
        "target_current_A",
        "actual_liion_current_A",
        "cell_voltage_V",
        "cell_SOC",
        "average_negative_electrode_SOC",
        "average_positive_electrode_SOC"
    });
    model.result().numerical(gev).set("looplevelinput", new String[]{"last"});
    model.result().export().create("exp_metrics_" + scenario, "Table");
    model.result().export("exp_metrics_" + scenario).set("table", tbl);
    model.result().export("exp_metrics_" + scenario).set("filename", WORKDIR + "/metrics_" + scenario + ".csv");
    model.result().export("exp_metrics_" + scenario).set("header", true);
  }

  private static void addImageExport(Model model, String scenario, String plotGroupTag, String suffix) {
    String tag = "img_" + scenario + "_" + suffix;
    model.result().export().create(tag, "Image");
    model.result().export(tag).set("sourcetype", "plotgroup");
    model.result().export(tag).set("sourceobject", plotGroupTag);
    model.result().export(tag).set("target", "file");
    model.result().export(tag).set("imagetype", "png");
    model.result().export(tag).set("pngfilename", WORKDIR + "/plots/" + scenario + "_" + suffix + ".png");
    model.result().export(tag).set("width", "1200");
    model.result().export(tag).set("height", "900");
    model.result().export(tag).set("unit", "px");
    model.result().export(tag).set("lockratio", "off");
    model.result().export(tag).set("resolution", "120");
    model.result().export(tag).set("antialias", "on");
    model.result().export(tag).set("zoomextents", "on");
  }

  private static void runScenario(String modelTag, String scenario, String socStart) throws Exception {
    Model model = ModelUtil.load(modelTag, BASE);
    applyCW391Params(model, scenario, socStart);
    addMetrics(model, scenario);
    addImageExport(model, scenario, "pg7", "separator_current_density");
    addImageExport(model, scenario, "pg8", "particle_surface_soc");
    addImageExport(model, scenario, "pg9", "relative_utilization");

    System.out.println("RUN_SCENARIO " + scenario);
    model.study("std1").run();
    model.result().numerical("gev_metrics_" + scenario).setResult();
    model.result().export("exp_metrics_" + scenario).run();
    try {
      model.result().export("img_" + scenario + "_separator_current_density").run();
      model.result().export("img_" + scenario + "_particle_surface_soc").run();
      model.result().export("img_" + scenario + "_relative_utilization").run();
    } catch (Exception ex) {
      System.out.println("WARN: image export failed for " + scenario + ": " + ex.getMessage());
    }
    model.save(WORKDIR + "/CW391_3D_P2D_" + scenario + ".mph");
    ModelUtil.remove(model.tag());
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(true);
    runScenario("highsoc", "soc90_100", "0.90");
    runScenario("reference", "soc45_55", "0.45");
  }
}
