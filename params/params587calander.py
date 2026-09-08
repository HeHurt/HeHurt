"""587 Ah parameters calibrated for activated calendar-aging simulations."""

from params587 import get_hithium_params as get_base_params


CALIBRATED_SEI_KINETIC_RATE_M_S = 4.8e-15
CALIBRATED_EC_DIFFUSIVITY_M2_S = 2.1e-22
CALIBRATED_SEI_ACTIVATION_ENERGY_J_MOL = 39000.0


def get_hithium_params(t_factor=1, temperature=298.15):
    """Return 587 Ah parameters with the calibrated calendar-aging SEI terms."""
    params = dict(get_base_params(t_factor, temperature))
    params.update({
        "SEI kinetic rate constant [m.s-1]": (
            CALIBRATED_SEI_KINETIC_RATE_M_S * t_factor
        ),
        "EC diffusivity [m2.s-1]": (
            CALIBRATED_EC_DIFFUSIVITY_M2_S * t_factor
        ),
        "SEI growth activation energy [J.mol-1]": (
            CALIBRATED_SEI_ACTIVATION_ENERGY_J_MOL
        ),
    })
    return params
