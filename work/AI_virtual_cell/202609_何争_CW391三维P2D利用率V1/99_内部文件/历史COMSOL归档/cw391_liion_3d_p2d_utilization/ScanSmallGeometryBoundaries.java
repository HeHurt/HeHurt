import com.comsol.model.*;
import com.comsol.model.util.*;

public class ScanSmallGeometryBoundaries {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void applySmallCW391Geometry(Model model) {
    model.param().set("W_cell", "10[mm]");
    model.param().set("H_cell", "20[mm]");
    model.param().set("W_tab", "5[mm]");
    model.param().set("H_tab", "1[mm]");
    model.param().set("L_neg_cc", "8[um]");
    model.param().set("L_pos_cc", "14[um]");
    model.param().set("L_neg", "85.85414192842925[um]");
    model.param().set("L_sep", "12.8[um]");
    model.param().set("L_pos", "100.73606892305158[um]");
    model.component("comp1").geom("geom1").feature("blk2").set("lz", "L_pos_cc/2");
    model.component("comp1").geom("geom1").feature("blk2").set("size",
        new String[]{"W_tab", "H_tab", "L_pos_cc/2"});
  }

  private static void printInts(String prefix, int[] values) {
    System.out.print(prefix);
    for (int value : values) {
      System.out.print(" " + value);
    }
    System.out.println();
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    applySmallCW391Geometry(model);
    model.component("comp1").geom("geom1").run();

    int[] counts = model.component("comp1").geom("geom1").measureFinal().getNEntities();
    printInts("NEntities(dim0..3) =", counts);

    for (int b = 1; b <= counts[2]; b++) {
      try {
        model.component("comp1").geom("geom1").measureFinal().selection().geom("geom1", 2);
        model.component("comp1").geom("geom1").measureFinal().selection().set(new int[]{b});
        double area = model.component("comp1").geom("geom1").measureFinal().getArea();
        double[] bb = model.component("comp1").geom("geom1").measureFinal().getBoundingBox();
        int[] adj = model.component("comp1").geom("geom1").getAdj(2, 3, b);
        System.out.print("boundary " + b + " area=" + area + " adjDomains=");
        for (int domain : adj) {
          System.out.print(" " + domain);
        }
        System.out.print(" bbox=");
        for (double value : bb) {
          System.out.print(" " + value);
        }
        System.out.println();
      } catch (Exception ex) {
        System.out.println("boundary " + b + " error=" + ex.getMessage());
      }
    }
    ModelUtil.remove(model.tag());
  }
}
