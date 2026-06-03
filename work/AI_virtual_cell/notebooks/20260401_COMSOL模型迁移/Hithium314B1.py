import pybamm
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from pathlib import Path
import os

try:
    from ..logger import get_logger
except ImportError:
    from logger import get_logger

def fileload(file_path):
    data = pd.read_csv(file_path, header=None, sep='\t')
    return {0: data[0].to_numpy(), 1: data[1].to_numpy()}

logger = get_logger(__name__)

F = 96485.33212
script_path = Path(os.path.abspath(__file__)).parent
params_dir = script_path / 'params'
battery_design = {
    'anodeThickness': 129, # um, 双层+铜箔
    'anodeThicknessRebound': 0.0234, # 厚度反弹率
    # 'anodeThicknessRebound': 0, # 厚度反弹率
    'anodeCuFoilThickness': 6, # um
    'anodeRealDensity': 2.2279, # g/cm^3
    'anodeGramSpecCap': 350, # mAh/g
    'anodeLoading': 0.967, 
    'anodeCWCoating': 0.152,
    'anodePD': 1.60, # g/cm^3
    'anodeLength': 14950.705, # mm
    'anodeWidth': 190.5, # mm
    'cathodeThickness': 181, # um, 双层+铝箔
    'cathodeThicknessRebound': 0.0074, # 厚度反弹率
    # 'cathodeThicknessRebound': 0, # 厚度反弹率
    'cathodeAlFoilThickness': 14, # um
    'cathodeRealDensity': 3.488, # g/cm^3
    'cathodeGramSpecCap': 148, # mAh/g
    'cathodeLoading': 0.982,
    'cathodeCWCoating': 0.328,
    'cathodePD': 2.55, # g/cm^3
    'cathodeLength': 14596.095, # mm
    'cathodeWidth': 187, # mm
    'designNominalCap': 314, # Ah
    'designCb': 1.108,
    'jrVal': 2
}

model_params = []

params = { # 可调参参数
    'Dpos': 1.6e-16,
    'Dneg': 1.060e-14,
    'Kneg': 1.2121e-9,
    'Kpos': 1.1131e-10,
    'csmax_neg': 1.0, # 负极最大浓度修正系数
    'csmax_pos': 1.0, # 正极最大浓度修正系数
    'socmin_neg': 0.013641,
    'socmax_pos': 0.948,
    'Qx': 1.01, # 总容量修正系数
    'Bruggeman': 1.5,
    'R': 0.0001002,
    'E_D_p': 3.03e4, # 可选
    'E_D_n': 3.03e4, # 可选
    'E_K_p': 35000, # 可选
    'E_K_n': 35000 # 可选
}

lfp_ocv_data = pd.read_csv(params_dir / 'LFP.dat', header=None, sep='\t')
lfp_charge_ocv_data = lfp_ocv_data.copy()
lfp_charge_ocv_data[1] = lfp_charge_ocv_data[1] + 0.02
lfp_discharge_ocv_data = lfp_ocv_data.copy()
lfp_discharge_ocv_data[1] = lfp_discharge_ocv_data[1] - 0.02
LFP = {
    'dv50': 0.631 * 2, # um
    'charge_open_circuit_voltage': {0: lfp_charge_ocv_data[0].to_numpy(), 1: lfp_charge_ocv_data[1].to_numpy()},
    'discharge_open_circuit_voltage': {0: lfp_discharge_ocv_data[0].to_numpy(), 1: lfp_discharge_ocv_data[1].to_numpy()},
    'sigma': 100, # S/m
    'k_revise': False,
    'D_revise': False,
    'k_int': fileload(params_dir / 'K_pos_int.dat'),
    'D_int': fileload(params_dir / 'D_pos_int.dat')
}

Gr = {
    'dv50': 5.755 * 2, # um
    'charge_open_circuit_voltage': fileload(params_dir / 'Gr_charge.dat'),
    'discharge_open_circuit_voltage': fileload(params_dir / 'Gr_discharge.dat'),
    'sigma': 4.453, # S/m
    'k_revise': False,
    'D_revise': True,
    'k_int': fileload(params_dir / 'K_neg_int.dat'),
    'D_int': fileload(params_dir / 'D_neg_int.dat')
}

Electrolyte = {
    'c0': 900, # mol/m^3
    'sigma': fileload(params_dir / 'E_sigma.dat'),
    'Ds': fileload(params_dir / 'E_DL.dat'),
    'transNum': fileload(params_dir / 'E_transpNm.dat'),
    'thermodynamic': fileload(params_dir / 'E_thermodynamic.dat')
}

Separator = {
    'porosity': 0.38,
    'thickness': 1.1e-05
}


class Battery(object):
    def __init__(self, params):
        if isinstance(params, str):
            params = [params]
        self.params = params
        pass

    def get_params(self, charge_state, params):
        pass

class BatteryDirect(Battery):
    def __init__(self, battery_params, model_params, LFP, Gr, Electrolyte, Separator):
        converted_battery_params = self._convert_battery_design(battery_params)

        super(BatteryDirect, self).__init__(model_params)
        default_params = {
            "Anode Material Real Density(g/cm^3)": 2.2279,
            "Cathode Material Real Density(g/cm^3)": 3.488,
            "Anode Spec.Cap(mAh/g)": 340,
            "Cathode Spec.Cap(mAh/g)": 144,
            "Anode Loading": 0.967,
            "Cathode Loading": 0.972,
            "Anode PD(g/cm^3)": 1.55,
            "Cathode PD(g/cm^3)": 2.45,
            "Anode CW(g/1540.25m2)": 0.152,
            "Cathode CW(g/1540.25m2)": 0.328,
            "Anode Thickness(um)": 10.1e-05 / 1e-6,
            "Cathode Thickness(um)": 13.5e-05 / 1e-6,
            "Cathode Length(mm)": 17.06216 / 1e-3,
            "Cathode Width(mm)": 0.1875 / 1e-3,
            "Anode Length(mm)": 17.06216 / 1e-3 * 1.036,
            "Anode Width(mm)": 0.1875 / 1e-3,
            "Anode Material Dv50(um)": 1.27e-5 / 1e-6,
            "Cathode Material Dv50(um)": 9.78e-7 / 1e-6,
            "Nominal CAP(Ah)@0.5P": 280,
            "CB": 1.126,
            "JR": 2
        }
        default_params.update(converted_battery_params)
        default_params.update({
            "Anode Material Dv50(um)": Gr.get('dv50',1.27e-5 / 1e-6),
            "Cathode Material Dv50(um)": LFP.get('dv50',9.78e-7 / 1e-6)
        })

        soc = np.linspace(0, 1, 500)
        self.soc = soc
        self.Gr_charge = interp1d(Gr['charge_open_circuit_voltage'][0], Gr['charge_open_circuit_voltage'][1], kind='linear', fill_value="extrapolate")(soc)
        self.LFP_charge = interp1d(LFP['charge_open_circuit_voltage'][0], LFP['charge_open_circuit_voltage'][1], kind='linear', fill_value="extrapolate")(soc)
        self.LFP_discharge = interp1d(LFP['discharge_open_circuit_voltage'][0], LFP['discharge_open_circuit_voltage'][1], kind='linear', fill_value="extrapolate")(soc)
        self.Gr_discharge = interp1d(Gr['discharge_open_circuit_voltage'][0], Gr['discharge_open_circuit_voltage'][1], kind='linear', fill_value="extrapolate")(soc)
        self.CB = default_params['CB']
        self.anode_thickness = default_params['Anode Thickness(um)'] * 1e-6 /2 
        self.cathode_thickness = default_params['Cathode Thickness(um)'] * 1e-6 / 2
        self.rho_neg = default_params["Anode Material Real Density(g/cm^3)"]
        self.rho_pos = default_params["Cathode Material Real Density(g/cm^3)"]
        self.c_max_pos = self.rho_pos  * 1e6 * default_params["Cathode Spec.Cap(mAh/g)"] / 1000 * 3600 / F
        self.c_max_neg = self.rho_neg  * 1e6 * default_params["Anode Spec.Cap(mAh/g)"] / 1000 * 3600 / F
        self.den_pos = default_params['Cathode CW(g/1540.25m2)'] / 1540.25
        self.den_neg = default_params['Anode CW(g/1540.25m2)'] / 1540.25
        # self.epss_neg = default_params["Anode PD(g/cm^3)"] / self.rho_neg
        # self.epss_pos = default_params["Cathode PD(g/cm^3)"] / self.rho_pos
        self.epss_neg = self.den_neg /(self.rho_neg*self.anode_thickness) * default_params['Anode Loading']
        self.epss_pos = self.den_pos /(self.rho_pos*self.cathode_thickness) * default_params['Cathode Loading']
        self.epsl_neg = 1 - self.epss_neg / default_params['Anode Loading']
        self.epsl_pos = 1 - self.epss_pos / default_params['Cathode Loading']
        self.Ac = default_params["Cathode Width(mm)"] * default_params["Cathode Length(mm)"] * 1e-6 * 2 * 2
        self.ah_neg = self.den_neg * default_params["Anode Spec.Cap(mAh/g)"] * self.Ac * 1e3
        self.ah_pos = self.den_pos * default_params["Cathode Spec.Cap(mAh/g)"] * self.Ac * 1e3
        self.default_params = default_params
    
        self.Electrolyte = Electrolyte
        self.LFP = LFP
        self.Gr = Gr
        self.Separator = Separator
    
        logger.info(
            "Battery SelfDefined parameters:\n"
            "  den_neg: %f\n"
            "  den_pos: %f\n"
            "  c_max_neg: %f\n"
            "  c_max_pos: %f\n"
            "  epss_neg: %f\n"
            "  epss_pos: %f\n"
            "  epsl_neg: %f\n"
            "  epsl_pos: %f\n"
            "  ah_neg: %f\n"
            "  ah_pos: %f\n"
            "  Anode Material Dv50(um): %s\n"
            "  Cathode Material Dv50(um): %s\n"
            "  Cathode Thickness(um): %s\n"
            "  Anode Thickness(um): %s\n"
            "  Nominal CAP(Ah): %s\n",
            self.den_neg/1e-3, self.den_pos/1e-3,
            self.c_max_neg, self.c_max_pos,
            self.epss_neg, self.epss_pos, self.epsl_neg, self.epsl_pos, self.ah_neg, self.ah_pos,
            self.default_params["Anode Material Dv50(um)"],
            self.default_params["Cathode Material Dv50(um)"],
            self.default_params['Cathode Thickness(um)'] / 2,
            self.default_params['Anode Thickness(um)'] / 2,
            self.default_params['Nominal CAP(Ah)@0.5P']
        )

    def get_params(self, charge_state, params):
        logger.debug("model params: %s\nparams:%s"%(self.params, params))
        if 'socpos_max' in params.keys():
            params['socmax_pos'] = params['socpos_max']
        if 'socneg_min' in params.keys():
            params['socmin_neg'] = params['socneg_min']
        if 'diffT' in self.params:
            E_D_p = params.get('E_D_p', 3.03e4)
            E_D_n = params.get('E_D_n', 3.03e4)
            E_K_p = params.get('E_K_p', 35000)
            E_K_n = params.get('E_K_n', 35000)
        else:
            E_D_p = 3.03e4
            E_D_n = 3.03e4
            E_K_p = 35000
            E_K_n = 35000

        Dpos = params.get('Dpos', 2.00e-16)
        Dneg = params.get('Dneg', 2.60e-14)
        Kneg = params.get('Kneg',3.60e-9)
        Kpos = params.get('Kpos', 6.14e-11)
        Qx = params.get('Qx',1)
        csmax_neg = self.c_max_neg * params.get('csmax_neg', 1.02)
        csmax_pos = self.c_max_pos * params.get('csmax_pos', 1.049)
        socmin_neg = params.get('socmin_neg', 0.014)
        socmax_pos = params.get('socmax_pos', 0.974)
        Bruggeman = params.get('Bruggeman', 1.5)
        R = params.get('R',0.00005)

        def LFP_diffusivity(sto, T):
            D_ref = Dpos
            E_D_s = E_D_p
            if self.LFP['D_revise']:
                D_revise = pybamm.Interpolant(self.LFP['D_int'][0], self.LFP['D_int'][1], sto, name='D_pos', interpolator="linear")
            else:
                D_revise = 1
            arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
            return D_revise * D_ref * arrhenius

        def Gr_diffusivity(sto, T):
            D_ref = Dneg
            E_D_s = E_D_n
            if self.Gr['D_revise']:
                D_revise = pybamm.Interpolant(self.Gr['D_int'][0], self.Gr['D_int'][1], sto, name='D_neg', interpolator="linear")
            else:
                D_revise = 1
            arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
            return D_revise * D_ref * arrhenius

        def graphite_exchange_current_density(c_e, c_s_surf, c_s_max, T):
            sto = c_s_surf / c_s_max
            c_l_ref = 1e3
            m_ref = Kneg  # (A/m2)(m3/mol)**1.5 - includes ref concentrations
            E_r = E_K_n
            if self.Gr['k_revise']:
                K_revise = pybamm.Interpolant(self.Gr['k_int'][0], self.Gr['k_int'][1], sto, name='Neg_i0', interpolator="linear")
            else:
                K_revise = 1
            arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
            return m_ref * arrhenius * (c_e / c_l_ref) ** 0.5 * c_s_surf ** 0.5 * (
                    c_s_max - c_s_surf) ** 0.5 * K_revise * F

        def LFP_exchange_current_density(c_e, c_s_surf, c_s_max, T):
            sto = c_s_surf / c_s_max
            c_l_ref = 1e3
            m_ref = Kpos # (A/m2)(m3/mol)**1.5 - includes ref concentrations
            E_r = E_K_p
            arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
            if self.LFP['k_revise']:
                K_revise = pybamm.Interpolant(self.LFP['k_int'][0], self.LFP['k_int'][1], sto, name='Pos_i0', interpolator="linear")
            else:
                K_revise = 1
            return m_ref * arrhenius * (c_e / c_l_ref) ** 0.5 * c_s_surf ** 0.5 * (
                    c_s_max - c_s_surf) ** 0.5 * K_revise * F

        def electrolyte_diffusivity_Nyman2008_arrhenius(c_e, T):
            D_c_e_ratio = pybamm.Interpolant(self.Electrolyte['Ds'][0], self.Electrolyte['Ds'][1], c_e, name='D_c_e', interpolator='linear')
            D_c_e = D_c_e_ratio / (1 - c_e * 59e-6)
            E_D_c_e = 17000
            arrhenius = np.exp(E_D_c_e / pybamm.constants.R * (1 / 298.15 - 1 / T))
            return D_c_e * arrhenius
        
        def transfer_num(c_e, T):
            return pybamm.Interpolant(self.Electrolyte['transNum'][0], self.Electrolyte['transNum'][1], c_e, name='Trans_num', interpolator='linear')

        def electrolyte_conductivity(c_e, T):
            E_sigma = 4000
            arrhenius = np.exp(E_sigma / pybamm.constants.R * (1 / 298.15 - 1 / T))
            return pybamm.Interpolant(self.Electrolyte['sigma'][0], self.Electrolyte['sigma'][1], c_e, name='Sigma_ele',
                                        interpolator='linear') * arrhenius
        
        def electrolyte_thermodynamic_factor(c_e, T):
            return 1 + pybamm.Interpolant(self.Electrolyte['thermodynamic'][0], self.Electrolyte['thermodynamic'][1], c_e, name='Thermodynamic_factor', interpolator='linear')

        if charge_state == 'hysteresis':
            # current sigmoid 模式：定义 lithiation/delithiation 四条 OCP 曲线
            def LFP_ocp_lithiation(sto):
                return pybamm.Interpolant(self.LFP['discharge_open_circuit_voltage'][0], self.LFP['discharge_open_circuit_voltage'][1], sto, name='Pos_OCP_lith', interpolator='linear')
            def LFP_ocp_delithiation(sto):
                return pybamm.Interpolant(self.LFP['charge_open_circuit_voltage'][0], self.LFP['charge_open_circuit_voltage'][1], sto, name='Pos_OCP_delith', interpolator='linear')
            def graphite_ocp_lithiation(sto):
                return pybamm.Interpolant(self.Gr['charge_open_circuit_voltage'][0], self.Gr['charge_open_circuit_voltage'][1], sto, name='Neg_OCP_lith', interpolator='linear')
            def graphite_ocp_delithiation(sto):
                return pybamm.Interpolant(self.Gr['discharge_open_circuit_voltage'][0], self.Gr['discharge_open_circuit_voltage'][1], sto, name='Neg_OCP_delith', interpolator='linear')
            _use_hysteresis = True
        elif charge_state == 'charge':
            def LFP_ocp_Hithium280Ah(sto):
                return pybamm.Interpolant(self.LFP['charge_open_circuit_voltage'][0], self.LFP['charge_open_circuit_voltage'][1], sto, name='Pos_OCP', interpolator='linear')

            def graphite_ocp_Hithium280Ah(sto):
                return pybamm.Interpolant(self.Gr['discharge_open_circuit_voltage'][0], self.Gr['discharge_open_circuit_voltage'][1], sto, name='Neg_OCP', interpolator='linear')
            _use_hysteresis = False
        elif charge_state == 'discharge':
            def LFP_ocp_Hithium280Ah(sto):
                return pybamm.Interpolant(self.LFP['discharge_open_circuit_voltage'][0], self.LFP['discharge_open_circuit_voltage'][1], sto, name='Pos_OCP', interpolator='linear')

            def graphite_ocp_Hithium280Ah(sto):
                return pybamm.Interpolant(self.Gr['charge_open_circuit_voltage'][0], self.Gr['charge_open_circuit_voltage'][1], sto, name='Neg_OCP', interpolator='linear')
            _use_hysteresis = False
        else:
            raise ValueError('Charge state must be "charge", "discharge" or "hysteresis"')
        
        hithium_params = {
            "Current function [A]": 0,  # 占位符：PyBaMM实验控制会自动替换此值
            "Negative electrode thickness [m]": self.default_params["Anode Thickness(um)"] * 1e-6 / 2,
            "Separator thickness [m]": self.Separator.get('thickness', 1.6e-05),
            "Positive electrode thickness [m]": self.default_params["Cathode Thickness(um)"] * 1e-6 / 2,
            "Negative particle radius [m]": self.default_params["Anode Material Dv50(um)"] * 1e-6 / 2,
            "Positive particle radius [m]": self.default_params["Cathode Material Dv50(um)"] * 1e-6 / 2,
            "Electrode height [m]": self.default_params["Cathode Length(mm)"] * 1e-3 * 2 * self.default_params.get('JR', 2) * Qx,
            "Electrode width [m]": self.default_params["Cathode Width(mm)"] * 1e-3,
            "Nominal cell capacity [A.h]": self.default_params["Nominal CAP(Ah)@0.5P"],
            "Maximum concentration in negative electrode [mol.m-3]": csmax_neg,
            "Maximum concentration in positive electrode [mol.m-3]": csmax_pos,
            "Positive electrode porosity": self.epsl_pos,
            "Positive electrode active material volume fraction": self.epss_pos,
            "Negative electrode porosity": self.epsl_neg,
            "Negative electrode active material volume fraction": self.epss_neg,
            'Separator porosity': self.Separator.get('porosity', 0.38),
            "Initial concentration in negative electrode [mol.m-3]": csmax_neg * socmin_neg,
            "Initial concentration in positive electrode [mol.m-3]": csmax_pos * socmax_pos,
            "Lower voltage cut-off [V]": 2.5,
            "Upper voltage cut-off [V]": 3.65,
            # "Open-circuit voltage at 0% SOC [V]": 2.5,
            # "Open-circuit voltage at 100% SOC [V]": 3.65,
            "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
            "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
            'Electrolyte diffusivity [m2.s-1]': electrolyte_diffusivity_Nyman2008_arrhenius,
            "Electrolyte conductivity [S.m-1]": electrolyte_conductivity,
            'Cation transference number': transfer_num,
            "Thermodynamic factor": electrolyte_thermodynamic_factor,
            "Positive electrode diffusivity [m2.s-1]": LFP_diffusivity,
            "Negative electrode diffusivity [m2.s-1]": Gr_diffusivity,
            "Positive electrode Bruggeman coefficient (electrode)": 1.5,
            "Positive electrode Bruggeman coefficient (electrolyte)": 1.5,
            "Negative electrode Bruggeman coefficient (electrolyte)": Bruggeman,
            "Negative electrode Bruggeman coefficient (electrode)": Bruggeman,
            'Separator Bruggeman coefficient (electrolyte)': 1.5,
            "Positive electrode conductivity [S.m-1]": self.LFP.get('sigma', 4),
            "Negative electrode conductivity [S.m-1]": self.Gr.get('sigma', 4),
            "Initial concentration in electrolyte [mol.m-3]": self.Electrolyte.get('c0', 900),
            "Negative electrode OCP entropic change [V.K-1]": 0,
            "Positive electrode OCP entropic change [V.K-1]": 0,
            'Contact resistance [Ohm]': R,
            'Positive electrode double-layer capacity [F.m-2]': 0,
            'Negative electrode double-layer capacity [F.m-2]': 0,
            'Ambient temperature [K]': 298.15,
            'Initial temperature [K]': 298.15,
            'Reference temperature [K]': 298.15,
            "Number of electrodes connected in parallel to make a cell": 1.0,
            "Number of cells connected in series to make a battery": 1.0,
        }
        # 根据模式设置 OCP 键
        if _use_hysteresis:
            hithium_params.update({
                "Positive electrode lithiation OCP [V]": LFP_ocp_lithiation,
                "Positive electrode delithiation OCP [V]": LFP_ocp_delithiation,
                "Negative electrode lithiation OCP [V]": graphite_ocp_lithiation,
                "Negative electrode delithiation OCP [V]": graphite_ocp_delithiation,
            })
        else:
            hithium_params.update({
                "Negative electrode OCP [V]": graphite_ocp_Hithium280Ah,
                "Positive electrode OCP [V]": LFP_ocp_Hithium280Ah,
            })
        if 'sei' in self.params:
            hithium_params.update({
                "SEI kinetic rate constant [m.s-1]": params['K_sei'],
                "EC diffusivity [m2.s-1]": params['D_K_ratio'] * params['K_sei']
            })
        if 'stripping' in self.params:
            def stripping_exchange_current_density_OKane2020(c_e, c_Li, T):
                k_stripping = params['beta'] * pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")
                E_D = 17000
                arrhenius = np.exp(E_D / pybamm.constants.R * (1 / 298.15 - 1 / T))

                return k_stripping * arrhenius

            hithium_params.update({
                "Lithium plating kinetic rate constant [m.s-1]": 6.05e-6,
                "Lithium plating transfer coefficient": 0.5,
                "Exchange-current density for stripping [A.m-2]": stripping_exchange_current_density_OKane2020,
            })
        if 'partially reversible' in self.params:
            def stripping_exchange_current_density_OKane2020(c_e, c_Li, T):
                k_stripping = params['beta'] * pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")

                return k_stripping * c_Li

            def plating_exchange_current_density_OKane2020(c_e, c_Li, T):
                k_plating = pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")
                return k_plating * c_e

            hithium_params.update({
                "Lithium plating kinetic rate constant [m.s-1]": 6.05e-6,
                "Lithium plating transfer coefficient": 0.5,
                "Exchange-current density for stripping [A.m-2]": stripping_exchange_current_density_OKane2020,
                "Exchange-current density for plating [A.m-2]": plating_exchange_current_density_OKane2020,
            })
        if 'MPM' in self.params:  # 多粒径分布参数
            def f_a_dist_p_dim(R):  # 正极粒径分布
                return (0.35 * pybamm.lognormal(R, 2.0e-07, 0.30 * 2.0e-07) +
                        0.65 * pybamm.lognormal(R, 7.9e-6, 0.63 * 7.9e-6))

            def f_a_dist_n_dim(R):  # 负极粒径分布
                return pybamm.lognormal(R, 1.26e-5 / 2, 0.5 * 1.26e-5 / 2)

            hithium_params.update({
                "Negative minimum particle radius [m]": 0,
                "Positive minimum particle radius [m]": 0,
                "Negative maximum particle radius [m]": 31.1e-6 / 2,
                "Positive maximum particle radius [m]": 1.0e-6,
                "Negative area-weighted " + "particle-size distribution [m-1]": f_a_dist_n_dim,
                "Positive area-weighted " + "particle-size distribution [m-1]": f_a_dist_p_dim
            })
        if 'thermal' in self.params:
            def LFP_entropic(sto):
                du_dT = (-0.00 + 0.00 * sto ** 1 + -0.05 * sto ** 2 + 0.29 * sto ** 3 + -0.99 * (
                    sto) ** 4 + 1.96 * (
                             sto) ** 5 + -2.26 * sto ** 6 + 1.39 * sto ** 7 + -0.35 * sto ** 8)
                return du_dT / 5

            def Gr_entropic(sto):
                du_dT = (
                        0.00 + -0.00 * sto ** 1 + -0.12 * sto ** 2 + 1.93 * sto ** 3 + -12.48 * sto ** 4 + 44.21 * sto ** 5 + -94.31 * sto ** 6 + 124.42 * sto ** 7 + -99.50 * sto ** 8 + 44.26 * sto ** 9 + -8.41 * sto ** 10)
                return du_dT / 5

            hx, hy, hz = 0.2746, 0.07305, 0.2128
            hithium_params.update(
                {
                    "Cell volume [m3]": hx * hy * hz,
                    "Total heat transfer coefficient [W.m-2.K-1]": 50,
                    "Cell cooling surface area [m2]": 2 * (hx * hy + hx * hz + hy * hz),
                    "Negative electrode specific heat capacity [J.kg-1.K-1]": 1185.75,
                    "Negative electrode thermal conductivity [W.m-1.K-1]": 1.17,
                    "Positive electrode specific heat capacity [J.kg-1.K-1]": 924.0,
                    "Positive electrode thermal conductivity [W.m-1.K-1]": 1.79,
                    "Separator specific heat capacity [J.kg-1.K-1]": 500.0,
                    "Separator thermal conductivity [W.m-1.K-1]": 0.16,
                    "Contact resistance [Ohm]": 6e-5,
                    'Negative electrode OCP entropic change [V.K-1]': Gr_entropic,
                    'Positive electrode OCP entropic change [V.K-1]': LFP_entropic,
                    "Initial temperature [K]": 299.15,
                    "Casing heat capacity [J.K-1]": 30,
                    "Environment thermal resistance [K.W-1]": 10,
                }
            )
        return hithium_params

    def _convert_battery_design(self, battery_design):
        def get_numeric_param(battery_design, key, default):
            val = battery_design.get(key, default)
            if not isinstance(val, (int, float)):
                raise ValueError(f"Parameter '{key}' must be a numeric value.")
            return float(val)

        """转换电池设计参数"""
        full_anode_thickness = get_numeric_param(battery_design, 'anodeThickness', 10.1e-05 / 1e-6)
        full_cathode_thickness = get_numeric_param(battery_design, 'cathodeThickness', 13.5e-05 / 1e-6)
        anode_foil_thickness = get_numeric_param(battery_design, 'anodeCuFoilThickness', 6)
        cathode_foil_thickness = get_numeric_param(battery_design, 'cathodeAlFoilThickness', 13)
        anode_rebound = get_numeric_param(battery_design, 'anodeThicknessRebound', 0)
        cathode_rebound = get_numeric_param(battery_design, 'cathodeThicknessRebound', 0)
        anode_thickness = full_anode_thickness * (1 + anode_rebound) - anode_foil_thickness
        cathode_thickness = full_cathode_thickness * (1 + cathode_rebound) - cathode_foil_thickness

        converted_battery_params = {
            "Anode Material Real Density(g/cm^3)": get_numeric_param(battery_design, 'anodeRealDensity', 2.2279),
            "Cathode Material Real Density(g/cm^3)": get_numeric_param(battery_design, 'cathodeRealDensity', 3.488),
            "Anode Spec.Cap(mAh/g)": get_numeric_param(battery_design, 'anodeGramSpecCap', 350),
            "Cathode Spec.Cap(mAh/g)": get_numeric_param(battery_design, 'cathodeGramSpecCap', 144),
            "Anode Loading": get_numeric_param(battery_design, 'anodeLoading', 0.967),
            "Cathode Loading": get_numeric_param(battery_design, 'cathodeLoading', 0.967),
            "Anode PD(g/cm^3)": get_numeric_param(battery_design, 'anodePD', 1.55),
            "Cathode PD(g/cm^3)": get_numeric_param(battery_design, 'cathodePD', 2.45),
            "Anode CW(g/1540.25m2)": get_numeric_param(battery_design, 'anodeCWCoating', 0.152),
            "Cathode CW(g/1540.25m2)": get_numeric_param(battery_design, 'cathodeCWCoating', 0.328),
            "Anode Thickness(um)": anode_thickness,
            "Cathode Thickness(um)": cathode_thickness,
            "Cathode Length(mm)": get_numeric_param(battery_design, 'cathodeLength', 17.06216 / 1e-3),
            "Cathode Width(mm)": get_numeric_param(battery_design, 'cathodeWidth', 0.1875 / 1e-3),
            "Anode Length(mm)": get_numeric_param(battery_design, 'anodeLength', 17.06216 / 1e-3 * 1.036),
            "Anode Width(mm)": get_numeric_param(battery_design, 'anodeWidth', 0.1875 / 1e-3),
            "Nominal CAP(Ah)@0.5P": int(battery_design.get('designNominalCap', 280)),
            "CB": get_numeric_param(battery_design, 'designCb', 1.126),
        }
        return converted_battery_params
    
def get_parameter_values():
    battery = BatteryDirect(battery_design, model_params, LFP, Gr, Electrolyte, Separator)
    return battery.get_params('charge', params)
