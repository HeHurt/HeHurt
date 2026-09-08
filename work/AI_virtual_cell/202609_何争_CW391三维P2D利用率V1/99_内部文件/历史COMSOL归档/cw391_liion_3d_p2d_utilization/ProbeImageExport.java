import com.comsol.model.*;
import com.comsol.model.util.*;

public class ProbeImageExport {
  private static final String WORKDIR =
      "D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization";

  public static void main(String[] args) throws Exception {
    Model model = ModelUtil.load("Model", WORKDIR + "/pouch_cell_utilization_base.mph");
    model.result().export().create("imgprobe", "Image");
    System.out.println("## image export properties");
    for (String prop : model.result().export("imgprobe").properties()) {
      System.out.println(prop);
    }
    ModelUtil.remove(model.tag());
  }
}
