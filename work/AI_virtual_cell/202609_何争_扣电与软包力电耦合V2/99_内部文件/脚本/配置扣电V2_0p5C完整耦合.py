from com.comsol.model.util import ModelUtil


SOURCE = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_参数化闭合堆叠_修正版.mph"
OUTPUT = r"C:\HithiumSSD\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_0p5C_100N完整耦合_计算版.mph"


def set_selection(feature, entities):
    feature.selection().set(entities)


def main():
    for tag in ["coin_setup", "coin_verify"]:
        try:
            ModelUtil.remove(tag)
        except Exception:
            pass

    model = ModelUtil.load("coin_setup", SOURCE)
    c = model.component("comp1")

    # Full coupled 0.5C condition.
    model.param().set("SOC", "0.01")
    model.param().set("F_ext", "100[N]")
    model.param().set("coupling_on", "1")
    model.param().set("local_porosity_on", "1")
    model.param().set("breathing_on", "1")
    model.param().set("breathing_mode", "2")
    model.param().set("cycle_rest", "600[s]")
    model.param().set("V_charge_cut", "3.65[V]")
    model.param().set("V_discharge_cut", "2.5[V]")
    c.variable("var1").set("C", "0.5")

    # Build the user-approved geometry without changing its dimensions.
    geom = c.geom("geom1")
    geom.run()

    # Correct-polarity electrochemical domains and terminals.
    liion = c.physics("liion")
    liion.selection().set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    set_selection(liion.feature("pce1"), [6])
    set_selection(liion.feature("pce2"), [4])
    set_selection(liion.feature("cc1"), [1, 2, 3, 7, 8, 9, 10])
    set_selection(liion.feature("egnd1"), [20])
    set_selection(liion.feature("ecd1"), [2])
    liion.feature("ecd1").set("Its", "I")
    liion.feature("socicd1").set("SOC_init", "SOC")

    # Geometry rebuilding clears the terminal probes used by vol_loaded and the
    # cycle controller. Both probes are evaluated on the positive terminal.
    set_selection(c.probe("bnd1"), [2])
    set_selection(c.probe("bnd2"), [2])

    # Restore the initial-potential partition lost during geometry rebuilding.
    set_selection(liion.feature("init2"), [7])
    set_selection(liion.feature("init3"), [3])
    set_selection(liion.feature("init4"), [4])

    # Solid mechanics and nonlinear breathing domains.
    solid = c.physics("solid")
    solid.selection().set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    set_selection(solid.feature("fix_bottom"), [20])
    set_selection(solid.feature("load_top"), [2])
    set_selection(solid.feature("lemm1").feature("breath_neg_v8"), [6])
    set_selection(solid.feature("lemm1").feature("breath_pos_v8"), [4])

    variable_domains = {
        "mech_steel": [1, 2, 8, 9, 10], "mech_pp": [11],
        "mech_cu": [7], "mech_neg": [6], "mech_sep": [5],
        "mech_pos": [4], "mech_al": [3],
        "var_v7_neg": [6], "var_v7_sep": [5], "var_v7_pos": [4],
        "var_v8_neg": [6], "var_v8_sep": [5], "var_v8_pos": [4],
    }
    for tag, domains in variable_domains.items():
        c.variable(tag).selection().set(domains)

    material_domains = {
        "mat1": [6], "mat2": [4], "mat3": [5], "mat4": [3], "mat5": [7],
        "mat6": [1, 2, 8, 9, 10], "mat7": [11],
    }
    for tag, domains in material_domains.items():
        c.material(tag).selection().set(domains)

    # Restore the compact hybrid mesh.
    mesh = c.mesh("mesh1")
    mesh.feature("size1").selection().set([4, 6])
    mesh.feature("map1").selection().set([3, 4, 5, 6, 7])
    mesh.feature("ftri2").selection().set([1, 2, 8, 9, 10, 11])
    mesh.run()

    # Full charge-rest-discharge time horizon; use a smaller first BDF step for
    # the tightly coupled electrochemical-mechanical initialization.
    model.study("std_v9").feature("time").set("tlist", "range(0,60,18000)")
    model.sol("sol3").feature("t1").set("tlist", "range(0,60,18000)")
    model.sol("sol3").feature("t1").set("initialstepbdf", "0.1[s]")
    model.sol("sol3").feature("t1").set("initialstepbdfactive", "on")
    model.sol("sol3").feature("t1").set("maxorder", "2")

    for soltag in model.sol().tags():
        model.sol(soltag).clearSolutionData()
    model.save(OUTPUT)
    ModelUtil.remove("coin_setup")

    check = ModelUtil.load("coin_verify", OUTPUT)
    cc = check.component("comp1")
    print("saved", OUTPUT)
    print("geometry", list(cc.geom("geom1").getNEntities()))
    print("mesh", cc.mesh("mesh1").getNumElem(), cc.mesh("mesh1").getMinQuality())
    print("i_1C_A", check.param().evaluate("i_1C"))
    print("i_0p5C_A", check.param().evaluate("0.5*i_1C"))
    for name in ["SOC", "F_ext", "coupling_on", "local_porosity_on", "breathing_on", "breathing_mode"]:
        print("param", name, check.param().get(name))
    for ftag in ["init1", "init2", "init3", "init4", "pce1", "pce2", "egnd1", "ecd1"]:
        print("liion_selection", ftag, list(cc.physics("liion").feature(ftag).selection().entities()))
    print("breath_neg", list(cc.physics("solid").feature("lemm1").feature("breath_neg_v8").selection().entities()))
    print("breath_pos", list(cc.physics("solid").feature("lemm1").feature("breath_pos_v8").selection().entities()))
    print("mech_pp", list(cc.variable("mech_pp").selection().entities()))
    for soltag in check.sol().tags():
        print("solution", soltag, "empty", check.sol(soltag).isEmpty())
    ModelUtil.remove("coin_verify")


main()
