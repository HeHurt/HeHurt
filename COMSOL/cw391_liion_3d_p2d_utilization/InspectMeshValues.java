import com.comsol.model.*;
import com.comsol.model.util.*;

public class InspectMeshValues {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printProperty(Model model, String feat, String prop) {
    try {
      String value = model.component("comp1").mesh("mesh1").feature(feat).getString(prop);
      System.out.println(feat + "." + prop + ".string = " + value);
    } catch (Exception ex) {
      // Continue with other accessors.
    }
    try {
      String[] values = model.component("comp1").mesh("mesh1").feature(feat).getStringArray(prop);
      System.out.print(feat + "." + prop + ".stringArray =");
      for (String value : values) {
        System.out.print(" [" + value + "]");
      }
      System.out.println();
    } catch (Exception ex) {
      // Continue with other accessors.
    }
    try {
      int[] values = model.component("comp1").mesh("mesh1").feature(feat).getIntArray(prop);
      System.out.print(feat + "." + prop + ".intArray =");
      for (int value : values) {
        System.out.print(" " + value);
      }
      System.out.println();
    } catch (Exception ex) {
      // Continue with other accessors.
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    String[] feats = model.component("comp1").mesh("mesh1").feature().tags();
    for (String feat : feats) {
      System.out.println("## " + feat + " label=" + model.component("comp1").mesh("mesh1").feature(feat).label());
      try {
        int[] entities = model.component("comp1").mesh("mesh1").feature(feat).selection().entities();
        System.out.print(feat + ".selection.entities =");
        for (int entity : entities) {
          System.out.print(" " + entity);
        }
        System.out.println();
      } catch (Exception ex) {
        System.out.println(feat + ".selection.entities = <unavailable> " + ex.getMessage());
      }
      String[] props = model.component("comp1").mesh("mesh1").feature(feat).properties();
      for (String prop : props) {
        printProperty(model, feat, prop);
      }
    }
    ModelUtil.remove(model.tag());
  }
}
