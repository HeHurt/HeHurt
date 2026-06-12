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

LFP_ocp_charge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=0.011)
LFP_ocp_discharge = build_ocp_function("LFP.csv", name="Pos_OCP", offset=-0.011)
graphite_ocp_charge = build_ocp_function("Gr_charge.csv", name="Neg_OCP")
graphite_ocp_discharge = build_ocp_function("Gr_discharge.csv", name="Neg_OCP")

def get_hithium_params(t_factor=1,temperature=298.15):
    LFP_diffusivity = build_diffusivity(
        1.6e-16,
        select_by_requested_temperature(temperature, 65000, 20000, threshold=298),
    )
    Gr_diffusivity = build_diffusivity(
        1.06e-14,
        select_by_requested_temperature(temperature, 60000, 20000, threshold=298),
    )
    graphite_exchange_current_density = build_exchange_current_density(
        1.2121e-9,
        select_by_requested_temperature(temperature, 70000, 20000, threshold=298),
    )
    LFP_exchange_current_density = build_exchange_current_density(
        1.1131e-10,
        select_by_requested_temperature(temperature, 60000, 20000, threshold=298),
    )
    cracking_rate_Ai2020 = build_cracking_rate(t_factor)

    def plating_exchange_current_density_OKane2020(c_e, c_Li, T):
        k_plating = pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")
        return pybamm.constants.F * k_plating * c_e

    def stripping_exchange_current_density_OKane2020(c_e, c_Li, T):
        k_plating = pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")
        return pybamm.constants.F * k_plating * c_Li

    if temperature < 298.15:
        k_sei = 0.01
        D_sei = 3
    else:
        k_sei = .1
        # D_sei = 3
        D_sei = 2
      
    hithium_params = build_lfp_cell_params(temperature, {
        # 电池几何参数
        "Negative electrode thickness [m]": 7.35922E-5,
        "Separator thickness [m]": 1.1e-05,
        "Positive electrode thickness [m]": 8.60925E-5,
        "Negative particle radius [m]": 5.5E-6 ,
        "Positive particle radius [m]": 4.75E-7 ,
        "Electrode height [m]": 0.196,
        "Electrode width [m]":  12.365*2*4,
        
        # 电池容量参数
        "Nominal cell capacity [A.h]": 587,
        "Maximum concentration in negative electrode [mol.m-3]": 29094,
        "Maximum concentration in positive electrode [mol.m-3]": 18897,
        
        # 电极结构参数
        "Positive electrode porosity": 0.23418,
        "Positive electrode active material volume fraction":0.74591,
        "Negative electrode porosity": 0.32168,
        "Negative electrode active material volume fraction": 0.6634,
        'Separator porosity': 0.4,
                
        # OCP曲线
        "Negative electrode OCP [V]": graphite_ocp_discharge,
        "Positive electrode OCP [V]": LFP_ocp_discharge,
        "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
        "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,     
        "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
        "Positive electrode delithiation OCP [V]": LFP_ocp_charge,
        "Negative electrode OCP entropic change [V.K-1]": graphite_entropic,
        "Positive electrode OCP entropic change [V.K-1]": LFP_entropic,
        # 初始条件（SOC ≈ 5%，避免极低 SOC 导致老化模型 SEI 初始化发散）
        "Initial concentration in negative electrode [mol.m-3]": 29094 * 0.045,  # 1454.7
        "Initial concentration in positive electrode [mol.m-3]": 19521 * 0.955,  # 18545.0
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,
        
        # 电化学参数
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
        "Positive particle diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,
        
        #传热
        "Total heat transfer coefficient [W.m-2.K-1]": 30,

        # 电极导电性
        "Positive electrode conductivity [S.m-1]": 91.3,
        "Negative electrode conductivity [S.m-1]": 5,

        # 其他电参数
        'Contact resistance [Ohm]': 0.056276e-3,
        
        # "Positive electrode initial crack width [m]": 0,
        "Ratio of lithium moles to SEI moles":1.5,
        "SEI partial molar volume [m3.mol-1]": 9.645e-5 ,
        "Negative electrode LAM constant proportional term [s-1]": 0.5*1e-7 * t_factor,
        "Negative electrode cracking rate": cracking_rate_Ai2020,
        "SEI kinetic rate constant [m.s-1]": 4.8e-14 * k_sei * t_factor,
        "EC diffusivity [m2.s-1]": 3.5e-22 * D_sei * t_factor,
        "SEI growth activation energy [J.mol-1]": 50000 ,
        "Lithium plating kinetic rate constant [m.s-1]": 1e-4 ,
        # "": stripping_exchange_current_density_OKane2020,
        "Exchange-current density for stripping [A.m-2]": 1e-3,
        "Exchange-current density for plating [A.m-2]": 1.5e-3,

    })
    return hithium_params