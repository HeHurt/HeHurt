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
)

electrolyte_diffusivity_Nyman2008_arrhenius = electrolyte_diffusivity_nyman2008_arrhenius
plating_exchange_current_density_OKane2020 = plating_exchange_current_density_okane2020
LFP_entropic = common_lfp_entropic
graphite_entropic = common_graphite_entropic

LFP_ocp_charge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=0.02)
LFP_ocp_discharge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=-0.03)
LFP_ocp_Hithium280Ah = build_ocp_function("LFP.csv", name="Pos_OCP", offset=0.02)
graphite_ocp_charge = build_ocp_function("Gr_charge.csv", name="Neg_OCP")
graphite_ocp_discharge = build_ocp_function("Gr_discharge.csv", name="Neg_OCP")
graphite_ocp_Hithium280Ah = build_ocp_function("Gr_charge.csv", name="Neg_OCP")

def get_hithium_params(t_factor=1,temperature=298.15):
    LFP_diffusivity = build_diffusivity(
        2.4e-16 / 1.5,
        lambda T: 65000 * (T <= 273) + 55000 * ((T > 273) * (T < 298)) + 20000 * (T >= 298),
    )
    Gr_diffusivity = build_diffusivity(
        1.06e-14,
        lambda T: 60000 * (T <= 273) + 50000 * ((T > 273) * (T < 298)) + 20000 * (T >= 298),
    )
    graphite_exchange_current_density = build_exchange_current_density(
        1.2121e-9,
        lambda T: 70000 * (T <= 273) + 60000 * ((T > 273) * (T < 298)) + 20000 * (T >= 298),
    )
    LFP_exchange_current_density = build_exchange_current_density(
        1.1131e-10 * 0.75,
        lambda T: 65000 * (T <= 273) + 35000 * ((T > 273) * (T < 298)) + 20000 * (T >= 298),
    )
    cracking_rate_Ai2020 = build_cracking_rate(t_factor, base_rate=0.2 * 2.1939307272313407e-21)

    if temperature < 298.15:
        k_sei = 0.01
        D_sei = 3.5
    else:
        k_sei = .1
        D_sei = 2
    
    hithium_params = build_lfp_cell_params(temperature, {
        # 电池几何参数
        "Negative electrode thickness [m]": 113.525e-6,
        "Separator thickness [m]": 1.1e-05,
        "Positive electrode thickness [m]": 135.7125e-6,
        "Negative particle radius [m]": 5.5e-6,
        "Positive particle radius [m]": 0.45e-6,
        "Electrode height [m]": 0.555,
        "Electrode width [m]": 0.2135 * 61 * 2 * 2,
        
        # 电池容量参数
        "Nominal cell capacity [A.h]": 1361.9,
        "Maximum concentration in negative electrode [mol.m-3]": 29094,
        "Maximum concentration in positive electrode [mol.m-3]": 20042,
        
        # 电极结构参数
        "Positive electrode porosity":0.2906   ,
        "Positive electrode active material volume fraction":  0.6881 ,
        "Negative electrode porosity": 0.3045 ,
        "Negative electrode active material volume fraction": 0.6733 ,
        'Separator porosity': 0.4,
    
        # 初始条件
        "Initial concentration in negative electrode [mol.m-3]": 396.87+0,
        "Initial concentration in positive electrode [mol.m-3]": 19000,
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,
        
        # 电化学参数
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
        "Positive particle diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,
        
        # 电极导电性
        "Positive electrode conductivity [S.m-1]": 91.3,
        "Negative electrode conductivity [S.m-1]": 100,
        
        # OCP曲线
        "Negative electrode OCP [V]": graphite_ocp_Hithium280Ah,
        "Positive electrode OCP [V]": LFP_ocp_Hithium280Ah,
        "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
        "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,     
        "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
        "Positive electrode delithiation OCP [V]": LFP_ocp_charge,

        # 其他电参数
        'Contact resistance [Ohm]': 0.96101e-4,
        
        # 老化参数
        "Positive electrode cracking rate": 0,
        "Positive electrode initial crack length [m]": 0,
        "Positive electrode initial crack width [m]": 0,
        "Ratio of lithium moles to SEI moles":1.8,
        "Outer SEI partial molar volume [m3.mol-1]": 0.00009645 ,
        "Negative electrode LAM constant proportional term [s-1]": 1.5 * 1e-7 * t_factor,
        "SEI kinetic rate constant [m.s-1]": 4.809982610110174e-14 * k_sei * t_factor,
        "EC diffusivity [m2.s-1]": 3.487219488169518e-22 * D_sei * t_factor,
        "Negative electrode cracking rate": cracking_rate_Ai2020,
        "Lithium plating kinetic rate constant [m.s-1]": 0.00003181158194366325,
        "SEI growth activation energy [J.mol-1]": 49887.19876117447 * 0.5,
        "Exchange-current density for stripping [A.m-2]": 1e-3,
        "Exchange-current density for plating [A.m-2]": 1.5e-3,

        # 电解液干涸相关参数
        "Current solvent concentration in the reservoir [mol.m-3]": 2000,
        "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
        "Initial total electrolyte volume in whole cell [m3]": 2.5e-5,
        "Initial total electrolyte volume in jelly roll [m3]": 2.0e-5,
        "Electrolyte dry out rate [m3.s-1]": 1e-12
    })
    return hithium_params