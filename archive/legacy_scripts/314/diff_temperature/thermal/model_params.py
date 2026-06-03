import pybamm
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

sigma = pd.read_csv(r'D:\Users\hez\Desktop\hithium\diff_temperature\params\E_sigma.csv', header=None)
Ds = pd.read_csv(r'D:\Users\hez\Desktop\hithium\diff_temperature\params\E_DL_int1.csv', header=None)
transNum = pd.read_csv(r'D:\Users\hez\Desktop\hithium\diff_temperature\params\E_transpNm.csv', header=None)
LFP = pd.read_csv(r'D:\Users\hez\Desktop\hithium\diff_temperature\params\LFP.csv', header=None)
Gr_charge = pd.read_csv(r'D:\Users\hez\Desktop\hithium\diff_temperature\params\Gr_discharge.csv', header=None)
Gr_discharge = pd.read_csv(r'D:\Users\hez\Desktop\hithium\diff_temperature\params\Gr_charge.csv', header=None)

LFP_func = interp1d(LFP[0], LFP[1], fill_value='extrapolate')
Gr_charge_func = interp1d(Gr_charge[0], Gr_charge[1], fill_value='extrapolate')
Gr_discharge_func = interp1d(Gr_discharge[0], Gr_discharge[1], fill_value='extrapolate')

before_soc = np.linspace(0, 0.66, 500)
after_soc = np.linspace(0.66, 1, 500)
before_Gr = Gr_charge_func(before_soc)
after_Gr = Gr_charge_func(after_soc)
after_soc = after_soc + (after_soc - 0.66) / 0.34 * 0.1
Gr_soc = np.concatenate([before_soc, after_soc])
Gr_value = np.concatenate([before_Gr, after_Gr])
Gr_charge_func = interp1d(Gr_soc / 1.1, Gr_value, fill_value='extrapolate')

# soc = np.linspace(0, 1, 500)
soc = np.linspace(0, 1, 500)
LFP = LFP_func(soc)
Gr_charge = Gr_charge_func(soc)
Gr_discharge = Gr_discharge_func(soc)

Ds_x = Ds[0].to_numpy()
Ds_y = Ds[1].to_numpy()
sigma_x = sigma[0].to_numpy()
sigma_y = sigma[1].to_numpy()
transNum_x = transNum[0].to_numpy()
transNum_y = transNum[1].to_numpy()

F = 96485.33212
CB = 1.126
rho_neg = 2.2279
rho_pos = 3.488
c_max_pos = rho_pos * 0.972 * 1e6 * 144 / 1000 * 3600 / F
c_max_neg = rho_neg * 0.967 * 1e6 * 340 / 1000 * 3600 / F * 1.036
epss_neg = 1.55 / rho_neg
epss_pos = 2.45 / rho_pos
epsl_neg = 1 - epss_neg / 0.967
epsl_pos = 1 - epss_pos / 0.972
ah_neg = c_max_neg * 10.1e-05 * 0.1875 * 17.06216 * F * epss_neg * 2 / 3600
ah_pos = c_max_pos * 13.5e-05 * 0.1875 * 17.06216 * F * epss_pos * 2 / 3600

K_LFP_func_x = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1])
K_LFP_func_y = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
K_Gr_func_x = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1])
K_Gr_func_y = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

# D_LFP_func_x = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1])
# D_LFP_func_y = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
D_LFP_func_x = np.array([0., 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                         0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.])
D_LFP_func_y = np.array([0.88919258, 1.06041215, 1.09296689, 1.0909677, 1.07379678,
                         1.04048572, 1.03638599, 1.1021048, 1.11036805, 1.09269533,
                         1.06940283, 1.04281708, 1.03288313, 1.02650979, 1.01672362,
                         1.00656133, 0.99831895, 1.03691014, 1.03402531, 0.91502884,
                         0.74564028])
# D_Gr_func_x = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1])
# D_Gr_func_y = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
D_Gr_func_x = np.array([0., 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                        0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.])
D_Gr_func_y = np.array([0.94283397, 1.02816909, 1.14378027, 1.08151869, 0.92259547,
                        0.86260705, 0.84345644, 0.8685853, 0.94009384, 1.03057526,
                        1.11412581, 1.06846954, 0.8839978, 0.76997053, 0.78111289,
                        0.86336662, 1.03226405, 1.1790598, 1.22087785, 1.17218599,
                        0.9977045])

hithium_param = [-15.29962874, -13.97469413, -8.98506223, -9.47395851]
input_params = {}
key_list = ['Dpos', 'Dneg', 'Kneg', 'Kpos']
for i, key in enumerate(key_list):
    input_params[key] = np.power(10, hithium_param[i])
Qx = 0.98
ocv_params = {'socmin_neg': 0.00407, 'socmax_pos': 0.9652, 'csmax_neg': 0.91856367 * Qx, 'csmax_pos': 1.06197408 * Qx}

Gr_discharge_popt = np.array([1.13640119e+03, 3.68112040e-01, 4.85800303e+02, 1.13633267e+03,
                              2.21352300e+01, - 1.85105195e-01, 4.35903311e-02, 1.15394165e+01,
                              1.68226566e-01, 1.64331269e-02, 2.03680387e+01, 5.62719748e-01,
                              7.10705992e-02, 1.87747157e+01, 9.94782741e-01])
Gr_charge_popt = np.array([1.84251988e-01, 5.91077564e-01, 1.46587633e+02, 1.44840519e-01,
                           3.76883491e+01, 3.35414231e-02, 4.77511427e-02, 9.25532845e+00,
                           1.91882172e-01, 1.93918703e-02, 2.38252679e+01, 5.81654795e-01,
                           1.22464212e-01, 1.96805420e+01, 1.01690171e+00])
LFP_popt = np.array([1.18571751e+02, 9.03316045e+02, 3.42720199e+00, 1.36718042e-03,
                     6.18773530e-01, 1.51355706e+00, - 8.45688688e+02])


def Gr_curve_func(sto, params):
    a = params[0]
    b = params[1]
    result = a + b * np.exp(-params[2] * sto)
    terms = params[3:]
    for i in range(1, len(terms) // 3 + 1):
        result += - terms[3 * i - 3] * np.tanh((sto - terms[3 * i - 1]) * terms[3 * i - 2])
    return result


def LFP_curve_func(sto, params):
    c1 = -params[0] * sto
    c2 = -params[1] * (1 - sto) - params[6] * (1 - sto)
    k = params[2] - params[3] * sto + params[4] * np.exp(c1) - params[5] * np.exp(c2)
    return k


def get_model(model_type):
    if model_type == 'base':
        model = pybamm.lithium_ion.DFN(
            {
                "contact resistance": 'true',  # 需要打开contact resistance才可以加入接触电阻
            }
        )
    elif model_type == 'aging':
        model = pybamm.lithium_ion.DFN(
            {
                "SEI": "solvent-diffusion limited",
                "SEI porosity change": "true",
                "lithium plating": "partially reversible",
                "lithium plating porosity change": "true",  # alias for "SEI porosity change"
                "particle mechanics": ("swelling and cracking", "swelling only"),
                "SEI on cracks": "true",
                "loss of active material": "stress-driven",
                "calculate discharge energy": "true",  # for compatibility with older PyBaMM versions
                "contact resistance": "true",
            }
        )
    else:
        raise ValueError('Model type not recognized')
    return model


def get_param(charge_state, params):
    def LFP_diffusivity(sto, T):
        D_ref = params['Dpos']
        E_D_s = 3.03e4
        # D_revise = pybamm.Interpolant(D_LFP_func_x, D_LFP_func_y, sto, name='D_pos', interpolator="cubic")
        arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
        D_revise = 1
        return D_revise * D_ref * arrhenius

    def Gr_diffusivity(sto, T):
        D_ref = params['Dneg']
        E_D_s = 3.03e4
        # D_revise = pybamm.Interpolant(D_Gr_func_x, D_Gr_func_y, sto, name='D_neg', interpolator="cubic")
        D_revise = 1
        # D_revise = D_ref
        # E_D_s not given by Chen et al (2020), so taken from Ecker et al. (2015) instead
        arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
        # arrhenius = 1
        return D_revise * D_ref * arrhenius

    def graphite_exchange_current_density(c_e, c_s_surf, c_s_max, T):
        sto = c_s_surf / c_s_max
        c_l_ref = 1e3
        m_ref = params['Kneg']  # (A/m2)(m3/mol)**1.5 - includes ref concentrations
        E_r = 35000
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
        # arrhenius = 1
        # K_revise = pybamm.Interpolant(K_Gr_func_x, K_Gr_func_y, sto, name='Neg_i0', interpolator="cubic")
        K_revise = 1
        return m_ref * arrhenius * (c_e / c_l_ref) ** 0.5 * c_s_surf ** 0.5 * (c_s_max - c_s_surf) ** 0.5 * K_revise * F

    def LFP_exchange_current_density(c_e, c_s_surf, c_s_max, T):
        sto = c_s_surf / c_s_max
        c_l_ref = 1e3
        m_ref = params['Kpos']  # (A/m2)(m3/mol)**1.5 - includes ref concentrations
        E_r = 35000
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
        # arrhenius = 1
        # K_revise = pybamm.Interpolant(K_LFP_func_x, K_LFP_func_y, sto, name='Pos_i0', interpolator="cubic")
        K_revise = 1
        return m_ref * arrhenius * (c_e / c_l_ref) ** 0.5 * c_s_surf ** 0.5 * (c_s_max - c_s_surf) ** 0.5 * K_revise * F

    # def f_a_dist_p_dim(R):
    #     Y1 = lognorm(s=0.30225683, scale=np.power(10, -6.37331887))
    #     Y2 = lognorm(s=0.69177807, scale=np.power(10, -5.8))
    #     Y = 0.337 * Y1.pdf(R) + 0.663 * Y2.pdf(R)
    #     return Y / R
    def f_a_dist_p_dim(R):
        return 0.663 * pybamm.lognormal(R, 4.233e-07, 0.31148143 * 4.233e-07) + 0.337 * pybamm.lognormal(R, 1.584e-6,
                                                                                                         0.69177807 * 1.584e-6)

    # def f_a_dist_n_dim(R):
    #     Y = 1 / 1.025 * lognorm(s=4.981e-01, scale=np.power(10, -4.899e+00)).pdf(R)
    #     return Y / R
    def f_a_dist_n_dim(R):
        return pybamm.lognormal(R, 1.26e-5, 4.981e-01 * 1.26e-5)

    # def transfer_num(c_e, T):
    #     return pybamm.Interpolant(transNum_x, transNum_y, c_e, name='Trans_num', interpolator='cubic')
    #
    # def electrolyte_conductivity(c_e, T):
    #     return pybamm.Interpolant(sigma_x, sigma_y, c_e, name='Sigma_ele', interpolator='cubic')
    #
    # def electrolyte_diffusivity(c_e, T):
    #     return pybamm.Interpolant(Ds_x, Ds_y, c_e, name='D_ele', interpolator='cubic')

    if charge_state == 'charge':
        def LFP_ocp_Hithium280Ah(sto):
            return pybamm.Interpolant(soc, LFP, sto, name='Pos_OCP', interpolator='cubic')

        def graphite_ocp_Hithium280Ah(sto):
            return pybamm.Interpolant(soc, Gr_charge, sto, name='Neg_OCP', interpolator='cubic')

    elif charge_state == 'discharge':
        def LFP_ocp_Hithium280Ah(sto):
            return pybamm.Interpolant(soc, LFP, sto, name='Pos_OCP', interpolator='cubic')

        def graphite_ocp_Hithium280Ah(sto):
            return pybamm.Interpolant(soc, Gr_discharge, sto, name='Neg_OCP', interpolator='cubic')

    else:
        raise ValueError('Charge state must be "charge" or "discharge"')

    def electrolyte_diffusivity_Nyman2008_arrhenius(c_e, T):
        D_c_e = 8.794e-11 * (c_e / 1000) ** 2 - 3.972e-10 * (c_e / 1000) + 4.862e-10

        # Nyman et al. (2008) does not provide temperature dependence
        # So use temperature dependence from Ecker et al. (2015) instead

        E_D_c_e = 17000
        arrhenius = np.exp(E_D_c_e / pybamm.constants.R * (1 / 298.15 - 1 / T))

        return 2 * D_c_e * arrhenius

    hithium_params = {
        # cell
        "Negative electrode thickness [m]": 10.1e-05 / 2,
        "Separator thickness [m]": 1.6e-05,
        "Positive electrode thickness [m]": 13.5e-05 / 2,
        "Negative particle radius [m]": 1.45e-5,
        "Positive particle radius [m]": 9.78e-7,
        "Electrode height [m]": 17.06216 * 2,
        "Electrode width [m]": 0.1875,
        "Nominal cell capacity [A.h]": 280,
        "Number of electrodes connected in parallel to make a cell": 2.0,
        "Maximum concentration in negative electrode [mol.m-3]": c_max_neg * params['csmax_neg'] * params['Qx'],
        "Maximum concentration in positive electrode [mol.m-3]": c_max_pos * params['csmax_pos'] * params['Qx'],
        "Positive electrode porosity": epsl_pos,
        "Positive electrode active material volume fraction": epss_pos,
        "Negative electrode porosity": epsl_neg,
        "Negative electrode active material volume fraction": epss_neg,
        'Separator porosity': 0.42,
        "Initial concentration in negative electrode [mol.m-3]": c_max_neg * params['csmax_neg'] * params[
            'socmin_neg'] * params['Qx'],
        "Initial concentration in positive electrode [mol.m-3]": c_max_pos * params['csmax_pos'] * params[
            'socmax_pos'] * params['Qx'],
        "Lower voltage cut-off [V]": 2.5,
        "Upper voltage cut-off [V]": 3.65,
        "Open-circuit voltage at 0% SOC [V]": 2.5,
        "Open-circuit voltage at 100% SOC [V]": 3.65,
        # "Open-circuit voltage at 0% SOC [V]": 2.5,
        # "Open-circuit voltage at 100% SOC [V]": 3.65,
        "Negative electrode exchange-current density [A.m-2]"
        "": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]"
        "": LFP_exchange_current_density,
        'Electrolyte diffusivity [m2.s-1]': electrolyte_diffusivity_Nyman2008_arrhenius,
        # "Electrolyte conductivity [S.m-1]": electrolyte_conductivity,
        # "Positive electrode diffusivity [m2.s-1]": 1.2e-16,
        # "Negative electrode diffusivity [m2.s-1]": 1.06e-14,
        "Positive electrode diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative electrode diffusivity [m2.s-1]": Gr_diffusivity,
        "Positive electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrolyte)": params['Bruggeman'],
        "Negative electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode conductivity [S.m-1]": 100,
        "Negative electrode conductivity [S.m-1]": 4.453,
        "Initial concentration in electrolyte [mol.m-3]": 900.0,
        "Negative electrode OCP [V]": graphite_ocp_Hithium280Ah,
        "Positive electrode OCP [V]": LFP_ocp_Hithium280Ah,
        # 'Cation transference number': transfer_num,
        'Contact resistance [Ohm]': params['R'],
        'Positive electrode double-layer capacity [F.m-2]': 0,
        'Negative electrode double-layer capacity [F.m-2]': 0,
        "Negative minimum particle radius [m]": 0,
        "Positive minimum particle radius [m]": 0,
        "Negative maximum particle radius [m]": 31.1e-6,
        "Positive maximum particle radius [m]": 4.12e-6,
        "Negative area-weighted " + "particle-size distribution [m-1]": f_a_dist_n_dim,
        "Positive area-weighted " + "particle-size distribution [m-1]": f_a_dist_p_dim,
    }
    return hithium_params


def get_exp(Prate=280 * 3.2, period=0.5, idle_time=10, condition_type=0, rate=0.5, idle_days=None, cycle_num=1):
    if condition_type == 0:
        # 放电工况
        discharge_cycle_exp = pybamm.Experiment(
            [("Discharge at %dW until 2.5 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time))])
        # 充电工况
        charge_cycle_exp = pybamm.Experiment(
            [("Charge at %dW until 3.65 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time))])
        cycle_exp = pybamm.Experiment(
            [("Charge at %dW until 3.65 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time),
              "Discharge at %dW until 2.5 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time))] * cycle_num)
        ref_exp = pybamm.Experiment(
            [("Charge at %dW until 3.65 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time),
              "Discharge at %dW until 2.5 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time))]
        )
        return {'charge': charge_cycle_exp, 'discharge': discharge_cycle_exp, 'cycle': cycle_exp, 'ref': ref_exp}
    elif condition_type == 1:
        charge_cycle_exp = pybamm.Experiment(
            [
                ("Charge at %fW for 22 minutes or until 3.65V (%f minute period)" % (0.5 * Prate, period),
                 "Charge at %fW for 2 minutes or until 3.65V (%f minute period)" % (0.75 * Prate, 0.1 * period),
                 "Charge at %fW for 30 minutes or until 3.65V (%f minute period)" % (0.5 * Prate, period)) * 12 +
                ("Charge at %fW until 3.65V (%f minute period)" % (0.5 * Prate, period),
                 "Rest for %d minute (0.1 minute period)" % 30)
            ]
        )
        discharge_cycle_exp = pybamm.Experiment(
            [
                ("Discharge at %fW for 1 minutes or until 2.5 V (%f minute period)" % (0.75 * Prate, 0.1 * period),
                 "Discharge at %fW for 20 minutes or until 2.5 V (%f minute period)" % (0.5 * Prate, period)) * 3 +
                # ageing cycles
                ("Discharge at %fW until 2.5 V (%.1f minute period)" % (0.5 * Prate, period),
                 "Rest for %d minute (0.1 minute period)" % 30)
            ]
        )
    elif condition_type == 2:
        charge_cycle_exp = pybamm.Experiment(
            [
                ("Charge at %fW for 17 minutes or until 3.65V (%f minute period)" % (0.5 * Prate, period),
                 "Charge at %fW for 1 minutes or until 3.65V (%f minute period)" % (0.6 * Prate, 0.05 * period),
                 "Charge at %fW for 5 minutes or until 3.65V (%f minute period)" % (0.5 * Prate, period)) * 12 +
                ("Charge at %fW until 3.65V (%f minute period)" % (0.5 * Prate, period),
                 "Rest for %d minute (0.1 minute period)" % 30)
            ]

        )
        discharge_cycle_exp = pybamm.Experiment(
            [
                ("Discharge at %fW until 2.5 V (%f minute period)" % (0.6 * Prate, period),  # ageing cycles
                 "Rest for %d minute (0.1 minute period)" % 30)
            ]
        )
    elif condition_type == 3:
        discharge_cycle_exp = pybamm.Experiment(
            [("Discharge at %dW until 2.5 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time))])
        # 充电工况
        charge_cycle_exp = pybamm.Experiment(
            [("Charge at %dW until 3.65 V (%.1f minute period)" % (rate * Prate, period),
              "Rest for %d minute (0.1 minute period)" % (idle_time))])
        idle_day_array = np.arange(idle_days['start'], idle_days['end'], idle_days['step'])
        idle_step = idle_days['step']
        idle_exp = {}
        before_idle_day = 0
        for idle_day in idle_day_array:
            idle_minute = (idle_day - before_idle_day) * 24 * 60
            before_idle_day = idle_day
            one_idle_exp = pybamm.Experiment(
                [
                    "Rest for %d minute (0.5 minute period)" % (idle_time),
                    "Rest for %d minute (1440 minute period)" % (idle_minute - idle_time),
                ]
            )
            idle_exp[idle_day] = one_idle_exp
        return {'charge': charge_cycle_exp, 'discharge': discharge_cycle_exp, "idle": idle_exp}
    else:
        raise ValueError('Condition must be None or 1 or 2')
    return {'charge': charge_cycle_exp, 'discharge': discharge_cycle_exp}
