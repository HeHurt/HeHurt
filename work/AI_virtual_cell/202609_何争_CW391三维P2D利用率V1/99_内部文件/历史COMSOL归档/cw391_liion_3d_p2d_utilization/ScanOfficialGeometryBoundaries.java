import com.comsol.model.*;
import com.comsol.model.util.*;

public class ScanOfficialGeometryBoundaries {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    model.component("comp1").geom("geom1").run();
    int[] counts = model.component("comp1").geom("geom1").measureFinal().getNEntities();
    System.out.print("NEntities(dim0..3) =");
    for (int value : counts) {
      System.out.print(" " + value);
    }
    System.out.println();
    for (int b = 1; b <= counts[2]; b++) {
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
    }
    ModelUtil.remove(model.tag());
  }
}
