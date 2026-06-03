/*
 * PatentCurrentBalanceModel.java
 *
 * Mechanism verification model for:
 * "A cell design structure for improving inner/outer winding current difference".
 *
 * COMSOL 6.4 Java model. The model uses two parallel current branches
 * (inner winding and outer winding) and compares a baseline equal-tab design
 * with the patent differential-tab design.
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

public class PatentCurrentBalanceModel {

  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/patent_current_balance";

  public static Model run() {
    Model model = ModelUtil.create("Model");
    model.modelPath(WORKDIR);
    model.label("PatentCurrentBalanceModel.mph");
    model.comments(
        "Mechanism verification for inner/outer winding current equalization. "
        + "Baseline uses identical tabs. Patent design uses higher-resistance "
        + "inner tabs and lower-resistance outer tabs to compensate winding-path resistance.");

    model.param().set("I_app", "314[A]", "Applied discharge current for a 314 Ah-class cell");
    model.param().set("Tamb", "298.15[K]", "Ambient temperature");
    model.param().set("t_end", "1800[s]", "Simulation duration");
    model.param().set("Cth", "4200[J/K]", "Thermal capacitance of each representative winding zone");
    model.param().set("hA", "0.55[W/K]", "Lumped heat transfer coefficient to ambient");

    model.param().set("R_wind_inner", "0.050[mohm]", "Intrinsic inner winding/electrode-tab path resistance");
    model.param().set("R_wind_outer", "0.110[mohm]", "Intrinsic outer winding/electrode-tab path resistance");
    model.param().set("R_tab_common", "0.030[mohm]", "Baseline identical tab resistance");
    model.param().set("R_tab_inner_pat", "0.090[mohm]", "Patent high-resistance inner tab by narrowing/thinning");
    model.param().set("R_tab_outer_pat", "0.030[mohm]", "Patent low-resistance outer tab by widening/thickening");

    model.component().create("comp1", true);
    model.component("comp1").geom().create("geom1", 1);
    model.component("comp1").geom("geom1").create("i1", "Interval");
    model.component("comp1").geom("geom1").feature("i1").set("coordsource", "vector");
    model.component("comp1").geom("geom1").feature("i1").set("coordvec", "0, 1");
    model.component("comp1").geom("geom1").run();

    model.component("comp1").variable().create("var1");
    model.component("comp1").variable("var1").label("Branch resistance and current definitions");
    model.component("comp1").variable("var1").set("R_inner_base", "R_wind_inner+R_tab_common");
    model.component("comp1").variable("var1").set("R_outer_base", "R_wind_outer+R_tab_common");
    model.component("comp1").variable("var1").set("R_inner_pat", "R_wind_inner+R_tab_inner_pat");
    model.component("comp1").variable("var1").set("R_outer_pat", "R_wind_outer+R_tab_outer_pat");

    model.component("comp1").variable("var1").set(
        "I_inner_base", "I_app*(1/R_inner_base)/(1/R_inner_base+1/R_outer_base)");
    model.component("comp1").variable("var1").set(
        "I_outer_base", "I_app*(1/R_outer_base)/(1/R_inner_base+1/R_outer_base)");
    model.component("comp1").variable("var1").set(
        "I_inner_pat", "I_app*(1/R_inner_pat)/(1/R_inner_pat+1/R_outer_pat)");
    model.component("comp1").variable("var1").set(
        "I_outer_pat", "I_app*(1/R_outer_pat)/(1/R_inner_pat+1/R_outer_pat)");

    model.component("comp1").variable("var1").set("Q_inner_base", "I_inner_base^2*R_wind_inner");
    model.component("comp1").variable("var1").set("Q_outer_base", "I_outer_base^2*R_wind_outer");
    model.component("comp1").variable("var1").set("Q_inner_pat", "I_inner_pat^2*R_wind_inner");
    model.component("comp1").variable("var1").set("Q_outer_pat", "I_outer_pat^2*R_wind_outer");
    model.component("comp1").variable("var1").set("Q_tab_inner_base", "I_inner_base^2*R_tab_common");
    model.component("comp1").variable("var1").set("Q_tab_outer_base", "I_outer_base^2*R_tab_common");
    model.component("comp1").variable("var1").set("Q_tab_inner_pat", "I_inner_pat^2*R_tab_inner_pat");
    model.component("comp1").variable("var1").set("Q_tab_outer_pat", "I_outer_pat^2*R_tab_outer_pat");

    model.component("comp1").variable("var1").set(
        "imbalance_base", "abs(I_inner_base-I_outer_base)/((I_inner_base+I_outer_base)/2)");
    model.component("comp1").variable("var1").set(
        "imbalance_pat", "abs(I_inner_pat-I_outer_pat)/((I_inner_pat+I_outer_pat)/2)");
    model.component("comp1").variable("var1").set(
        "inner_heat_reduction", "(Q_inner_base-Q_inner_pat)/Q_inner_base");
    model.component("comp1").variable("var1").set(
        "outer_utilization_gain", "(I_outer_pat-I_outer_base)/I_outer_base");
    model.component("comp1").variable("var1").set("T_inner_base_C", "TinnerBase-273.15[K]");
    model.component("comp1").variable("var1").set("T_outer_base_C", "TouterBase-273.15[K]");
    model.component("comp1").variable("var1").set("T_inner_pat_C", "TinnerPat-273.15[K]");
    model.component("comp1").variable("var1").set("T_outer_pat_C", "TouterPat-273.15[K]");

    model.component("comp1").physics().create("ge", "GlobalEquations", "geom1");
    model.component("comp1").physics("ge").feature("ge1").set("DependentVariableQuantity", "none");
    model.component("comp1").physics("ge").feature("ge1").set("SourceTermQuantity", "none");

    model.component("comp1").physics("ge").feature("ge1")
        .setIndex("name", "TinnerBase", 0, 0)
        .setIndex("equation", "TinnerBaset-((Q_inner_base-hA*(TinnerBase-Tamb))/Cth)", 0, 0)
        .setIndex("initialValueU", "Tamb", 0, 0)
        .setIndex("initialValueUt", "0[K/s]", 0, 0)
        .setIndex("description", "Baseline inner winding temperature", 0, 0);
    model.component("comp1").physics("ge").feature("ge1")
        .setIndex("name", "TouterBase", 1, 0)
        .setIndex("equation", "TouterBaset-((Q_outer_base-hA*(TouterBase-Tamb))/Cth)", 1, 0)
        .setIndex("initialValueU", "Tamb", 1, 0)
        .setIndex("initialValueUt", "0[K/s]", 1, 0)
        .setIndex("description", "Baseline outer winding temperature", 1, 0);
    model.component("comp1").physics("ge").feature("ge1")
        .setIndex("name", "TinnerPat", 2, 0)
        .setIndex("equation", "TinnerPatt-((Q_inner_pat-hA*(TinnerPat-Tamb))/Cth)", 2, 0)
        .setIndex("initialValueU", "Tamb", 2, 0)
        .setIndex("initialValueUt", "0[K/s]", 2, 0)
        .setIndex("description", "Patent inner winding temperature", 2, 0);
    model.component("comp1").physics("ge").feature("ge1")
        .setIndex("name", "TouterPat", 3, 0)
        .setIndex("equation", "TouterPatt-((Q_outer_pat-hA*(TouterPat-Tamb))/Cth)", 3, 0)
        .setIndex("initialValueU", "Tamb", 3, 0)
        .setIndex("initialValueUt", "0[K/s]", 3, 0)
        .setIndex("description", "Patent outer winding temperature", 3, 0);

    model.study().create("std1");
    model.study("std1").create("time", "Transient");
    model.study("std1").feature("time").set("tlist", "range(0,60,t_end)");
    model.study("std1").feature("time").set("rtol", "1e-6");

    model.sol().create("sol1");
    model.sol("sol1").study("std1");
    model.sol("sol1").attach("std1");
    model.sol("sol1").create("st1", "StudyStep");
    model.sol("sol1").feature("st1").set("study", "std1");
    model.sol("sol1").feature("st1").set("studystep", "time");
    model.sol("sol1").create("v1", "Variables");
    model.sol("sol1").create("t1", "Time");
    model.sol("sol1").feature("t1").set("tlist", "range(0,60,t_end)");
    model.sol("sol1").feature("t1").set("plot", "off");
    model.sol("sol1").feature("t1").set("plotgroup", "Default");
    model.sol("sol1").feature("t1").set("rtol", "1e-6");
    model.sol("sol1").feature("t1").set("maxorder", 2);
    model.sol("sol1").feature("t1").create("fc1", "FullyCoupled");
    model.sol("sol1").feature("t1").feature("fc1").set("linsolver", "dDef");

    model.result().table().create("tbl_metrics", "Table");
    model.result().table("tbl_metrics").comments("Final scalar metrics for baseline and patent designs");
    model.result().numerical().create("gev_metrics", "EvalGlobal");
    model.result().numerical("gev_metrics").set("data", "dset1");
    model.result().numerical("gev_metrics").set("table", "tbl_metrics");
    model.result().numerical("gev_metrics").set("expr", new String[]{
        "I_inner_base", "I_outer_base", "imbalance_base",
        "I_inner_pat", "I_outer_pat", "imbalance_pat",
        "Q_inner_base", "Q_outer_base", "Q_inner_pat", "Q_outer_pat",
        "Q_tab_inner_base", "Q_tab_outer_base", "Q_tab_inner_pat", "Q_tab_outer_pat",
        "inner_heat_reduction", "outer_utilization_gain",
        "T_inner_base_C", "T_outer_base_C", "T_inner_pat_C", "T_outer_pat_C"
    });
    model.result().numerical("gev_metrics").set("descr", new String[]{
        "Baseline inner current", "Baseline outer current", "Baseline current imbalance",
        "Patent inner current", "Patent outer current", "Patent current imbalance",
        "Baseline inner JR heat", "Baseline outer JR heat",
        "Patent inner JR heat", "Patent outer JR heat",
        "Baseline inner tab heat", "Baseline outer tab heat",
        "Patent inner tab heat", "Patent outer tab heat",
        "Inner heat reduction", "Outer current utilization gain",
        "Baseline inner temperature", "Baseline outer temperature",
        "Patent inner temperature", "Patent outer temperature"
    });

    model.result().table().create("tbl_timeseries", "Table");
    model.result().numerical().create("gev_timeseries", "EvalGlobal");
    model.result().numerical("gev_timeseries").set("data", "dset1");
    model.result().numerical("gev_timeseries").set("table", "tbl_timeseries");
    model.result().numerical("gev_timeseries").set("expr", new String[]{
        "I_inner_base", "I_outer_base", "I_inner_pat", "I_outer_pat",
        "T_inner_base_C", "T_outer_base_C", "T_inner_pat_C", "T_outer_pat_C"
    });
    model.result().numerical("gev_timeseries").set("descr", new String[]{
        "Baseline inner current", "Baseline outer current",
        "Patent inner current", "Patent outer current",
        "Baseline inner temperature", "Baseline outer temperature",
        "Patent inner temperature", "Patent outer temperature"
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
    model.study("std1").run();
    model.result().numerical("gev_metrics").set("looplevelinput", new String[]{"last"});
    model.result().numerical("gev_metrics").setResult();
    model.result().numerical("gev_timeseries").setResult();
    model.result().export("exp_metrics").run();
    model.result().export("exp_timeseries").run();
    model.save(WORKDIR + "/PatentCurrentBalanceModel.mph");
  }
}
