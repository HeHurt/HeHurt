from params import get_cell_params_module_name, list_cell_params, load_cell_params


def test_registry_resolves_common_cell_aliases():
    assert get_cell_params_module_name("MIC") == "paramsMIC"
    assert get_cell_params_module_name("1175Ah") == "paramsMIC"
    assert get_cell_params_module_name("280") == "params280"
    assert get_cell_params_module_name("314") == "params314"
    assert get_cell_params_module_name("587") == "params587"
    assert get_cell_params_module_name("587calander") == "params587calander"


def test_registry_lists_aliases_without_exposing_internal_state():
    first = list_cell_params()
    first["MIC"] = "broken"

    assert list_cell_params()["MIC"] == "paramsMIC"


def test_load_cell_params_returns_required_parameter_function():
    for cell, capacity in [("MIC", 1175), ("280", 280), ("314", 314), ("587", 587)]:
        get_hithium_params = load_cell_params(cell)
        params = get_hithium_params(1, 298.15)

        assert "Nominal cell capacity [A.h]" in params
        assert params["Nominal cell capacity [A.h]"] == capacity


def test_params314_alias_loads_legacy_314_parameters():
    from params.params314 import get_hithium_params

    params = get_hithium_params(1, 298.15)
    assert params["Nominal cell capacity [A.h]"] == 314


def test_registry_has_no_dangling_module_references():
    """registry 里的每个模块名都必须对应磁盘上真实存在的 paramsXXX.py。"""
    from params import PARAMS_ROOT, list_cell_params

    missing = sorted(
        {module for module in list_cell_params().values()
         if not (PARAMS_ROOT / f"{module}.py").exists()}
    )
    assert not missing, f"registry 引用了不存在的参数模块: {missing}"


def test_every_params_module_is_registered():
    """磁盘上每个 paramsXXX.py 都必须在 registry 登记,防止新增后漏注册。"""
    from params import PARAMS_ROOT, list_cell_params

    on_disk = {
        path.stem for path in PARAMS_ROOT.glob("params*.py")
        if path.stem != "params"  # params.py 是 legacy 便捷入口,不是电芯参数集
    }
    unregistered = sorted(on_disk - set(list_cell_params().values()))
    assert not unregistered, f"参数模块未登记到 registry: {unregistered}"


def test_registry_resolves_cw363_cw368_cw501_aliases():
    assert get_cell_params_module_name("1300CW363") == "params1300CW363"
    assert get_cell_params_module_name("CW363") == "params1300CW363"
    assert get_cell_params_module_name("CW368") == "paramsLDSCW368"
    assert get_cell_params_module_name("LDSCW368") == "paramsLDSCW368"
    assert get_cell_params_module_name("CW501") == "paramsLDSCW501"
    assert get_cell_params_module_name("LDSCW501") == "paramsLDSCW501"
