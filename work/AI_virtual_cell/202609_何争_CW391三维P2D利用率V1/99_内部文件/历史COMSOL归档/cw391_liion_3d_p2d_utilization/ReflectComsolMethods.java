import com.comsol.model.*;
import com.comsol.model.util.*;
import java.lang.reflect.Method;
import java.util.TreeSet;

public class ReflectComsolMethods {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  private static void printMethods(String title, Object obj, String filter) {
    System.out.println("## " + title + " class=" + obj.getClass().getName());
    TreeSet<String> names = new TreeSet<String>();
    for (Method method : obj.getClass().getMethods()) {
      String name = method.toString();
      if (filter == null || name.toLowerCase().contains(filter.toLowerCase())) {
        names.add(name);
      }
    }
    for (String name : names) {
      System.out.println(name);
    }
  }

  public static void main(String[] args) throws Exception {
    ModelUtil.showProgress(false);
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    printMethods("geom1", model.component("comp1").geom("geom1"), "measure");
    printMethods("geom1-adj", model.component("comp1").geom("geom1"), "adj");
    printMethods("selection sel1", model.component("comp1").selection("geom1_sel1"), "entity");
    printMethods("selection sel1-adj", model.component("comp1").selection("geom1_sel1"), "adj");
    printMethods("mesh map1 selection", model.component("comp1").mesh("mesh1").feature("map1").selection(), "entity");
    ModelUtil.remove(model.tag());
  }
}
