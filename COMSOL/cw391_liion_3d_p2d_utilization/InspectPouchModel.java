import com.comsol.model.*;
import com.comsol.model.util.*;

public class InspectPouchModel {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printTags(String title, String[] tags) {
    System.out.println("## " + title);
    if (tags == null) {
      System.out.println("(null)");
      return;
    }
    for (String tag : tags) {
      System.out.println(tag);
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    model.modelPath(WORKDIR);

    printTags("components", model.component().tags());
    printTags("parameters", model.param().varnames());
    for (String comp : model.component().tags()) {
      System.out.println("## component " + comp);
      printTags("geom", model.component(comp).geom().tags());
      printTags("physics", model.component(comp).physics().tags());
      printTags("materials", model.component(comp).material().tags());
      printTags("mesh", model.component(comp).mesh().tags());
      for (String mesh : model.component(comp).mesh().tags()) {
        try {
          System.out.println("## mesh " + mesh + " features");
          printTags(mesh + " features", model.component(comp).mesh(mesh).feature().tags());
          for (String feat : model.component(comp).mesh(mesh).feature().tags()) {
            System.out.println("mesh_feature_label " + mesh + "/" + feat + " = "
                + model.component(comp).mesh(mesh).feature(feat).label());
            try {
              printTags("mesh properties " + mesh + "/" + feat,
                  model.component(comp).mesh(mesh).feature(feat).properties());
            } catch (Exception ex) {
              System.out.println("mesh properties " + mesh + "/" + feat + " = <unavailable>");
            }
          }
        } catch (Exception ex) {
          System.out.println("<mesh feature details unavailable>");
        }
      }
      printTags("selections", model.component(comp).selection().tags());
      for (String sel : model.component(comp).selection().tags()) {
        try {
          System.out.println("selection_label " + sel + " = "
              + model.component(comp).selection(sel).label());
        } catch (Exception ex) {
          System.out.println("selection_label " + sel + " = <unavailable>");
        }
      }
      printTags("couplings", model.component(comp).cpl().tags());
      printTags("variables", model.component(comp).variable().tags());
      printTags("probes", model.component(comp).probe().tags());
      for (String phys : model.component(comp).physics().tags()) {
        System.out.println("## physics " + phys + " features");
        printTags(phys + " features", model.component(comp).physics(phys).feature().tags());
        for (String feat : model.component(comp).physics(phys).feature().tags()) {
          try {
            System.out.println("feature_label " + phys + "/" + feat + " = "
                + model.component(comp).physics(phys).feature(feat).label());
            try {
              printTags("properties " + phys + "/" + feat,
                  model.component(comp).physics(phys).feature(feat).properties());
            } catch (Exception pex) {
              System.out.println("properties " + phys + "/" + feat + " = <unavailable>");
            }
          } catch (Exception ex) {
            System.out.println("feature_label " + phys + "/" + feat + " = <unavailable>");
          }
        }
      }
      for (String var : model.component(comp).variable().tags()) {
        System.out.println("## variable " + comp + "/" + var);
        try {
          printTags(var + " names", model.component(comp).variable(var).varnames());
          for (String name : model.component(comp).variable(var).varnames()) {
            System.out.println(name + " = " + model.component(comp).variable(var).get(name));
          }
        } catch (Exception ex) {
          System.out.println("<variable details unavailable>");
        }
      }
    }
    printTags("studies", model.study().tags());
    for (String std : model.study().tags()) {
      System.out.println("## study " + std + " features");
      printTags(std + " features", model.study(std).feature().tags());
    }
    printTags("solutions", model.sol().tags());
    printTags("datasets", model.result().dataset().tags());
    printTags("tables", model.result().table().tags());
    printTags("numerical", model.result().numerical().tags());
    printTags("exports", model.result().export().tags());
    printTags("plotgroups", model.result().tags());
    for (String pg : model.result().tags()) {
      System.out.println("## plotgroup " + pg + " label = " + model.result(pg).label());
      try {
        printTags(pg + " features", model.result(pg).feature().tags());
        for (String feat : model.result(pg).feature().tags()) {
          System.out.println("plot_feature " + pg + "/" + feat + " label = "
              + model.result(pg).feature(feat).label());
          try {
            String[] expr = model.result(pg).feature(feat).getStringArray("expr");
            for (String e : expr) {
              System.out.println("plot_expr " + pg + "/" + feat + " = " + e);
            }
          } catch (Exception ex) {
            // Some plot features do not expose an expr array.
          }
        }
      } catch (Exception ex) {
        System.out.println("<plot details unavailable>");
      }
    }
    for (String num : model.result().numerical().tags()) {
      System.out.println("## numerical " + num);
      try {
        String[] expr = model.result().numerical(num).getStringArray("expr");
        for (String e : expr) {
          System.out.println("expr " + e);
        }
      } catch (Exception ex) {
        System.out.println("<expr unavailable>");
      }
    }

    String[] checkParams = {
      "L_sep", "L_pos", "L_neg", "L_pos_cc", "L_neg_cc",
      "W_cell", "H_cell", "H_tab", "W_tab", "L_cell",
      "i0ref_pos", "i0ref_neg", "rp_pos", "rp_neg",
      "sigmas_neg", "sigmas_pos", "csmax_pos", "epss_pos",
      "csmax_neg", "epss_neg", "SOC_start", "SOC_window",
      "C_rate", "sim_time"
    };
    System.out.println("## selected parameter expressions");
    for (String p : checkParams) {
      try {
        System.out.println(p + " = " + model.param().get(p));
      } catch (Exception ex) {
        System.out.println(p + " = <missing>");
      }
    }

    ModelUtil.remove(model.tag());
  }
}
