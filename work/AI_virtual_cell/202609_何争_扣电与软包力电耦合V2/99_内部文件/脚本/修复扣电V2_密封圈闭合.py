from com.comsol.model.util import ModelUtil


SOURCE = r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_参数化堆叠_待审核.mph"
OUTPUT = r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_参数化闭合堆叠_修正版.mph"


def main():
    for tag in ["closure_fix", "closure_verify"]:
        try:
            ModelUtil.remove(tag)
        except Exception:
            pass

    model = ModelUtil.load("closure_fix", SOURCE)
    model.param().set("W_g", "R_pc-R_nc_bot")
    geom = model.component("comp1").geom("geom1")
    geom.run()

    # Geometry rebuild can invalidate explicit selections. Reassert the verified
    # correct-polarity mapping before rebuilding the hybrid mesh.
    component = model.component("comp1")
    liion = component.physics("liion")
    liion.selection().set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    liion.feature("pce1").selection().set([6])
    liion.feature("pce2").selection().set([4])
    liion.feature("cc1").selection().set([1, 2, 3, 7, 8, 9, 10])
    liion.feature("egnd1").selection().set([20])
    liion.feature("ecd1").selection().set([2])

    solid = component.physics("solid")
    solid.selection().set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    solid.feature("fix_bottom").selection().set([20])
    solid.feature("load_top").selection().set([2])

    variable_domains = {
        "mech_steel": [1, 2, 8, 9, 10], "mech_pp": [11],
        "mech_cu": [7], "mech_neg": [6], "mech_sep": [5], "mech_pos": [4],
        "mech_al": [3], "var_v7_neg": [6], "var_v7_sep": [5], "var_v7_pos": [4],
        "var_v8_neg": [6], "var_v8_sep": [5], "var_v8_pos": [4],
    }
    for tag, domains in variable_domains.items():
        component.variable(tag).selection().set(domains)

    material_domains = {
        "mat1": [6], "mat2": [4], "mat3": [5], "mat4": [3], "mat5": [7],
        "mat6": [1, 2, 8, 9, 10], "mat7": [11],
    }
    for tag, domains in material_domains.items():
        component.material(tag).selection().set(domains)

    mesh = component.mesh("mesh1")
    mesh.feature("size1").selection().set([4, 6])
    mesh.feature("map1").selection().set([3, 4, 5, 6, 7])
    mesh.feature("ftri2").selection().set([1, 2, 8, 9, 10, 11])
    mesh.run()

    for solution_tag in model.sol().tags():
        model.sol(solution_tag).clearSolutionData()
    model.save(OUTPUT)
    ModelUtil.remove("closure_fix")

    check = ModelUtil.load("closure_verify", OUTPUT)
    c = check.component("comp1")
    g = c.geom("geom1")
    print("saved", OUTPUT)
    print("W_g", check.param().get("W_g"))
    print("radial_gap_expression", "R_pc-R_nc_bot-W_g")
    print("geometry_entities", list(g.getNEntities()))
    print("mesh_elements", c.mesh("mesh1").getNumElem())
    print("pce1", list(c.physics("liion").feature("pce1").selection().entities()))
    print("pce2", list(c.physics("liion").feature("pce2").selection().entities()))
    print("ground", list(c.physics("liion").feature("egnd1").selection().entities()))
    print("current", list(c.physics("liion").feature("ecd1").selection().entities()))
    print("gasket_material", list(c.material("mat7").selection().entities()))
    for solution_tag in check.sol().tags():
        print("solution", solution_tag, "empty", check.sol(solution_tag).isEmpty())
    ModelUtil.remove("closure_verify")


main()
