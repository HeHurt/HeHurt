import com.comsol.model.*;
import com.comsol.model.util.*;

public class InspectSelections {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printEntities(Model model, String sel) {
    try {
      int[] domains = model.component("comp1").selection(sel).entities(3);
      System.out.print(sel + ".domains =");
      for (int domain : domains) {
        System.out.print(" " + domain);
      }
      System.out.println();
    } catch (Exception ex) {
      System.out.println(sel + ".domains = <unavailable> " + ex.getMessage());
    }
    try {
      int[] boundaries = model.component("comp1").selection(sel).entities(2);
      System.out.print(sel + ".boundaries =");
      for (int boundary : boundaries) {
        System.out.print(" " + boundary);
      }
      System.out.println();
    } catch (Exception ex) {
      System.out.println(sel + ".boundaries = <unavailable> " + ex.getMessage());
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    model.modelPath(WORKDIR);
    model.component("comp1").geom("geom1").run();
    for (String sel : model.component("comp1").selection().tags()) {
      System.out.println("## " + sel + " label=" + model.component("comp1").selection(sel).label());
      printEntities(model, sel);
    }
    ModelUtil.remove(model.tag());
  }
}
