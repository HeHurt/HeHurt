"""BatteryProject 配置与常量。"""
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import pybamm
from scipy.interpolate import interp1d

logger = logging.getLogger(__name__)


# === 项目路径 ===
PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"
PARAMS_DIR = WORKSPACE_DIR / "params"

# === 绘图默认配置 ===
DEFAULT_PLOT_STYLE = "science"
DEFAULT_FONT_SANS_SERIF = ["Microsoft YaHei", "SimHei", "Calibri", "DejaVu Sans"]

# === 熵系数数据 ===
ENTROPY_FILE = DATA_DIR / "entropy_coeffs.xlsx"
TARGET_PTS = 1000

# 延迟加载的熵系数数组
DUDT_CHG = None
DUDT_DCHG = None


def load_entropy(entropy_file=None, target_pts=TARGET_PTS):
    """加载熵系数，返回 (dudt_chg, dudt_dchg)。"""
    global DUDT_CHG, DUDT_DCHG
    file = Path(entropy_file) if entropy_file else ENTROPY_FILE
    try:
        df = pd.read_excel(file, header=None)
        DUDT_CHG = df.iloc[:target_pts, 0].values
        DUDT_DCHG = df.iloc[:target_pts, 1].values
    except Exception as primary_exc:
        logger.warning(
            "Failed to load entropy table from %s (%s); falling back to LFP-graphite analytic.",
            file, primary_exc,
        )
        try:
            sto = np.linspace(0, 1, target_pts)
            dudt_fallback = LFP_entropic(sto) - graphite_entropic(sto)
            DUDT_CHG = dudt_fallback
            DUDT_DCHG = dudt_fallback
        except Exception as fallback_exc:
            logger.error(
                "Entropy fallback also failed (%s); defaulting to zeros — reversible heat term will be wrong.",
                fallback_exc,
            )
            DUDT_CHG = np.zeros(target_pts)
            DUDT_DCHG = np.zeros(target_pts)
    return DUDT_CHG, DUDT_DCHG


def ensure_entropy_loaded():
    if DUDT_CHG is None or DUDT_DCHG is None:
        load_entropy()


# === 实验默认参数 ===
RATES = [0.125, 0.25, 0.5]
TEMPERATURES = [298.15, 318.15]
ACCELERATION_FACTOR = 50
NOMINAL_CAPACITY = 1175
DATA_FILE = DATA_DIR / "循环数据-20260106.xlsx"


# === 材料参数 ===
F = 96485.33212

# 延迟加载的材料参数（首次调用 OCP 函数时触发）
_soc_grid = None
_LFP_interp = None
_Gr_charge_interp = None
_Gr_discharge_interp = None
_material_params_loaded = False


def _ensure_material_params_loaded():
    """延迟加载材料参数 CSV 文件，仅在首次调用时读取。"""
    global _soc_grid, _LFP_interp, _Gr_charge_interp, _Gr_discharge_interp
    global _material_params_loaded
    if _material_params_loaded:
        return
    _soc_grid = np.linspace(0, 1, 500)
    try:
        LFP_df = pd.read_csv(PARAMS_DIR / "LFP.csv", header=None)
        Gr_charge_df = pd.read_csv(PARAMS_DIR / "Gr_charge.csv", header=None)
        Gr_discharge_df = pd.read_csv(PARAMS_DIR / "Gr_discharge.csv", header=None)

        _LFP_interp = interp1d(LFP_df[0], LFP_df[1], fill_value="extrapolate")(_soc_grid)
        _Gr_charge_interp = interp1d(Gr_charge_df[0], Gr_charge_df[1], fill_value="extrapolate")(_soc_grid)
        _Gr_discharge_interp = interp1d(Gr_discharge_df[0], Gr_discharge_df[1], fill_value="extrapolate")(_soc_grid)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"材料参数 CSV 未找到，请确认 {PARAMS_DIR} 目录存在并包含 LFP.csv 等文件: {e}"
        ) from e
    _material_params_loaded = True


def electrolyte_diffusivity_Nyman2008_arrhenius(c_e, T):
    p = [5.55347004e-20, -2.75740663e-16, 2.48896764e-13, 3.50298875e-10]
    D_c_e = p[0] * 1000 ** 3 + p[1] * 1000 ** 2 + p[2] * 1000 + p[3]
    # 注：E_D_c_e 保留为占位，待有实验活化能数据后启用
    E_D_c_e = 0
    if E_D_c_e != 0:
        arrhenius = np.exp(E_D_c_e / pybamm.constants.R * (1 / 298.15 - 1 / T))
        return D_c_e * arrhenius
    return D_c_e


def electrolyte_conductivity(c_e, T):
    sigma_e = 0.1297 * (c_e / 1000) ** 3 - 2.51 * (c_e / 1000) ** 1.5 + 3.329 * (c_e / 1000)
    # 注：E_sigma_e 保留为占位，待有实验活化能数据后启用
    E_sigma_e = 0
    if E_sigma_e != 0:
        arrhenius = np.exp(E_sigma_e / pybamm.constants.R * (1 / 298.15 - 1 / T))
        return sigma_e * arrhenius
    return sigma_e


def LFP_ocp_charge(sto):
    _ensure_material_params_loaded()
    return pybamm.Interpolant(_soc_grid, _LFP_interp + 0.02, sto, name="Pos_OCP", interpolator="cubic")


def LFP_ocp_discharge(sto):
    _ensure_material_params_loaded()
    return pybamm.Interpolant(_soc_grid, _LFP_interp - 0.03, sto, name="Pos_OCP", interpolator="cubic")


def graphite_ocp_charge(sto):
    _ensure_material_params_loaded()
    return pybamm.Interpolant(_soc_grid, _Gr_charge_interp, sto, name="Neg_OCP", interpolator="cubic")


def graphite_ocp_discharge(sto):
    _ensure_material_params_loaded()
    return pybamm.Interpolant(_soc_grid, _Gr_discharge_interp, sto, name="Neg_OCP", interpolator="cubic")


# 向后兼容别名：与 LFP_ocp_charge / graphite_ocp_charge 行为一致
LFP_ocp_Hithium280Ah = LFP_ocp_charge
graphite_ocp_Hithium280Ah = graphite_ocp_charge


def LFP_entropic(sto):
    du_dt = (
        -1.39262467e-01 * (sto ** 8)
        + 6.02393209e-01 * (sto ** 7)
        - 1.07457345e00 * (sto ** 6)
        + 1.02239130e00 * (sto ** 5)
        - 5.59871056e-01 * (sto ** 4)
        + 1.76951351e-01 * (sto ** 3)
        - 3.02491476e-02 * (sto ** 2)
        + 2.11209531e-03 * (sto ** 1)
        + 8.62182125e-06
    )
    return du_dt


def graphite_entropic(sto):
    du_dt = (
        2.29827815e01 * (sto ** 9)
        - 9.60265948e01 * (sto ** 8)
        + 1.66281204e02 * (sto ** 7)
        - 1.54174573e02 * (sto ** 6)
        + 8.24040908e01 * (sto ** 5)
        - 2.53676448e01 * (sto ** 4)
        + 4.20323260e00 * (sto ** 3)
        - 3.03662776e-01 * (sto ** 2)
        + 4.46024654e-04 * (sto ** 1)
        + 6.00000000e-04
    )
    return du_dt


def plating_exchange_current_density_OKane2020(c_e, c_Li, T):
    E_plating = 11178
    arrhenius = np.exp(E_plating / pybamm.constants.R * (1 / 298.15 - 1 / T))
    k_plating = pybamm.Parameter("Lithium plating kinetic rate constant [m.s-1]")
    return k_plating * arrhenius


def get_hithium_params(t_factor=1, temperature=298.15):
    """生成 Hithium 参数字典（供 pybamm.ParameterValues.update 使用）。

    参数
    ----
    t_factor : float
        老化加速因子，按比例放大 SEI/析锂/裂纹/LAM 等速率常数。
    temperature : float
        目标环境温度 (K)。同时用于：
        - 选择低温/高温活化能分段（E_D_s、E_r、k_sei、D_sei）；
        - 设置返回字典中的 "Ambient temperature [K]"。
        注意 pybamm.Experiment(temperature=...) 仍会覆盖 ambient。
    """
    def LFP_diffusivity(sto, T):
        D_ref = 2.4e-16
        E_D_s = 45000 if temperature < 298 else 20000
        arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
        return D_ref * arrhenius

    def Gr_diffusivity(sto, T):
        D_ref = 1.06e-14
        E_D_s = 50000 if temperature < 298 else 20000
        arrhenius = np.exp(E_D_s / pybamm.constants.R * (1 / 298.15 - 1 / T))
        return D_ref * arrhenius

    def graphite_exchange_current_density(c_e, c_s_surf, c_s_max, T):
        c_l_ref = 1e3
        m_ref = 1.2121e-9
        E_r = 60000 if temperature < 298 else 20000
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
        K_revise = 1
        return m_ref * arrhenius * (c_e / c_l_ref) ** 0.5 * c_s_surf ** 0.5 * (c_s_max - c_s_surf) ** 0.5 * K_revise * F

    def LFP_exchange_current_density(c_e, c_s_surf, c_s_max, T):
        c_l_ref = 1e3
        m_ref = 1.1131e-10
        E_r = 35000 if temperature < 298 else 20000
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
        K_revise = 1
        return m_ref * arrhenius * (c_e / c_l_ref) ** 0.5 * c_s_surf ** 0.5 * (c_s_max - c_s_surf) ** 0.5 * K_revise * F

    def cracking_rate_Ai2020(T):
        k_cr = 2.1939307272313407e-21 * t_factor
        Eac_cr = 10000
        arrhenius = np.exp(Eac_cr / pybamm.constants.R * (1 / 298.15 - 1 / T))
        return k_cr * arrhenius

    def LAM_rate(T=temperature):
        k_lam_neg = 1.0882895732868533e-7 * t_factor
        E_r = 60000
        arrhenius = np.exp(E_r / pybamm.constants.R * (1 / 298.15 - 1 / T))
        return k_lam_neg * arrhenius

    if temperature < 298.15:
        k_sei = 0.001
        D_sei = 3
    else:
        k_sei = 0.1
        D_sei = 1.2 * 1.8

    hithium_params = {
        "Negative electrode thickness [m]": 6.525e-05,
        "Separator thickness [m]": 1.1e-05,
        "Positive electrode thickness [m]": 8.3e-05 * 1.01,
        "Negative particle radius [m]": 5.755e-6,
        "Positive particle radius [m]": 6.31e-7,
        "Electrode height [m]": 14.56682 * 2,
        "Electrode width [m]": 0.1875,
        "Nominal cell capacity [A.h]": 314,
        "Number of electrodes connected in parallel to make a cell": 2.0,
        "Maximum concentration in negative electrode [mol.m-3]": 29094,
        "Maximum concentration in positive electrode [mol.m-3]": 20042,
        "Positive electrode porosity": 0.25895,
        "Positive electrode active material volume fraction": 0.72846,
        "Negative electrode porosity": 0.34317,
        "Negative electrode active material volume fraction": 0.63515,
        "Separator porosity": 0.38,
        "Initial concentration in negative electrode [mol.m-3]": 396.87,
        "Initial concentration in positive electrode [mol.m-3]": 19000,
        "Initial concentration in electrolyte [mol.m-3]": 1000.0,
        "Lower voltage cut-off [V]": 2.5,
        "Upper voltage cut-off [V]": 3.65,
        "Open-circuit voltage at 0% SOC [V]": 2.5,
        "Open-circuit voltage at 100% SOC [V]": 3.65,
        "Negative electrode exchange-current density [A.m-2]": graphite_exchange_current_density,
        "Positive electrode exchange-current density [A.m-2]": LFP_exchange_current_density,
        "Positive particle diffusivity [m2.s-1]": LFP_diffusivity,
        "Negative particle diffusivity [m2.s-1]": Gr_diffusivity,
        "Electrolyte diffusivity [m2.s-1]": electrolyte_diffusivity_Nyman2008_arrhenius,
        "Electrolyte conductivity [S.m-1]": electrolyte_conductivity,
        "Total heat transfer coefficient [W.m-2.K-1]": 30,
        # 注：PyBaMM 不读取 "Effective volumetric heat capacity"（它由各组分
        # density × specific heat 计算得到），原 1040 条目为无效配置已删除；
        # 如需调热容请改各组分 "X specific heat capacity [J.kg-1.K-1]"。
        "Effective thermal conductivity [W.m-1.K-1]": 2,
        "Ambient temperature [K]": temperature,
        "Positive electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrolyte)": 1.5,
        "Negative electrode Bruggeman coefficient (electrode)": 1.5,
        "Positive electrode conductivity [S.m-1]": 91.3,
        "Negative electrode conductivity [S.m-1]": 5,
        "Negative electrode OCP [V]": graphite_ocp_Hithium280Ah,
        "Positive electrode OCP [V]": LFP_ocp_Hithium280Ah,
        "Negative electrode lithiation OCP [V]": graphite_ocp_charge,
        "Negative electrode delithiation OCP [V]": graphite_ocp_discharge,
        "Positive electrode lithiation OCP [V]": LFP_ocp_discharge,
        "Positive electrode delithiation OCP [V]": LFP_ocp_charge,
        "Negative electrode OCP entropic change [V.K-1]": graphite_entropic,
        "Positive electrode OCP entropic change [V.K-1]": LFP_entropic,
        "Contact resistance [Ohm]": 0.6e-4,
        "Positive electrode double-layer capacity [F.m-2]": 0,
        "Negative electrode double-layer capacity [F.m-2]": 0,
        "Lithium plating transfer coefficient": 0.5,
        # 注意：此处使用数值覆盖 plating_exchange_current_density_OKane2020 函数
        "Exchange-current density for plating [A.m-2]": 1.5e-3,
        "Positive electrode cracking rate": 0,
        "Positive electrode initial crack length [m]": 0,
        "Positive electrode initial crack width [m]": 0,
        "Ratio of lithium moles to SEI moles": 1.4,
        "Outer SEI partial molar volume [m3.mol-1]": 0.00009645,
        "Initial inner SEI thickness [m]": 5e-9,
        "Negative electrode LAM constant proportional term [s-1]": 0.3 * 1e-7 * t_factor,
        "SEI kinetic rate constant [m.s-1]": 4.8e-14 * k_sei * t_factor,
        "EC diffusivity [m2.s-1]": 3.5e-22 * D_sei * t_factor,
        "Negative electrode cracking rate": cracking_rate_Ai2020,
        "Lithium plating kinetic rate constant [m.s-1]": 3e-5 * t_factor,
        "SEI growth activation energy [J.mol-1]": 49887.19876117447 * 0.5,
        "Current solvent concentration in the reservoir [mol.m-3]": 900,
        "Current electrolyte concentration in the reservoir [mol.m-3]": 1000,
        "Initial total electrolyte volume in whole cell [m3]": 3e-3,
        "Initial total electrolyte volume in jelly roll [m3]": 0.0027387,
        "Electrolyte dry out rate [m3.s-1]": 2e-14,
    }
    return hithium_params
