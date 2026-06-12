"""电解液干涸 (Electrolyte Dry-out) 模块。

基于 Li2024 论文 (14995785) 的实现思路，将电解液干涸机制从 Fun_NC.py 中
提取、重构并集成到 BatteryProject 框架中。

核心物理逻辑
-----------
1. SEI 生长消耗 EC 溶剂 → 电解液体积减少
2. SEI/锂析出占据孔隙 → 孔隙体积减少
3. 若消耗量 > 孔隙减少量 → 需要从储备罐补充电解液
4. 若储备罐不足 → 出现干涸(Ratio_Dryout < 1)，等效压缩电极宽度
5. 若消耗量 < 孔隙减少量 → 电解液被挤出到储备罐

使用方法
-------
>>> from src.electrolyte_dryout import DryoutTracker
>>> tracker = DryoutTracker(params, excess_ratio=1.2)
>>> # 每段仿真结束后调用
>>> tracker.update(sol, params)
>>> # 绘图
>>> tracker.plot()
"""

import numpy as np
import matplotlib.pyplot as plt


class DryoutTracker:
    """电解液干涸状态追踪器。

    Parameters
    ----------
    params : pybamm.ParameterValues
        当前模型参数（会被就地修改以注入干涸相关初始值）。
    excess_ratio : float
        初始电解液过量比（>1 表示有储备罐余量）。
    """

    def __init__(self, params, excess_ratio=1.2):
        self.enabled = excess_ratio >= 1.0

        # 从 params 读取几何参数
        L_n = params["Negative electrode thickness [m]"]
        L_p = params["Positive electrode thickness [m]"]
        L_s = params["Separator thickness [m]"]
        L_y = params["Electrode width [m]"]
        L_z = params["Electrode height [m]"]
        eps_n = params["Negative electrode porosity"]
        eps_p = params["Positive electrode porosity"]
        eps_s = params["Separator porosity"]

        pore_vol = (L_n * eps_n + L_p * eps_p + L_s * eps_s) * L_y * L_z
        self._vol_jr = pore_vol
        self._vol_tot = pore_vol * excess_ratio

        # 储备罐初始浓度：默认取电解液初始浓度
        c_e_init = params["Initial concentration in electrolyte [mol.m-3]"]
        c_EC_init = float(params.get(
            "EC initial concentration in electrolyte [mol.m-3]",
            params.get("Bulk solvent concentration [mol.m-3]", 4541.0)))

        # 向 params 注入干涸追踪所需参数
        _safe_update(params, "Current total electrolyte volume in whole cell [m3]", self._vol_tot)
        _safe_update(params, "Current total electrolyte volume in jelly roll [m3]", self._vol_jr)
        _safe_update(params, "Current solvent concentration in the reservoir [mol.m-3]", c_EC_init)
        _safe_update(params, "Current electrolyte concentration in the reservoir [mol.m-3]", c_e_init)
        _safe_update(params, "Ratio of Li-ion concentration change in electrolyte consider solvent consumption", 1.0)
        _safe_update(params, "Ratio of electrolyte dry out in jelly roll", 1.0)
        _safe_update(params, "Initial Electrode width [m]", L_y)
        _safe_update(params, "Initial Electrode height [m]", L_z)

        # 历史追踪
        self.history = {
            "Vol_Elely_Tot": [self._vol_tot * 1e6],   # mL
            "Vol_Elely_JR": [self._vol_jr * 1e6],
            "Vol_Pore_tot": [pore_vol * 1e6],
            "Ratio_Dryout": [1.0],
            "Ratio_CeEC": [1.0],
            "Ratio_CeLi": [1.0],
            "Width": [L_y],
            "Vol_EC_consumed": [0.0],
            "Vol_Elely_need": [0.0],
            "Vol_Elely_add": [0.0],
            "Vol_Pore_decrease": [0.0],
            "c_e_reservoir": [c_e_init],
            "c_EC_reservoir": [c_EC_init],
        }

        print(f"[DryoutTracker] 初始电解液总量: {self._vol_tot*1e6:.4f} mL, "
              f"卷芯内: {self._vol_jr*1e6:.4f} mL, "
              f"过量比: {excess_ratio:.2f}")

    def update(self, sol, params):
        """根据当前仿真解更新干涸状态并修改 params。

        Parameters
        ----------
        sol : pybamm.Solution
            本段仿真解（需包含 SEI 锂损失、孔隙率等变量）。
        params : pybamm.ParameterValues
            当前参数字典，会被就地更新。

        Returns
        -------
        data_pack : dict
            本轮干涸计算的关键中间量。
        """
        if not self.enabled:
            # 干涸未启用时仍返回空结构
            _safe_update(params, "Ratio of Li-ion concentration change in electrolyte consider solvent consumption", 1.0)
            return {}

        data_pack = _cal_new_con_update(sol, params)
        self._append_history(data_pack)
        return data_pack

    def _append_history(self, dp):
        """将本轮计算结果追加到历史记录。"""
        self.history["Vol_Elely_Tot"].append(dp["Vol_Elely_Tot_new"] * 1e6)
        self.history["Vol_Elely_JR"].append(dp["Vol_Elely_JR_new"] * 1e6)
        self.history["Vol_Pore_tot"].append(dp["Vol_Pore_tot_new"] * 1e6)
        self.history["Ratio_Dryout"].append(dp["Ratio_Dryout"])
        self.history["Ratio_CeEC"].append(dp["Ratio_CeEC_JR"])
        self.history["Ratio_CeLi"].append(dp["Ratio_CeLi_JR"])
        self.history["Width"].append(dp["Width_new"])
        self.history["Vol_EC_consumed"].append(dp["Vol_EC_consumed"] * 1e6)
        self.history["Vol_Elely_need"].append(dp["Vol_Elely_need"] * 1e6)
        self.history["Vol_Elely_add"].append(dp["Vol_Elely_add"] * 1e6)
        self.history["Vol_Pore_decrease"].append(dp["Vol_Pore_decrease"] * 1e6)
        self.history["c_e_reservoir"].append(dp["c_e_r_new"])
        self.history["c_EC_reservoir"].append(dp["c_EC_r_new"])

    def plot(self, figsize=(18, 10)):
        """绘制电解液干涸演化的 6 子图综合面板。"""
        plot_dryout(self.history, figsize=figsize)

    def get_lam_dryout_pct(self):
        """计算因干涸引起的等效 LAM 百分比。

        Returns
        -------
        np.ndarray
            每步的干涸 LAM 百分比 (100 - Width/Width_0 * 100)。
        """
        widths = np.array(self.history["Width"])
        return 100 - widths / widths[0] * 100

    def summary(self):
        """打印当前干涸状态摘要。"""
        h = self.history
        print(f"  电解液总量: {h['Vol_Elely_Tot'][0]:.4f} → {h['Vol_Elely_Tot'][-1]:.4f} mL")
        print(f"  卷芯内量:   {h['Vol_Elely_JR'][0]:.4f} → {h['Vol_Elely_JR'][-1]:.4f} mL")
        print(f"  干涸比例:   {h['Ratio_Dryout'][-1]:.4f}")
        print(f"  电极宽度:   {h['Width'][0]:.6f} → {h['Width'][-1]:.6f} m")
        lam_dry = self.get_lam_dryout_pct()
        print(f"  干涸LAM:    {lam_dry[-1]:.2f}%")


def apply_dryout_to_initial_conditions(model, sol, params, porosity_factors=None):
    """将干涸浓度修正应用到初始条件，返回新模型。

    这是 Fun_NC.py 中 ``Run_Model_Base_On_Last_Solution`` 内
    对初始条件修正逻辑的封装。

    Parameters
    ----------
    model : pybamm.lithium_ion.BaseModel
        当前 PyBaMM 模型。
    sol : pybamm.Solution
        上一段仿真解。
    params : pybamm.ParameterValues
        包含 ``Ratio of Li-ion concentration change ...`` 的参数字典。

    Returns
    -------
    model_new : pybamm.lithium_ion.BaseModel
        已注入修正初始条件的新模型。
    """
    ratio = params.get(
        "Ratio of Li-ion concentration change in electrolyte consider solvent consumption",
        1.0)

    dict_short = _get_last_state(model, sol)

    # 修正电解液浓度（干涸 + 溶剂消耗效应）
    for key in (
        "Negative electrode porosity times concentration [mol.m-3]",
        "Separator porosity times concentration [mol.m-3]",
        "Positive electrode porosity times concentration [mol.m-3]",
    ):
        if key in dict_short:
            dict_short[key] = dict_short[key] * ratio

    # 膨胀力耦合：把孔隙率压缩因子同步乘到 ε·c_e 状态（保持 c_e 不变）
    if porosity_factors:
        _apply_porosity_factors_to_state(dict_short, porosity_factors)

    return model.set_initial_conditions_from(dict_short, inplace=False)


# ---------------------------------------------------------------------------
#  内部函数
# ---------------------------------------------------------------------------

_POROSITY_TIMES_CONC_KEYS = {
    "negative electrode": "Negative electrode porosity times concentration [mol.m-3]",
    "separator": "Separator porosity times concentration [mol.m-3]",
    "positive electrode": "Positive electrode porosity times concentration [mol.m-3]",
}


def _apply_porosity_factors_to_state(dict_short, porosity_factors):
    """把力学压缩因子乘到 ε·c_e 状态上（与孔隙率参数同因子，保持 c_e 不变）。

    孔隙率本身在 PyBaMM 中是代数量（初始孔隙率参数 - 副反应产物体积），
    参数端的压缩由 SwellingCoupler.update 完成；这里只同步电解液状态，
    被挤出的电解液在下一次 DryoutTracker.update 经 Vol_Pore_decrease
    进入 reservoir。
    """
    for domain, factor in porosity_factors.items():
        key = _POROSITY_TIMES_CONC_KEYS.get(domain)
        if key and key in dict_short:
            dict_short[key] = dict_short[key] * factor


def _safe_update(params, key, value):
    """安全更新 ParameterValues，自动处理 check_already_exists。"""
    params.update({key: value})


def _get_last_state(model, sol):
    """从 sol 中提取末态变量字典，用于设置下一段仿真的初始条件。

    直接复用 Fun_NC.py 中 ``Get_Last_state`` 的逻辑：
    将 "Porosity times concentration" 和 "Electrolyte potential" 拆
    成负极/隔膜/正极三个分区变量。
    """
    import pybamm as pb

    dict_short = {}
    list_short = []
    for var, _ in model.initial_conditions.items():
        list_short.append(var._name)

    # 拆分合并变量为分区变量
    if "Porosity times concentration [mol.m-3]" in list_short:
        list_short.remove("Porosity times concentration [mol.m-3]")
        list_short.extend([
            "Negative electrode porosity times concentration [mol.m-3]",
            "Separator porosity times concentration [mol.m-3]",
            "Positive electrode porosity times concentration [mol.m-3]",
        ])
    if "Electrolyte potential [V]" in list_short:
        list_short.remove("Electrolyte potential [V]")
        list_short.extend([
            "Negative electrolyte potential [V]",
            "Separator electrolyte potential [V]",
            "Positive electrolyte potential [V]",
        ])

    for name in list_short:
        dict_short[name] = sol.last_state[name].data

    return dict_short


def _cal_new_con_update(sol, params):
    """核心干涸计算函数。

    基于 14995785/Fun_NC.py 中 ``Cal_new_con_Update`` 的完整物理逻辑，
    计算 EC 消耗、孔隙变化、电解液补充/挤出，并就地更新 params。

    Returns
    -------
    dict : 包含所有中间计算量的字典。
    """
    # ── Step 1: 读取参数 ──
    L_p = params["Positive electrode thickness [m]"]
    L_n = params["Negative electrode thickness [m]"]
    L_s = params["Separator thickness [m]"]
    L_y = params["Electrode width [m]"]
    L_z = params["Electrode height [m]"]

    c_EC_r_old = params["Current solvent concentration in the reservoir [mol.m-3]"]
    c_e_r_old = params["Current electrolyte concentration in the reservoir [mol.m-3]"]
    c_EC_JR_old = float(params.get(
        "Bulk solvent concentration [mol.m-3]",
        params.get("EC initial concentration in electrolyte [mol.m-3]", 4541.0)))

    # 锂损失量
    LLINegSEI = (sol["Loss of lithium to negative SEI [mol]"].entries[-1]
                 - sol["Loss of lithium to negative SEI [mol]"].entries[0])

    try:
        LLINegSEIcr = (sol["Loss of lithium to negative SEI on cracks [mol]"].entries[-1]
                       - sol["Loss of lithium to negative SEI on cracks [mol]"].entries[0])
    except KeyError:
        LLINegSEIcr = 0.0

    cLi_Xavg = sol["X-averaged electrolyte concentration [mol.m-3]"].entries[-1]

    # 孔隙体积（始末）
    PoreVolNeg_0 = sol["X-averaged negative electrode porosity"].entries[0] * L_n * L_y * L_z
    PoreVolSep_0 = sol["X-averaged separator porosity"].entries[0] * L_s * L_y * L_z
    PoreVolPos_0 = sol["X-averaged positive electrode porosity"].entries[0] * L_p * L_y * L_z
    PoreVolNeg_1 = sol["X-averaged negative electrode porosity"].entries[-1] * L_n * L_y * L_z
    PoreVolSep_1 = sol["X-averaged separator porosity"].entries[-1] * L_s * L_y * L_z
    PoreVolPos_1 = sol["X-averaged positive electrode porosity"].entries[-1] * L_p * L_y * L_z

    Vol_Pore_tot_new = PoreVolNeg_1 + PoreVolSep_1 + PoreVolPos_1

    # ── Step 2: 干涸核心方程 ──
    Vol_Elely_Tot_old = params["Current total electrolyte volume in whole cell [m3]"]
    Vol_Elely_JR_old = params["Current total electrolyte volume in jelly roll [m3]"]

    VmolEC = float(params.get("EC partial molar volume [m3.mol-1]", 6.684e-5))

    Vol_Pore_decrease = Vol_Elely_JR_old - Vol_Pore_tot_new

    # EC 消耗量: EC:Li:SEI = 2:2:1 简化为 1:1 (与原代码一致)
    Vol_EC_consumed = (LLINegSEI + LLINegSEIcr) * 1 * VmolEC

    Vol_Elely_need = Vol_EC_consumed - Vol_Pore_decrease
    Vol_Elely_Tot_new = Vol_Elely_Tot_old - Vol_EC_consumed

    # ── Step 3: 分情况计算 ──
    if Vol_Elely_need < 0:
        # 情况 A: 电解液被挤出
        Vol_Elely_squeezed = -Vol_Elely_need
        Vol_Elely_add = 0.0
        Vol_Elely_JR_new = Vol_Pore_tot_new
        Ratio_Dryout = Vol_Elely_Tot_new / Vol_Elely_JR_new
        Ratio_CeEC_JR = 1.0
        Ratio_CeLi_JR = 1.0

        Vol_Elely_reservoir_old = Vol_Elely_Tot_old - Vol_Elely_JR_old
        SqueezedLiMol = Vol_Elely_squeezed * cLi_Xavg
        SqueezedECMol = Vol_Elely_squeezed * c_EC_JR_old
        LiMol_reservoir_new = Vol_Elely_reservoir_old * c_e_r_old + SqueezedLiMol
        ECMol_reservoir_new = Vol_Elely_reservoir_old * c_EC_r_old + SqueezedECMol
        new_res_vol = Vol_Elely_reservoir_old + Vol_Elely_squeezed
        c_e_r_new = LiMol_reservoir_new / new_res_vol if new_res_vol > 0 else c_e_r_old
        c_EC_r_new = ECMol_reservoir_new / new_res_vol if new_res_vol > 0 else c_EC_r_old
        Width_new = L_y
    else:
        # 情况 B: 需要补充电解液 (或刚好持平)
        Vol_Elely_squeezed = 0.0
        if Vol_Elely_Tot_old > Vol_Elely_JR_old:
            available = Vol_Elely_Tot_old - Vol_Elely_JR_old
            if available >= Vol_Elely_need:
                # B1: 储备充足，完全补
                Vol_Elely_add = Vol_Elely_need
                Vol_Elely_JR_new = Vol_Pore_tot_new
                Ratio_Dryout = 1.0
            else:
                # B2: 储备不足，部分补
                Vol_Elely_add = available
                Vol_Elely_JR_new = Vol_Elely_Tot_new
                Ratio_Dryout = Vol_Elely_JR_new / Vol_Pore_tot_new
        else:
            # B3: 无储备
            Vol_Elely_add = 0.0
            Vol_Elely_JR_new = Vol_Elely_Tot_new
            Ratio_Dryout = Vol_Elely_JR_new / Vol_Pore_tot_new

        # 混合浓度更新
        TotLi_Elely_JR_Old = sol["Total lithium in electrolyte [mol]"].entries[-1]
        TotLi_Elely_JR_New = TotLi_Elely_JR_Old + Vol_Elely_add * c_e_r_old
        TotECMol_JR = Vol_Elely_JR_old * c_EC_JR_old - LLINegSEI + Vol_Elely_add * c_EC_r_old

        Ratio_CeEC_JR = (TotECMol_JR / Vol_Elely_JR_new / c_EC_JR_old) if (Vol_Elely_JR_new > 0 and c_EC_JR_old > 0) else 1.0
        Ratio_CeLi_JR = (TotLi_Elely_JR_New / TotLi_Elely_JR_Old / Ratio_Dryout) if (TotLi_Elely_JR_Old > 0 and Ratio_Dryout > 0) else 1.0

        c_e_r_new = c_e_r_old
        c_EC_r_new = c_EC_r_old
        Width_new = Ratio_Dryout * L_y

    # ── Step 4: 更新 params ──
    _safe_update(params, "Bulk solvent concentration [mol.m-3]",
                 c_EC_JR_old * Ratio_CeEC_JR)
    _safe_update(params, "EC initial concentration in electrolyte [mol.m-3]",
                 c_EC_JR_old * Ratio_CeEC_JR)
    _safe_update(params, "Ratio of Li-ion concentration change in electrolyte consider solvent consumption",
                 Ratio_CeLi_JR)
    _safe_update(params, "Current total electrolyte volume in whole cell [m3]",
                 Vol_Elely_Tot_new)
    _safe_update(params, "Current total electrolyte volume in jelly roll [m3]",
                 Vol_Elely_JR_new)
    _safe_update(params, "Ratio of electrolyte dry out in jelly roll",
                 Ratio_Dryout)
    _safe_update(params, "Electrode width [m]", Width_new)
    _safe_update(params, "Current solvent concentration in the reservoir [mol.m-3]",
                 c_EC_r_new)
    _safe_update(params, "Current electrolyte concentration in the reservoir [mol.m-3]",
                 c_e_r_new)

    return {
        "Vol_EC_consumed": Vol_EC_consumed,
        "Vol_Elely_need": Vol_Elely_need,
        "Vol_Elely_add": Vol_Elely_add,
        "Vol_Elely_Tot_new": Vol_Elely_Tot_new,
        "Vol_Elely_JR_new": Vol_Elely_JR_new,
        "Vol_Pore_tot_new": Vol_Pore_tot_new,
        "Vol_Pore_decrease": Vol_Pore_decrease,
        "c_e_r_new": c_e_r_new,
        "c_EC_r_new": c_EC_r_new,
        "Ratio_Dryout": Ratio_Dryout,
        "Ratio_CeEC_JR": Ratio_CeEC_JR,
        "Ratio_CeLi_JR": Ratio_CeLi_JR,
        "Width_new": Width_new,
    }


# ---------------------------------------------------------------------------
#  可视化
# ---------------------------------------------------------------------------

def plot_dryout(history, figsize=(18, 10)):
    """绘制干涸演化综合面板 (2×3 子图)。

    Parameters
    ----------
    history : dict
        DryoutTracker.history 字典。
    figsize : tuple
        图形尺寸。
    """
    steps = np.arange(len(history["Ratio_Dryout"]))

    fig, axes = plt.subplots(2, 3, figsize=figsize)

    # 1) 电解液体积
    ax = axes[0, 0]
    ax.plot(steps, history["Vol_Elely_Tot"], "o-", label="Total")
    ax.plot(steps, history["Vol_Elely_JR"], "s-", label="Jelly Roll")
    ax.plot(steps, history["Vol_Pore_tot"], "^-", label="Pore Vol")
    ax.set_ylabel("Volume (mL)")
    ax.set_title("Electrolyte Volume")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 2) 干涸比例
    ax = axes[0, 1]
    ax.plot(steps, history["Ratio_Dryout"], "o-", color="tab:red")
    ax.set_ylabel("Ratio")
    ax.set_title("Dryout Ratio")
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)

    # 3) 电极宽度
    ax = axes[0, 2]
    widths = np.array(history["Width"])
    ax.plot(steps, widths * 1e3, "o-", color="tab:green")
    ax.set_ylabel("Width (mm)")
    ax.set_title("Electrode Width")
    ax.grid(True, alpha=0.3)

    # 4) EC 消耗 & 需求
    ax = axes[1, 0]
    ax.plot(steps, history["Vol_EC_consumed"], "o-", label="EC consumed")
    ax.plot(steps, history["Vol_Elely_need"], "s-", label="Elely need")
    ax.plot(steps, history["Vol_Elely_add"], "^-", label="Elely added")
    ax.set_ylabel("Volume (mL)")
    ax.set_xlabel("Step")
    ax.set_title("EC Consumption")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 5) 浓度比例
    ax = axes[1, 1]
    ax.plot(steps, history["Ratio_CeEC"], "o-", label="CeEC ratio")
    ax.plot(steps, history["Ratio_CeLi"], "s-", label="CeLi ratio")
    ax.set_ylabel("Ratio")
    ax.set_xlabel("Step")
    ax.set_title("Concentration Ratios")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 6) 储备罐浓度
    ax = axes[1, 2]
    ax.plot(steps, history["c_e_reservoir"], "o-", label="Li+ reservoir")
    ax.plot(steps, history["c_EC_reservoir"], "s-", label="EC reservoir")
    ax.set_ylabel("Concentration (mol/m³)")
    ax.set_xlabel("Step")
    ax.set_title("Reservoir Concentrations")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle("Electrolyte Dry-out Evolution", fontsize=14, fontweight="bold")
    fig.tight_layout()


def run_aging_with_dryout(
    model, params, experiment, solver, var_pts,
    starting_solution=None,
    tracker=None,
    swelling_coupler=None,
    n_blocks=10,
    cycles_per_block=20,
    t_factor=50,
    temperature=298.15,
    get_hithium_params=None,
    showprogress=True,
):
    """分块运行老化仿真，每块之间执行干涸更新。

    这是将原 Fun_NC.py 中 ``Run_P2_Excel`` 的主循环逻辑简化封装的
    便捷函数。每个 block 之间会：
      1. 调用 tracker.update() 计算干涸
      2. 调用 apply_dryout_to_initial_conditions() 修正初始条件
      3. 使用更新后的 params 启动下一个 block

    Parameters
    ----------
    model : pybamm.lithium_ion.BaseModel
        DFN 或 SPM 模型。
    params : pybamm.ParameterValues
        参数字典（会被就地修改）。
    experiment : callable or pybamm.Experiment
        如果是 callable，则签名为 ``experiment(cycles_per_block)``，返回 Experiment。
        如果是 pybamm.Experiment，直接使用。
    solver : pybamm Solver
    var_pts : dict
    starting_solution : pybamm.Solution or None
    tracker : DryoutTracker or None
        传入 None 时不执行干涸更新（退化为普通分块仿真）。
    n_blocks : int
        分块数量。
    cycles_per_block : int
        每块循环数。
    t_factor : int
        加速因子。
    temperature : float
        温度 (K)。
    get_hithium_params : callable or None
        参数更新函数，签名 ``get_hithium_params(t_factor, temperature)``。
        每块开始前调用以更新老化参数。
    showprogress : bool
        是否显示进度。

    Returns
    -------
    sol_list : list[pybamm.Solution]
        每块的仿真解列表。
    """
    import pybamm

    sol = starting_solution
    sol_list = []

    for i_block in range(n_blocks):
        print(f"\n=== Block {i_block+1}/{n_blocks} ===")

        # 可选：刷新老化参数。tracker 启用时仅首块刷新一次——否则
        # get_hithium_params 会把 tracker 管理的几何键 (Electrode width)
        # 重置为原值，抹掉累计的干涸压缩。
        if get_hithium_params is not None and (
            (tracker is None and swelling_coupler is None) or i_block == 0
        ):
            params.update(
                get_hithium_params(t_factor, temperature=temperature),
            )

        # 干涸更新
        if tracker is not None and sol is not None:
            tracker.update(sol, params)

        # 膨胀力 -> 孔隙率（块间准静态耦合，见 src/swelling_coupling.py）
        porosity_factors = None
        if swelling_coupler is not None and sol is not None:
            porosity_factors = swelling_coupler.update(sol, params)

        # 构建实验
        if callable(experiment) and not isinstance(experiment, pybamm.Experiment):
            exp = experiment(cycles_per_block)
        else:
            exp = experiment

        # 构建模型初始条件
        if (tracker is not None or porosity_factors) and sol is not None:
            model_run = apply_dryout_to_initial_conditions(
                model, sol, params, porosity_factors=porosity_factors
            )
        else:
            model_run = model

        sim = pybamm.Simulation(
            model_run,
            experiment=exp,
            parameter_values=params,
            solver=solver,
            var_pts=var_pts,
        )

        if sol is not None:
            sol = sim.solve(
                starting_solution=sol,
                showprogress=showprogress,
                calc_esoh=False,
            )
        else:
            sol = sim.solve(showprogress=showprogress)

        sol_list.append(sol)

    # 最后一块结束后再更新一次
    if tracker is not None and sol is not None:
        tracker.update(sol, params)
    if swelling_coupler is not None and sol is not None:
        swelling_coupler.update(sol, params)

    return sol_list
