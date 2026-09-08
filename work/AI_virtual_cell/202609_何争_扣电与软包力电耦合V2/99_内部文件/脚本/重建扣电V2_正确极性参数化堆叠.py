from com.comsol.model.util import ModelUtil


MODEL_PATH = r"D:\Users\hez\Desktop\hithium\work\AI_virtual_cell\202609_何争_扣电与软包力电耦合V2\02_模型\扣电_V2_正确极性_参数化堆叠_待审核.mph"


def set_selection(feature, entities):
    feature.selection().set(entities)


def add_rectangle(geom, tag, size, pos):
    feature = geom.feature().create(tag, "Rectangle")
    feature.set("size", size)
    feature.set("pos", pos)
    feature.set("base", "corner")
    return feature


def add_table_polygon(geom, tag, table):
    feature = geom.feature().create(tag, "Polygon")
    feature.set("source", "table")
    feature.set("table", table)
    feature.set("type", "solid")
    return feature


def main():
    for tag in ["oldv9", "v2build"]:
        try:
            ModelUtil.remove(tag)
        except Exception:
            pass

    model = ModelUtil.load("v2build", MODEL_PATH)
    component = model.component("comp1")

    # Geometry design parameters from the correct CR2430 reference model.
    # t_ca and t_an are the intended user-facing positive/negative electrode design variables.
    params = {
        "R_nc_bot": "10.3[mm]",
        "R_nc_wall_in": "10.05[mm]",
        "t_nc_bot": "0.25[mm]",
        "H_nc_wall": "1.9[mm]",
        # Radially close the insulating gasket against the inner wall of the
        # positive shell. A fixed 1.575 mm leaves a 0.345 mm open annular gap.
        "W_g": "R_pc-R_nc_bot",
        "H_g": "1.9[mm]",
        "R_sp": "10[mm]",
        "t_bsp": "0.4[mm]",
        "z_bsp": "1.95[mm]",
        "R_el": "10.25[mm]",
        "t_al": "0.01[mm]",
        "t_ca": "0.13675[mm]",
        "t_sep": "0.009[mm]",
        "t_an": "0.11155[mm]",
        "t_cu": "0.01[mm]",
        "z_stack": "2.35[mm]",
        "t_tsp": "0.4[mm]",
        "H_nc_wall_full": "2.6[mm]",
        "H_nc_wall_in": "2.3[mm]",
        "R_pc": "12.22[mm]",
        "H_pc": "2.8[mm]",
        "loadfac": "1.09",
        "z_al": "z_stack",
        "z_ca": "z_al+t_al",
        "z_sep": "z_ca+t_ca",
        "z_an": "z_sep+t_sep",
        "z_cu": "z_an+t_an",
        "z_stack_top": "z_cu+t_cu",
        "z_nc": "z_stack_top+t_nc_bot+t_tsp",
        "delta_max": "z_nc-H_nc_wall_full-t_nc_bot",
        "uz": "loadfac*delta_max",
    }
    for name, expression in params.items():
        model.param().set(name, expression)

    # Rebind selections before replacing the imported geometry. The new native geometry
    # follows the reference model's entity numbering, so these explicit IDs remain valid
    # when it is built below.
    liion = component.physics("liion")
    liion.selection().set([4, 5, 6])
    set_selection(liion.feature("pce1"), [6])  # graphite negative electrode
    set_selection(liion.feature("pce2"), [4])  # LFP positive electrode
    # Separator is the Li-ion Battery interface's non-editable complement of pce1/pce2.
    # With the root selection limited to [4, 5, 6], it resolves to domain 5.
    set_selection(liion.feature("cc1"), [1, 2, 3, 7, 8, 9, 10])
    set_selection(liion.feature("egnd1"), [20])  # upper negative terminal
    set_selection(liion.feature("ecd1"), [2])    # lower positive terminal

    solid = component.physics("solid")
    set_selection(solid.feature("fix_bottom"), [20])
    set_selection(solid.feature("load_top"), [2])

    variable_domains = {
        "mech_steel": [1, 2, 8, 9, 10], "mech_pp": [11],
        "mech_cu": [7], "mech_neg": [6], "mech_sep": [5], "mech_pos": [4],
        "mech_al": [3], "var_v7_neg": [6], "var_v7_sep": [5], "var_v7_pos": [4],
        "var_v8_neg": [6], "var_v8_sep": [5], "var_v8_pos": [4],
    }
    for tag, domains in variable_domains.items():
        component.variable(tag).selection().set(domains)

    # Avoid compiling a disabled Solid Mechanics field into the 0 N / uncoupled
    # electrochemical baseline. The original multiplicative form still evaluates
    # solid.sz/withsol() when coupling_on=0; conditional branches preserve the
    # coupled expressions while making the baseline executable from a clean model.
    for phase in ["neg", "sep", "pos"]:
        base = "epsl_" + phase
        beta = "beta_" + phase
        group = component.variable("var_v8_" + phase)
        group.set(
            "p_comp_" + phase + "_v8",
            "if(coupling_on<0.5,0[Pa],min(p_local_cap,max(0[Pa],-solid.sz)))",
        )
        group.set(
            "epsl_" + phase + "_v8",
            "if(coupling_on<0.5," + base + ",max(epsl_floor," + base
            + "*(1-" + beta + "*p_comp_" + phase + "_v8)))",
        )
    for phase in ["neg", "sep", "pos"]:
        base = "epsl_" + phase
        beta = "beta_" + phase
        group = component.variable("var_v7_" + phase)
        group.set(
            "p_comp_" + phase + "_v7",
            "if(coupling_on<0.5,0[Pa],min(p_local_cap,max(0[Pa],withsol('sol2',-solid.sz,setval(F_ext,F_ext)))))",
        )
        group.set(
            "epsl_" + phase + "_v7",
            "if(coupling_on<0.5," + base + ",epsl_" + phase + "_mech+local_porosity_on*"
            + "(max(epsl_floor," + base + "*(1-" + beta + "*p_comp_" + phase + "_v7))-epsl_"
            + phase + "_mech))",
        )

    material_domains = {
        "mat1": [6], "mat2": [4], "mat3": [5], "mat4": [3], "mat5": [7],
        "mat6": [1, 2, 8, 9, 10], "mat7": [11],
    }
    for tag, domains in material_domains.items():
        component.material(tag).selection().set(domains)
    component.material("mat6").label("Structural steel")
    component.material("mat6").propertyGroup("def").set("thermalconductivity", "44.5[W/(m*K)]")
    component.material("mat6").propertyGroup("def").set("electricconductivity", "4.032e6[S/m]")
    component.material("mat6").propertyGroup("def").set("density", "7850[kg/m^3]")
    component.material("mat7").label("Polycarbonate [solid]")
    component.material("mat7").propertyGroup("def").set("density", "1200[kg/m^3]")
    component.material("mat2").propertyGroup("def").set("youngsmodulus", "1.178[GPa]")
    model.param().set("E_pp", "2.4[GPa]")
    model.param().set("nu_pp", "0.37")
    model.param().set("rho_pp", "1200[kg/m^3]")

    # Replace the stale static GDS import by the native, parameter-linked 2D axisymmetric geometry.
    geom = component.geom("geom1")
    geom.feature().clear()

    add_table_polygon(
        geom,
        "pol1",
        [
            ["0", "z_nc"],
            ["R_nc_bot+2*t_nc_bot", "z_nc"],
            ["R_nc_bot+2*t_nc_bot", "z_nc-H_nc_wall_in"],
            ["R_nc_bot+t_nc_bot", "z_nc-H_nc_wall_in"],
            ["R_nc_bot+t_nc_bot", "z_nc-t_nc_bot"],
            ["0", "z_nc-t_nc_bot"],
            ["0", "z_nc"],
        ],
    )
    add_rectangle(geom, "r1", ["W_g", "H_g"], ["R_nc_bot", "z_nc-H_nc_wall_full"])
    add_rectangle(geom, "r2", ["t_nc_bot", "0.45[mm]"], ["10.3[mm]", "z_nc-H_nc_wall_full+H_g"])
    union = geom.feature().create("uni1", "Union")
    union.selection("input").set(["r1", "r2"])
    difference = geom.feature().create("dif1", "Difference")
    difference.selection("input").set(["uni1"])
    difference.selection("input2").set(["pol1"])
    difference.set("keepadd", "off")
    difference.set("keepsubtract", "on")

    spring = geom.feature().create("spring", "Polygon")
    spring.set("source", "vectors")
    spring.set(
        "x",
        ["3.96573246620696[mm]", "4.16573246620696[mm]", "10.034267533793[mm]", "10.034267533793[mm]", "9.83426753379304[mm]", "3.96573246620696[mm]"],
    )
    spring.set(
        "y",
        ["t_nc_bot", "t_nc_bot", "1.75[mm]", "1.95[mm]", "1.95[mm]", "0.45[mm]"],
    )
    spring.set("type", "solid")

    add_table_polygon(
        geom,
        "pol2",
        [
            ["0", "0"],
            ["R_pc+t_nc_bot", "0"],
            ["R_pc+t_nc_bot", "H_pc"],
            ["R_pc", "H_pc"],
            ["R_pc", "t_nc_bot"],
            ["0", "t_nc_bot"],
            ["0", "0"],
        ],
    )
    add_rectangle(geom, "bspacer", ["R_sp", "t_bsp"], ["0", "z_bsp"])
    add_rectangle(geom, "al", ["R_el", "t_al"], ["0", "z_al"])
    add_rectangle(geom, "cathode", ["R_el", "t_ca"], ["0", "z_ca"])
    add_rectangle(geom, "sep", ["R_el", "t_sep"], ["0", "z_sep"])
    add_rectangle(geom, "anode", ["R_el", "t_an"], ["0", "z_an"])
    add_rectangle(geom, "cu", ["R_el", "t_cu"], ["0", "z_cu"])
    add_rectangle(geom, "tspacer", ["R_sp", "t_tsp"], ["0", "z_stack_top"])
    delete = geom.feature().create("del1", "Delete")
    delete.selection("input").set("dif1", [1])
    # COMSOL owns the terminal Finalize feature. Resolve the new native geometry only
    # after all dependent selections have been rebound to the intended entity numbers.
    geom.run()

    # Geometry replacement resets explicit entity selections. Reapply them only now.
    # The Li-ion Battery root excludes the nonconductive PC spacer, leaving domain 5
    # as the sole automatic Separator domain after the porous electrodes and conductors
    # are assigned.
    liion.selection().set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    set_selection(liion.feature("pce1"), [6])
    set_selection(liion.feature("pce2"), [4])
    set_selection(liion.feature("cc1"), [1, 2, 3, 7, 8, 9, 10])
    set_selection(liion.feature("egnd1"), [20])
    set_selection(liion.feature("ecd1"), [2])
    solid.selection().set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    set_selection(solid.feature("fix_bottom"), [20])
    set_selection(solid.feature("load_top"), [2])
    for tag, domains in variable_domains.items():
        component.variable(tag).selection().set(domains)
    for tag, domains in material_domains.items():
        component.material(tag).selection().set(domains)

    # Old solutions are tied to the reversed, imported geometry and must not be reused.
    for solution_tag in model.sol().tags():
        model.sol(solution_tag).clearSolutionData()

    # Restore the V1 hybrid mesh intent after geometry replacement: mapped through-thickness
    # elements for the five-layer stack, with free triangles only in the hardware domains.
    mesh = component.mesh("mesh1")
    mesh.feature("size1").selection().set([4, 6])
    mesh.feature("map1").selection().set([3, 4, 5, 6, 7])
    mesh.feature("ftri2").selection().set([1, 2, 8, 9, 10, 11])
    mesh.run()
    model.save(MODEL_PATH)

    print("saved", MODEL_PATH)
    print("geometry_objects", list(geom.objectNames()))
    print("geometry_entities", list(geom.getNEntities()))
    print("pce1_graphite", list(liion.feature("pce1").selection().entities()))
    print("pce2_lfp", list(liion.feature("pce2").selection().entities()))
    print("sep", list(liion.feature("sep1").selection().entities()))
    print("cc", list(liion.feature("cc1").selection().entities()))
    print("ground_top_negative", list(liion.feature("egnd1").selection().entities()))
    print("current_bottom_positive", list(liion.feature("ecd1").selection().entities()))
    print("fixed_top", list(solid.feature("fix_bottom").selection().entities()))
    print("loaded_bottom", list(solid.feature("load_top").selection().entities()))
    print("mesh_elements", mesh.getNumElem())
    print("mesh_min_quality", mesh.getMinQuality())


main()
