# -*- coding: utf-8 -*-
"""生成《LDS CW501 膨胀力老化对标》查看用 notebook。"""
import json
import os
import nbformat as nbf

CALIB = r"C:\Users\hez\WorkBuddy\2026-08-05-19-58-13\exp_force_calib"
DATA = CALIB + r"\data"
OUT = CALIB + r"\outputs"

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3 (BatteryProject venv)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}
cells = []

# ---------- 0. 标题 ----------
cells.append(nbf.v4.new_markdown_cell("""# LDS CW501 膨胀力老化对标（Sim vs Exp）

- 实验数据：`E:\\Downloads\\膨胀力数据整理.xlsx`（循环膨胀力对比 5 组 + 单圈膨胀力 2 组）
- 体系参数：`paramsLDSCW501.py`（`C:\\HithiumSSD\\hithium\\params`）
- 仿真引擎：BatteryProject（PyBaMM DFN 老化模型 + `calculate_cycle_swelling` 膨胀力模型）
- 标定目标：**同时对标容量保持率（SOH）与膨胀力（F_max / F_min）**

> **如何查看**：直接全部运行即可（默认加载已算好的结果，秒开）。
> **如何重跑**：把下方 `RERUN_SIM` 改为 `True` 后重跑"§5 重跑仿真"单元（需 BatteryProject venv，每工况约 40s）。
> **内核**：推荐使用 `C:\\HithiumSSD\\hithium\\BatteryProject\\.venv`（含 pybamm + science 样式）；只用查看功能时任意 Python 3 均可。"""))

# ---------- 1. 环境与路径 ----------
cells.append(nbf.v4.new_code_cell("""# -*- coding: utf-8 -*-
# 1. 环境与路径
import os, sys, json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

%matplotlib inline
try:
    plt.style.use("science")          # BatteryProject venv 才有
except Exception:
    plt.style.use("default")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"

CALIB = r"C:\\Users\\hez\\WorkBuddy\\2026-08-05-19-58-13\\exp_force_calib"
DATA  = os.path.join(CALIB, "data")
OUT   = os.path.join(CALIB, "outputs")

try:
    import pybamm
    print(f"PyBaMM {pybamm.__version__} —— 支持重跑仿真")
    HAVE_PYBAMM = True
except Exception:
    print("未安装 pybamm —— 仅可查看已算结果（重跑仿真需要 BatteryProject venv）")
    HAVE_PYBAMM = False
print("工作目录:", CALIB)
"""))

# ---------- 2. 实验数据 ----------
cells.append(nbf.v4.new_markdown_cell("""## 1. 实验数据概览

`4EALDS+1EAMIC` 表：5 组循环（25℃ 0.125P/0.25P，LDS ×4 + MIC ×1），逐圈记录 SOH、最大/最小膨胀力。
`LDS-A2样 / LDS-A4轮` 表：每 100 圈捞一圈的单圈膨胀力剖面（cls1/100/200/300）。"""))

cells.append(nbf.v4.new_code_cell("""# 2. 实验数据概览
def load_exp_cycle_force():
    with open(os.path.join(DATA, "cycle_force_comparison.json"), encoding="utf-8") as f:
        groups = json.load(f)
    out = {}
    for g in groups:
        rows = [r for r in g["data"] if r.get("SOH") not in (None, "")]
        if not rows:
            continue
        cyc = np.arange(1, len(rows) + 1)
        soh  = np.array([float(r["SOH"]) for r in rows])
        fmax = np.array([float(r["F_max"]) if r["F_max"] not in (None, "") else np.nan for r in rows])
        fmin = np.array([float(r["F_min"]) if r["F_min"] not in (None, "") else np.nan for r in rows])
        key = f"{g['condition']} {g['tech']}"
        out.setdefault(key, []).append(dict(condition=g["condition"], tech=g["tech"],
                                            cycle=cyc, retention=soh/100.0,
                                            max_force=fmax, min_force=fmin))
    return out

exp = load_exp_cycle_force()
fig, axes = plt.subplots(1, 3, figsize=(17, 4.6))
styles = {"25℃ 0.125P": ("#1f77b4", "-"), "25℃ 0.25P": ("#d62728", "-")}
for key, lst in exp.items():
    cond = key.split(" LDS")[0] if "LDS" in key else key.split(" MIC")[0]
    col, ls = styles.get(cond, ("#999999", "--"))
    for e in lst:
        axes[0].plot(e["cycle"], e["retention"]*100, ls, color=col, alpha=0.7, lw=1.0)
        axes[1].plot(e["cycle"], e["max_force"],  ls, color=col, alpha=0.7, lw=1.0)
        axes[2].plot(e["cycle"], e["min_force"],  ls, color=col, alpha=0.7, lw=1.0)
axes[0].set(xlabel="Cycle", ylabel="SOH [%]", title="容量保持率")
axes[1].set(xlabel="Cycle", ylabel="Force [N]", title="最大膨胀力 F_max")
axes[2].set(xlabel="Cycle", ylabel="Force [N]", title="最小膨胀力 F_min")
for ax in axes: ax.grid(True, alpha=0.3)
fig.suptitle("实验数据概览（虚线=单电芯，同色双线=平行样）", fontsize=13, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.94))
plt.show()

import pandas as pd
rows = []
for key, lst in exp.items():
    for e in lst:
        v = np.isfinite(e["max_force"]) & np.isfinite(e["min_force"])
        c, fmx, fmn, r = e["cycle"][v], e["max_force"][v], e["min_force"][v], e["retention"][v]
        rows.append(dict(工况=e["condition"], 技术=e["tech"], 圈数=int(c[-1]),
                         SOH终点=f"{r[-1]*100:.1f}%",
                         Fmax=f"{fmx[0]:.0f}→{fmx[-1]:.0f} N",
                         Fmin=f"{fmn[0]:.0f}→{fmn[-1]:.0f} N",
                         Fmin斜率=f"{np.polyfit(c, fmn, 1)[0]*100:.1f} N/100c"))
pd.DataFrame(rows)
"""))

# ---------- 3. 标定配方 ----------
cells.append(nbf.v4.new_markdown_cell("""## 2. 仿真设置与标定配方

**仿真**：DFN 老化模型（SEI ec-reaction-limited + 孔隙率变化、析锂不可逆、裂纹、LAM、接触电阻），
25℃ 恒流充放电（Charge 0.125C/0.25C → 3.65V，Rest，Discharge → 2.5V，Rest），
`t_factor=50` 加速 × 8 圈 ≈ 400 等效圈。

**力模型**：`F = max(0, k_eff·ΔL + preload)`，`ΔL = 可逆呼吸(石墨/LFP 应变函数) + 不可逆膜厚(SEI+析锂+死锂+裂纹SEI)×β·a_n·L_n`。

**关键杠杆（本工作通过扫描得到）**：

| 参数 | 作用 | 调法 |
|---|---|---|
| `EC diffusivity`（有效倍率 0.125P: ×0.55 / 0.25P: ×1.0） | 控制 SEI/膜生长总量 → **容量保持率** 主旋钮 | 每 +25% ≈ SOH 损失 +1.6pp/400c |
| `Negative electrode surface area to volume ratio` ×3.6 | 膜厚→位移 力学放大（BET 比表面积 > 几何 3ε/r），**不消耗锂、不影响 SOH** | 控制 F_min 斜率 |
| `Outer SEI partial molar volume` ×4 + `Li/SEI moles` ×0.5 | 膜厚/Li 损失解耦 | 辅助 F_min 斜率 |
| `k_eff`（0.125P: 3.0e6 N/m / 0.25P: 1.02e7 N/m） | 夹具-电芯等效刚度，控制振幅与力水平 | 0.25P 夹具更硬（实测振幅 ~4×） |
| `preload_force`（296 / 310 N） | 初始预紧力 = F_min 起点 | 直接取实验第 1 圈 F_min |"""))

cells.append(nbf.v4.new_code_cell("""# 3. 标定配方（显示用）
params_df = pd.DataFrame([
    ["EC diffusivity 倍率", "0.55", "1.00", "SEI 膜生长速率（有效值，补偿仿真时间驱动 vs 实验循环驱动）"],
    ["a_n 比表面积", "×3.6", "×3.6", "膜厚→膨胀位移放大（BET 面积，纯力学、不耗锂）"],
    ["SEI 偏摩尔体积", "×4", "×4", "膜厚/Li 损失解耦"],
    ["Li/SEI 摩尔比", "×0.5", "×0.5", "降低 SEI 的锂消耗"],
    ["k_eff 等效刚度 [N/m]", "3.0e6", "1.02e7", "夹具刚度（0.25P 夹具更硬）"],
    ["preload 预紧力 [N]", "296", "310", "实验第 1 圈 F_min"],
    ["t_factor / 圈数", "50 / 8", "50 / 8", "≈400 等效圈"],
], columns=["参数", "0.125P", "0.25P", "说明"])
params_df
"""))

# ---------- 4. 对标结果 ----------
cells.append(nbf.v4.new_markdown_cell("""## 3. 最终对标结果（Sim vs Exp）

SOH 与 F_min（不可逆膨胀力老化）双工况均对标上；F_max 终点略低 —— 原因见 §6 说明。"""))

cells.append(nbf.v4.new_code_cell("""# 4. 最终对标图
with open(os.path.join(OUT, "final_calibration.json"), encoding="utf-8") as f:
    cal = json.load(f)
colors = {"25°C 0.125P": "#1f77b4", "25°C 0.25P": "#d62728"}
T_FACTOR = cal["t_factor"]

fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
for label, cfg in cal["conditions"].items():
    col = colors[label]
    cyc = np.arange(1, len(cfg["retention"]) + 1) * T_FACTOR
    axes[0].plot(cyc, np.array(cfg["retention"])*100, "o-", color=col, ms=4, lw=1.4, label=f"Sim {label}")
    axes[1].plot(cyc, cfg["max_force"], "o-", color=col, ms=4, lw=1.4, label=f"Sim {label}")
    axes[2].plot(cyc, cfg["min_force"], "o-", color=col, ms=4, lw=1.4, label=f"Sim {label}")
for cond in ["25℃ 0.125P", "25℃ 0.25P"]:
    col = colors[cond.replace("℃", "°C")]
    for e in exp.get(cond, []):
        axes[0].plot(e["cycle"], e["retention"]*100, "--", color=col, alpha=0.55, lw=1.0)
        axes[1].plot(e["cycle"], e["max_force"], "--", color=col, alpha=0.55, lw=1.0)
        axes[2].plot(e["cycle"], e["min_force"], "--", color=col, alpha=0.55, lw=1.0)
    axes[0].plot([], [], "--", color=col, alpha=0.8, label=f"Exp {cond} (2 cells)")
axes[0].set(xlabel="Cycle", ylabel="SOH [%]", title="容量保持率")
axes[1].set(xlabel="Cycle", ylabel="Force [N]", title="最大膨胀力 F_max")
axes[2].set(xlabel="Cycle", ylabel="Force [N]", title="最小膨胀力 F_min")
for ax in axes:
    ax.legend(fontsize=8, frameon=False); ax.grid(True, alpha=0.3)
fig.suptitle("LDS CW501 膨胀力老化对标 — 最终标定（实线=Sim，虚线=Exp）", fontsize=13, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.94))
plt.show()
"""))

cells.append(nbf.v4.new_code_cell("""# 5. 数值对标表（Sim vs Exp 终点值）
exp_target = {
    "25°C 0.125P": dict(soh=4.89, fmin=(384, 404), fmax=(532, 581), fmin_slope=(24, 31), fmax_slope=(53, 60)),
    "25°C 0.25P":  dict(soh=4.83, fmin=(646, 662), fmax=(979, 1027), fmin_slope=(91, 97), fmax_slope=(103, 112)),
}
res_rows = []
for label, cfg in cal["conditions"].items():
    t = exp_target[label]
    res_rows.append(dict(工况=label,
        SOH损失_Sim=f"{cfg['soh_loss_pct']:.2f}%", SOH损失_Exp=f"{t['soh']:.2f}%",
        Fmin终点_Sim=f"{cfg['fmin_end']:.0f}N", Fmin终点_Exp=f"{t['fmin'][0]}–{t['fmin'][1]}N",
        Fmin斜率_Sim=f"{cfg['slope_min_N100c']:.1f}", Fmin斜率_Exp=f"{t['fmin_slope'][0]}–{t['fmin_slope'][1]}",
        Fmax终点_Sim=f"{cfg['fmax_end']:.0f}N", Fmax终点_Exp=f"{t['fmax'][0]}–{t['fmax'][1]}N"))
pd.DataFrame(res_rows)
"""))

# ---------- 5. 单圈 ----------
cells.append(nbf.v4.new_markdown_cell("""## 4. 单圈膨胀力剖面（实验，每 100 圈捞一圈）

圈内剖面体现可逆呼吸（充电膨胀/放电收缩）与预紧力基线；随圈数整体上移即不可逆膜厚累积。"""))

cells.append(nbf.v4.new_code_cell("""# 6. 单圈膨胀力剖面
fig2, axes2 = plt.subplots(1, 2, figsize=(14, 4.6))
for ax, fn, title in [
    (axes2[0], "single_cycle_LDS-A2样A1F9R00001-25C0.125P.json", "LDS-A2样 25℃ 0.125P"),
    (axes2[1], "single_cycle_LDS-A4轮A组25C0.25P.json", "LDS-A4轮A组 25℃ 0.25P"),
]:
    with open(os.path.join(DATA, fn), encoding="utf-8") as f:
        groups = json.load(f)
    for grp in groups:
        pts = np.array([p[2] for p in grp["points"] if p[2] is not None], dtype=float)
        t = np.arange(len(pts)) / max(len(pts) - 1, 1)
        ax.plot(t, pts, lw=1.1, label=grp["cycle_marker"])
    ax.set(xlabel="归一化圈内时间", ylabel="Force [N]", title=title)
    ax.legend(fontsize=8, frameon=False); ax.grid(True, alpha=0.3)
fig2.tight_layout()
plt.show()
print("注：曲线为整圈放电腿（满充→空放），起点=满充态力（≈F_max 侧），终点=空放态力（≈F_min 侧）。")
"""))

# ---------- 6. 局限 ----------
cells.append(nbf.v4.new_markdown_cell("""## 5. 对标结论与模型局限

**已对标上（推荐参数组合，见 §2 表）**
- ✅ **容量保持率**：0.125P 损失 5.13%（实验 4.87–4.89%）；0.25P 损失 4.49%（实验 4.30–4.32%）
- ✅ **最小膨胀力 F_min**（不可逆膨胀力老化）：0.125P 296→405N（实验 296→384–404N，斜率 27.3 vs 24–31 N/100c）；
  0.25P 310→660N（实验 309–316→646–662N，斜率 87.5 vs 91–97 N/100c）
- ✅ 0.25P 相对 0.125P 的 F_min 斜率比 ≈3.4× —— 用 **夹具刚度 k_eff 不同**（3.0e6 vs 1.02e7 N/m）解释，与实测振幅比一致

**未完全对标上（结构性局限，非调参可解）**
- ⚠️ **F_max 振幅增长**：实验振幅 23→160N（0.125P）/ 107→350N（0.25P），线性弹簧 + 有界石墨应变
  （max 13.2%×L_n ≈ 15μm）最多给出 ~36N（k_eff=3e6）。F_max 终点低 ~100–270N。
  建议后续扩展：**力相关刚度 k_eff(F)**（夹具压缩非线性）、或更陡的膨胀函数、或气体析出项。
- ⚠️ **仿真 SEI 时间驱动 vs 实验近似循环驱动**：0.25P 单圈时间短 → 模型 SEI 生长偏少，
  用分工况 EC 有效倍率（0.55 / 1.0 ≈ 循环时间比 2.0）补偿，属工程近似。

**一句话结论**：容量保持率由 EC 扩散率（SEI 膜生长）主控；F_min 老化斜率由「SEI 膜生长 × 力学放大 a_n × k_eff」联合控制，
其中 a_n（比表面积）可纯力学放大而不消耗锂，是同时兼顾 SOH 与膨胀力的关键解耦旋钮。"""))

# ---------- 7. 重跑 ----------
cells.append(nbf.v4.new_markdown_cell("""## 6.（可选）重跑仿真

将 `RERUN_SIM` 改为 `True` 后运行本单元，会用上表参数重算两工况并刷新 `final_calibration.json`。
（需 BatteryProject venv 内核：`C:\\HithiumSSD\\hithium\\BatteryProject\\.venv\\Scripts\\python.exe`，每工况约 40s）"""))

cells.append(nbf.v4.new_code_cell("""# 7. 重跑仿真（默认 False）
RERUN_SIM = False
if RERUN_SIM:
    assert HAVE_PYBAMM, "需要 BatteryProject venv（含 pybamm）"
    if CALIB not in sys.path:
        sys.path.insert(0, CALIB)
    import importlib
    import lds_force_core as core
    importlib.reload(core)
    # 覆盖 run_final 的参数设置后执行
    exec(open(os.path.join(CALIB, "run_final.py"), encoding="utf-8").read().replace("if __name__ == '__main__':", ""))
    print("已重跑并刷新 outputs/final_calibration.json，请重跑 §3 对标图单元查看。")
else:
    print("RERUN_SIM=False，直接查看已算结果（重跑请改为 True 后再运行本单元）。")
"""))

nb.cells = cells
nb_path = os.path.join(CALIB, "LDS_CW501_膨胀力老化对标.ipynb")
with open(nb_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("saved:", nb_path)
