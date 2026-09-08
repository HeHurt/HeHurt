## 2026-09-01 single-layer pouch geometry and mesh repair

- A loaded axisymmetric `LithiumIonBatteryMPH` interface locks the geometry axisymmetry flag; deleting only its `axi1` boundary node is insufficient. For a Cartesian 2D migration, retain parameters/materials/functions, remove the old interface, set the geometry Cartesian, then recreate `LithiumIonBatteryMPH` and rebind its features.
- In COMSOL 6.4 the actual creatable interface type for this installation is `LithiumIonBatteryMPH`, not `LithiumIonBattery`. The default `socicd1`, `sep1`, `nf1`, `ins1`, and `init1` nodes own non-editable selections; configure their properties and let applicable selections update automatically.
- Interpolation feature tags and callable names can differ (`ocv_gr_charge` tag previously exposed `ocv_gr_discharge3`). Recreate migrated interpolation functions with an explicit `funcname`, import the file data, and verify function evaluation before solving.
- Adding collector-extension and tab domains changes every downstream domain number. Rebuild material and physics selections from generated or coordinate-based selections, then independently reload and assert them; do not reuse the original explicit IDs.
- Geometry explicit selections can retain old entities when `set("fin", ...)` is called without clearing. Clear and rebuild each selection, and verify electrode, separator, conductor, material, and terminal selections separately.
- A newly created COMSOL mesh already contains the default `size` feature. Configure that feature directly; creating another feature with tag `size` fails with a duplicate-object error.
- For this thin layered 2D cross-section, a mapped quadrilateral mesh is the appropriate review baseline. Use one-to-one generated domain selections and remesh after reload before adding electrochemical physics.

## 2026-08-10 coin V6 mechanics audit

- Failure class: API syntax issue.
- `GeomSequence.axisymmetric()` in COMSOL 6.4 exposes a boolean setter but no zero-argument getter. A read-only audit failed before reaching model-tree inspection.
- Repair: omit the nonessential getter and infer the formulation from the geometry/physics configuration instead. The source MPH was not modified.
- A second read-only probe showed that the physics root object does not implement `properties()`; only physics feature nodes do. Repair: inspect the default Solid Mechanics feature tree and its feature properties, omitting root-property enumeration.
- `BoundaryLoad.forceType="Pressure"` is invalid in COMSOL 6.4. The accepted pressure-like option reported by the API is `FollowerPressure`; use it with the `pressure` property. Other valid choices are `ForceArea`, `ForceDefArea`, and `TotalForce`.
- The automatically created Solid Mechanics `lemm1` is a mandatory default/fallback material node: its selection is not editable and the node cannot be removed. For domain-specific elastic properties, retain `lemm1`, point it to shared expressions (`E_mech`, `nu_mech`, `rho_mech`), and define those expressions in disjoint, domain-selected variable groups.
- Mechanical `Eval` values follow the dataset/display unit unless the numerical feature explicitly sets `unit`. An apparent 48.8 m displacement was actually returned in the geometry display unit (um). Always set `Pa`, `m`, or `1` explicitly before interpreting mechanics smoke metrics.

## 2026-08-11 coin V6 saved-sweep postprocessing

- Failure class: Environment/path/license issue (session acquisition response).
- The first custom read-only extraction attempt started COMSOL but `sim-cli` returned no session id. The model was not modified.
- Repair path: inspect pinned-runtime session state, reuse only a healthy identified COMSOL session, and do not terminate unknown processes.

## 2026-08-11 方案1 phis0_ec1 空方程诊断

- Failure class: Mesh issue.
- `comp1.liion.phis0_ec1` 的空方程不一定表示 `Electrode Current` 边界号无效；本例边界 43、46 几何有效且邻接正极集流体域 9，但 `mesh1` 未给域 2、9 生成三维体单元，端子边界 43、46 也没有二维面单元。
- Repair: 将 `mesh1/swe2` 的域选择从 `[1, 8]` 扩展为 `[1, 2, 8, 9]`。内存验证后网格完整，域 2 生成棱柱单元、域 9 生成六面体单元，最小瞬态求解通过。
- Diagnostic script issue: 初版 solver-tree 审计把 `StudyFeatureListClient` 当作可调用对象。改为优先使用 `manager.get(tag)`，再以可调用方式 fallback。
- Live-file handling: 原 `方案1.mph` 存在 `.lock` 且 `ComsolUI` 正在运行；字节备份可创建，但 `Get-FileHash` 读取源文件被共享锁拒绝。此时不得强制覆盖原文件，应另存修复模型，完成重载和 smoke 后再由用户关闭原模型并决定是否替换。

## 2026-08-12 coin V7 local pressure-porosity coupling

- A domain variable containing `withsol('sol2',...)` can be consumed by a new electrochemical study, but evaluating that same variable directly on the source mechanics dataset creates an invalid nested cross-solution context. For mechanics-only validation plots, evaluate `solid.sz` directly and apply the same constitutive expression outside `withsol`.
- COMSOL numerical postprocessing nodes in this workflow require an explicit integer `solnum`; the string `end` produced a "constant expressions only" error even though the transient solve had succeeded. Identify the transient dataset from its `t` series, then use the last integer solution index.
- A parameter introduced after a legacy saved solution may be unavailable when evaluating that old dataset. Use an equivalent unit-explicit literal only for legacy-result validation; retain the named parameter in the new model and verify it through the new study smoke.
- On the COMSOL 6.4 Transient study feature used by the coin model, `sweeptype` accepts `filled` or `sparse`, not `specified`. For a single scanned parameter, omit `sweeptype`; `pname`, `plistarr`, and `punit` are sufficient.

## 2026-08-12 coin V8 intercalation breathing coupling

- Failure class: API syntax issue. `ExternalStrain.StrainInput="Strain"` is invalid in COMSOL 6.4; use `"StrainTensor"`, then supply the axisymmetric axial eigenstrain as the third item of the three-component `eext` array.
- Failure class: Postprocessing/export issue. A transient solve can create multiple datasets pointing to the same solution, while not every dataset accepts domain-average numerical features. Select the dataset by both solution tag and a successful field probe; in this 2D axisymmetric model use `AvSurface` for domain averages, not `AvVolume`.
- Failure class: Environment/path/license issue (outer launcher timeout only). A 60 s shell timeout terminated the waiting client while the COMSOL session remained healthy; rerun long studies with a sufficiently long launcher timeout and distinguish that condition from a COMSOL convergence failure.

## 2026-08-18 CW363 thin-layer mesh rebuild

- Failure class: Mesh issue. After the CW363 design dimensions changed, `mesh1` reloaded as empty/incomplete; the existing `swe1` reported 134 low-quality prisms, while empty tail nodes `ftri3/swe3` left the sequence in a rebuild state.
- Blindly refining the free-triangle source from the old coarse setting to `hmax=15[mm]`, `hmin=2[mm]` increased the mesh to 16,052 prisms but reduced minimum volume quality to `2.109e-13`; refinement alone does not repair a bad sweep topology.
- Repair: replace the main source face with a mapped quadrilateral mesh and retain a directed hexahedral sweep for domains `[1,4,5,6,9]`; retain the existing prism sweep for `[2,3,7,8]`; remove `ftri3/swe3`. Reload verification confirmed 4,200 hexes plus 792 prisms and volume elements on every domain 1-9.
- The 557 mm in-plane length versus 6-13 um collector thickness creates an unavoidable aspect ratio above `1e4`, so COMSOL still flags `swe1` with a low isotropic quality metric. For this thin-layer model, require structured sweep orientation, complete domain coverage, and a minimal solve before treating the mesh as production-validated; do not claim the warning disappeared. No solve was run in this mesh-only task.
## 2026-08-19 CW501 Load Cycle parameter-sweep convergence

- Failure class: Solver/convergence issue at the first constant-power charge endpoint. Repeated failures occurred at `t*C≈3866–3868 s` for different geometry/resistance cases, showing that the failure followed normalized charge progress rather than a particular `L_JR_pos` or `R` value.
- The saved solver used a fully coupled Newton limit of only 4 iterations. The Battery Load Cycle feature adds an algebraic `I_app` state plus indicator/discrete event states, so its power-to-rest transition is more nonlinear than the prior explicit Electrode Current expression.
- Repair evidence: for `L_JR_pos=880[mm]`, `R=0.042329836[mΩ]`, `C=0.167`, increasing only the fully coupled maximum iterations from 4 to 15 allowed the runtime-only solve to complete through 26000 s, beyond the repeatable baseline failure at 23149.8846 s. The source `.mph` was not modified.
- Mesh refinement and smaller output steps are not primary repairs for this signature. First raise the nonlinear iteration budget and use a realistic Load Cycle electrode-potential initial guess; then verify one isolated case before restoring the paired sweep.
- Postprocessing note: COMSOL numerical evaluation `solnum` requires explicit integer solution indices in this workflow; the string `all` produced a constant-expression error after the solve had already succeeded.

## 2026-08-20 coin V9 nonlinear breathing full cycle

- A study can activate the Events physics but still fail to execute the intended protocol when each event feature's `StudyStep` remains bound to another transient step. For a copied/new study, rebind `DiscreteStates`, `IndicatorStates`, and every `ImplicitEvent` to the new `study/time` tag, then verify negative current and the lower-voltage event in the solution.
- Do not accept a fixed end time as a full charge-discharge cycle merely because a discharge segment exists. Acceptance must require the lower cutoff, a post-event zero-current sample, and sufficient final time. In this model 12,000 s captured only about 60% of discharge; 18,000 s completed the cycle.
- The COMSOL Python `ModelClient` used by the live session has no `evaluate()` convenience method. For unsolved build verification, read interpolation tables back with `getStringMatrix("table")`; reserve numerical features for solved datasets.
- Keep literature curve shape and effective electrode-scale amplitude as separate parameters. Particle/lattice volume changes must not be applied directly as porous-electrode axial strain without a scale conversion or an explicit calibration statement.

## 2026-08-24 CW501 Load Cycle repeated error-test failure

- Failure class: Solver/convergence issue at the same first constant-power charge cutoff identified previously. The new failed case is `L_JR_pos=1480[mm]`, `R=0.091312254[mΩ]`, `C=0.25`; the screenshot failure time gives `t*C=3875.90 s`, within the earlier cross-case band of about `3866-3929 s`.
- The saved solver now has `maxiter=25`, so the prior Newton-budget bottleneck was improved. However, the Fully Coupled tolerance factor was raised to `ntolfact=2`; this doubles the nonlinear termination tolerance relative to `rtol=1e-3`, while the BDF local error test remains controlled by `rtol`. A step can therefore leave Newton sooner and then be repeatedly rejected by the time integrator.
- The model still uses BDF with maximum order 2, free internal steps, initial step `0.01[s]`, and the BDF nonlinear controller off. First controlled repair: keep `maxiter=25`, restore `ntolfact=1`, enable the BDF nonlinear controller, and rerun only the failed case. If necessary, use BDF maximum order 1 for that isolated switching test.
- Smaller output spacing and further mesh refinement are not primary repairs for this signature. The source `.mph` was not modified, and this audit did not run a new solve.

## 2026-08-24 CW501 Load Cycle follow-up after BDF stabilization

- Restoring `ntolfact=1`, enabling the BDF nonlinear controller, and limiting BDF to order 1 increased the number of completed sweep cases but did not eliminate the event-transition failure. The new parametric solution stored `L1480/C0.167`, `L1480/C0.25`, and `L1780/C0.167`; the next case `L1780/R0.101173238/C0.25` failed at `15818.6725 s` with repeated error-test failures.
- The voltage trace contains abrupt jumps at Power-to-Rest and Rest-to-Power transitions. These are expected for an ideal instantaneous load change but remain numerically harsh because true constant power adds the algebraic relation between voltage and `liion.lc1.I_app`.
- The saved Load Cycle still has `phis0init=1[V]`. This is an electrode-potential constraint initial guess, not the physical OCV/SOC initial condition, so correcting it is secondary for failures occurring at later cycle events.
- Next controlled repair: manually scale `comp1.liion.lc1.I_app` with `i_1C*C` and rerun the isolated failed case. If needed, constrain the internal maximum BDF step to `5[s]`. If constant power is not mandatory, a Current/C-rate Load Cycle is the simpler production formulation because it removes the `P=VI` algebraic coupling.

## 2026-08-24 CW501 event-interface second-cycle efficiency design

- The event model is numerically simpler because active `comp1.liion.ec1` directly consumes `Its=I`; it does not add the Load Cycle algebraic `I_app` state. Its existing `Q1` and `W1` equations use absolute current/power and therefore accumulate all phases and all cycles together.
- Second-cycle batch extraction does not require fixed time windows. Add a discrete `cycle_id` initialized to 1, increment it in the discharge-end event, and gate separate charge/discharge ODE accumulators with `cycle_id==2` plus the sign of `liion.Its_ec1`.
- Use the model's existing energy expression `liion.Its_ec1*voltage` and its existing Ah/A and Wh/W custom-unit convention. At the final time of every parametric outer solution, evaluate `E_ch_2`, `E_dis_2`, and `E_dis_2/E_ch_2`.
- The saved Case1~41D event protocol has charge-to-rest, rest-to-discharge, and discharge-to-charge transitions; it does not currently include an active post-discharge rest, so protocol parity must be restored before comparing its efficiency with the Load Cycle model.

## 2026-08-24 CW501 generated solver-sequence mismatch

- Failure class: Solver/convergence issue caused by editing a solver sequence that was not used by the active sweep. The new error explicitly referenced `sol15/t1`; readback showed the requested settings only on `sol1/t1` (`maxiter=25`, `ntolfact=1`, BDF `maxorder=1`, nonlinear controller on, initial step `0.01[s]`).
- The actual `sol15/t1` still used `maxiter=4`, BDF `maxorder=2`, nonlinear controller off, and initial step `1[s]`. A later Case failure therefore does not disprove the adjusted settings; it shows that COMSOL generated/used another solver sequence.
- Always match the solver tag in the error message to the edited Solver Configuration. For this model, show/edit `Solution 15 (sol15)` or regenerate one study-linked solver sequence, then verify the real `Time` and `FullyCoupled` properties before recomputing.
- `comp1.liion.lc1.phis0init=1[V]` is confirmed, but it is a time-zero initial guess and not the primary cause of the repeated first-charge cutoff failure. COMSOL 6.4 does not expose/document it as a standard Load Cycle field in all GUI visibility modes.

## 2026-08-24 CW501 event-interface implementation and smoke validation

- The original discharge-cutoff event directly reinitialized `charge2=1`, so adding only a cycle counter would not create a post-discharge rest. A separate `hold_dis` discrete state is required: discharge cutoff sets `hold_dis=1` and `TimeOfSwitch=root.t`; a new implicit event starts `charge2` when `t-TimeOfSwitch-1800[s]>0` and `hold_dis>0`.
- Initialize `cycle_id=1` and increment it at each discharge cutoff. Gate second-cycle accumulators with `cycle_id==2`, `charge2`, and `discharge2`; this avoids fixed time windows and remains valid across parameter combinations with different event times.
- The prior study horizon `20000/C` was too short for the complete second discharge at `C=0.25`: the model was still discharging at 80,000 s. Extending the horizon to `25000/C` completed the cutoff at 81,631.1 s in the smoke case.
- Runtime smoke evidence for `L_JR_pos=580[mm]`, `R=0.062205123[mΩ]`, `C=0.25`: both charge-rest and discharge-rest intervals were about 1,804.5 s at the stored-output resolution; second-cycle charge energy was 4,712.00 Wh, discharge energy was 4,485.66 Wh, and efficiency was 0.951964.
- COMSOL `EvalGlobal.getReal()` returned SI-base numeric magnitudes for these custom Ah/A and Wh/W global-equation units even when the requested display unit was Ah or Wh. The COMSOL result table applies the configured display units; external Python verification must divide the raw charge/energy magnitudes by 3,600 before reporting Ah/Wh.

## 2026-08-31 单层软包双侧极耳3D P2D建模

- COMSOL 6.4 的官方3D P2D模板中，`pce1/pce2` 的电子电导率由材料属性组提供；直接向 `pce*.sigmas` 写入表达式会报“未知参数 sigmas”。迁移扣电模型时应保留材料驱动的电子电导率路径，仅重绑孔隙率、活性物质体积分数和初始SOC等可写接口属性。
- 同一模板的 `Electric Ground` 与 `Electrode Current` 中，`IncludeContactResistance` 是数值枚举，需设置为 `"1"` 或 `"0"`；`"on"`/`"off"` 会报参数值无效。
- 初始SOC为1%的LFP/石墨3D P2D模型中，默认的 `Current Distribution Initialization` 稳态步可在残差约`4.2e-3`时因默认`1e-3`相对容差中止；首轮低SOC调试宜移除该预初始化，先验证时间依赖求解器能从SOC初值直接推进，再决定是否以较松容差恢复该步。

# 2026-09-01 — 2D pouch 1C current must follow the actual electrode geometry

- **Class:** Material/parameter/unit issue.
- **Symptom:** A nominal 0.5C pouch cycle reached nearly full electrode lithiation in about 4200 s, while coulomb counting with `I/i_1C` reported only 59.3% SOC.
- **Root cause:** The migrated `i_1C` used coin areal-loading thicknesses (`t_an=111.55 um`, `t_ca=136.75 um`) while the pouch geometry used `L_neg=61.5 um` and `L_pos=84 um`. The 2D out-of-plane thickness was already correct at 52 mm.
- **Fix:** Define `i_1C_pouch_geom=min(ah_pos_soc1*L_pos/t_ca,ah_neg_soc1*L_neg/t_an)` and use it in the terminal current and C-rate postprocessing.
- **Verification:** The corrected 0.5C charge ended at 7358.6 s; electrode-state SOC reached 100.02% and coulomb-counted SOC 103.20%. The remaining 3.2-point gap is a bounded N/P and capacity-window calibration issue.
- **Rule:** After migrating electrochemistry to a geometry with different electrode thickness or area, never reuse a capacity-derived current without recomputing capacity from the active domain geometry and verifying it against average electrode SOC.

## 2026-09-01 软包 V8 电压回弹与二维力学场诊断

- Failure class: Postprocessing/export issue. 在未先确认 `geom1` 空间维度时，把显示上极薄的二维截面误判为三维结构，会错误地把厚度方向从 `y` 改成 `z`。本模型是二维截面，厚度方向确为 `y`，因此压力应使用 `-solid.sy`、呼吸应变应写入 `y` 分量、厚度位移应读取 `v`。
- 二维域平均使用 `AvSurface`、二维边界平均使用 `AvLine`；三维模型才分别使用 `AvVolume` 和 `AvSurface`。COMSOL 报“不支持的几何实体层级/非法实体编号”时，应先核对空间维度和选择层级，不要继续猜边界编号。
- Y 轴显示放大 100 倍只影响绘图外观，不改变求解坐标、载荷方向或应力分量。该模型加载面法向为 `[0,1]`，加载边长为 86 mm，乘以面外宽度 52 mm 得 4472 mm²；`100 N / 4472 mm² = 22.361 kPa`，与无呼吸时三层平均压力一致。
- `solid.mises` 是等效应力，厚度孔隙率反馈使用的是压缩法向应力 `max(0,-solid.sy)`。嵌锂呼吸下石墨膨胀、LFP收缩且界面完全粘结，会产生自平衡失配应力和端部局部峰值；局部峰值不能当作 100 N 的平均外压。
- 机制对照必须只改变一个因素。旧图同时改变了外力、`coupling_on` 和 `breathing_mode`，不能归因于呼吸。匹配后的两组均为 100 N、`coupling_on=1`，仅切换 `breathing_mode=0/2`。
- 回弹幅度应定义为“静置电压减去各自放电截止瞬间电压”，不能用静置后的绝对电压高低代替。匹配对照中无呼吸总回弹为 386.59 mV，有呼吸为 391.60 mV，呼吸使回弹增加 5.02 mV；旧图所谓软包方向相反是指标读取错误。

## 2026-09-02 扣电 V9 统一 0 N 无耦合基线

- Failure class: Model tag or feature tag issue. 扣电 V9 只有 `breathing_mode`，没有像软包一样被物理表达式实际消费的 `coupling_on`；仅设置一个同名参数不能代表关闭耦合。
- 统一基线必须让开关同时控制：`V_contact_drop`、顶部机械载荷、呼吸外应变以及三层压力–孔隙率反馈。0 N、`coupling_on=0`、`breathing_mode=0` 回读后，压力为 0、三层孔隙率在全循环保持基准常数。
- 中文输出文件名通过通用 audit launcher 时曾未在预期位置生成结果文件；COMSOL 正式模型仍可使用中文名，但 launcher 的机器审计输出优先使用纯英文文件名，并在任务结束后归档到内部 JSON 目录。

## 2026-09-03 扣电与软包基线电压差异审计

- Failure class: Postprocessing/export issue. 同一任务包内不同模型的完整循环不一定绑定同名 dataset；本次扣电完整0 N基线位于 `dset3`，软包基线位于 `dset1`。跨模型比较必须逐个 dataset 验证时间终点且同时包含正、负电流，不能默认读取 `dset1`。
- 扣电自定义 `theta_neg_v8/theta_pos_v8` 依赖颗粒额外维度，直接按物理场二维域做 `AvSurface` 会出现变量未定义。未确认额外维度映射前，基线电压对齐可先用电流积分得到额定容量SOC；若要比较颗粒嵌锂状态，应使用模型中已验证的平均算子或内置多孔电极平均SOC变量。

## 2026-09-03 扣电 V2 正确极性与参数化堆叠重建

- Failure class: Geometry build issue / Selection-domain issue / Solver-convergence issue.
- 用原生二维轴对称 primitives 重建 `coin.mphbin` 时，几何修改会清空或错置物理场、材料和网格选择；必须在 `geom.run()` 后重新绑定 LiIon、Solid Mechanics、Variables、Materials 和 Mesh，不能沿用旧域号。
- 正确堆叠从下到上为正极壳体、Al/LFP/隔膜/石墨/Cu、负极壳体。最终拓扑应回读为 42 个点、52 条边界、11 个域；顶部边界 20 为负极接地/固定，底部边界 2 为正极电流/载荷。
- 为支持电极厚度设计变更，应把每层 z 坐标写成前序层厚度的累积表达式；负极壳体位置使用 `z_nc=z_stack_top+t_nc_bot+t_tsp`，而不是固定坐标。
- 几何重建后若不恢复原网格域选择，自动网格会从约 1,900 个单元膨胀到约 38,500 个。将 Al/LFP/隔膜/石墨/Cu 重新绑定到映射网格、其余结构绑定自由三角形后，网格恢复为 1,935 个单元。
- 当前几何、网格和选择回读已通过，但 600 s 时间依赖烟雾计算仍在装配后失败，且报错文本未完整解码。不得把几何验收等同于求解验收；清空失败解、恢复正式时间列表，待用户审核几何后再单独诊断 solver/event 初始化链。

## 2026-09-03 扣电 V2 密封闭合与力学变量选择修复

- Failure class: Geometry build issue / Selection-domain issue.
- 参考模型名义参数 `W_g=1.575 mm` 小于壳体间实际径向距离 `R_pc-R_nc_bot=1.92 mm`，原生几何重建后会明确显示 0.345 mm 开口。需要用 `W_g=R_pc-R_nc_bot` 建立设计约束，使 PC 密封圈严格贴合正极壳内壁；闭合后拓扑由 52 条边界变为 53 条边界，域数仍为 11。
- 几何重建不仅会清空电极变量组，也会清空原本存在的 `mech_steel` 与 `mech_pp` 选择。仅恢复 `mech_cu/mech_neg/mech_sep/mech_pos/mech_al` 会导致域 11 上 `E_mech` 未定义。应恢复 `mech_steel=[1,2,8,9,10]`、`mech_pp=[11]`。
- 修复上述选择后，`std_mech` 稳态力学烟雾计算通过；120 s `std_v9` 全耦合瞬态仍在 `sol3/t1` 失败，说明瞬态还有独立问题，不能再归因于密封圈力学材料缺失。

## 2026-09-04 扣电 V2 完整耦合循环与端子探针修复

- Failure class: Selection-domain issue / Solver-convergence issue / Runtime timeout issue.
- 几何重建后，组件边界探针 `bnd1`（`phis` 端电压）和 `bnd2`（端电流）选择为空；循环事件读取 `vol_loaded=vol+V_contact_drop`，因此空探针会让启用事件的瞬态在初始化阶段失败。关闭事件后逐层加入电化学、力学、压力反馈和呼吸均能通过，是定位该问题的关键证据。
- 将 `bnd1/bnd2` 都重新绑定到正极电流端边界 2 后，120 s 全耦合烟雾计算通过，18000 s 完整循环在 7115.7 s 和约 14707 s 正常触发充、放电截止事件。
- `sim exec` 的默认单段执行超时为 300 s；本算例首次在约 331 s 完成求解，但超时发生在 `model.save()` 之前，导致解未落盘。长求解前应在服务进程中提高 `sim._timeout.DEFAULT_TIMEOUT_S`，或使用显式支持长超时的运行入口，并在脚本内“求解后立即保存”。
- 本扣电的 `i_1C=16.3985 mA`，0.5C 电流为 8.1993 mA；不得沿用软包 0.13 Ah 的容量基准。最终解包含 307 个输出时刻、0–18000 s，充/放电容量为 16.207/15.916 mAh。
- 空间后处理显示外缘局部压缩压力达到 2 MPa 限幅值，而三层区域平均压力峰值仅 0.313 MPa。尖角/接触附近局部峰值必须与区域平均量同时报告，并在网格独立性和材料标定前只作为热点定位依据。
- 最终验收脚本首次错误地断言了不存在的参数 `I_0p5C`，COMSOL 返回“未知模型参数”；该模型的真实容量基准参数是 `i_1C`，0.5C 电流由循环表达式计算。验收脚本应优先回读模型中实际存在的参数/边界表达式，不能凭命名约定构造参数名；改为校验 `i_1C` 后复验通过。
