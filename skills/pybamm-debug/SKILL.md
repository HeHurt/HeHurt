---
name: pybamm-debug
description: 生成可跑通的 PyBaMM/liionpack 电化学仿真脚本,处理版本兼容调试与物理合理性自检:protocol→语法、P2D/SPMe、老化降解、liionpack 模组级耦合、依赖报错排查。不含 COMSOL(见 comsol-java)与报告排版(见 hithium-ppt)。
---

# PyBaMM / liionpack 仿真脚本 + 调试 + 物理自检

## 何时用 / 不用
- **用**:写能直接跑的 PyBaMM/liionpack 脚本;protocol→语法转换;降解/老化建模;依赖版本报错排查;结果物理合理性核查。
- **不用**:COMSOL(`comsol-java`)、PPT/报告(`hithium-ppt`)、纯概念问答(直接答即可)。

## 标准工作流
1. **建隔离环境**:专用 venv,不污染系统/其他项目。
2. **运行时 introspect**:`inspect.signature(...)`、`pybamm.parameter_sets`、打印 model.options;**不要凭记忆猜 API 名**,版本间会变。
3. **写脚本**:最小可跑 → 再加复杂度。内联中文注释。
4. **跑 + 调试**:见下方兼容矩阵与陷阱清单。
5. **物理自检**:见 checklist,数值不合理先怀疑参数/模型,别急着出结论。

---

## 已验证可跑的版本组合(⚠️ 点位时间约 2026-06,库漂移快,以 introspect 为准)

| 库 | 已验证版本 | 备注 |
|---|---|---|
| pybamm | **24.9.0** | 与 liionpack 0.4.0 兼容的关键锚点 |
| liionpack | **0.4.0** | 模组级耦合 |
| pandas | **2.2.3** | 见下方 CoW 陷阱 |

**降级触发条件(踩过的硬坑)**
- `pybamm 26.5` 删了 `len_rhs_sens` → **liionpack 0.4.0 直接崩**。要么降 pybamm 到 24.9.0,要么等 liionpack 适配。
- `pandas 3.0` 默认 Copy-on-Write → `.values` 返回**只读数组**,liionpack 的 `power_loss` 崩。降到 `pandas 2.2.3`。

> 原则:**锁定一组已验证版本写进 requirements**,别裸装最新。

---

## 已知物理/参数陷阱
1. **Chen2020 的 SEI 活化能默认 = 0 J/mol** → SEI 增长**无温度依赖**,热异质性会算出"零老化分化"。要显式设到物理合理值(约 `3.8e4 J/mol`)才有意义。
2. **状态续算用 `starting_solution`**:分段老化时,把上一段 solution 传进下一段,降解状态才能正确累积。
3. **plating 低 C 可忽略、低温/快充才显著**:0.25C 下析锂≈0 是正常的,别当 bug。

---

## P-rate → 实际功率换算(LFP 恒功率工况)
- 约定:`1P = Q_nom(Ah) × 3.2 V`(LFP 标称电压)。
- protocol 步映射到 PyBaMM 原生语法:
  `"Discharge at X W until 2.8 V"` / `"Charge at X W for N minutes or until 3.55 V"`。
- 恒功率下 `I = P/V`:放电电压降→电流升,充电反之,**电流台阶是斜的不是平的**,别画成方波。
- 大电芯:留 `Q_NOM_REAL` 开关(如 314Ah/587Ah),功率自动按比例缩放;公共参数集 + SPMe 仅作占位,正式工作换实测辨识参数或 ECM。

---

## 降解子模型 option string 速查
| 机制 | option 关键字 | 类型 |
|---|---|---|
| SEI 增长 | `"solvent-diffusion limited"` 等 6 选 | LLI |
| 析锂 | `"irreversible"` / `"partially reversible"` / `"reversible"` | LLI |
| 颗粒力学 | `"swelling only"` / `"swelling and cracking"` | — |
| SEI on cracks | 裂纹面积耦合 SEI | LLI |
| 活性物质损失 LAM | `"stress-driven"` / `"reaction-driven"` / `"stress and reaction-driven"` / `"current-driven"` | LAM |

起步参数集:**`OKane2022`**(集成降解);需裂纹/力学补 **`Ai2020`**。用 `ParameterValues.update()` 注入。

---

## liionpack 模组老化:时间尺度分离编排
1. **耦合快照**:跑短时 liionpack,得到每颗 cell 的电流/温度分布。
2. **独立老化块**:各 cell 用快照电流做独立单体老化,状态经 `starting_solution` 续算。
3. **循环**:回到步骤 1。
> 近似边界(写进注释):老化后的状态**尚未**反馈回快照的电流分布——长循环后分化会被低估。要更准就闭环这一步。

---

## 物理合理性自检 Checklist
- [ ] 容量衰减单调、量级合理(无突跳/反弹除非有机制)
- [ ] SEI 增长有温度依赖(活化能 ≠ 0)
- [ ] 析锂在低 C/常温下接近 0,低温快充才显著
- [ ] 负极孔隙率下降幅度物理合理
- [ ] 电流符号约定明确(放电正 or 充电正)
- [ ] 已验证版本锁进 requirements,可复现

## 用法
```
/pybamm-debug 把这个 5.4.1 负载/过载 protocol 转成 PyBaMM 恒功率语法,587Ah,跑出电流-时间曲线
/pybamm-debug liionpack 4 cell 异质换热做老化分化,报 len_rhs_sens 错误
```
