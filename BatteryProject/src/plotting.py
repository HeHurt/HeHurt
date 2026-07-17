"""绘图工具与 BatteryPlotter 类。"""
import logging
import re

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from .config import DEFAULT_PLOT_STYLE, DEFAULT_FONT_SANS_SERIF
from .analysis import calculate_rrmse_from_sol

logger = logging.getLogger(__name__)


def _apply_default_style():
    """应用默认绘图风格与字体配置。"""
    try:
        if DEFAULT_PLOT_STYLE:
            plt.style.use(DEFAULT_PLOT_STYLE)
    except Exception as exc:
        logger.warning("Failed to apply plot style %r (%s); using matplotlib default.", DEFAULT_PLOT_STYLE, exc)
    if DEFAULT_FONT_SANS_SERIF:
        plt.rcParams["font.sans-serif"] = DEFAULT_FONT_SANS_SERIF
    plt.rcParams["axes.unicode_minus"] = False


class BatteryPlotter:
    def __init__(self):
        """初始化绘图器的实验/仿真数据容器与颜色分配器。"""
        _apply_default_style()
        self.exp_db = {}
        self.sim_db = {}
        self.color_map = {}
        self.color_pool = plt.cm.tab10(np.linspace(0, 1, 10))
        self.color_idx = 0

    def _get_normalized_key(self, label):
        """将标签归一化，用于实验/仿真曲线共用同一颜色。"""
        s = label.replace("(Sim)", "").replace("(Exp)", "").replace("_sim", "").replace("_exp", "")
        return s.lower().replace(" ", "").replace("°", "")

    def _get_color(self, label):
        """按归一化标签获取稳定颜色；首次出现时自动分配。"""
        key = self._get_normalized_key(label)
        if key not in self.color_map:
            self.color_map[key] = self.color_pool[self.color_idx % len(self.color_pool)]
            self.color_idx += 1
        return self.color_map[key]

    @staticmethod
    def _normalize_retention(retention):
        """保持率统一为 0–1 小数（全库内部表示）；百分制输入自动 /100。"""
        ret = np.asarray(retention, dtype=float)
        finite = ret[np.isfinite(ret)]
        if finite.size > 0 and finite.mean() > 2.0:
            ret = ret / 100.0
        return ret

    def add_exp_data(self, label, cycle, capacity, retention):
        """写入一组实验数据（循环数、容量、保持率）。

        retention 内部统一存 0–1 小数；传入百分制（均值 > 2）会自动 /100。
        绘图时由 plot() 统一 ×100 显示为百分比。
        """
        self.exp_db[label] = {"x": np.array(cycle), "cap": np.array(capacity), "ret": self._normalize_retention(retention)}

    def add_sim_data(self, label, cycle, capacity, retention):
        """写入一组仿真数据（循环数、容量、保持率）。

        retention 内部统一存 0–1 小数；传入百分制（均值 > 2）会自动 /100。
        绘图时由 plot() 统一 ×100 显示为百分比。
        """
        self.sim_db[label] = {"x": np.array(cycle), "cap": np.array(capacity), "ret": self._normalize_retention(retention)}

    def _resolve_keys(self, db, target):
        """将 target 解析为待绘制 key 列表。"""
        if target is None:
            return []
        if target == "all":
            return list(db.keys())
        if isinstance(target, str):
            return [k for k in db.keys() if target in k]
        if isinstance(target, tuple):
            return [k for k in db.keys() if all(kw in k for kw in target)]
        return target

    @staticmethod
    def _is_discharge_label(lbl):
        """判断标签是否为放电相关分量。"""
        s = str(lbl).lower()
        return any(token in s for token in ["_dchg", "discharge", "_dschg"])

    @classmethod
    def _is_charge_label(cls, lbl):
        """判断标签是否为充电相关分量（排除误判放电）。"""
        s = str(lbl).lower()
        return (any(token in s for token in ["_chg", "charge"])) and (not cls._is_discharge_label(lbl))

    @staticmethod
    def _finalize_axis(ax, title, xlabel, ylabel, xlim, ylim, invert_xaxis):
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, linestyle="--", alpha=0.4)
        if xlim:
            ax.set_xlim(xlim)
        if invert_xaxis:
            ax.invert_xaxis()
        if ylim:
            ax.set_ylim(ylim)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            by_label = dict(zip(labels, handles))
            ax.legend(by_label.values(), by_label.keys(), loc="best", fontsize=9)

    def plot(
        self,
        target_exp=None,
        target_sim=None,
        figsize=(14, 5),
        title_left="放电容量",
        ylabel_left="Capacity (mAh)",
        title_right="容量保持率",
        ylabel_right="Retention (%)",
        xlim=None,
        ylim_left=None,
        ylim_right=None,
        factor=1.0,
        bias=0.0,
        xlabel="Cycle Number",
        invert_xaxis=False,
        mode=None,
    ):
        """绘制实验/仿真容量与保持率对比图（左：容量，右：保持率）。

        历史上 ``mode="heat"`` 会切换到产热双图；该入口已迁移到
        :py:meth:`plot_heat`。``mode`` 参数仍接受但不再生效，传入
        ``"heat"`` 会发出 DeprecationWarning 并转发到 ``plot_heat``。
        """
        if mode is not None and str(mode).lower() == "heat":
            import warnings
            warnings.warn(
                "BatteryPlotter.plot(mode='heat') is deprecated; "
                "use BatteryPlotter.plot_heat(...) instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return self.plot_heat(
                target_exp=target_exp,
                target_sim=target_sim,
                figsize=figsize,
                xlim=xlim,
                ylim_left=ylim_left,
                ylim_right=ylim_right,
                factor=factor,
                bias=bias,
                xlabel=xlabel,
                invert_xaxis=invert_xaxis,
            )

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

        def _plot_lines(db, targets, style_type):
            keys_to_plot = sorted(self._resolve_keys(db, targets))
            for lbl in keys_to_plot:
                if lbl not in db:
                    continue
                data = db[lbl]
                color = self._get_color(lbl)
                y_left = data["cap"] * factor + bias
                y_right = data["ret"] * 100  # 内部 0–1 小数，显示为百分比
                if style_type == "exp":
                    kw = {"ls": "-", "lw": 2.0, "alpha": 0.7, "label": f"{lbl} (Exp)"}
                else:
                    kw = {"ls": "--", "lw": 2.5, "alpha": 0.9, "label": f"{lbl} (Sim)"}
                ax1.plot(data["x"], y_left, color=color, **kw)
                ax2.plot(data["x"], y_right, color=color, **kw)

        _plot_lines(self.exp_db, target_exp, style_type="exp")
        _plot_lines(self.sim_db, target_sim, style_type="sim")

        self._finalize_axis(ax1, title_left, xlabel, ylabel_left, xlim, ylim_left, invert_xaxis)
        self._finalize_axis(ax2, title_right, xlabel, ylabel_right, xlim, ylim_right, invert_xaxis)
        plt.tight_layout()
        return fig, (ax1, ax2)

    def plot_heat(
        self,
        target_exp=None,
        target_sim=None,
        figsize=(14, 5),
        title_left="充电产热",
        ylabel_left="功率 (W)",
        title_right="放电产热",
        ylabel_right="功率 (W)",
        xlim=None,
        ylim_left=None,
        ylim_right=None,
        factor=1.0,
        bias=0.0,
        xlabel="Cycle Number",
        invert_xaxis=False,
    ):
        """绘制充电产热（左）与放电产热（右）双图。

        通过标签关键字（``_chg`` / ``_dchg`` / ``charge`` / ``discharge``）
        路由：放电关键字命中走右图；其余（含未命中）走左图。
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

        def _plot_heat(db, targets, style_type):
            keys_to_plot = sorted(self._resolve_keys(db, targets))
            for lbl in keys_to_plot:
                if lbl not in db:
                    continue
                data = db[lbl]
                color = self._get_color(lbl)
                y_heat = data["cap"] * factor + bias
                if style_type == "exp":
                    kw = {"ls": "-", "lw": 2.0, "alpha": 0.7, "label": f"{lbl} (Exp)"}
                else:
                    kw = {"ls": "--", "lw": 2.5, "alpha": 0.9, "label": f"{lbl} (Sim)"}
                if self._is_discharge_label(lbl):
                    ax2.plot(data["x"], y_heat, color=color, **kw)
                else:
                    ax1.plot(data["x"], y_heat, color=color, **kw)

        _plot_heat(self.exp_db, target_exp, style_type="exp")
        _plot_heat(self.sim_db, target_sim, style_type="sim")

        self._finalize_axis(ax1, title_left, xlabel, ylabel_left, xlim, ylim_left, invert_xaxis)
        self._finalize_axis(ax2, title_right, xlabel, ylabel_right, xlim, ylim_right, invert_xaxis)
        plt.tight_layout()
        return fig, (ax1, ax2)


def different_cycle_voltage(sol, battery_model, rate, temperature, acceleration_factor=50):
    """绘制不同循环下的充/放电电压-容量曲线，并附循环色条。"""
    _apply_default_style()
    colors = plt.get_cmap("coolwarm")
    fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(20, 6), gridspec_kw={"width_ratios": [10, 10]})
    for i in range(0, len(sol.cycles), 1):
        t = sol.cycles[i]["Time [s]"].entries
        capacity = sol.cycles[i]["Throughput capacity [A.h]"].entries
        current = sol.cycles[i]["Current [A]"].entries
        t = t[current < 0] - t[current < 0][0]
        capacity = capacity[current < 0] - capacity[current < 0][0]
        voltage = sol.cycles[i]["Voltage [V]"].entries
        ax1.plot(capacity, voltage[current < 0], color=colors(i / len(sol.cycles)), lw=3)
    ax1.set_xlabel("Capacity (Ah)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title(f"Simulated charge curves of {battery_model} battery cells under {rate} cycle @{temperature}")
    for i in range(0, len(sol.cycles), 1):
        t = sol.cycles[i]["Time [s]"].entries
        capacity = sol.cycles[i]["Throughput capacity [A.h]"].entries
        current = sol.cycles[i]["Current [A]"].entries
        t = t[current > 0] - t[current > 0][0]
        capacity = capacity[current > 0] - capacity[current > 0][0]
        voltage = sol.cycles[i]["Voltage [V]"].entries
        ax2.plot(capacity, voltage[current > 0], color=colors(i / len(sol.cycles)), lw=3)
    ax2.set_xlabel("Capacity (Ah)")
    ax2.set_ylabel("Voltage (V)")
    ax2.set_title(f"Simulated discharge curves of {battery_model} battery cells under {rate} cycle @{temperature}")
    fig.subplots_adjust(right=0.85)
    cbar_ax = fig.add_axes([0.88, 0.15, 0.02, 0.7])
    sm = plt.cm.ScalarMappable(cmap=colors, norm=plt.Normalize(vmin=1, vmax=len(sol.cycles) * acceleration_factor))
    cbar = plt.colorbar(sm, cax=cbar_ax)
    cbar.set_label("Cycle Number")
    plt.tight_layout()


def subplot(nrows, ncols, colorbar=False):
    """创建按原始模型包风格缩放的多子图画布。"""
    figsize = matplotlib.rcParams["figure.figsize"]
    fig, ax = plt.subplots(nrows, ncols, figsize=(figsize[0] * ncols, figsize[1] * nrows))
    plt.subplots_adjust(wspace=0.25, hspace=0.25)
    plt.rcParams["axes.edgecolor"] = "black"

    if nrows == 1 and ncols == 1:
        bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    elif nrows == 1 or ncols == 1:
        bbox = ax[0].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    else:
        bbox = ax[0][0].get_window_extent().transformed(fig.dpi_scale_trans.inverted())

    ratio = 1.2 if colorbar else 1
    fig.set_size_inches(
        (figsize[0] * figsize[0] * ncols / bbox.width * ratio, figsize[1] * figsize[1] * nrows / bbox.height)
    )
    return fig, ax


def plot_analysis(sol, t_factor=50):
    """综合分析图：老化主图 + 充电末端析锂诊断。"""
    fig, ax = subplot(2, 4)
    sample_cycle = np.arange(1, len(sol.cycles), 1)
    plot_cycle_layer(ax[0, 0], sol, t_factor)
    plot_charge_discharge(sol, np.arange(1, len(sol.cycles), 5), t_factor, ax[0, 1])
    plot_electrolyte(ax[0, 2], sol, sample_cycle, t_factor)
    plot_plating_overpotential(ax[0, 3], sol, sample_cycle, t_factor)
    plot_charge_end_surface_stoichiometry(ax[1, 0], sol, sample_cycle, t_factor)
    plot_plating_term_decomposition(ax[1, 1], sol, sample_cycle, t_factor)
    plot_lithium_loss(ax[1, 2], sol, step=10)
    plot_porosity(ax[1, 3], sol)
    return fig, ax


def plot_cycle_layer(ax, sol, t_factor=50):
    """绘制 SOH 衰减曲线（每圈放电容量归一化）。"""
    from .analysis import get_discharge_capacity

    qd = get_discharge_capacity(sol).get("discharge_capacity", np.array([]))
    if qd.size <= 1 or not np.isfinite(qd[1]) or qd[1] == 0:
        return
    cycle = np.arange(0, t_factor * len(qd[1:]), t_factor)
    ax.plot(cycle, qd[1:] / qd[1], label="Sim")
    ax.set_xlabel("Cycle")
    ax.set_ylabel("SOH")
    ax.set_title("SOH degradation curve")
    ax.legend(prop={"size": 8, "weight": "normal"})


def plot_electrolyte(ax, sol, index, t_factor=50):
    """绘制不同循环下充电后负极电解液浓度最小值变化。"""
    con_electrolyte_sep_min = []
    con_electrolyte_col_min = []
    valid_index = []

    for cycle_no in index:
        try:
            x1 = sol.cycles[cycle_no]["Negative electrolyte concentration [mol.m-3]"].entries[0, :]
            x2 = sol.cycles[cycle_no]["Negative electrolyte concentration [mol.m-3]"].entries[-1, :]
        except Exception:
            continue
        con_electrolyte_col_min.append(np.min(x1))
        con_electrolyte_sep_min.append(np.min(x2))
        valid_index.append(cycle_no)

    if len(valid_index) == 0:
        return
    valid_index = np.asarray(valid_index)
    ax.plot(valid_index * t_factor, con_electrolyte_sep_min, label="Seperator")
    ax.plot(valid_index * t_factor, con_electrolyte_col_min, label="Collector")
    ax.legend()
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Electrolyte Concentration [mol.m-3]")
    ax.set_title("Minimum Concentration of Electrolyte on charging")


def plot_plating_analysis(sol, cycles):
    """绘制指定循环下析锂相关时序诊断图。"""
    fig, ax = subplot(2, 2)
    for i in cycles:
        t = sol.cycles[i]["Time [s]"].entries[:]
        t = t - t[0]

        plt_ax = ax[0, 0]
        plt_ax.plot(t, sol.cycles[i]["Negative electrode surface potential difference [V]"].entries[-1, :], label=i)
        plt_ax.set_ylabel("Surface potential difference [V]")
        plt_ax.set_xlabel("Time [s]")
        plt_ax.set_title("Surface potential difference at one cycle")
        plt_ax.legend()

        plt_ax = ax[0, 1]
        plt_ax.plot(t, sol.cycles[i]["Negative electrode SEI film overpotential [V]"].entries[-1, :], label=i)
        plt_ax.set_ylabel("SEI film overpotential [V]")
        plt_ax.set_xlabel("Time [s]")
        plt_ax.set_title("SEI film overpotential at one cycle")
        plt_ax.legend()

        plt_ax = ax[1, 0]
        plt_ax.plot(
            t,
            sol.cycles[i]["Negative electrode surface potential difference [V]"].entries[-1, :]
            + sol.cycles[i]["Negative electrode SEI film overpotential [V]"].entries[-1, :],
            label=i,
        )
        plt_ax.set_ylabel("Plating overpotential [V]")
        plt_ax.set_xlabel("Time [s]")
        plt_ax.set_title("Plating overpotential at one cycle")
        plt_ax.legend()

        plt_ax = ax[1, 1]
        plt_ax.plot(
            t,
            sol.cycles[i]["Negative lithium plating interfacial current density [A.m-2]"].entries[-1, :],
            label=i,
        )
        plt_ax.set_ylabel("Plating interfacial current density [A.m-2]")
        plt_ax.set_xlabel("Time [s]")
        plt_ax.set_title("Plating interfacial current density at one cycle")
        plt_ax.legend()
    return fig, ax


def plot_lithium_loss(ax, sol, step=1):
    """绘制老化组分容量损失分解曲线。"""
    Qt = sol["Throughput capacity [A.h]"].entries[::step]
    Q_SEI = sol["Loss of capacity to negative SEI [A.h]"].entries[::step]
    Q_SEI_cr = sol["Loss of capacity to negative SEI on cracks [A.h]"].entries[::step]
    Q_plating = sol["Loss of capacity to negative lithium plating [A.h]"].entries[::step]
    Q_side = sol["Total capacity lost to side reactions [A.h]"].entries[::step]
    Q_LLI = sol["Total lithium lost [mol]"].entries[::step] * 96485.3 / 3600
    Q_LAM = sol["Loss of lithium due to loss of active material in negative electrode [mol]"].entries[::step] * 96485.3 / 3600
    ax.plot(Qt, Q_SEI, label="SEI", linestyle="dashed")
    ax.plot(Qt, Q_SEI_cr, label="SEI on cracks", linestyle="dashdot")
    ax.plot(Qt, Q_plating, label="Li plating", linestyle="dotted")
    ax.plot(Qt, Q_side, label="All side reactions", linestyle=(0, (6, 1)))
    ax.plot(Qt, Q_LAM, label="LAM")
    ax.plot(Qt, Q_LLI, label="All LLI")
    ax.set_xlabel("Throughput capacity (Ah)")
    ax.set_ylabel("Capacity loss (Ah)")
    ax.set_title("Aging components decomposition")
    ax.legend()


def plot_charge_discharge(sol, index, t_factor=50, input_ax=None):
    """绘制多个循环的整段充放电电压-时间曲线。"""
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors

    if len(index) == 0:
        return

    if input_ax is None:
        fig, ax = subplot(1, 1, True)
    else:
        ax = input_ax
    colors = plt.get_cmap("coolwarm")
    norm1 = mcolors.Normalize(vmin=index[0] * t_factor, vmax=index[-1] * t_factor)
    im1 = cm.ScalarMappable(norm=norm1, cmap=colors)
    for cycle_no in index:
        ax.plot(
            sol.cycles[cycle_no]["Time [s]"].entries - sol.cycles[cycle_no]["Time [s]"].entries[0],
            sol.cycles[cycle_no]["Voltage [V]"].entries,
            color=colors(cycle_no / index[-1]),
        )
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Voltage [V]")
        ax.set_title("Charge and Discharge curve at different cycle")
    if input_ax is None:
        fig.colorbar(im1, ax=ax, label="Cycle")


def _collect_charge_diagnostics(sol, sample_cycle):
    """收集充电段的析锂诊断量。"""
    diagnostics = {
        "cycle": [],
        "eta_min": [],
        "delta_phi_at_eta_min": [],
        "eta_sei_at_eta_min": [],
        "sto_xav_charge_end": [],
        "sto_max_charge_end": [],
    }

    for cycle in sample_cycle:
        try:
            cycle_solution = sol.cycles[cycle]
            current = np.asarray(cycle_solution["Current [A]"].entries).reshape(-1)
            charge_index = np.flatnonzero(current < 0)
            if charge_index.size == 0:
                continue

            eta_charge = np.asarray(
                cycle_solution[
                    "Negative electrode lithium plating reaction overpotential [V]"
                ].entries
            )[..., charge_index]
            delta_phi_charge = np.asarray(
                cycle_solution["Negative electrode surface potential difference [V]"].entries
            )[..., charge_index]
            eta_sei_charge = np.asarray(
                cycle_solution["Negative electrode SEI film overpotential [V]"].entries
            )[..., charge_index]

            eta_min_index = np.unravel_index(np.argmin(eta_charge), eta_charge.shape)
            charge_end_index = int(charge_index[-1])
            sto_xav = np.asarray(
                cycle_solution["X-averaged negative particle surface stoichiometry"].entries
            ).reshape(-1)
            sto_field = np.asarray(
                cycle_solution["Negative particle surface stoichiometry"].entries
            )[..., charge_end_index]

            diagnostics["cycle"].append(cycle)
            diagnostics["eta_min"].append(float(np.min(eta_charge)))
            diagnostics["delta_phi_at_eta_min"].append(
                float(np.asarray(delta_phi_charge[eta_min_index]))
            )
            diagnostics["eta_sei_at_eta_min"].append(
                float(np.asarray(eta_sei_charge[eta_min_index]))
            )
            diagnostics["sto_xav_charge_end"].append(float(sto_xav[charge_end_index]))
            diagnostics["sto_max_charge_end"].append(float(np.max(np.asarray(sto_field))))
        except (IndexError, KeyError, TypeError, ValueError):
            continue

    return {key: np.asarray(value) for key, value in diagnostics.items()}


def plot_charge_end_surface_stoichiometry(ax, sol, sample_cycle, t_factor):
    """绘制充电末端负极表面化学计量比。"""
    diagnostics = _collect_charge_diagnostics(sol, sample_cycle)
    cycle = diagnostics["cycle"] * t_factor
    if cycle.size == 0:
        return

    ax.plot(cycle, diagnostics["sto_xav_charge_end"], label="X-averaged")
    ax.plot(cycle, diagnostics["sto_max_charge_end"], label="Global max", linestyle="dashed")
    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Surface stoichiometry")
    ax.set_title("Negative surface stoichiometry at charge end")
    ax.legend()


def plot_plating_term_decomposition(ax, sol, sample_cycle, t_factor):
    """绘制充电段最危险位置处的 Δφ 与 η_SEI 分解。"""
    diagnostics = _collect_charge_diagnostics(sol, sample_cycle)
    cycle = diagnostics["cycle"] * t_factor
    if cycle.size == 0:
        return

    ax.plot(cycle, diagnostics["delta_phi_at_eta_min"], label=r"$\Delta\phi$ at min $\eta$")
    ax.plot(
        cycle,
        diagnostics["eta_sei_at_eta_min"],
        label=r"$\eta_{SEI}$ at min $\eta$",
        linestyle="dashed",
    )
    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Potential (V)")
    ax.set_title("Potential terms at charge-only minimum plating overpotential")
    ax.legend()


def plot_plating_overpotential(ax, sol, sample_cycle, t_factor):
    """绘制充电段全域析锂反应过电位最小值随循环变化。"""
    diagnostics = _collect_charge_diagnostics(sol, sample_cycle)
    cycle = diagnostics["cycle"] * t_factor
    if cycle.size == 0:
        return
    ax.plot(cycle, diagnostics["eta_min"], label="Charge-only global minimum")
    ax.legend()
    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Minimum Negative overpotential (V)", fontsize=12)
    ax.set_title("Charge-only global minimum negative overpotential", fontsize=12)


def plot_sei(ax, sol):
    """绘制 SEI 厚度分解（总/内层/外层/裂纹）。"""
    Qt = sol["Throughput capacity [A.h]"].entries
    L_SEI = sol["X-averaged negative total SEI thickness [m]"].entries
    L_SEI_outer = sol["X-averaged negative outer SEI thickness [m]"].entries
    L_SEI_inner = sol["X-averaged negative inner SEI thickness [m]"].entries
    L_SEI_crack = sol["X-averaged negative SEI on cracks thickness [m]"].entries
    ax.plot(Qt, L_SEI, label="Total")
    ax.plot(Qt, L_SEI_outer, label="Outer")
    ax.plot(Qt, L_SEI_inner, label="Inner")
    ax.plot(Qt, L_SEI_crack, label="crack")
    ax.set_ylabel("SEI thickness [m]")
    ax.set_xlabel("Throughput capacity [A.h]")
    ax.set_title("Decompose of SEI")
    ax.legend()


def plot_porosity(ax, sol, step=1):
    """绘制负极孔隙率随吞吐容量变化。"""
    Qt = sol["Throughput capacity [A.h]"].entries[::step]
    eps_neg_avg = sol["X-averaged negative electrode porosity"].entries[::step]
    eps_neg_sep = sol["Negative electrode porosity"].entries[-1, ::step]
    eps_neg_CC = sol["Negative electrode porosity"].entries[0, ::step]
    ax.plot(Qt, eps_neg_avg, label="Average")
    ax.plot(Qt, eps_neg_sep, label="Separator", linestyle="dotted")
    ax.plot(Qt, eps_neg_CC, label="Current collector", linestyle="dashed")
    ax.set_xlabel("Throughput capacity (Ah)")
    ax.set_ylabel("Negative electrode porosity")
    ax.set_title("Porosity vs. Cycle number")
    ax.legend()


def plot_overpotential(ax, sol, sample_cycle):
    """绘制单圈多种过电位时序。"""
    t = sol.cycles[sample_cycle]["Time [s]"].entries
    t = t - t[0]
    ax.plot(t, sol.cycles[sample_cycle]["X-averaged battery concentration overpotential [V]"].entries, label=r"$\eta_{concentration}$")
    ax.plot(t, sol.cycles[sample_cycle]["X-averaged battery negative reaction overpotential [V]"].entries, label=r"$\eta_{reaction}$")
    ax.plot(t, sol.cycles[sample_cycle]["X-averaged electrolyte overpotential [V]"].entries, label=r"$\eta_{electrolyte}$")
    ax.plot(t, sol.cycles[sample_cycle]["X-averaged SEI film overpotential [V]"].entries, label=r"$\eta_{SEI}$")
    ax.legend()
    ax.set_ylabel("Over Potential [V]")
    ax.set_xlabel("Time [s]")
    ax.set_title("Different OverPotential")


def matplotlib_to_plotly(cmap, pl_entries):
    """将 matplotlib colormap 转为 Plotly colorscale。"""
    cmap = plt.get_cmap(cmap)
    h = 1.0 / (pl_entries - 1)
    pl_colorscale = []
    for k in range(pl_entries):
        C = list(map(np.uint8, np.array(cmap(k * h)[:3]) * 255))
        pl_colorscale.append([k * h, "rgb" + str((C[0], C[1], C[2]))])
    return pl_colorscale


def plot_efficiency_vs_cycle(sol, acceleration_factor=50):
    """绘制单个工况的能量效率与充放电能量随循环变化曲线。"""
    if sol is None:
        return None

    from .analysis import compute_cycle_energies

    res = compute_cycle_energies(sol)
    efficiency = res["efficiency"]
    e_discharge = res["e_discharge"]
    e_charge = res["e_charge"]
    if len(efficiency) == 0:
        return None

    x = res["cycle_index"] * acceleration_factor

    # 使用一行两列子图：左图为能效，右图为充放电能量
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(x, efficiency, marker='o', linestyle='-', color='b')
    ax1.set_xlabel('Cycle Number')
    ax1.set_ylabel('Energy efficiency')
    ax1.set_title('Energy efficiency vs Cycle Number')
    ax1.grid(True)

    ax2.plot(x, np.array(e_discharge), marker='o', linestyle='-', color='b', label='Discharge')
    ax2.plot(x, np.abs(np.array(e_charge)), marker='o', linestyle='-', color='red', label='Charge')
    ax2.legend()
    ax2.set_xlabel('Cycle Number')
    ax2.set_ylabel('Energy (Wh)')
    ax2.set_title('Energy vs Cycle Number')
    ax2.grid(True)

    plt.tight_layout()


def plot_efficiency_vs_cycle_all(sol_list, rate_range, cycles_per_block=50, xlim=None, ylim=None):
    """
    绘制所有倍率下的能效随循环变化曲线，包含图例。
    """
    from .analysis import compute_cycle_energies

    plt.figure(figsize=(10, 6))
    for sol, rate in zip(sol_list, rate_range):
        if sol is None:
            continue
        res = compute_cycle_energies(sol)
        efficiency = res["efficiency"]
        if len(efficiency) == 0:
            continue
        x = res["cycle_index"] * cycles_per_block
        plt.plot(x, efficiency, marker='o', linestyle='-', label=f'{rate}P')

    plt.xlabel('Cycle Number')
    plt.ylabel('Energy efficiency')
    plt.title('Energy efficiency vs Cycle Number (All Rates)')
    plt.legend()
    plt.grid(True)

    if xlim is not None:
        plt.xlim(xlim)
    if ylim is not None:
        plt.ylim(ylim)


def _short_rate_label(label: str) -> str:
    """从原始标签中提取简短倍率标记（如 0.5P、1P）。"""
    match = re.search(r"([0-9]*\.?[0-9]+)P", str(label))
    return f"{match.group(1)}P" if match else str(label)


def _short_temp_label(label: str) -> str:
    """从标签中提取温度标记（如 25°C、-10°C）。"""
    match = re.search(r"(-?[0-9]+(?:\.[0-9]+)?)\s*°?C", str(label), flags=re.IGNORECASE)
    if not match:
        return ""
    value = match.group(1)
    return f"{value}°C"


def _normalize_filter_text(text: str) -> str:
    """统一筛选文本格式（小写、去空白、温标符号归一）。"""
    return str(text).strip().lower().replace("℃", "°c")


def _split_filter_total(filter_total):
    """将综合筛选条件拆分为温度关键词与倍率/工况关键词。"""
    if filter_total is None:
        return [], []

    tokens = [filter_total] if isinstance(filter_total, str) else list(filter_total)
    temp_tokens = []
    rate_tokens = []
    for token in tokens:
        s = _normalize_filter_text(token)
        if not s:
            continue
        # 约定：温度筛选必须显式包含 °c 或 ℃
        if "°c" in s:
            temp_tokens.append(s)
        else:
            # 非温度项统一视作倍率/工况关键词（支持 P、C 等）
            rate_tokens.append(s)
    return temp_tokens, rate_tokens


def _match_any(tokens, text: str):
    """判断文本是否命中任一关键词；无关键词时默认通过。"""
    if not tokens:
        return True
    t = _normalize_filter_text(text)
    return any(tok in t for tok in tokens)


def _match_filter_total(rate_label: str, raw_label: str, filter_total=None):
    """综合判断当前曲线是否满足温度与倍率筛选条件。"""
    temp_tokens, rate_tokens = _split_filter_total(filter_total)
    raw = str(raw_label)
    rate = str(rate_label)

    temp_ok = _match_any(temp_tokens, raw)
    # 倍率关键词优先匹配 rate_label，也允许在原始 label 中匹配
    rate_ok = _match_any(rate_tokens, rate) or _match_any(rate_tokens, raw)
    return temp_ok and rate_ok


def _resolve_swelling_x(sol, point_count, x_axis="cycle", acceleration_factor=50):
    """解析膨胀图横坐标：支持循环数或 SOH。"""
    x_axis_norm = str(x_axis).strip().lower()
    if x_axis_norm == "soh":
        from .analysis import get_discharge_capacity

        caps = get_discharge_capacity(sol).get("discharge_capacity", np.array([]))
        caps = np.asarray(caps).reshape(-1)
        if caps.size > 0 and np.isfinite(caps[0]) and caps[0] != 0:
            soh = (caps / caps[0]) * 100.0
            valid_count = min(point_count, soh.size)
            return soh[:valid_count], "SOH (%)", valid_count

    x = np.arange(1, point_count + 1) * acceleration_factor
    return x, "Cycle Number", point_count


def plot_swelling_for_condition(
    sol,
    label,
    params,
    x_axis="cycle",
    acceleration_factor=50,
    omega_n=0.1 * 3.1e-6,
    omega_p=0,
    k_stiffness=1.0e9,
    preload_force=0.0,
    method="engineering",
    reference="parameter_initial",
    **swelling_kwargs,
):
    """绘制单一工况的膨胀分解图（基线/振幅）与包络图（最大/最小）。"""
    from .analysis import calculate_cycle_swelling

    max_f, min_f, eoc_f, amp_f = calculate_cycle_swelling(
        sol,
        params,
        return_components=True,
        omega_n=omega_n,
        omega_p=omega_p,
        k_stiffness=k_stiffness,
        preload_force=preload_force,
        method=method,
        reference=reference,
        **swelling_kwargs,
    )
    if len(max_f) == 0:
        return

    x_vals, x_label, valid_count = _resolve_swelling_x(
        sol,
        len(max_f),
        x_axis=x_axis,
        acceleration_factor=acceleration_factor,
    )
    max_f = max_f[:valid_count]
    min_f = min_f[:valid_count]
    eoc_f = eoc_f[:valid_count]
    amp_f = amp_f[:valid_count]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))

    ax1.plot(x_vals, eoc_f, label=f"{label} Irreversible Baseline (EOC)")
    ax1.plot(x_vals, amp_f, label=f"{label} Reversible Amplitude (max-min)")
    ax1.set_xlabel(x_label)
    ax1.set_ylabel("Force (N)")
    ax1.set_title("Swelling Decomposition: Baseline vs Amplitude")
    if str(x_axis).strip().lower() == "soh":
        ax1.invert_xaxis()
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2.plot(x_vals, max_f, label=f"{label} Max Swelling Force")
    ax2.plot(x_vals, min_f, label=f"{label} Min Swelling Force")
    ax2.set_xlabel(x_label)
    ax2.set_ylabel("Force (N)")
    ax2.set_title("Swelling Envelope (Original Definition)")
    if str(x_axis).strip().lower() == "soh":
        ax2.invert_xaxis()
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()


def plot_swelling(
    sol_list,
    sim_labels_list,
    params,
    x_axis="cycle",
    acceleration_factor=50,
    filter_total=None,
    omega_n=0.1 * 3.1e-6,
    omega_p=0,
    k_stiffness=1.0e9,
    preload_force=0.0,
    method="engineering",
    reference="parameter_initial",
    **swelling_kwargs,
):
    """对比多工况膨胀分量，并可按温度/倍率条件筛选。"""
    from .analysis import calculate_cycle_swelling

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    x_label = "Cycle Number" if str(x_axis).strip().lower() != "soh" else "SOH (%)"
    total_env_data = []

    # 若同倍率对应多个温度，图例自动带温度以避免重名
    all_rate_labels = [_short_rate_label(lbl) for lbl in sim_labels_list]
    duplicated_rates = {r for r in all_rate_labels if all_rate_labels.count(r) > 1}

    for idx, (sol, label) in enumerate(zip(sol_list, sim_labels_list)):
        if sol is None:
            continue
        max_f, min_f, eoc_f, amp_f = calculate_cycle_swelling(
            sol,
            params,
            return_components=True,
            omega_n=omega_n,
            omega_p=omega_p,
            k_stiffness=k_stiffness,
            preload_force=preload_force,
            method=method,
            reference=reference,
            **swelling_kwargs,
        )
        if len(eoc_f) == 0:
            continue

        x_vals, x_label, valid_count = _resolve_swelling_x(
            sol,
            len(eoc_f),
            x_axis=x_axis,
            acceleration_factor=acceleration_factor,
        )
        max_f = max_f[:valid_count]
        min_f = min_f[:valid_count]
        eoc_f = eoc_f[:valid_count]
        amp_f = amp_f[:valid_count]
        rate_label = _short_rate_label(label)
        temp_label = _short_temp_label(label)
        display_label = f"{temp_label} {rate_label}".strip() if rate_label in duplicated_rates and temp_label else rate_label
        color = plt.cm.tab10(idx % 10)

        if not _match_filter_total(rate_label, label, filter_total=filter_total):
            continue

        # 子图：分别绘制不可逆基线与可逆振幅
        ax1.plot(x_vals, eoc_f, label=display_label, color=color)
        ax2.plot(x_vals, amp_f, label=display_label, color=color)
        total_env_data.append((x_vals, max_f, min_f, display_label, color))

    ax1.set_title("Irreversible Baseline")
    ax1.set_xlabel(x_label)
    ax1.set_ylabel("Force (N)")
    if str(x_axis).strip().lower() == "soh":
        ax1.invert_xaxis()
    ax1.grid(True, linestyle="--", alpha=0.4)
    handles1, labels1 = ax1.get_legend_handles_labels()
    if handles1:
        ax1.legend(title="Condition")

    ax2.set_title("Reversible Amplitude")
    ax2.set_xlabel(x_label)
    ax2.set_ylabel("Force (N)")
    if str(x_axis).strip().lower() == "soh":
        ax2.invert_xaxis()
    ax2.grid(True, linestyle="--", alpha=0.4)
    handles2, labels2 = ax2.get_legend_handles_labels()
    if handles2:
        ax2.legend(title="Condition")

    plt.tight_layout()

    if total_env_data:
        fig_total, ax_total = plt.subplots(1, 1, figsize=(8, 5))
        for x_vals, max_f, min_f, rate_label, color in total_env_data:
            # 总包络图：同色实线为 Max，虚线为 Min
            ax_total.plot(x_vals, max_f, color=color, linestyle="-", linewidth=2.0, label=f"{rate_label} Max")
            ax_total.plot(x_vals, min_f, color=color, linestyle="--", linewidth=2.0, label=f"{rate_label} Min")

        ax_total.set_title("Total Swelling Envelope: Max and Min")
        ax_total.set_xlabel(x_label)
        ax_total.set_ylabel("Force (N)")
        if str(x_axis).strip().lower() == "soh":
            ax_total.invert_xaxis()
        ax_total.grid(True, linestyle="--", alpha=0.4)
        ax_total.legend(title="Condition / Type")
        plt.tight_layout()
    else:
        logger.warning("未找到匹配过滤条件的数据（filter_total=%s），已跳过总包络图。", filter_total)


def plot_swelling_coupling(
    sol,
    label,
    params,
    x_axis="cycle",
    acceleration_factor=50,
    pressure_history=None,
    cycles_per_block=None,
    **swelling_kwargs,
):
    """绘制膨胀力-孔隙率耦合总览：左=力包络（max/min/EOC），右=真实孔隙率+面压。

    横轴支持 ``x_axis="cycle"``（圈数 × acceleration_factor）或 ``"soh"``，
    与 :func:`plot_swelling_for_condition` 同款切换（SOH 模式自动反转横轴）。

    右图实线为仿真**真实**孔隙率状态量（``X-averaged ... porosity``，随
    SEI/析锂堵孔下跌——孔隙率损失主因）；红虚线为耦合面压（力学，二阶量）。

    Parameters
    ----------
    pressure_history : array-like or None
        ``SwellingCoupler.history["pressure_pa"]``（逐 block 面压，Pa）。
        None 时右图只画孔隙率。
    cycles_per_block : int or None
        每 block 仿真圈数，用于把面压点映射到横轴；提供 pressure_history 时必填。
    **swelling_kwargs :
        透传给 :func:`calculate_cycle_swelling` 的力模型参数
        （如 ``**coupler.swelling_kwargs``，保证与耦合器一致）。

    Returns
    -------
    (fig, (ax1, ax2)) 或 None（无有效数据时）。
    """
    from .analysis import calculate_cycle_swelling

    if pressure_history is not None and cycles_per_block is None:
        raise ValueError("提供 pressure_history 时必须同时给 cycles_per_block")

    max_f, min_f, eoc_f, _ = calculate_cycle_swelling(
        sol, params, return_components=True, **swelling_kwargs
    )
    if len(max_f) == 0:
        return None

    x_vals, x_label, valid_count = _resolve_swelling_x(
        sol, len(max_f), x_axis=x_axis, acceleration_factor=acceleration_factor
    )
    x_vals = np.asarray(x_vals)[:valid_count]
    max_f = max_f[:valid_count]
    min_f = min_f[:valid_count]
    eoc_f = eoc_f[:valid_count]
    invert = str(x_axis).strip().lower() == "soh"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))

    # 左：膨胀力包络
    ax1.plot(x_vals, max_f, "o-", lw=2, ms=4, label=f"{label} Max force")
    ax1.plot(x_vals, min_f, "s-", lw=2, ms=4, label=f"{label} Min force")
    ax1.plot(x_vals, eoc_f, "^--", lw=1.5, ms=3, label=f"{label} EOC force")
    ax1.fill_between(x_vals, min_f, max_f, alpha=0.1)
    ax1.set_xlabel(x_label)
    ax1.set_ylabel("Force (N)")
    ax1.set_title("Swelling Force Envelope")
    ax1.legend(fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.4)

    # 右：真实孔隙率状态量（每圈末）
    porosity_vars = (
        ("X-averaged negative electrode porosity", "eps_n", "tab:blue", "o-"),
        ("X-averaged separator porosity", "eps_s", "tab:orange", "s-"),
        ("X-averaged positive electrode porosity", "eps_p", "tab:green", "^-"),
    )
    legend_lines = []
    for var, lbl, color, style in porosity_vars:
        try:
            eps = np.array(
                [float(c[var].entries[-1]) for c in sol.cycles]
            )[:valid_count]
        except Exception:
            continue
        ln, = ax2.plot(x_vals, eps, style, color=color, lw=1.6, ms=4, label=lbl)
        legend_lines.append(ln)
    ax2.set_xlabel(x_label)
    ax2.set_ylabel("Porosity (-)")
    ax2.grid(True, linestyle="--", alpha=0.4)

    # 右轴：面压（逐 block 映射到同一横轴）
    if pressure_history is not None:
        pressure = np.asarray(pressure_history, dtype=float)
        ax2b = ax2.twinx()

        def _block_x(k):
            ci = k * cycles_per_block - 1
            if ci < 0:
                return x_vals[0]
            return x_vals[min(ci, valid_count - 1)]

        block_x = np.array([_block_x(k) for k in range(len(pressure))])
        ln_pr, = ax2b.plot(block_x, pressure / 1e3, "--", color="tab:red",
                           lw=2, label="Pressure (kPa)")
        ax2b.set_ylabel("Pressure (kPa)", color="tab:red")
        ax2b.tick_params(axis="y", labelcolor="tab:red")
        legend_lines.append(ln_pr)

    ax2.legend(legend_lines, [ln.get_label() for ln in legend_lines],
               loc="best", fontsize=8)
    ax2.set_title("Porosity (SEI clogging) & Stack Pressure")

    if invert:
        ax1.invert_xaxis()
        ax2.invert_xaxis()

    plt.tight_layout()
    return fig, (ax1, ax2)


def process_sol_list_for_all_heat_components(
    plotter_instance,
    sol_list,
    label_list,
    acceleration_factor=50,
    x_axis="cycle",
):
    """批量计算并注入全部产热分量（充/放电的不可逆、可逆与总热）。"""
    from .analysis import get_all_heat_components

    logger.info("计算全部分量热数据 (Irrev, Rev, Total)...")
    for sol, label in zip(sol_list, label_list):
        try:
            data = get_all_heat_components(sol, label)
            if len(data.get("irrev_dchg", [])) == 0:
                continue
            sample_arr = np.asarray(data["irrev_dchg"])
            x_vals, _, valid_count = _resolve_swelling_x(
                sol,
                len(sample_arr),
                x_axis=x_axis,
                acceleration_factor=acceleration_factor,
            )
            x_vals = np.asarray(x_vals)[:valid_count]

            def inject(suffix, y_data):
                """将有效（非 NaN）分量曲线写入 plotter 仿真数据库。"""
                y_data = np.asarray(y_data)[:valid_count]
                mask = ~np.isnan(y_data)
                if np.any(mask):
                    full_label = f"{label}_{suffix}"
                    plotter_instance.add_sim_data(full_label, x_vals[mask], y_data[mask], np.zeros_like(y_data[mask]))

            inject("Irrev_Dchg", data["irrev_dchg"])
            inject("Rev_Dchg", data["rev_dchg"])
            inject("Total_Dchg", data["total_dchg"])
            inject("Irrev_Chg", data["irrev_chg"])
            inject("Rev_Chg", data["rev_chg"])
            inject("Total_Chg", data["total_chg"])
        except Exception as e:
            logger.warning("%s 热量计算失败: %s", label, e)


# === PEP 8 命名别名（向后兼容，原名保留可用） ===
Different_cycle_voltage = different_cycle_voltage


def plot_and_calculate_rrmse(df, x_columns, y_columns, sol_list, labels, colors, charge_or_discharge):
    """对比仿真/实验电压曲线，并输出误差指标（向后兼容，内部复用 calculate_rrmse_from_sol）。"""
    results = calculate_rrmse_from_sol(df, x_columns, y_columns, sol_list, labels, charge_or_discharge)
    for res, color in zip(results, colors):
        label = res["label"]
        plt.plot(res["x_sim"], res["y_sim"], linestyle="--", linewidth=1, color=color, label=f"{label}P Sim")
        plt.plot(res["x_exp"], res["y_exp"], linestyle="-", linewidth=1, color=color, label=f"{label}P")
        if np.isfinite(res["rmse"]):
            logger.info("%sP %s曲线 RMSE: %.4f", label, charge_or_discharge, res["rmse"])
            logger.info("%sP %s曲线 RRMSE: %.4f%%", label, charge_or_discharge, res["rrmse"] * 100)
        else:
            logger.warning("%sP %s曲线 RMSE/RRMSE 无有效数据。", label, charge_or_discharge)
    plt.xlabel("Capacity(Ah)")
    plt.ylabel("Voltage(V)")
    plt.title(f"Comparison of {charge_or_discharge} voltage curve \n between Sim and Exp")
    plt.legend()
    plt.grid(True)
