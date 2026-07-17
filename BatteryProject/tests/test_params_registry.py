from params import get_cell_params_module_name, list_cell_params, load_cell_params


def test_registry_resolves_common_cell_aliases():
    assert get_cell_params_module_name("MIC") == "paramsMIC"
    assert get_cell_params_module_name("1175Ah") == "paramsMIC"
    assert get_cell_params_module_name("280") == "params280"
    assert get_cell_params_module_name("314") == "params314"
    assert get_cell_params_module_name("587") == "params587"


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
