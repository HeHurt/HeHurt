import pybamm

from common import (
    build_cracking_rate,
    build_diffusivity,
    build_exchange_current_density,
    build_lfp_cell_params,
    build_ocp_function,
    electrolyte_conductivity,
    electrolyte_diffusivity_nyman2008_arrhenius,
    graphite_entropic as common_graphite_entropic,
    lfp_entropic as common_lfp_entropic,
    plating_exchange_current_density_okane2020,
    select_by_requested_temperature,
)

electrolyte_diffusivity_Nyman2008_arrhenius = electrolyte_diffusivity_nyman2008_arrhenius
plating_exchange_current_density_OKane2020 = plating_exchange_current_density_okane2020
LFP_entropic = common_lfp_entropic
graphite_entropic = common_graphite_entropic

LFP_ocp_charge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=0.02)
LFP_ocp_discharge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=-0.02)
graphite_ocp_charge = build_ocp_function("Gr_charge.csv", name="Neg_OCP")
graphite_ocp_discharge = build_ocp_function("Gr_discharge.csv", name="Neg_OCP")

def get_hithium_params(t_factor=1, temperature=298.15):
    LFP_diffusivity = build_diffusivity(
        1.92e-16,
        select_by_requested_temperature(temperature, 45000, 20000, threshold=298),
    )
    Gr_diffusivity = build_diffusivity(
        1.06e-14,
        select_by_requested_temperature(temperature, 50000, 20000, threshold=298),
    )
    graphite_exchange_current_density = build_exchange_current_density(
        1.2121e-9,
        select_by_requested_temperature(temperature, 60000, 20000, threshold=298),
    )
    LFP_exchange_current_density = build_exchange_current_density(
        1.1131e-10,
        select_by_requested_temperature(temperature, 35000, 20000, threshold=298),
    )
    cracking_rate_Ai2020 = build_cracking_rate(t_factor)

    if temperature < 298.15:
        k_sei = 0.001
        D_sei = 3
    else:
        k_sei = 0.12
        D_sei = 1.4 * 2

    electrolyte_volume_scale = 3.75 / 314

    hithium_params = build_lfp_cell_params(temperature, {
        "Negative electrode thickness [m]": 0.00013390683330628144,
        "Separator thickness [m]": 1.1e-05,
        "Positive electrode thickness [m]": 0.00010604339122436833,
        "Negative particle radius [m]": 5.9e-06,
        "Positive particle radius [m]": 4.3e-07,
        "Electrode height [m]": 0.682,
        "Electrode width [m]": 0.086 * 2,
        "Nominal cell capacity [A.h]": 3.75,
        "Maximum concentration in negative electrode [mol.m-3]": 29094,
        "Maximum concentration in positive electrode [mol.m-3]": 19261,
        "Positive electrode porosity": 0.2775229348864212,
        "Positive electrode active material volume fraction": 0.7087500008764208,
        "Negative electrode porosity": 0.31774316480508713,
        "Negative electrode active material volume fraction": 0.6638359006446503,
        "Separator porosity": 0.38,
        "Initial concentration in negative electrode [mol.m-3]": 396.87,
        "Initial concentration in positive electrode [mol.m-3]": 18259,
        "Initial concentration in electrolyte [mol.m-3]": 960.0,
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
        "Positive particle diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,
        "Total heat transfer coefficient [W.m-2.K-1]": 30,
        # PyBaMM 不读取这两个名字（有效值由各组分 density/specific heat/conductivity 计算）。
        "Positive electrode conductivity [S.m-1]": 4.5,
        "Negative electrode conductivity [S.m-1]": 100,
        "Negative electrode OCP [V]": graphite_ocp_discharge,
        "Positive electrode OCP [V]": LFP_ocp_discharge,
        "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
        "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,
        "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
        "Positive electrode delithiation OCP [V]": LFP_ocp_charge,
        "Negative electrode OCP entropic change [V.K-1]": graphite_entropic,
        "Positive electrode OCP entropic change [V.K-1]": LFP_entropic,
        "Contact resistance [Ohm]": 1e-4,
        "Positive electrode cracking rate": 0,
        "Positive electrode initial crack length [m]": 0,
        "Positive electrode initial crack width [m]": 0,
        "Ratio of lithium moles to SEI moles": 2,
        "SEI partial molar volume [m3.mol-1]": 0.00009645,
        "Negative electrode LAM constant proportional term [s-1]": 1e-7 * t_factor,
        "SEI kinetic rate constant [m.s-1]": 4.8e-14 * k_sei * t_factor,
        "EC diffusivity [m2.s-1]": 3.5e-22 * D_sei * t_factor,
        "Negative electrode cracking rate": cracking_rate_Ai2020,
        "Lithium plating kinetic rate constant [m.s-1]": 6e-5,
        "SEI growth activation energy [J.mol-1]": 49887.19876117447,
        "Exchange-current density for stripping [A.m-2]": 1.5e-3,
        "Exchange-current density for plating [A.m-2]": 1.5e-3,
        "Current solvent concentration in the reservoir [mol.m-3]": 1000,
        "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
        "Initial total electrolyte volume in whole cell [m3]": 3e-3 * electrolyte_volume_scale,
        "Initial total electrolyte volume in jelly roll [m3]": 0.0027387 * electrolyte_volume_scale,
        "Electrolyte dry out rate [m3.s-1]": 2e-14,
    })
    return hithium_params