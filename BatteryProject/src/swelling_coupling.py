"""膨胀力-孔隙率 块间准静态耦合（电化学-力双向耦合，路线 A）。

机制
----
每个老化仿真 block 结束后：

1. 用 :func:`src.analysis.calculate_cycle_swelling` 的力模型计算圈末（EOC）
   膨胀力，换算面压 P = F / (L_y·L_z)；
2. 增量弹性压缩：factor_k = 1 - (P - P_prev) / K_k。K_k 为各域压缩模量，
   隔膜最软最先被压；P 回落时 factor > 1，弹性可恢复；
3. 就地更新 params 中三个孔隙率参数——PyBaMM 的 ReactionDriven 孔隙率
   = 初始孔隙率参数 - 副反应产物体积，压缩初始孔隙率参数即全程生效；
4. 续跑前由 ``apply_dryout_to_initial_conditions(..., porosity_factors=...)``
   把同一因子乘到 "porosity times concentration" 状态上以保持 c_e 不变；
   被挤出的电解液在下一次 DryoutTracker.update 经 Vol_Pore_decrease
   自动进入 reservoir，与干涸模块共用一套孔隙体积账本。

与 ``run_aging_with_dryout`` 集成：传 ``swelling_coupler=SwellingCoupler(params, ...)``。
"""

import logging

import numpy as np

from .analysis import calculate_cycle_swelling

logger = logging.getLogger(__name__)

#: 各域孔隙率参数名
POROSITY_PARAM_KEYS = {
    "negative electrode": "Negative electrode porosity",
    "separator": "Separator porosity",
    "positive electrode": "Positive electrode porosity",
}

#: 默认压缩模量 K_k [Pa]：隔膜最软；量级为文献典型值，应由实测标定
DEFAULT_COMPACTION_MODULI = {
    "negative electrode": 8.0e8,
    "separator": 1.0e8,
    "positive electrode": 8.0e8,
}

#: 孔隙率下限，防止压缩到非物理值
MIN_POROSITY = 0.05


class SwellingCoupler:
    """块间准静态 膨胀力 -> 孔隙率 耦合器。

    Parameters
    ----------
    params : pybamm.ParameterValues
        当前参数字典（``update`` 时会被就地修改孔隙率参数）。
    k_stiffness : float
        夹具刚度（N/m）。
    k_cell : float or None
        电芯堆叠刚度（N/m），与夹具串联得到 k_eff。
    preload_force : float
        初始预紧力（N）。BOL 状态视为已在预紧下平衡，
        参考压强 = preload_force / 面积。
    beta_irreversible : float
        副反应产物顶出系数 β，透传给力模型。
    omega_n, omega_p, expansion_function_n, expansion_function_p, method :
        透传给 :func:`calculate_cycle_swelling` 的力模型参数。
    compaction_moduli : dict or None
        各域压缩模量 {domain: Pa}，缺省项用 DEFAULT_COMPACTION_MODULI。
    area : float or None
        受力面面积 [m2]，用于 F -> P 换算。None 时取
        Electrode width × height——注意卷绕电芯该值是展开面积，
        会低估面压，建议显式传壳体大面面积。
    max_step_compression : float
        单个 block 孔隙率因子相对 1 的最大偏离（防数值死亡螺旋）。
    """

    def __init__(
        self,
        params,
        k_stiffness=1.0e9,
        k_cell=None,
        preload_force=0.0,
        beta_irreversible=1.0,
        omega_n=0.1 * 3.1e-6,
        omega_p=0.0,
        expansion_function_n="graphite",
        expansion_function_p="lfp",
        method="engineering",
        compaction_moduli=None,
        max_step_compression=0.05,
        area=None,
    ):
        if area is None:
            area = params["Electrode width [m]"] * params["Electrode height [m]"]
        self.area = float(area)

        self.swelling_kwargs = dict(
            omega_n=omega_n,
            omega_p=omega_p,
            k_stiffness=k_stiffness,
            k_cell=k_cell,
            preload_force=preload_force,
            beta_irreversible=beta_irreversible,
            expansion_function_n=expansion_function_n,
            expansion_function_p=expansion_function_p,
            method=method,
            reference="parameter_initial",
        )
        self.compaction_moduli = dict(DEFAULT_COMPACTION_MODULI)
        if compaction_moduli:
            self.compaction_moduli.update(compaction_moduli)
        self.max_step_compression = float(max_step_compression)

        self._last_pressure = preload_force / self.area
        self.history = {
            "eoc_force_n": [float(preload_force)],
            "pressure_pa": [self._last_pressure],
            "factor_negative": [1.0],
            "factor_separator": [1.0],
            "factor_positive": [1.0],
            "porosity_negative": [self._porosity_or_nan(params, "negative electrode")],
            "porosity_separator": [self._porosity_or_nan(params, "separator")],
            "porosity_positive": [self._porosity_or_nan(params, "positive electrode")],
        }

    @staticmethod
    def _porosity_or_nan(params, domain):
        try:
            return float(params[POROSITY_PARAM_KEYS[domain]])
        except Exception:
            return float("nan")

    def update(self, sol, params):
        """由当前解计算 EOC 膨胀力，压缩 params 孔隙率参数，返回各域因子。

        Returns
        -------
        dict
            ``{domain: factor}``。续跑前应把该因子经
            ``apply_dryout_to_initial_conditions(porosity_factors=...)``
            同步乘到电解液浓度状态上。空 dict 表示本次无可用力数据。
        """
        try:
            _, _, eoc_forces, _ = calculate_cycle_swelling(
                sol, params, return_components=True, **self.swelling_kwargs
            )
        except Exception as exc:
            logger.warning("SwellingCoupler: force calc failed (%s); block skipped.", exc)
            return {}
        eoc_forces = np.asarray(eoc_forces, dtype=float)
        if eoc_forces.size == 0 or not np.isfinite(eoc_forces[-1]):
            logger.warning("SwellingCoupler: no valid EOC force; block skipped.")
            return {}

        force = float(eoc_forces[-1])
        pressure = force / self.area
        delta_p = pressure - self._last_pressure

        lo = 1.0 - self.max_step_compression
        hi = 1.0 + self.max_step_compression
        factors = {}
        for domain, key in POROSITY_PARAM_KEYS.items():
            factor = float(np.clip(1.0 - delta_p / self.compaction_moduli[domain], lo, hi))
            try:
                eps_old = float(params[key])
            except Exception:
                logger.warning("SwellingCoupler: %r is not a scalar; domain skipped.", key)
                factors[domain] = 1.0
                continue
            eps_new = max(eps_old * factor, MIN_POROSITY)
            factor = eps_new / eps_old if eps_old > 0 else 1.0
            params.update({key: eps_new})
            factors[domain] = factor

        self._last_pressure = pressure
        self.history["eoc_force_n"].append(force)
        self.history["pressure_pa"].append(pressure)
        self.history["factor_negative"].append(factors["negative electrode"])
        self.history["factor_separator"].append(factors["separator"])
        self.history["factor_positive"].append(factors["positive electrode"])
        self.history["porosity_negative"].append(self._porosity_or_nan(params, "negative electrode"))
        self.history["porosity_separator"].append(self._porosity_or_nan(params, "separator"))
        self.history["porosity_positive"].append(self._porosity_or_nan(params, "positive electrode"))
        return factors

    def summary(self):
        """打印膨胀力-孔隙率耦合状态摘要。"""
        h = self.history
        print(f"  EOC 膨胀力: {h['eoc_force_n'][0]:.1f} -> {h['eoc_force_n'][-1]:.1f} N")
        print(f"  面压:       {h['pressure_pa'][0] / 1e3:.3f} -> {h['pressure_pa'][-1] / 1e3:.3f} kPa")
        print(f"  孔隙率 ε_n: {h['porosity_negative'][0]:.4f} -> {h['porosity_negative'][-1]:.4f}")
        print(f"  孔隙率 ε_s: {h['porosity_separator'][0]:.4f} -> {h['porosity_separator'][-1]:.4f}")
        print(f"  孔隙率 ε_p: {h['porosity_positive'][0]:.4f} -> {h['porosity_positive'][-1]:.4f}")
