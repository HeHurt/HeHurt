"""PyBaMM parameter set for the LDS CW368 1362.4 Ah LFP cell.

Geometry and electrode structure are derived from the ``LDS CW368`` column in
the supplied design-parameter workbook. Parameters not present in that workbook
(kinetics, OCP, ageing, and thermal properties) retain the established Hithium
LFP baseline and are explicitly identified below.
"""

import numpy as np
import pybamm

from common import (
    SOC_GRID,
    _load_profile,
    build_cracking_rate,
    build_diffusivity,
    build_exchange_current_density,
    build_lfp_cell_params,
    build_ocp_function,
    electrolyte_diffusivity_nyman2008_arrhenius,
    graphite_entropic as common_graphite_entropic,
    lfp_entropic as common_lfp_entropic,
    plating_exchange_current_density_okane2020,
)


electrolyte_diffusivity_Nyman2008_arrhenius = (
    electrolyte_diffusivity_nyman2008_arrhenius
)
plating_exchange_current_density_OKane2020 = (
    plating_exchange_current_density_okane2020
)
LFP_entropic = common_lfp_entropic
graphite_entropic = common_graphite_entropic

LFP_ocp_charge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=0.02)
LFP_ocp_discharge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=-0.02)

DESIGN_ELECTRODE_WIDTH_M = 0.2135 * 83 * 2 * 2
EFFECTIVE_AREA_FACTOR = 0.937
NEGATIVE_OCP_STO_WARP_DELTA = 0.07771413
NEGATIVE_OCP_STO_WARP_START = 0.212309
NEGATIVE_OCP_STO_WARP_END = 0.6
NEGATIVE_OCP_STO_WARP_SMOOTHING = 0.06011121
NEGATIVE_OCP_VOLTAGE_OFFSET_V = -0.002748570205130587


def _cw368_negative_stoichiometry_warp(sto):
    """Smoothly move the graphite mid-stoichiometry staging transitions."""
    left = 1 / (
        1
        + np.exp(
            -(sto - NEGATIVE_OCP_STO_WARP_START)
            / NEGATIVE_OCP_STO_WARP_SMOOTHING
        )
    )
    right = 1 / (
        1
        + np.exp(
            (sto - NEGATIVE_OCP_STO_WARP_END)
            / NEGATIVE_OCP_STO_WARP_SMOOTHING
        )
    )
    return np.clip(sto + NEGATIVE_OCP_STO_WARP_DELTA * left * right, 0, 1)


def _build_cw368_graphite_ocp(file_name, name):
    """Build the CW368-calibrated graphite OCP from the common baseline table."""
    soc, values = _load_profile(file_name)
    warped_values = np.interp(
        _cw368_negative_stoichiometry_warp(soc),
        soc,
        values,
    )
    calibrated_values = warped_values + NEGATIVE_OCP_VOLTAGE_OFFSET_V

    def ocp(sto):
        return pybamm.Interpolant(
            SOC_GRID,
            calibrated_values,
            sto,
            name=name,
            interpolator="cubic",
        )

    return ocp


graphite_ocp_charge = _build_cw368_graphite_ocp(
    "Gr_charge.csv",
    "Neg_OCP_CW368_charge",
)
graphite_ocp_discharge = _build_cw368_graphite_ocp(
    "Gr_discharge.csv",
    "Neg_OCP_CW368_discharge",
)


def get_hithium_params(
    t_factor=1,
    temperature=298.15,
    effective_area_factor=EFFECTIVE_AREA_FACTOR,
):
    """Return LDS CW368 overrides with an explicit electrode-area basis."""
    lfp_diffusivity = build_diffusivity(
        2.4e-16 / 1.5,
        lambda T: (
            65000 * (T <= 273)
            + 55000 * ((T > 273) * (T < 298))
            + 20000 * (T >= 298)
        ),
    )
    graphite_diffusivity = build_diffusivity(
        1.06e-14,
        lambda T: (
            60000 * (T <= 273)
            + 50000 * ((T > 273) * (T < 298))
            + 20000 * (T >= 298)
        ),
    )
    graphite_exchange_current_density = build_exchange_current_density(
        1.2121e-9,
        lambda T: (
            70000 * (T <= 273)
            + 60000 * ((T > 273) * (T < 298))
            + 20000 * (T >= 298)
        ),
    )
    lfp_exchange_current_density = build_exchange_current_density(
        1.1131e-10,
        lambda T: (
            65000 * (T <= 273)
            + 35000 * ((T > 273) * (T < 298))
            + 20000 * (T >= 298)
        ),
    )
    cracking_rate = build_cracking_rate(
        t_factor,
        base_rate=0.2 * 2.1939307272313407e-21,
    )

    if temperature < 298.15:
        k_sei = 0.01
        d_sei = 3.5
    else:
        k_sei = 0.1
        d_sei = 0.5

    return build_lfp_cell_params(
        temperature,
        {
            # Geometry: direct from the LDS CW368 design column.
            "Negative electrode thickness [m]": 80.45e-6,
            "Separator thickness [m]": 11e-6,
            "Positive electrode thickness [m]": 96.5125e-6,
            "Negative particle radius [m]": 5.5e-6,
            "Positive particle radius [m]": 0.45e-6,
            "Electrode height [m]": 0.555,
            # The effective-area factor is calibrated against the measured
            # 25 °C usable capacity (~1214 Ah); the unscaled design width is
            # retained above for auditability.
            "Electrode width [m]": (
                DESIGN_ELECTRODE_WIDTH_M * effective_area_factor
            ),
            # Capacity and concentrations.
            "Nominal cell capacity [A.h]": 1362.4,
            "Maximum concentration in negative electrode [mol.m-3]": 29094,
            "Maximum concentration in positive electrode [mol.m-3]": 20042,
            # Volume fractions derived from mass fraction and coating density.
            # Active densities: LFP 3.6 g.cm-3, graphite 2.2 g.cm-3;
            # inactive solids: 1.8 g.cm-3.
            "Positive electrode porosity": 0.2868055555555556,
            "Positive electrode active material volume fraction": (
                0.973 * 2.5 / 3.6
            ),
            "Negative electrode porosity": 0.2911818181818182,
            "Negative electrode active material volume fraction": (
                0.973 * 1.55 / 2.2
            ),
            "Separator porosity": 0.4,
            # Initial conditions.
            "Initial concentration in negative electrode [mol.m-3]": 396.87,
            "Initial concentration in positive electrode [mol.m-3]": 19000,
            "Initial concentration in electrolyte [mol.m-3]": 1000.0,
            # Electrochemistry: Hithium LFP baseline, not supplied in design table.
            # The graphite staging transitions are smoothly shifted in
            # stoichiometry using the 25 °C 0.125P/0.25P full-cell curves.
            "Negative electrode exchange-current density [A.m-2]": (
                graphite_exchange_current_density
            ),
            "Positive electrode exchange-current density [A.m-2]": (
                lfp_exchange_current_density
            ),
            "Positive particle diffusivity [m2.s-1]": lfp_diffusivity,
            "Negative particle diffusivity [m2.s-1]": graphite_diffusivity,
            "Positive electrode conductivity [S.m-1]": 91.3,
            "Negative electrode conductivity [S.m-1]": 100,
            "Negative electrode OCP [V]": graphite_ocp_discharge,
            "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
            "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,
            "Positive electrode OCP [V]": LFP_ocp_discharge,
            "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
            "Positive electrode delithiation OCP [V]": LFP_ocp_charge,
            "Negative electrode OCP entropic change [V.K-1]": graphite_entropic,
            "Positive electrode OCP entropic change [V.K-1]": LFP_entropic,
            # Similar-format baseline; retained as an explicit calibration term.
            "Contact resistance [Ohm]": 7.018e-5,
            # Ageing parameters retained for compatibility, disabled in benchmark.
            "Positive electrode cracking rate": 0,
            "Positive electrode initial crack length [m]": 0,
            "Positive electrode initial crack width [m]": 0,
            "Ratio of lithium moles to SEI moles": 2,
            "SEI partial molar volume [m3.mol-1]": 0.00009645 * 0.8,
            "Negative electrode LAM constant proportional term [s-1]": (
                2e-7 * t_factor
            ),
            "SEI kinetic rate constant [m.s-1]": (
                4.8e-14 * k_sei * t_factor
            ),
            "EC diffusivity [m2.s-1]": 3.5e-22 * d_sei * t_factor,
            "Negative electrode cracking rate": cracking_rate,
            "Lithium plating kinetic rate constant [m.s-1]": (
                0.00003181158194366325 * t_factor
            ),
            "SEI growth activation energy [J.mol-1]": (
                49887.19876117447 * 0.6
            ),
            "Exchange-current density for stripping [A.m-2]": 2e-3,
            "Exchange-current density for plating [A.m-2]": 2e-3,
            "Current solvent concentration in the reservoir [mol.m-3]": 1000,
            "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
            "Initial total electrolyte volume in whole cell [m3]": 2.5e-5,
            "Initial total electrolyte volume in jelly roll [m3]": 2.0e-5,
            "Electrolyte dry out rate [m3.s-1]": 1e-12,
        },
    )
