import com.comsol.model.*;
import com.comsol.model.util.*;

public class InspectMaterials {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printProp(Model model, String mat, String pg, String prop) {
    try {
      String value = model.component("comp1").material(mat).propertyGroup(pg).getString(prop);
      System.out.println(mat + "." + pg + "." + prop + " = " + value);
    } catch (Exception ex) {
      // Continue.
    }
    try {
      String[] values = model.component("comp1").material(mat).propertyGroup(pg).getStringArray(prop);
      System.out.print(mat + "." + pg + "." + prop + "[] =");
      for (String value : values) {
        System.out.print(" [" + value + "]");
      }
      System.out.println();
    } catch (Exception ex) {
      // Continue.
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    for (String mat : model.component("comp1").material().tags()) {
      System.out.println("## " + mat + " label=" + model.component("comp1").material(mat).label());
      try {
        int[] domains = model.component("comp1").material(mat).selection().entities(3);
        System.out.print(mat + ".domains =");
        for (int domain : domains) {
          System.out.print(" " + domain);
        }
        System.out.println();
      } catch (Exception ex) {
        System.out.println(mat + ".domains = <unavailable> " + ex.getMessage());
      }
      for (String pg : model.component("comp1").material(mat).propertyGroup().tags()) {
        System.out.println("propertyGroup " + pg);
        try {
          for (String prop : model.component("comp1").material(mat).propertyGroup(pg).properties()) {
            printProp(model, mat, pg, prop);
          }
        } catch (Exception ex) {
          System.out.println(pg + ".properties = <unavailable>");
        }
      }
    }
    ModelUtil.remove(model.tag());
  }
}
