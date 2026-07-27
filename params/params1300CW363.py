# params1300CW363.py
#
# 基于《仿真所需设计参数表模板-to宫士鼎-(2).xlsx》中 "MIC CW 363" 列的设计参数生成。
# 格式严格参照 paramsMIC.py：仅通过 build_lfp_cell_params(temperature, overrides)
# 提供本芯差异项（几何 / 浓度 / 动力学 / 老化），共有脚手架项由 common.py 补全。
#
# 取值来源（对照设计参数表 "MIC CW 363" 列）：
#   - 几何：单面极片厚度（反弹后）、JR极片长度/宽度、阴极极片层数、JR个数、粒径 Dv50  —— 直接取自表
#   - 孔隙率/活性物质体积分数：由表中「活性物质占比」×「压密(涂层密度)」推导
#        AMVF = 活性物质占比 × 涂层密度 / 活性物质真密度
#        其中真密度假设 LFP≈3.6、石墨≈2.2、粘结/导电剂≈1.8 g/cm³（项目未给，需核对）
#   - 动力学/老化/SEI/OCP：沿用 paramsMIC.py 的拟合基线（设计表不含这些项）
#
# 需注意的口径问题（已在此文件显式标注）：
#   1) 隔膜厚度：表中填 0.011，单位标注 μm 但应为 ~11 μm（与 paramsMIC/CW500 的 1.1e-5 m 一致），
#      此处按 11 μm = 1.1e-5 m 填入，若确为其它单位请改 "Separator thickness [m]"。
#   2) 标称容量：表中「设计容量」= 1199.468 Ah；文件名 "1300" 若代表目标标称容量，请把
#      "Nominal cell capacity [A.h]" 改为 1300。
#   3) 电解液体积：沿用 paramsMIC 的初值（2.5e-5 / 2.0e-5 m³），未用表中「注液系数 3.443」换算
#      （换算还需电解质密度等，后续按需求再接）。
#   4) 孔隙率为按上述公式推导的估算值，正式标定前请用实测涂层密度/真密度复核。

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
graphite_ocp_charge = build_ocp_function("Gr_charge.csv", name="Neg_OCP")
graphite_ocp_discharge = build_ocp_function("Gr_discharge.csv", name="Neg_OCP")

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
        1.1131e-10,
        lambda T: 65000 * (T <= 273) + 35000 * ((T > 273) * (T < 298)) + 20000 * (T >= 298),
    )
    cracking_rate_Ai2020 = build_cracking_rate(t_factor, base_rate=0.2 * 2.1939307272313407e-21)

    if temperature < 298.15:
        k_sei = 0.01
        D_sei = 3.5
    else:
        k_sei = .1
        D_sei = .5

    hithium_params = build_lfp_cell_params(temperature, {
        # 电池几何参数（取自设计参数表 "MIC CW 363" 列）
        "Negative electrode thickness [m]": 9.435e-05,          # 阳极单面极片厚度（反弹后）94.35 μm
        "Separator thickness [m]": 1.1e-05,                     # 隔膜厚度：表中0.011为~11 μm单位误标，按11 μm取
        "Positive electrode thickness [m]": 9.5005e-05,         # 阴极单面极片厚度（反弹后）95.005 μm
        "Negative particle radius [m]": 6.0055e-06,             # 石墨 Dv50 12.011 μm / 2
        "Positive particle radius [m]": 4.5e-07,                # LFP Dv50 0.9 μm / 2
        "Electrode height [m]": 0.557,                          # JR极片长度 557 mm
        "Electrode width [m]": 0.1955*82*2*2,                   # JR极片宽度195.5mm × 阴极极片层数82 × 双面 × JR个数2

        # 电池容量参数（取自设计参数表）
        "Nominal cell capacity [A.h]": 1199.4680548035492,      # 表中「设计容量」；若"1300"为目标标称请改此处
        "Maximum concentration in negative electrode [mol.m-3]": 29094,
        "Maximum concentration in positive electrode [mol.m-3]": 20042,

        # 电极结构参数（由表中「活性物质占比」×「压密」推导，真密度假设 LFP3.6/石墨2.2/其它1.8）
        "Positive electrode porosity": 0.2818,
        "Positive electrode active material volume fraction": 0.6818,
        "Negative electrode porosity": 0.3132,
        "Negative electrode active material volume fraction": 0.6593,
        'Separator porosity': 0.38,

        # 初始条件（沿用 paramsMIC 基线）
        "Initial concentration in negative electrode [mol.m-3]": 396.87+0,
        "Initial concentration in positive electrode [mol.m-3]": 19000,
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,

        # 电化学参数（沿用 paramsMIC 基线）
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
        "Positive particle diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,

        # 电极导电性
        "Positive electrode conductivity [S.m-1]": 91.3,
        "Negative electrode conductivity [S.m-1]": 100,

        # OCP曲线
        "Negative electrode OCP [V]": graphite_ocp_discharge,
        "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
        "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,
        "Positive electrode OCP [V]": LFP_ocp_discharge,
        "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
        "Positive electrode delithiation OCP [V]": LFP_ocp_charge,
        "Negative electrode OCP entropic change [V.K-1]": graphite_entropic,
        "Positive electrode OCP entropic change [V.K-1]": LFP_entropic,

        # 其他电参数
        'Contact resistance [Ohm]': 7.018e-5,

        # 老化参数（沿用 paramsMIC 基线）
        "Positive electrode cracking rate": 0,
        "Positive electrode initial crack length [m]": 0,
        "Positive electrode initial crack width [m]": 0,
        "Ratio of lithium moles to SEI moles":2,
        "SEI partial molar volume [m3.mol-1]": 0.00009645*0.8 ,
        "Negative electrode LAM constant proportional term [s-1]":2 * 1e-7 * t_factor,
        "SEI kinetic rate constant [m.s-1]": 4.8e-14 * k_sei * t_factor,
        "EC diffusivity [m2.s-1]": 3.5e-22 * D_sei * t_factor,
        "Negative electrode cracking rate": cracking_rate_Ai2020,
        "Lithium plating kinetic rate constant [m.s-1]": 0.00003181158194366325 * t_factor,
        "SEI growth activation energy [J.mol-1]": 49887.19876117447 * 0.6,
        "Exchange-current density for stripping [A.m-2]": 2e-3,
        "Exchange-current density for plating [A.m-2]": 2e-3,

        # 电解液干涸相关参数（沿用 paramsMIC 基线）
        "Current solvent concentration in the reservoir [mol.m-3]": 1000,
        "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
        "Initial total electrolyte volume in whole cell [m3]": 2.5e-5,
        "Initial total electrolyte volume in jelly roll [m3]": 2.0e-5,
        "Electrolyte dry out rate [m3.s-1]": 1e-12
    })
    return hithium_params
