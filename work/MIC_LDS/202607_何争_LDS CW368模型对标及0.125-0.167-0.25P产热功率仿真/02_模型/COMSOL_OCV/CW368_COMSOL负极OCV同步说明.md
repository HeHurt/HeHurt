# CW368 修正负极 OCV 在 COMSOL 中的同步方法

## 1. 推荐做法：直接导入修正后的 OCP 表

在 COMSOL 中分别创建两个一维插值函数：

- `OCV_neg_ch(theta_n)`：
  `CW368_Gr_charge_OCP_calibrated.dat`
- `OCV_neg_dis(theta_n)`：
  `CW368_Gr_discharge_OCP_calibrated.dat`

设置建议：

- Argument unit：`1`
- Function unit：`V`
- Interpolation：Piecewise cubic
- 数据范围：`0 ≤ theta_n ≤ 1`
- 避免在范围外外推，优先限制输入到 `[0,1]`

其中：

```text
theta_n = c_s_neg_surface / c_s_max_neg
```

充电时负极发生 lithiation，使用 `OCV_neg_ch`；放电时负极发生
delithiation，使用 `OCV_neg_dis`。如果现有 COMSOL 模型已有充放电
迟滞或方向选择器，应替换选择器两侧的函数，不要再增加第二层开关。

采用这一路线时，负极 `theta_min/theta_max`、`csmax_neg`、电极容量和
N/P 配平先保持原模型值不变。修正已经包含在 OCP 表内。

## 2. 等效做法：保留原 OCP 表，修改函数自变量

若不想替换原始 `Gr_charge/Gr_discharge` 表，可在 COMSOL 中定义：

```text
theta_n_raw = c_s_neg_surface/c_s_max_neg

theta_n_eff =
min(1,max(0,
theta_n_raw
+0.07771413
 /(1+exp(-(theta_n_raw-0.212309)/0.06011121))
 /(1+exp( (theta_n_raw-0.600000)/0.06011121))
))
```

然后令：

```text
Eeq_neg_charge =
OCV_neg_charge_original(theta_n_eff)-0.002748570205[V]

Eeq_neg_discharge =
OCV_neg_discharge_original(theta_n_eff)-0.002748570205[V]
```

这与导出的修正 OCP 表等效。两条路线只能选一条，不能同时使用。

## 3. 嵌锂区间如何设置

当前 CW368 PyBaMM 对标模型在 25℃完整窗口内的负极 bulk
stoichiometry 约为：

```text
0% SOC：theta_n ≈ 0.0080
100% SOC：theta_n ≈ 0.7768
```

正极对应约为：

```text
0% SOC：theta_p ≈ 0.9549
100% SOC：theta_p ≈ 0.0111
```

若 COMSOL 当前容量和初始 OCV已经匹配，保留原来的嵌锂区间，只替换 OCP
表。若是从头建立 CW368，可把上述 bulk stoichiometry 作为初始检查值，
再通过静置 OCV和正负极容量配平确定最终区间；不要用充电端子截止
3.65 V 反解 100% SOC。

本次 warp 在负极两个端点仅产生很小变化：

```text
f(0.0080) ≈ 0.0105
f(0.7768) ≈ 0.7807
```

但在中段变化显著：

```text
f(0.25) ≈ 0.3005
f(0.40) ≈ 0.4719
f(0.50) ≈ 0.5648
f(0.60) ≈ 0.6388
```

因此仅把嵌锂区间从 `[0.0080, 0.7768]` 改成
`[0.0105, 0.7807]`，不能复现平台移动；必须导入修正表或使用
`theta_n_eff` 非线性映射。

## 4. COMSOL 中需要检查的消费者

1. 负极 Particle Intercalation 节点的 `Eeq` 是否真正引用新的函数。
2. `theta_n` 使用表面浓度，而不是整电芯 SOC 或平均浓度。
3. 充放电方向选择是否与负极 lithiation/delithiation 一致。
4. `socicd1`、`socmin/socmax`、`csmax_neg` 和正负极容量配平没有被重复修改。
5. 更换 OCP 后先检查初始静置 OCV，再跑低倍率充放电 smoke case。
6. 电压截止仍使用 3.65/2.5 V 端子条件，但不能把它们当作 OCV 端点。

## 5. 验收建议

- 25℃低倍率中段平台拐点应提前，接近实测容量位置。
- 初始静置 OCV偏差应控制在几十 mV以内。
- 可用容量变化不应超过预设容差。
- 若平台改善但容量明显变化，先检查是否同时改了 OCP 表和嵌锂区间。
- 接触阻抗压降与 OCP 修正相互独立，不要用 OCP 再补偿一次接触压降。
