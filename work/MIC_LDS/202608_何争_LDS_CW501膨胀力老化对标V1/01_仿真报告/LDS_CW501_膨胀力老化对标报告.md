# LDS CW501 膨胀力老化对标报告

## 1. 数据提取

从 `E:\Downloads\膨胀力数据整理.xlsx` 提取（见 `03_输入数据/`）：

| 组 | 工况 | 技术 | 圈数 | SOH 终点 | F_max | F_min | F_min 斜率 |
|---|---|---|---|---|---|---|---|
| A1F9R00003 | 25℃ 0.125P | LDS | 368 | 95.05% | 321→581 | 296→404 | 31.1 N/100c |
| A1F9R00001 | 25℃ 0.125P | LDS | 368 | 95.07% | 320→532 | 299→384 | 24.3 N/100c |
| A0G2A00003 | 25℃ 0.25P | LDS | 356 | 95.73% | 419→979 | 316→662 | 90.9 N/100c |
| A0G2A00002 | 25℃ 0.25P | LDS | 355 | 95.74% | 420→1027 | 309→646 | 93.2 N/100c |
| A0G2A00002 | 25℃ 0.25P | MIC | 1588 | 89.69% | 445→1142 | 291→894 | 33.9 N/100c |

关键规律：0.25P 相对 0.125P 的 F_min 斜率比 ≈ 3.4×（≈ 两夹具刚度比），而 SOH 损失相近（≈4.3–4.9%/360c，近倍率无关）。

## 2. 仿真设置

- 模型：DFN + SEI(ec reaction limited) + SEI porosity change + 析锂(irreversible) + plating porosity change
  + particle mechanics(swelling and cracking / swelling only) + SEI on cracks + LAM(stress-driven) + contact resistance
- 工况：25℃ 恒流充放电（Charge 0.125C/0.25C → 3.65V / Rest / Discharge → 2.5V / Rest），t_factor=50，8 圈 ≈ 400 等效圈
- 力模型：`calculate_cycle_swelling`（engineering 法），F = max(0, k_eff·ΔL + preload)

## 3. 杠杆分析与调参结论（核心）

| 参数 | 倍率 | 作用 | 依据（扫描实验） |
|---|---|---|---|
| EC diffusivity | 0.125P: ×0.55 / 0.25P: ×1.0 | SEI 膜生长总量 → **SOH 主旋钮** | ×4 → SOH 损失 8.4%→15.1%，膜厚 83→157nm |
| Negative a_n (surface area/volume) | ×3.6 | 膜厚→位移力学放大（BET 面积），**不耗锂、不影响 SOH** | ×3 → F_min 斜率 8.7→27.1，SOH 不变 |
| Outer SEI partial molar volume | ×4 | 膜厚/Li 损失解耦 | 辅助 F_min 斜率 |
| Li/SEI 摩尔比 | ×0.5 | 降低 SEI 的锂消耗 | 辅助 SOH |
| k_eff（夹具刚度） | 3.0e6 / 1.02e7 N/m | 振幅与力水平；解释两工况斜率比 3.4× | 实验振幅比 ≈4× |
| preload | 296 / 310 N | F_min 起点 | = 实验第 1 圈 F_min |

**失效参数**：SEI kinetic rate constant（非限制环节）、Negative cracking rate 标量 override、Negative LAM（贡献 <1%）。

**一句话**：SOH 由 EC 扩散率控制；F_min 老化斜率 = SEI 膜生长 × a_n 力学放大 × k_eff；
a_n 是同时兼顾 SOH 与膨胀力的关键**解耦**旋钮。

## 4. 最终对标结果

见 `04_输出结果/final_calibration.png` 与 `final_calibration.json`。

- 0.125P：SOH 损失 5.13%（Exp 4.87–4.89%）；F_min 296→405N（Exp 296→384–404N），斜率 27.3 vs 24–31 N/100c
- 0.25P：SOH 损失 4.49%（Exp 4.30–4.32%）；F_min 310→660N（Exp 309–316→646–662N），斜率 87.5 vs 91–97 N/100c

## 5. 局限与后续

1. F_max 振幅增长（23→160 N）无法由线性弹簧+有界石墨应变（max ≈13.2%×L_n）复现 → F_max 终点偏低 100–270 N。
   建议：力相关刚度 k_eff(F)（夹具压缩非线性）、更陡膨胀函数、气体析出项。
2. 仿真 SEI 时间驱动 vs 实验近循环驱动 → 分工况 EC 有效倍率（工程近似）；或改用循环/吞吐量驱动的 SEI 子模型。
