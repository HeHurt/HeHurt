import com.comsol.model.*;
import com.comsol.model.util.*;

public class InspectGeometryValues {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printValue(Model model, String feat, String prop) {
    try {
      String value = model.component("comp1").geom("geom1").feature(feat).getString(prop);
      System.out.println(feat + "." + prop + ".string = " + value);
    } catch (Exception ex) {
      // Continue.
    }
    try {
      String[] values = model.component("comp1").geom("geom1").feature(feat).getStringArray(prop);
      System.out.print(feat + "." + prop + ".stringArray =");
      for (String value : values) {
        System.out.print(" [" + value + "]");
      }
      System.out.println();
    } catch (Exception ex) {
      // Continue.
    }
    try {
      int[] values = model.component("comp1").geom("geom1").feature(feat).getIntArray(prop);
      System.out.print(feat + "." + prop + ".intArray =");
      for (int value : values) {
        System.out.print(" " + value);
      }
      System.out.println();
    } catch (Exception ex) {
      // Continue.
    }
  }

  private static void printFeature(Model model, String feat, String indent) {
    System.out.println(indent + "## " + feat + " label="
        + model.component("comp1").geom("geom1").feature(feat).label()
        + " type=" + model.component("comp1").geom("geom1").feature(feat).getType());
    try {
      for (String prop : model.component("comp1").geom("geom1").feature(feat).properties()) {
        printValue(model, feat, prop);
      }
    } catch (Exception ex) {
      System.out.println(indent + feat + ".properties = <unavailable>");
    }
    try {
      for (String sub : model.component("comp1").geom("geom1").feature(feat).feature().tags()) {
        System.out.println(indent + "  subfeature=" + sub + " label="
            + model.component("comp1").geom("geom1").feature(feat).feature(sub).label()
            + " type=" + model.component("comp1").geom("geom1").feature(feat).feature(sub).getType());
        try {
          for (String prop : model.component("comp1").geom("geom1").feature(feat).feature(sub).properties()) {
            try {
              String value = model.component("comp1").geom("geom1").feature(feat).feature(sub).getString(prop);
              System.out.println(feat + "/" + sub + "." + prop + ".string = " + value);
            } catch (Exception ex) {
              // Continue.
            }
            try {
              String[] values = model.component("comp1").geom("geom1").feature(feat).feature(sub).getStringArray(prop);
              System.out.print(feat + "/" + sub + "." + prop + ".stringArray =");
              for (String value : values) {
                System.out.print(" [" + value + "]");
              }
              System.out.println();
            } catch (Exception ex) {
              // Continue.
            }
          }
        } catch (Exception ex) {
          System.out.println(indent + "  " + sub + ".properties = <unavailable>");
        }
      }
    } catch (Exception ex) {
      // No subfeatures.
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    for (String feat : model.component("comp1").geom("geom1").feature().tags()) {
      printFeature(model, feat, "");
    }
    ModelUtil.remove(model.tag());
  }
}
