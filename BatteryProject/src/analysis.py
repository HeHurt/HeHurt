"""数据提取与分析函数。"""

import logging
import re
import numpy as np
from scipy.interpolate import interp1d
from . import config

logger = logging.getLogger(__name__)

# 下面的函数实现了误差指标的计算与仿真/实验电压曲线的对比绘图。


def calc_rrmse(y_true, y_pred):
    """计算误差指标 RMSE 与相对 RMSE。

    参数
    ----
    y_true : array-like
        真实值序列。
    y_pred : array-like
        预测值序列（需与真实值同长度）。

    返回
    ----
    tuple(float, float)
        (rmse, rrmse)，其中 rrmse = rmse / mean(y_true)。
        当 mean(y_true) 为 0 或无效时 rrmse 返回 nan 并告警。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.shape != y_pred.shape:
        n = min(y_true.size, y_pred.size)
        logger.warning(
            "calc_rrmse: y_true(%d) 与 y_pred(%d) 长度不一致，截断到 %d。",
            y_true.size, y_pred.size, n,
        )
        y_true = y_true[:n]
        y_pred = y_pred[:n]
    diff = y_true - y_pred
    mask = np.isfinite(diff)
    if not np.any(mask):
        return np.nan, np.nan
    rmse = float(np.sqrt(np.mean((y_true[mask] - y_pred[mask]) ** 2)))
    mean_true = float(np.mean(y_true[mask]))
    if mean_true == 0 or not np.isfinite(mean_true):
        logger.warning("calc_rrmse: mean(y_true)=%.6g 为零或无效，rrmse 置为 nan。", mean_true)
        return rmse, np.nan
    return rmse, rmse / mean_true


def retention_from_capacity(caps):
    """按首圈容量归一为保持率（0–1 小数）；首圈为 0 或无效时返回全 0。"""
    caps = np.asarray(caps, dtype=float)
    if caps.size == 0:
        return caps
    base = caps[0]
    if base == 0 or not np.isfinite(base):
        return np.zeros_like(caps)
    return caps / base


def calculate_rrmse_from_sol(df, x_columns, y_columns, sol_list, labels, charge_or_discharge):
    """纯分析：对比仿真/实验电压曲线，返回每条曲线的 RMSE/RRMSE 以及绘图所需数据。

    返回
    ----
    list[dict]
        每个 dict 包含:
        - label, charge_or_discharge
        - x_exp, y_exp, x_sim, y_sim (用于绘图)
        - rmse, rrmse (误差指标，无效时为 nan)
    """
    results = []
    for x_col, y_col, sol, label in zip(x_columns, y_columns, sol_list, labels):
        # 实验侧：x/y 按行同时 dropna，保证长度一致
        sub = df[[x_col, y_col]].dropna()
        x_exp = sub[x_col].to_numpy(dtype=float)
        y_exp = sub[y_col].to_numpy(dtype=float)

        voltage = np.asarray(sol["Voltage [V]"].entries, dtype=float)
        cap = np.asarray(sol["Throughput capacity [A.h]"].entries, dtype=float)
        try:
            current = np.asarray(sol["Current [A]"].entries, dtype=float)
        except (KeyError, TypeError):
            current = np.full_like(voltage, np.nan)
        # 按电流符号切分充放电段（与 compute_cycle_energies 口径一致：
        # 电流>0 放电、<0 充电），不再依赖 voltage.argmax()，避免
        # CC-CV 平台/多段工况下切分错误。
        if charge_or_discharge == "charge":
            seg_mask = current < 0
        else:
            seg_mask = current > 0
        if np.any(seg_mask):
            x_sim = cap[seg_mask]
            y_sim = voltage[seg_mask]
            if x_sim.size > 0:
                x_sim = x_sim - x_sim[0]
        else:
            logger.warning(
                "calculate_rrmse_from_sol: 解中未找到 %s 段电流，回退整段曲线。",
                charge_or_discharge,
            )
            x_sim = cap
            y_sim = voltage
            if x_sim.size > 0:
                x_sim = x_sim - x_sim[0]

        if x_sim.size >= 2:
            f_sim = interp1d(x_sim, y_sim, bounds_error=False, fill_value="extrapolate")
            y_sim_interp = f_sim(x_exp)
            mask = np.isfinite(y_sim_interp) & np.isfinite(y_exp)
            if np.any(mask):
                rmse, rrmse = calc_rrmse(y_exp[mask], y_sim_interp[mask])
            else:
                rmse, rrmse = np.nan, np.nan
        else:
            logger.warning(
                "calculate_rrmse_from_sol: %s 段仿真点数不足(%d)，无法计算误差。",
                label, x_sim.size,
            )
            rmse, rrmse = np.nan, np.nan
        results.append({
            "label": label,
            "charge_or_discharge": charge_or_discharge,
            "x_exp": x_exp, "y_exp": y_exp,
            "x_sim": x_sim, "y_sim": y_sim,
            "rmse": rmse, "rrmse": rrmse,
        })
    return results
# 下面的函数实现了每圈放电容量的提取，基于仿真解中的电流和容量数据。


def get_discharge_capacity(sol):
    """提取每圈放电容量（Ah），累计每圈内所有放电步的容量绝对增量。

    返回 {'discharge_capacity': np.array([...])}
    """
    if sol is None:
        return {"discharge_capacity": np.array([])}
    caps = []
    for cycle in sol.cycles:
        cycle_cap = 0.0
        has_discharge_step = False
        for step in getattr(cycle, "steps", []):
            try:
                current = np.asarray(step["Current [A]"].entries, dtype=float)
            except (AttributeError, KeyError, TypeError):
                # PyBaMM may keep EmptySolution placeholders in cycle.steps.
                continue
            if current.size == 0:
                continue
            mean_I = np.mean(current)
            # 放电步判断：平均电流为正，且超过峰值电流的 1% 或绝对 0.01A（取较大者）
            peak_I = np.max(np.abs(current))
            threshold = max(peak_I * 0.01, 0.01)
            if mean_I > threshold:
                try:
                    Q = np.asarray(step["Throughput capacity [A.h]"].entries, dtype=float)
                except (AttributeError, KeyError, TypeError):
                    continue
                delta_Q = np.abs(Q[-1] - Q[0]) if Q.size > 0 else np.nan
                if np.isfinite(delta_Q):
                    cycle_cap += float(delta_Q)
                    has_discharge_step = True
        caps.append(cycle_cap if has_discharge_step else np.nan)
    return {"discharge_capacity": np.array(caps)}

# 下面的函数实现了热量分量的提取与平均，支持可逆热项的计算与容量轴插值。


def _parse_temperature_from_label(label_for_temp):
    """从标签字符串中解析温度（单位 K）。

    例如标签中包含 “25°C” 时返回 298.15。
    解析失败则回退为 298.15 K。
    """
    try:
        if label_for_temp:
            match = re.search(r"(-?\d+(?:\.\d+)?)\s*°?C", label_for_temp)
            return float(match.group(1)) + 273.15 if match else 298.15
    except Exception:
        pass
    return 298.15

# 下面的函数实现了多个数组的拼接平均，空列表时返回 NaN。


def _calc_concat_mean(list_of_arrays):
    """将多个数组拼接后求均值；空列表返回 NaN。"""
    if not list_of_arrays:
        return np.nan
    return np.mean(np.concatenate(list_of_arrays))

# 下面的函数实现了热量分量的统一提取，支持可逆热项的计算与容量轴插值。


def _collect_heat_components(sol, label_for_temp=None, include_reversible=False, require_capacity_for_reversible=False):
    """统一提取每圈热量分量（内部函数）。

    参数
    ----
    sol : pybamm.Solution
        循环仿真解。
    label_for_temp : str | None
        用于解析温度（例如 "25°C 0.25P"）。
    include_reversible : bool
        是否计算可逆热项 I*T*dU/dT。
    require_capacity_for_reversible : bool
        计算可逆热时是否强制要求容量点数>=2（便于插值）。

    返回
    ----
    dict[str, np.ndarray]
        六个键：irrev/rev/total × chg/dchg。
    """
    if sol is None:
        return {k: np.array([]) for k in ["irrev_chg", "irrev_dchg", "rev_chg", "rev_dchg", "total_chg", "total_dchg"]}

    # 统一返回容器：不可逆/可逆/总热，均按充放电拆分
    if include_reversible:
        config.ensure_entropy_loaded()
    # 温度用于可逆热项（I*T*dU/dT）
    T_k = _parse_temperature_from_label(label_for_temp)

    res = {k: [] for k in ["irrev_chg", "irrev_dchg", "rev_chg", "rev_dchg", "total_chg", "total_dchg"]}
    ocv_name = "X-averaged battery open-circuit voltage [V]"

    for cycle in sol.cycles:
        # 每圈内先收集“瞬时功率数组”，最后再做拼接平均
        inst_irrev_chg, inst_irrev_dchg = [], []
        inst_rev_chg, inst_rev_dchg = [], []

        for step in cycle.steps:
            try:
                current = step["Current [A]"].entries
            except TypeError:
                # EmptySolution：实验提前截止/未执行的步骤，无数据可取
                continue
            mean_I = np.mean(current)
            # 跳过静置步（电流过小，热量贡献可忽略）
            if np.abs(mean_I) < 0.05:
                continue

            V = step["Voltage [V]"].entries
            try:
                U = step[ocv_name].entries
            except KeyError:
                U = step["Battery open-circuit voltage [V]"].entries
            # 不可逆热：|V - U_ocv| * |I|
            p_irrev = np.abs(V - U) * np.abs(current)

            p_rev = None
            if include_reversible:
                Q = step["Throughput capacity [A.h]"].entries
                raw_cap = Q - Q[0] if len(Q) > 0 else np.array([])
                # 可逆热计算需要容量轴插值；点数太少会跳过
                if require_capacity_for_reversible and raw_cap.size < 2:
                    continue
                if raw_cap.size >= 2:
                    # 将电流重采样到统一容量网格，便于与 dU/dT 相乘
                    new_cap = np.linspace(0, raw_cap[-1], config.TARGET_PTS)
                    current_interp = np.interp(new_cap, raw_cap, current)
                    if mean_I < 0:
                        curr_dudt = config.DUDT_CHG if config.DUDT_CHG is not None else np.zeros(config.TARGET_PTS)
                    else:
                        curr_dudt = config.DUDT_DCHG if config.DUDT_DCHG is not None else np.zeros(config.TARGET_PTS)
                    # 可逆热：I * T * dU/dT
                    p_rev = current_interp * T_k * curr_dudt

            if mean_I < 0:
                inst_irrev_chg.append(p_irrev)
                if p_rev is not None:
                    inst_rev_chg.append(p_rev)
            else:
                inst_irrev_dchg.append(p_irrev)
                if p_rev is not None:
                    inst_rev_dchg.append(p_rev)

        avg_irrev_c = _calc_concat_mean(inst_irrev_chg)
        avg_irrev_d = _calc_concat_mean(inst_irrev_dchg)
        avg_rev_c = _calc_concat_mean(inst_rev_chg)
        avg_rev_d = _calc_concat_mean(inst_rev_dchg)

        res["irrev_chg"].append(avg_irrev_c)
        res["irrev_dchg"].append(avg_irrev_d)
        res["rev_chg"].append(avg_rev_c)
        res["rev_dchg"].append(avg_rev_d)
        res["total_chg"].append(avg_irrev_c + avg_rev_c)
        res["total_dchg"].append(avg_irrev_d + avg_rev_d)

    for k in res:
        res[k] = np.array(res[k])
    return res


def get_all_heat_components(sol, label_for_temp=None):
    """计算每圈充/放电的不可逆、可逆与总产热功率（平均值）。

    返回键
    ------
    - irrev_chg / irrev_dchg
    - rev_chg / rev_dchg
    - total_chg / total_dchg
    """
    return _collect_heat_components(
        sol,
        label_for_temp=label_for_temp,
        include_reversible=True,
        require_capacity_for_reversible=True,
    )

# 下面的函数实现了每圈膨胀力的估算与分解，基于浓度引起的体积变化与 SEI 厚度近似。


def _empty_swelling_table():
    """Return an empty swelling result table with the public column contract."""
    import pandas as pd

    return pd.DataFrame(
        columns=[
            "cycle",
            "max_force_n",
            "min_force_n",
            "eoc_force_n",
            "reversible_amplitude_n",
            "max_disp_m",
            "min_disp_m",
            "source_method",
        ]
    )


def _swelling_rows_to_table(rows):
    """Build a swelling result table from row dictionaries."""
    if not rows:
        return _empty_swelling_table()

    import pandas as pd

    return pd.DataFrame(rows, columns=_empty_swelling_table().columns)


def _normalize_swelling_method(method):
    """Validate and normalize swelling displacement source method."""
    normalized = str(method).strip().lower()
    if normalized not in {"engineering", "pybamm_thickness"}:
        raise ValueError("method must be 'engineering' or 'pybamm_thickness'")
    return normalized


def _normalize_swelling_reference(reference):
    """Validate and normalize swelling displacement reference convention."""
    normalized = str(reference).strip().lower()
    if normalized not in {"cycle_start", "solution_start", "parameter_initial"}:
        raise ValueError("reference must be 'cycle_start', 'solution_start', or 'parameter_initial'")
    return normalized


# ---------------------------------------------------------------------------
#  电极膨胀函数（嵌锂度 -> 厚度应变）
# ---------------------------------------------------------------------------

#: 石墨厚度应变-嵌锂度节点：分段线性近似石墨分阶膨胀（文献定形曲线，
#: 满嵌约 13.2%；建议用本厂膨胀仪数据重标定节点）。
GRAPHITE_EXPANSION_STO = (0.0, 0.12, 0.25, 0.5, 0.7, 1.0)
GRAPHITE_EXPANSION_STRAIN = (0.0, 0.020, 0.043, 0.062, 0.090, 0.132)

#: LFP 满嵌-脱嵌体积变化约 +6.6%，各向同性线性化为厚度应变（1/3）。
LFP_EXPANSION_STRAIN_MAX = 0.022


def graphite_expansion_fraction(sto):
    """石墨电极厚度应变 f(sto)，捕捉分阶非线性（中段平台 + 末端陡升）。"""
    return np.interp(
        np.asarray(sto, dtype=float),
        GRAPHITE_EXPANSION_STO,
        GRAPHITE_EXPANSION_STRAIN,
    )


def lfp_expansion_fraction(sto):
    """LFP 电极厚度应变 f(sto)：嵌锂膨胀，充电时与石墨呼吸反相、部分抵消。"""
    return LFP_EXPANSION_STRAIN_MAX * np.asarray(sto, dtype=float)


_EXPANSION_FUNCTIONS = {
    "graphite": graphite_expansion_fraction,
    "lfp": lfp_expansion_fraction,
}


def _resolve_expansion_function(func):
    """把 None / 字符串 / 可调用统一解析为膨胀函数（None 表示线性 ω 公式）。"""
    if func is None or callable(func):
        return func
    key = str(func).strip().lower()
    if key in ("", "none", "linear"):
        return None
    if key not in _EXPANSION_FUNCTIONS:
        raise ValueError(
            f"unknown expansion function {func!r}; "
            f"use one of {sorted(_EXPANSION_FUNCTIONS)}, None, or a callable"
        )
    return _EXPANSION_FUNCTIONS[key]


def _get_engineering_swelling_params(params):
    """Read geometry/concentration parameters for engineering swelling estimate."""
    try:
        pack = {
            "L_n": params["Negative electrode thickness [m]"],
            "L_p": params["Positive electrode thickness [m]"],
            "c_n_init": params["Initial concentration in negative electrode [mol.m-3]"],
            "c_p_init": params["Initial concentration in positive electrode [mol.m-3]"],
        }
    except Exception as exc:
        logger.warning(
            "Missing geometry/concentration params (%s); using approximate defaults for swelling estimate.",
            exc,
        )
        pack = {
            "L_n": 85e-6,
            "L_p": 75e-6,
            "c_n_init": 25000,
            "c_p_init": 1000,
        }

    def _optional(key):
        try:
            return params[key]
        except Exception:
            return None

    # 非线性膨胀函数需要最大浓度；不可逆项需要负极比表面积
    pack["c_n_max"] = _optional("Maximum concentration in negative electrode [mol.m-3]")
    pack["c_p_max"] = _optional("Maximum concentration in positive electrode [mol.m-3]")
    pack["a_n"] = _optional("Negative electrode surface area to volume ratio [m-1]")
    if pack["a_n"] is None:
        # PyBaMM 参数集常不直接提供比表面积：用 a = 3·ε_act/R 估算
        eps_act = _optional("Negative electrode active material volume fraction")
        r_n = _optional("Negative particle radius [m]")
        try:
            if eps_act is not None and r_n:
                pack["a_n"] = 3.0 * float(eps_act) / float(r_n)
        except Exception:
            pass
    return pack


_IRREVERSIBLE_THICKNESS_VARS = (
    "X-averaged negative SEI thickness [m]",
    "X-averaged negative lithium plating thickness [m]",
    "X-averaged negative dead lithium thickness [m]",
)


def _time_profile(variable):
    """把 (空间 x 时间) entries 压成时间序列。"""
    profile = np.asarray(variable.entries, dtype=float)
    if profile.ndim > 1:
        profile = np.mean(profile, axis=0)
    return profile.reshape(-1)


def _add_profiles(a, b):
    """对齐长度后逐点相加（a 可为 None）。"""
    if a is None:
        return b
    n = min(len(a), len(b))
    return a[:n] + b[:n]


def _irreversible_film_thickness(cycle):
    """副反应产物等效膜厚时间序列（SEI + 析锂 + 死锂 + 裂纹SEI×(粗糙度-1)）。

    口径与 PyBaMM ReactionDriven 孔隙率子模型一致；返回 None 表示解中
    没有任何副反应厚度变量。
    """
    total = None
    for name in _IRREVERSIBLE_THICKNESS_VARS:
        try:
            profile = _time_profile(cycle[name])
        except Exception:
            continue
        total = _add_profiles(total, profile)
    try:
        cr = _time_profile(cycle["X-averaged negative SEI on cracks thickness [m]"])
        rough = _time_profile(cycle["X-averaged negative electrode roughness ratio"])
        n = min(len(cr), len(rough))
        total = _add_profiles(total, cr[:n] * (rough[:n] - 1.0))
    except Exception:
        pass
    return total


def _irreversible_displacement(cycle, param_pack, beta_irreversible, run_state):
    """不可逆副反应位移 = β·a_n·L_n·Δδ_film。

    把单颗粒表面膜厚换算成电极级体积（乘比表面积 a_n 与电极厚度 L_n），
    再按顶出系数 β 折算为厚度增长（其余体积视为被孔隙吸收）。
    缺少 a_n 参数时禁用该项并告警一次。
    """
    film = _irreversible_film_thickness(cycle)
    if film is None or film.size == 0:
        return 0.0
    a_n = param_pack.get("a_n")
    if not a_n:
        if not run_state.get("warned_a_n"):
            logger.warning(
                "'Negative electrode surface area to volume ratio [m-1]' missing; "
                "irreversible swelling term disabled."
            )
            run_state["warned_a_n"] = True
        return 0.0
    if run_state.get("film_ref") is None:
        run_state["film_ref"] = float(film[0])
    return beta_irreversible * a_n * param_pack["L_n"] * (film - run_state["film_ref"])


def _electrode_breathing(c_avg, c_init, c_max, L, omega, f_expansion, run_state, warn_key):
    """单电极可逆呼吸位移：优先非线性 f(sto)，缺 c_max 时回退线性 ω 公式。"""
    if f_expansion is not None and c_max:
        sto = np.asarray(c_avg, dtype=float) / c_max
        return L * (f_expansion(sto) - f_expansion(c_init / c_max))
    if f_expansion is not None and not run_state.get(warn_key):
        logger.warning(
            "Maximum concentration parameter missing (%s); falling back to linear omega swelling.",
            warn_key,
        )
        run_state[warn_key] = True
    return L * (1 / 3) * omega * (np.asarray(c_avg, dtype=float) - c_init)


def _engineering_swelling_displacement(
    cycle, param_pack, omega_n, omega_p, f_n, f_p, beta_irreversible, run_state
):
    """由浓度/副反应状态计算电芯厚度位移时间序列。"""
    c_n_raw = cycle["X-averaged negative particle concentration [mol.m-3]"].entries
    c_p_raw = cycle["X-averaged positive particle concentration [mol.m-3]"].entries
    c_n_avg = np.mean(c_n_raw, axis=0) if getattr(c_n_raw, "ndim", 1) > 1 else c_n_raw
    c_p_avg = np.mean(c_p_raw, axis=0) if getattr(c_p_raw, "ndim", 1) > 1 else c_p_raw

    delta_L_n = _electrode_breathing(
        c_n_avg, param_pack["c_n_init"], param_pack.get("c_n_max"),
        param_pack["L_n"], omega_n, f_n, run_state, "warned_c_n_max",
    )
    delta_L_p = _electrode_breathing(
        c_p_avg, param_pack["c_p_init"], param_pack.get("c_p_max"),
        param_pack["L_p"], omega_p, f_p, run_state, "warned_c_p_max",
    )

    reversible = np.asarray(delta_L_n + delta_L_p, dtype=float).reshape(-1)
    irreversible = _irreversible_displacement(cycle, param_pack, beta_irreversible, run_state)
    if np.ndim(irreversible) == 0:
        return reversible + irreversible
    return _add_profiles(reversible, np.asarray(irreversible, dtype=float).reshape(-1))


def _pybamm_thickness_displacement(cycle, param_pack, beta_irreversible, run_state):
    """PyBaMM mechanics 厚度变化（粒子膨胀）+ 副反应不可逆位移。"""
    disp = np.asarray(cycle["Cell thickness change [m]"].entries, dtype=float).reshape(-1)
    irreversible = _irreversible_displacement(cycle, param_pack, beta_irreversible, run_state)
    if np.ndim(irreversible) == 0:
        return disp + irreversible
    return _add_profiles(disp, np.asarray(irreversible, dtype=float).reshape(-1))


def _resolve_swelling_displacement(
    cycle, method, param_pack, omega_n, omega_p, f_n, f_p, beta_irreversible, run_state
):
    """Resolve displacement profile and actual source method for one cycle."""
    if method == "pybamm_thickness":
        try:
            return (
                _pybamm_thickness_displacement(cycle, param_pack, beta_irreversible, run_state),
                "pybamm_thickness",
            )
        except Exception:
            logger.warning(
                "Cell thickness change [m] unavailable; falling back to engineering swelling estimate."
            )

    return (
        _engineering_swelling_displacement(
            cycle, param_pack, omega_n, omega_p, f_n, f_p, beta_irreversible, run_state
        ),
        "engineering",
    )


def _apply_swelling_reference(displacement, reference, solution_reference):
    """Apply reference convention to a raw displacement profile."""
    displacement = np.asarray(displacement, dtype=float).reshape(-1)
    if displacement.size == 0:
        return displacement, solution_reference

    if reference == "cycle_start":
        return displacement - displacement[0], solution_reference

    if reference == "solution_start":
        if solution_reference is None:
            solution_reference = float(displacement[0])
        return displacement - solution_reference, solution_reference

    return displacement, solution_reference


def calculate_cycle_swelling(
    sol,
    params,
    return_components=False,
    omega_n=0.1 * 3.1e-6,
    omega_p=0,
    k_stiffness=1.0e9,
    k_cell=None,
    preload_force=0.0,
    beta_irreversible=1.0,
    expansion_function_n="graphite",
    expansion_function_p="lfp",
    method="engineering",
    reference="parameter_initial",
    return_table=False,
):
    """逐圈计算膨胀力分解指标。

    力学模型::

        F(t) = max(0, k_eff·ΔL(t) + preload_force)        # 单边接触
        ΔL   = ΔL_rev(呼吸) + ΔL_irr(副反应产物累积)
        k_eff = 1 / (1/k_stiffness + 1/k_cell)            # 夹具-电芯串联

    参数
    ----
    omega_n / omega_p : float
        线性偏摩尔体积系数（m^3/mol）。仅当对应 expansion_function_* 为
        None、或参数缺少最大浓度时作为回退公式使用。
    k_stiffness : float
        夹具刚度（N/m）。
    k_cell : float or None
        电芯堆叠刚度（N/m）；None 表示电芯视为刚性（k_eff = k_stiffness）。
    preload_force : float
        初始预紧力（N）。电芯收缩脱离夹具后力被钳制到 0（单边接触）。
    beta_irreversible : float
        副反应产物顶出系数 β∈[0,1]：产物体积转化为电芯厚度增长的比例，
        其余视为被孔隙吸收。
    expansion_function_n / expansion_function_p : str, callable or None
        电极厚度应变函数 f(sto)。内置 ``"graphite"``（分段非线性）与
        ``"lfp"``（线性，充电时与石墨反相抵消）；None 退回线性 ω 公式。
        需要参数 "Maximum concentration in ... electrode [mol.m-3]"，
        缺失时自动回退 ω 公式并告警。
    method : {"engineering", "pybamm_thickness"}
        位移来源。``engineering`` 用浓度-厚度估算；``pybamm_thickness``
        优先读取 PyBaMM mechanics 的 ``Cell thickness change [m]``，
        缺失时回退 engineering。两种方法均叠加副反应不可逆位移
        β·a_n·L_n·Δδ_film（δ_film 为 SEI/析锂/死锂/裂纹SEI 等效膜厚之和，
        需参数 "Negative electrode surface area to volume ratio [m-1]"）。
    reference : {"cycle_start", "solution_start", "parameter_initial"}
        位移零点。``parameter_initial`` 使用参数/模型初值为零点；
        ``solution_start`` 以整段解首个有效点为零点；``cycle_start``
        以每圈首点为零点。
    return_table : bool
        True 时返回结构化 pandas.DataFrame，优先于 ``return_components``。

    返回
    ----
    - return_table=True：
      DataFrame，列为 cycle/max_force_n/min_force_n/eoc_force_n/
      reversible_amplitude_n/max_disp_m/min_disp_m/source_method。
    - 默认： (max_forces, min_forces)
    - return_components=True：
      (max_forces, min_forces, eoc_forces, reversible_amplitudes)
      其中 eoc_forces 为圈末膨胀力，reversible_amplitudes = max-min。
    """
    method = _normalize_swelling_method(method)
    reference = _normalize_swelling_reference(reference)
    f_n = _resolve_expansion_function(expansion_function_n)
    f_p = _resolve_expansion_function(expansion_function_p)

    if k_cell is None:
        k_eff = k_stiffness
    else:
        if k_stiffness <= 0 or k_cell <= 0:
            raise ValueError("k_stiffness and k_cell must be positive")
        k_eff = 1.0 / (1.0 / k_stiffness + 1.0 / k_cell)

    if sol is None:
        if return_table:
            return _empty_swelling_table()
        if return_components:
            return np.array([]), np.array([]), np.array([]), np.array([])
        return np.array([]), np.array([])

    Omega_n = omega_n
    Omega_p = omega_p
    param_pack = _get_engineering_swelling_params(params)

    max_forces = []
    min_forces = []
    eoc_forces = []
    reversible_amplitudes = []
    rows = []
    solution_reference = None
    run_state = {}

    for cycle_number, cycle in enumerate(sol.cycles, start=1):
        displacement, source_method = _resolve_swelling_displacement(
            cycle, method, param_pack, Omega_n, Omega_p, f_n, f_p,
            beta_irreversible, run_state,
        )
        displacement, solution_reference = _apply_swelling_reference(
            displacement, reference, solution_reference
        )

        force_profile = np.maximum(
            np.asarray(k_eff * displacement + preload_force, dtype=float).reshape(-1),
            0.0,
        )
        if force_profile.size > 0:
            max_f = np.max(force_profile)
            min_f = np.min(force_profile)
            eoc_f = force_profile[-1]
            max_disp = np.max(displacement)
            min_disp = np.min(displacement)

            max_forces.append(max_f)
            min_forces.append(min_f)
            eoc_forces.append(eoc_f)
            reversible_amplitudes.append(max_f - min_f)
            rows.append(
                {
                    "cycle": cycle_number,
                    "max_force_n": max_f,
                    "min_force_n": min_f,
                    "eoc_force_n": eoc_f,
                    "reversible_amplitude_n": max_f - min_f,
                    "max_disp_m": max_disp,
                    "min_disp_m": min_disp,
                    "source_method": source_method,
                }
            )
        else:
            prev_max = max_forces[-1] if max_forces else 0
            prev_min = min_forces[-1] if min_forces else 0
            prev_eoc = eoc_forces[-1] if eoc_forces else 0
            max_forces.append(prev_max)
            min_forces.append(prev_min)
            eoc_forces.append(prev_eoc)
            reversible_amplitudes.append(prev_max - prev_min)
            rows.append(
                {
                    "cycle": cycle_number,
                    "max_force_n": prev_max,
                    "min_force_n": prev_min,
                    "eoc_force_n": prev_eoc,
                    "reversible_amplitude_n": prev_max - prev_min,
                    "max_disp_m": np.nan,
                    "min_disp_m": np.nan,
                    "source_method": source_method,
                }
            )

    max_forces = np.array(max_forces)
    min_forces = np.array(min_forces)
    eoc_forces = np.array(eoc_forces)
    reversible_amplitudes = np.array(reversible_amplitudes)

    if return_table:
        return _swelling_rows_to_table(rows)
    if return_components:
        return max_forces, min_forces, eoc_forces, reversible_amplitudes
    return max_forces, min_forces


def compute_cycle_energies(sol):
    """计算每圈的充放电容量、能量与能效（公共底层函数）。

    返回
    ----
    dict
        - discharge_cap: np.array  放电容量 (Ah)
        - e_charge: np.array       充电能量 (Wh)
        - e_discharge: np.array    放电能量 (Wh)
        - efficiency: np.array     能效 (discharge/charge)
        - cycle_index: np.array    保留圈对应的原始圈号（空圈会被跳过，用此键对齐 x 轴）
    """
    if sol is None:
        empty = np.array([])
        return {
            "discharge_cap": empty,
            "e_charge": empty,
            "e_discharge": empty,
            "efficiency": empty,
            "cycle_index": np.array([], dtype=int),
        }

    caps, e_chgs, e_dchgs, cycle_idx = [], [], [], []
    for i_cycle, cycle in enumerate(sol.cycles):
        current = cycle["Current [A]"].entries
        V = cycle["Voltage [V]"].entries
        t = cycle["Time [h]"].entries

        mask_dchg = current > 0
        q_dchg = np.trapz(current[mask_dchg], t[mask_dchg]) if np.any(mask_dchg) else 0

        mask_chg = current < 0
        e_chg = abs(np.trapz(current[mask_chg] * V[mask_chg], t[mask_chg])) if np.any(mask_chg) else 0
        e_dchg = np.trapz(current[mask_dchg] * V[mask_dchg], t[mask_dchg]) if np.any(mask_dchg) else 0

        if q_dchg > 0 or e_chg > 0:
            caps.append(q_dchg)
            e_chgs.append(e_chg)
            e_dchgs.append(e_dchg)
            cycle_idx.append(i_cycle)

    caps = np.array(caps)
    e_chgs = np.array(e_chgs)
    e_dchgs = np.array(e_dchgs)
    cycle_idx = np.array(cycle_idx, dtype=int)

    with np.errstate(divide="ignore", invalid="ignore"):
        efficiencies = np.abs(e_dchgs / e_chgs)
        efficiencies = np.nan_to_num(efficiencies)

    return {
        "discharge_cap": caps,
        "e_charge": e_chgs,
        "e_discharge": e_dchgs,
        "efficiency": efficiencies,
        "cycle_index": cycle_idx,
    }


def extract_all_metrics_from_sol(sol):
    """从单个仿真结果提取容量、充放电能量与能效。"""
    res = compute_cycle_energies(sol)
    return res["discharge_cap"], res["e_charge"], res["e_discharge"], res["efficiency"]
