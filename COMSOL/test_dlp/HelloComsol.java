import com.comsol.model.*;
import com.comsol.model.util.*;

public class HelloComsol {
    public static Model run() {
        Model model = ModelUtil.create("Model");
        model.label("HelloComsol");
        model.component().create("comp1", true);
        return model;
    }

    public static void main(String[] args) throws Exception {
        Model model = run();
        model.save("d:/Users/hez/Desktop/hithium/COMSOL/test_dlp/HelloComsol.mph");
        ModelUtil.remove("Model");
        System.out.println("SAVED_OK");
    }
}
