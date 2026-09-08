---
title: 从控制方程到调参症状：直观理解 PyBaMM DFN 老化机制
author: 何争
digest: SEI、析锂、颗粒开裂、LAM、孔隙率与产热如何耦合，以及参数调高后曲线会怎么变。
cover: cover.png
---

# 从控制方程到调参症状：直观理解 PyBaMM DFN 老化机制

在 PyBaMM 的 DFN 模型中，SEI、析锂、颗粒开裂和活性材料损失并不是四条互不相关的经验曲线。它们会通过锂库存、反应面积、孔隙率、极化和温度相互耦合。

因此，看到“容量初期掉得快”“充电末端负极电位下降”“中后期突然出现膝点”或“产热快速上升”时，不能只盯一个参数。更有效的做法是：

> 先从可观察症状判断主导链路，再回到控制方程选择参数。

本文讨论下面这组常见配置：

```python
"SEI": "ec reaction limited"
"SEI porosity change": "true"
"lithium plating": "irreversible"
"lithium plating porosity change": "true"
"particle mechanics": ("swelling and cracking", "swelling only")
"SEI on cracks": "true"
"loss of active material": "stress-driven"
"calculate discharge energy": "true"
"contact resistance": "true"
"open-circuit potential": ("current sigmoid", "current sigmoid")
```

## 一、先记住三条耦合链

第一条是“副反应—孔隙率—极化—析锂”链：

```text
SEI / 析锂 → LLI 增加、孔隙率下降
            → 电解液传输阻力增加
            → 负极极化加重
            → 析锂进一步增强
```

第二条是“应力—裂纹—裂纹 SEI”链：

```text
颗粒应力 → 裂纹扩展 → 新生表面积增加
         → 裂纹 SEI 增长
         → LLI 与孔隙堵塞加快
```

第三条是“LAM—局部电流—极化与产热”链：

```text
应力 → LAM 增加 → 有效反应面积下降
     → 局部反应电流密度上升
     → 反应极化、产热和析锂风险上升
```

这三条链决定了一个重要事实：**相同 SOH 不代表相同阻抗，也不代表相同产热。**

## 二、SEI：谁控制初期斜率，谁控制后期自限

在 `ec reaction limited` 模型中，核心关系可写成：

![SEI生长、浓度与膜厚控制方程](formula_01_sei.png)

其中，`k_SEI`控制反应动力学，`D_EC`控制 EC 穿过 SEI 的能力，`L_SEI`同时增加扩散距离和膜阻。由于分母中存在 `1 + λ`，SEI 会随膜厚增长逐渐自限。

### 1. SEI kinetic rate constant

调高 `SEI kinetic rate constant`，最直接的表现是：

- 初期 SEI 电流增大；
- 初期容量保持率斜率变陡；
- 库仑效率降低；
- 膜阻和负极极化更快上升；
- 析锂风险可能被间接提前。

这是“前几十圈就掉得快”时最先检查的参数。

### 2. EC initial concentration

在其他量不变时，`EC initial concentration`近似线性放大 SEI 电流。调高后，LLI 增加，初期衰减通常更明显。

### 3. EC diffusivity

`EC diffusivity`更像“后期是否自限”的旋钮。调高后，EC 更容易穿过已经变厚的 SEI，厚膜的自钝化作用减弱，常见表现是：

- BOL 变化不一定很大；
- 中后期 SEI 仍能持续增长；
- 容量、DCR 和产热的后期膝点提前。

### 4. SEI partial molar volume 与 z_SEI

上图后两式给出了 SEI 摩尔浓度与膜厚之间的关系。

因此，真正控制“单位锂损失形成多少膜厚”的关键组合是 `V̄_SEI / z_SEI`。

- `SEI partial molar volume`增大：同样 SEI 摩尔数形成更厚的膜，阻抗和孔隙损失更快；
- `Ratio of lithium moles to SEI moles`增大：同样 LLI 对应的 SEI 摩尔数减少，膜厚和堵孔减弱。

这两个参数对容量与阻抗的影响并不等价。它们可能让能量、DCR 和产热先明显变化，而容量保持率变化相对有限。

### 5. Initial SEI thickness 与 SEI resistivity

增大初始 SEI 厚度或 SEI 电阻率，会使 BOL 极化和产热立即增加，充电平台更高、放电平台更低。

但“初始膜更厚”不等于“后续 SEI 长得更快”。由于扩散距离和膜阻已经增加，新增 SEI 的增长速率反而可能更低。

## 三、孔隙率：为什么后期容易突然加速

开启 SEI 和析锂引起的孔隙率变化后，可将总沉积厚度写成：

![副反应沉积导致孔隙率变化的控制方程](formula_02_porosity.png)

这意味着基础 SEI、析锂、dead lithium 和裂纹 SEI 都会占据电解液空间。

孔隙率的影响通常具有明显非线性：

- 早期小幅下降时，电压和产热变化可能不明显；
- 进入低孔隙率区域后，有效离子电导率和扩散能力快速下降；
- 电解液浓差极化、DCR 和欧姆热同时上升；
- 充电末端负极电位更容易进入析锂有利区；
- 最终形成“堵孔—极化—析锂—继续堵孔”的正反馈。

所以，后期产热快速上翘时，应优先检查孔隙率，而不是只看 SOH。

## 四、不可逆析锂：触发条件与反应速率要分开

析锂过电位和不可逆析锂电流可概括为：

![不可逆析锂的过电位、电流与dead lithium控制方程](formula_03_plating.png)

不可逆选项下，析出的锂不再参与后续剥离，而是按上图最后一式形成 dead lithium。

这里必须区分两个问题。

### 1. 什么时候进入析锂窗口

析锂是否有利，首先由负极表面电位差、SEI 膜过电位和模型中的门控判据决定。以下因素更容易让析锂提前：

- 负极固相扩散系数降低；
- 负极交换电流密度降低；
- SEI 膜阻增大；
- 负极孔隙率下降；
- 负极 LAM 导致有效反应面积减少；
- 充电倍率提高或温度降低。

### 2. 进入窗口后析多少

`Lithium plating kinetic rate constant`、plating 交换电流密度和 transfer coefficient 主要控制进入析锂窗口后的反应强度。

因此，把“plating 动力学参数调大”直接等同于“热力学触发点提前”并不严谨。更准确的说法是：

> 动力学参数调大后，一旦进入析锂有利区，析锂量和 dead lithium 会更快累积，容量膝点和堵孔膝点更早显现。

还要注意：部分工程版本会在 irreversible 分支中增加 sigmoid 门控，甚至修改 SEI 膜过电位的符号。此时 `j_0,stripping` 也可能间接参与“开关”判据。标定析锂前，必须以实际运行源码为准，不能只看官方文档或参数名。

## 五、颗粒开裂与裂纹 SEI：典型的后期加速器

颗粒表面拉应力驱动裂纹扩展。简化关系为：

![颗粒裂纹扩展的Paris型控制方程](formula_04_cracking.png)

各参数的直观影响如下：

- `cracking rate`增大：裂纹整体增长更快；
- 初始裂纹长度增大：初期已有更多裂纹面积，Paris 项也同时增大；
- 裂纹宽度或裂纹面密度增大：不一定改变裂纹传播速度，但会增加裂纹表面积；
- `Paris b`增大：应力强度因子增大，裂纹加快；
- `Paris m`增大：对高应力更敏感，常表现为前期差异不大、后期突然加速；
- 弹性模量、偏摩尔体积或粒径增大，以及固相扩散系数降低：浓度梯度和应力通常增大。

当前 tuple 配置表示：

- 负极：`swelling and cracking`，会发生裂纹传播；
- 正极：`swelling only`，计算膨胀和应力，但不开启裂纹传播。

所以，正极 cracking 参数在当前配置下基本不起作用。

开启 `SEI on cracks` 后，裂纹面积会直接成为新的 SEI 反应面积：

```text
开裂 → 新生表面 → 裂纹 SEI
     → LLI 与堵孔增加 → 极化继续上升
```

这也是“前期平缓、中后期突然变陡”最常见的来源之一。

## 六、应力驱动 LAM：为什么平台和产热一起变化

应力驱动 LAM 的核心关系可写成：

![应力驱动活性材料损失控制方程](formula_05_lam.png)

LAM 会降低活性材料体积分数和有效反应面积。同一总电流被迫集中到更小的面积上，局部反应电流密度上升，反应极化与反应热随之增加。

- `LAM constant proportional term`增大：在应力已经存在时，活性材料损失更快；
- `critical stress`减小：更容易进入 LAM 区域；
- `LAM exponential term`增大：低应力区影响可能减弱，高应力区敏感性显著增强，更容易形成后期膝点；
- 负极 LAM 增强：负极利用率和 N/P 裕量下降，局部电流增大，析锂风险上升；
- 正极 LAM 增强：正极更早成为容量限制端，充电平台更快抬升并提前触发上截止电压。

需要注意：`β_LAM`调大并不必然造成初期斜率增大。如果初期颗粒应力很低，LAM 仍可能主要表现为中后期加速。

## 七、老化参数如何传递到产热

产热可以按下面的口径理解：

![总产热的组成口径](formula_06_heat.png)

其中：

- 孔隙率下降、SEI 膜阻增加：主要推高欧姆热与电解液传输损失；
- LAM、动力学恶化：主要推高反应过电位与反应热；
- 接触电阻：直接增加 `I²R_contact`；
- 熵热系数与温度：决定可逆热 `Q̇_rev` 的大小和符号；
- current-sigmoid OCP：改变充放电 OCP 支路、端电压和反应过电位，但不具备真实的滞回状态记忆。

这也解释了为什么不同电芯的产热增长率可能相差很大：

> 容量衰减主要回答“还剩多少可循环锂和活性材料”，产热增长则更敏感于“阻抗、孔隙率和局部反应电流恶化了多少”。

如果某个模型在 60% SOH 时孔隙率仍较高、膜阻增长有限，即使容量已经明显衰减，产热也可能只增加不到 10%。反过来，如果孔隙率接近堵塞或有效反应面积大幅下降，产热完全可能增长一倍以上。

## 八、三个容易误读的接口

### calculate discharge energy

`calculate discharge energy = true`只增加容量、能量和 throughput energy 的积分统计，不改变电压、老化或产热。

### contact resistance

`contact resistance = true`让端电压包含接触电阻压降，并在相应热口径中增加 `I²R_contact`。

但如果 `Contact resistance [Ohm]`是常数，它不会随循环自行增长。若希望模拟接触劣化，需要显式定义随时间、循环或状态变化的接触电阻模型。

### current sigmoid OCP

`current sigmoid`根据电流方向在 lithiation 与 delithiation OCP 之间平滑切换。它会改变充放电平台、能量效率、反应过电位以及相应产热，但没有真实滞回模型的历史状态。

因此，充放电 OCP 支路方向、两支曲线的间距以及熵热系数口径必须同时检查。

## 九、按症状找参数

### 症状 1：初期容量保持率掉得快

优先检查：

- `SEI kinetic rate constant`
- `EC initial concentration`
- 初始 SEI 厚度是否造成过早截止

### 症状 2：能量比容量掉得快，平台先恶化

优先检查：

- `Contact resistance`
- `SEI resistivity`
- `SEI partial molar volume / z_SEI`
- 电解液传输参数

### 症状 3：前期正常，中后期突然出现膝点

优先检查：

- `Negative electrode cracking rate`
- `Negative electrode LAM constant proportional term`
- `EC diffusivity`
- 负极孔隙率是否进入低值区

### 症状 4：充电末端负极电位下降，析锂提前

优先检查：

- 负极扩散与交换电流密度；
- SEI 膜阻；
- 负极孔隙率；
- 负极 LAM；
- 温度、倍率和析锂门控判据。

进入析锂窗口后，再调整 plating 动力学参数。

### 症状 5：容量变化不大，但 DCR 和产热涨得快

优先检查：

- SEI 膜厚与电阻率；
- 孔隙率变化；
- Bruggeman 指数；
- 接触电阻；
- LAM 导致的局部反应电流集中。

## 十、推荐的标定顺序

1. 用 BOL 电压、DCR、能量效率和产热校准 OCP、动力学、电导率、扩散及接触电阻。
2. 用早期容量与库仑效率校准基础 SEI 参数。
3. 用中后期 DCR、孔隙率诊断和产热校准 `D_EC`、`V̄_SEI/z_SEI`及传输参数。
4. 用低温快充、负极参比电位或析锂实验校准 plating。
5. 用厚度、裂纹、LAM 或电极容量诊断校准力学参数。

最不推荐的做法，是只用一条容量保持率曲线同时拟合所有老化参数。

同样的 60% SOH，既可能来自大量 LLI 但阻抗增长有限，也可能来自严重堵孔和反应面积损失。前者产热可能变化不大，后者则可能出现数倍增长。

## 结语

如果只想快速记住主矛盾，可以归纳为五句话：

- 初期斜率先看基础 SEI；
- 充电末端先看负极极化与析锂窗口；
- 中后期膝点先看裂纹、LAM 和孔隙率；
- 能量比容量更敏感时先看阻抗；
- 产热快速增长时，不要只看 SOH，要看阻抗与局部反应状态。

参数名只是入口，真正决定曲线形状的是控制方程和机制之间的反馈。
