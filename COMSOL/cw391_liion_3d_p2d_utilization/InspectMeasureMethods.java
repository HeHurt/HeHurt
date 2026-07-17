import com.comsol.model.*;
import com.comsol.model.util.*;
import java.lang.reflect.Method;
import java.util.TreeSet;

public class InspectMeasureMethods {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printMethods(String title, Object obj) {
    System.out.println("## " + title + " class=" + obj.getClass().getName());
    TreeSet<String> names = new TreeSet<String>();
    for (Method method : obj.getClass().getMethods()) {
      names.add(method.toString());
    }
    for (String name : names) {
      if (name.contains("measure") || name.contains("selection") || name.contains("get")
          || name.contains("set") || name.contains("volume") || name.contains("area")
          || name.contains("geom") || name.contains("dim") || name.contains("all")) {
        System.out.println(name);
      }
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    printMethods("measure", model.component("comp1").geom("geom1").measure());
    printMethods("measureFinal", model.component("comp1").geom("geom1").measureFinal());
    printMethods("measureFinal.selection", model.component("comp1").geom("geom1").measureFinal().selection());
    ModelUtil.remove(model.tag());
  }
}
