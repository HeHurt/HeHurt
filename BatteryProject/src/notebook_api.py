"""Recommended compact notebook API.

``easy_imports`` remains available for legacy notebooks. New notebooks should
prefer this module plus task-specific imports from ``src.simulation`` or other
submodules when they need lower-level functions.
"""

from __future__ import annotations

from .analysis import calc_rrmse, get_discharge_capacity
from .compare import compare_all
from .experiment_utils import build_power_step
from .notebook import NotebookContext, load_params, setup_notebook
from .plotting import BatteryPlotter
from .simulation import (
    DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    FULL_PULSE_LIFECYCLE_MODEL_OPTIONS,
    LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS,
    extract_cycle_voltage_curve,
    p_rate_to_power_w,
    perform_dcr_test,
    prepare_pulse_lifecycle_scenarios,
    run_dcr_and_power_test,
    run_peak_current,
    run_pulse_lifecycle_scenarios,
    summarize_pulse_lifecycle_results,
)


__all__ = [
    "BatteryPlotter",
    "DEFAULT_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "FULL_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "LIGHT_PULSE_LIFECYCLE_MODEL_OPTIONS",
    "NotebookContext",
    "build_power_step",
    "calc_rrmse",
    "compare_all",
    "extract_cycle_voltage_curve",
    "get_discharge_capacity",
    "load_params",
    "p_rate_to_power_w",
    "perform_dcr_test",
    "prepare_pulse_lifecycle_scenarios",
    "run_dcr_and_power_test",
    "run_peak_current",
    "run_pulse_lifecycle_scenarios",
    "setup_notebook",
    "summarize_pulse_lifecycle_results",
]
