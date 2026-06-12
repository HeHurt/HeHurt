import pybamm

from common import (
    build_diffusivity,
    build_exchange_current_density,
    build_ocp_function,
    electrolyte_conductivity,
    electrolyte_diffusivity_nyman2008_arrhenius,
    select_by_requested_temperature,
)


electrolyte_diffusivity_Nyman2008_arrhenius = electrolyte_diffusivity_nyman2008_arrhenius

Na_ocp_charge = build_ocp_function("Na_revise.csv", name="Pos_OCP")
Na_ocp_discharge = build_ocp_function("Na_revise.csv", name="Pos_OCP")
HardC_charge = build_ocp_function("HardC.csv", name="Neg_OCP")
HardC_discharge = build_ocp_function("HardC.csv", name="Neg_OCP")
          
def get_hithium_params(t_factor=1,temperature=298.15):
    Na_diffusivity = build_diffusivity(
        2e-15,
        select_by_requested_temperature(temperature, 65000, 20000, threshold=298),
    )
    Gr_diffusivity = build_diffusivity(
        1.06e-14 * 5,
        select_by_requested_temperature(temperature, 60000, 20000, threshold=298),
    )
    graphite_exchange_current_density = build_exchange_current_density(
        1.2121e-9 * 2.5,
        select_by_requested_temperature(temperature, 70000, 20000, threshold=298),
    )
    Na_exchange_current_density = build_exchange_current_density(
        1.1131e-10 * 2.5,
        select_by_requested_temperature(temperature, 65000, 20000, threshold=298),
    )

    hithium_params = {
        # 电池几何参数
        "Negative electrode thickness [m]": 7.6E-5,
        "Separator thickness [m]": 1.4E-5 ,
        "Positive electrode thickness [m]": 7.85E-5 ,
        "Negative particle radius [m]": 2.3331E-6 ,
        "Positive particle radius [m]": 2.9395E-6,
        "Electrode height [m]": 0.1875 ,
        "Electrode width [m]": 14.297*2*2 *.9,
        
        # 电池容量参数
        "Nominal cell capacity [A.h]": 162,
        "Ambient temperature [K]": temperature,
        "Number of electrodes connected in parallel to make a cell": 1,
        "Maximum concentration in negative electrode [mol.m-3]": 23051,
        "Maximum concentration in positive electrode [mol.m-3]": 13484 ,
        
        # 电极结构参数
        "Positive electrode porosity": 0.26635 ,
        "Positive electrode active material volume fraction": 0.70966 ,
        "Negative electrode porosity":0.51095 ,
        "Negative electrode active material volume fraction": 0.46558 ,
        'Separator porosity': 0.42,
    
        # 初始条件
        "Initial concentration in negative electrode [mol.m-3]": 314.44,
        "Initial concentration in positive electrode [mol.m-3]": 11434+2000,
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,
        
        # 电压限制
        "Lower voltage cut-off [V]": 2.0,
        "Upper voltage cut-off [V]": 3.65,
        "Open-circuit voltage at 0% SOC [V]": 2.0,
        "Open-circuit voltage at 100% SOC [V]": 3.65,
        
        # 电化学参数
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": Na_exchange_current_density,
        'Electrolyte diffusivity [m2.s-1]': electrolyte_diffusivity_Nyman2008_arrhenius,
        "Electrolyte conductivity [S.m-1]": electrolyte_conductivity,
        "Positive particle diffusivity [m2.s-1]": Na_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,
        
        # Bruggeman系数
        "Positive electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrode)": 1.5,
        
        # 电极导电性
        "Positive electrode conductivity [S.m-1]": 91.3,
        "Negative electrode conductivity [S.m-1]": 100,
        
        # OCP曲线
        "Negative electrode OCP [V]": HardC_discharge,
        "Positive electrode OCP [V]": Na_ocp_charge,
        "Negative electrode lithiation OCP [V]": HardC_discharge,
        "Negative electrode delithiation OCP [V]": HardC_charge,     
        "Positive electrode lithiation OCP [V]": Na_ocp_discharge,
        "Positive electrode delithiation OCP [V]": Na_ocp_charge,

        
        # 其他电参数
        'Contact resistance [Ohm]': 1.6603e-4,
        'Positive electrode double-layer capacity [F.m-2]': 0,
        'Negative electrode double-layer capacity [F.m-2]': 0,
        
        # # 老化参数
        # "Lithium plating transfer coefficient": 0.5,
        # "Exchange-current density for plating [A.m-2]": plating_exchange_current_density_OKane2020,
        # "Positive electrode cracking rate": 0,
        # "Positive electrode initial crack length [m]": 0,
        # "Positive electrode initial crack width [m]": 0,
        # "Ratio of lithium moles to SEI moles":1.2,
        # "Outer SEI partial molar volume [m3.mol-1]": 0.00009645 * 1,
        # "Initial inner SEI thickness [m]": 5e-9,
        # "Negative electrode LAM constant proportional term [s-1]": 1 * 1e-7 * t_factor,
        # "SEI kinetic rate constant [m.s-1]": 4.809982610110174e-14 * k_sei * t_factor,
        # "EC diffusivity [m2.s-1]": 3.487219488169518e-22 * D_sei * t_factor,
        # "Negative electrode cracking rate": cracking_rate_Ai2020,
        # "Lithium plating kinetic rate constant [m.s-1]": 0.00003181158194366325,
        # "SEI growth activation energy [J.mol-1]": 49887.19876117447 * 0.5,
        # "Exchange-current density for stripping [A.m-2]": 1e-3,
        # "Exchange-current density for plating [A.m-2]": 1.5e-3,

        # # 电解液干涸相关参数
        # "Current solvent concentration in the reservoir [mol.m-3]": 2000,
        # "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
        # "Initial total electrolyte volume in whole cell [m3]": 2.5e-5,
        # "Initial total electrolyte volume in jelly roll [m3]": 2.0e-5,
        # "Electrolyte dry out rate [m3.s-1]": 1e-12
    }
    return hithium_params