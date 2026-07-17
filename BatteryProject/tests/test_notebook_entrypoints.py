import sys

from src.notebook import load_params, setup_notebook
from src.notebook_api import __all__ as notebook_api_all


def test_setup_notebook_prioritizes_workspace_before_params_root():
    ctx = setup_notebook(style=None, autoreload=False)

    project_index = sys.path.index(str(ctx.project_root))
    workspace_index = sys.path.index(str(ctx.workspace_root))
    params_index = sys.path.index(str(ctx.params_root))

    assert project_index < workspace_index < params_index


def test_load_params_uses_registry():
    get_hithium_params = load_params("MIC")
    params = get_hithium_params(1, 298.15)

    assert params["Nominal cell capacity [A.h]"] == 1175


def test_notebook_api_is_intentionally_small():
    assert len(notebook_api_all) <= 20
    assert "setup_notebook" in notebook_api_all
    assert "load_params" in notebook_api_all
    assert "run_peak_current" in notebook_api_all
    assert "run_dcr_and_power_test" in notebook_api_all
    assert "run_and_plot_all" not in notebook_api_all
