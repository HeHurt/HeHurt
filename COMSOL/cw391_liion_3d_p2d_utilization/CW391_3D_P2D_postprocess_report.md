# CW391 LFP/Gr 软包 3D-P2D 计算后处理报告

生成时间: 2026-06-16

## 1. 模型状态

本轮已基于 COMSOL 官方 `pouch_cell_utilization` 案例建立并跑通真实 `Lithium-Ion Battery` 接口模型。该模型包含 3D current collector/tab、porous electrode、separator 和 particle intercalation extra dimension，属于 3D-P2D / pseudo-4D 表述，不是等效电阻或简化 proxy 模型。

工作目录:

`D:\Users\hez\Desktop\hithium\COMSOL\cw391_liion_3d_p2d_utilization`

主要交付物:

- `CW391Liion3DP2DUtilization.java`: 自动建模、求解、导出脚本
- `CW391_3D_P2D_soc90_100.mph`: 90% -> 100% SOC 工况结果模型
- `CW391_3D_P2D_soc45_55.mph`: 45% -> 55% SOC 工况结果模型
- `metrics_soc90_100.csv`, `metrics_soc45_55.csv`: COMSOL 原始标量导出
- `postprocess_summary.csv`: 后处理汇总表
- `plots/*.png`: 场图导出

## 2. 当前计算版本的边界

最终计算版本使用小尺寸代表片几何和 CW391 层厚，平面尺寸为 `W_cell=10 mm`, `H_cell=20 mm`，tab 尺寸为 `W_tab=5 mm`, `H_tab=1 mm`。电化学体系已替换为 LFP/Gr 参数，并将端子电流改为 CW391 面积缩放目标电流。

网格问题定位和修复:

- 官方几何默认 Cu/Al 集流体厚度相等，因此两个 tab block 都用 `L_neg_cc/2` 厚度。
- CW391 参数中 `L_neg_cc=8 um`, `L_pos_cc=14 um`，若不修正，正极 tab 厚度仍为 4 um，而正极集流体半厚为 7 um，正极集流体域不可 sweep。
- 已将正极 tab block `blk2` 厚度改为 `L_pos_cc/2`，并保留官方 `mapped + swept` 网格策略。
- 修复后 `run_small_cw391_fixedtab.log` 显示两个工况均完成时间步进和图像导出，总运行时间 255 s。

因此，当前 `.mph` 是小尺寸 CW391 层厚版本，不是官方尺寸 mesh-safe 临时版。

## 3. 参数与工况

化学体系:

- 正极: LFP, 使用平滑 LFP-like equilibrium potential
- 负极: Graphite, 沿用官方石墨材料曲线并更新 CW391 关键参数
- 正极参数: `rp_pos=0.43 um`, `csmax_pos=22806 mol/m3`, `epss_pos=0.709`, `sigmas_pos=4 S/m`
- 负极参数: `rp_neg=5.90 um`, `csmax_neg=31370 mol/m3`, `epss_neg=0.664`, `sigmas_neg=100 S/m`

工况:

| 工况 | 起始 SOC | SOC 通量 | 时间 | 电流 |
|---|---:|---:|---:|---:|
| `soc90_100` | 0.90 | 0.10 | 90 s | 0.0413285 A |
| `soc45_55` | 0.45 | 0.10 | 90 s | 0.0413285 A |

面积缩放容量:

`Q_model_target = 0.0103321285 Ah`

## 4. 标量结果

| 工况 | 末端电压 / V | 末端 cell SOC | 平均负极 SOC | 平均正极 SOC |
|---|---:|---:|---:|---:|
| `soc90_100` | 3.621659 | 0.999998 | 0.682253 | 0.192548 |
| `soc45_55` | 3.545226 | 0.549997 | 0.383159 | 0.522352 |

对比:

- 同样 10% SOC 通量和同样电流下，`90 -> 100% SOC` 的末端电压比 `45 -> 55% SOC` 高 `76.4 mV`。
- `90 -> 100% SOC` 末端正极平均 SOC 降至 `0.193`，负极平均 SOC 升至 `0.682`；这说明高 SOC 窗口中电极平均嵌锂状态明显不同，局部 current utilization 梯度叠加到更靠近端点的电极状态上。
- 当前模型中的 in-plane utilization 形貌主要由 tab/current collector 几何和电流路径决定，因此两个 SOC 窗口的 relative utilization 图形近似一致；SOC 差异主要体现在电压和粒子表面 SOC 状态。

## 5. 场图

### 90 -> 100% SOC

Separator current density:

![soc90_100_separator_current_density](D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization/plots/soc90_100_separator_current_density.png)

Particle surface SOC:

![soc90_100_particle_surface_soc](D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization/plots/soc90_100_particle_surface_soc.png)

Relative utilization:

![soc90_100_relative_utilization](D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization/plots/soc90_100_relative_utilization.png)

### 45 -> 55% SOC

Separator current density:

![soc45_55_separator_current_density](D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization/plots/soc45_55_separator_current_density.png)

Particle surface SOC:

![soc45_55_particle_surface_soc](D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization/plots/soc45_55_particle_surface_soc.png)

Relative utilization:

![soc45_55_relative_utilization](D:/Users/hez/Desktop/hithium/COMSOL/cw391_liion_3d_p2d_utilization/plots/soc45_55_relative_utilization.png)

## 6. 初步机制判断

这轮结果支持一个重要拆分:

1. tab/current collector 引起的 in-plane 电流/利用率不均是存在的，且形貌稳定。
2. 单纯更换初始 SOC，在当前等温、无老化、无副反应的短期 3D-P2D 模型中，并不会自动产生明显不同的 relative utilization 形貌。
3. `90 -> 100% SOC` 的风险更可能来自同一空间不均匀分布叠加到更高的电极端点状态上: 局部过利用区域更接近负极高嵌锂、正极低嵌锂端点，因而更容易触发局部副反应、析锂/SEI 增厚、电解液氧化或界面膜颜色变化。
4. 若实验紫斑表现为从中心到边缘成圈状扩散，仅靠当前 tab 几何驱动的 3D-P2D 短期电流分布还不够，需要继续引入至少一个环状或面内扩散型驱动: 温度场、压力/接触不均、浸润/电解液耗竭、局部副反应/老化参数演化，或多层堆叠中层间散热/边界条件。

## 7. 下一步建议

优先级 1: 扩展几何与数值后处理

- 在已修复正极 tab 厚度的基础上，继续尝试用户照片比例或更接近实际极片比例的代表片。
- 导出 separator current density、particle surface SOC、relative utilization 的网格数据。
- 计算 `max/min/mean/std` 和边缘/中心区域均值差。
- 对比 `90 -> 100% SOC` 与参考 SOC 窗口的局部风险指标，而不是只比较全局容量保持率。

优先级 2: 增强机理

- 加入热场或 prescribed temperature map，比较中心/边缘温升差异。
- 加入高 SOC 副反应指标，如负极过电位、局部电解液电位降、正极电位窗口、局部 reaction current density。
- 若要解释紫斑扩散，建议将 3D-P2D 的局部分布结果映射到 1D 老化模型，或者在 3D 模型中加入简化副反应速率场作为后处理指标。

优先级 3: 与老化模型耦合

- 将 3D-P2D 得到的局部利用率/局部 SOC 偏差映射到 1D 老化模型。
- 对 90-100% SOC 和参考 SOC 窗口分别跑 SEI/LAM/析锂风险指标，形成短期分布 + 长期老化的联合解释链。
