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
LFP_ocp_discharge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=-0.02)
LFP_ocp = build_ocp_function("LFP.csv", name="Pos_OCP")
graphite_ocp_charge = build_ocp_function("Gr_charge.csv", name="Neg_OCP")
graphite_ocp_discharge = build_ocp_function("Gr_discharge.csv", name="Neg_OCP")
graphite_ocp = build_ocp_function("Gr_charge.csv", name="Neg_OCP")

def get_hithium_params(t_factor=1,temperature=298.15):
    LFP_diffusivity = build_diffusivity(
        1.6e-16 / 1.5,
        lambda T: 60000 * (T <= 273.15)
        + 45000 * ((T > 273.15) * (T <= 298.15))
        + 20000 * ((T > 298.15) * (T <= 318.15))
        + 10000 * (T > 318.15),
    )
    Gr_diffusivity = build_diffusivity(
        1.06e-14,
        lambda T: 60000 * (T <= 273.15)
        + 50000 * ((T > 273.15) * (T <= 298.15))
        + 20000 * ((T > 298.15) * (T <= 318.15))
        + 10000 * (T > 318.15),
    )
    graphite_exchange_current_density = build_exchange_current_density(
        1.2121e-9,
        lambda T: 70000 * (T <= 273.15)
        + 60000 * ((T > 273.15) * (T <= 298.15))
        + 20000 * ((T > 298.15) * (T <= 318.15))
        + 10000 * (T > 318.15),
    )
    LFP_exchange_current_density = build_exchange_current_density(
        7.4207e-11,
        lambda T: 60000 * (T <= 273.15)
        + 35000 * ((T > 273.15) * (T <= 298.15))
        + 20000 * ((T > 298.15) * (T <= 318.15))
        + 10000 * (T > 318.15),
    )
    cracking_rate_Ai2020 = build_cracking_rate(t_factor)

    if temperature < 298.15:
        k_sei = 0.001
        D_sei = 3
    else:
        k_sei = .1
        D_sei = 1.2*1.8
      
    hithium_params = build_lfp_cell_params(temperature, {
        # 电池几何参数
        "Negative electrode thickness [m]": 8.05e-05,
        "Separator thickness [m]": 1.2e-05,
        "Positive electrode thickness [m]": 8.95e-05*1.01,
        "Negative particle radius [m]": 5.755e-6,
        "Positive particle radius [m]": 6.31e-7,
        "Electrode height [m]": 13.6194,
        "Electrode width [m]": 0.187*2*2,
        
        # 电池容量参数
        "Nominal cell capacity [A.h]": 314,
        "Maximum concentration in negative electrode [mol.m-3]": 29925,
        "Maximum concentration in positive electrode [mol.m-3]": 20042,
        
        # 电极结构参数
        "Positive electrode porosity": 0.26793,
        "Positive electrode active material volume fraction": 0.71889,
        "Negative electrode porosity": 0.40458,
        "Negative electrode active material volume fraction": 0.58471,
        'Separator porosity': 0.38,
        
        # 初始条件
        "Initial concentration in negative electrode [mol.m-3]": 69.79,
        "Initial concentration in positive electrode [mol.m-3]": 17824.38,
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,
        
        # 电化学参数
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
        "Positive particle diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,

        #传热
        "Total heat transfer coefficient [W.m-2.K-1]": 30,

        # 电极导电性
        "Positive electrode conductivity [S.m-1]": 4.453,
        "Negative electrode conductivity [S.m-1]": 100,
        
        # OCP曲线 (基准键与 discharge 方向一致，确保 eSOH 与 initial_soc 映射对齐)
        "Negative electrode OCP [V]": graphite_ocp_discharge,
        "Positive electrode OCP [V]": LFP_ocp_discharge,
        "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
        "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,     
        "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
        "Positive electrode delithiation OCP [V]": LFP_ocp_charge,
        "Negative electrode OCP entropic change [V.K-1]": graphite_entropic,
        "Positive electrode OCP entropic change [V.K-1]": LFP_entropic,

        # 其他电参数
        'Contact resistance [Ohm]': 1.2e-4,
        
        # 老化参数
        "Positive electrode cracking rate": 0,
        "Positive electrode initial crack length [m]": 0,
        "Positive electrode initial crack width [m]": 0,
        "Ratio of lithium moles to SEI moles":2,
        "SEI partial molar volume [m3.mol-1]": 0.00009645,
        "Negative electrode LAM constant proportional term [s-1]": 1e-7 * t_factor,
        "SEI kinetic rate constant [m.s-1]": 4.8e-14 * k_sei * t_factor,
        "EC diffusivity [m2.s-1]": 3.5e-22 * D_sei * t_factor,
        "Negative electrode cracking rate": cracking_rate_Ai2020,
        "Lithium plating kinetic rate constant [m.s-1]": 6e-5,
        "SEI growth activation energy [J.mol-1]": 49887.19876117447 ,
        "Exchange-current density for stripping [A.m-2]": 1e-3,
        "Exchange-current density for plating [A.m-2]": 1.5e-3,

        # 电解液干涸相关参数
        "Current solvent concentration in the reservoir [mol.m-3]": 1000,
        "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
        "Initial total electrolyte volume in whole cell [m3]": 3e-3,
        "Initial total electrolyte volume in jelly roll [m3]": 0.0027387,
        "Electrolyte dry out rate [m3.s-1]": 2e-14
    })
    return hithium_params