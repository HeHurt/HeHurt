# 为什么电池在同一 SOC 下会有两个电压？

做电池模型对标时，经常会遇到一个现象：同一个 SOC，充电电压和放电电压并不相同。

但这里必须先区分两类完全不同的“回线”。

- 电流停止后快速消失的电压差，主要来自欧姆压降、反应极化和浓差极化。
- 充分静置后，在相同 SOC 或相同颗粒化学计量比下仍然存在的充放电 OCV 差，才属于本文讨论的电压磁滞。

DFN 和 SPMe 本身已经包含动力学、扩散和欧姆过程，因此自然能够产生动态极化回线。开启 hysteresis 选项，是在这些过程之外增加一套具有路径依赖的 OCP 模型。

它不能用来替代错误的电阻、扩散系数或交换电流密度。

对于 LFP，磁滞通常主要来自正极两相转变、成核势垒、亚稳相和相界面运动；对于石墨硅体系，Si 相也可能表现出非常明显的嵌锂/脱锂路径差异。

# PyBaMM 提供了哪三种磁滞模型？

在 PyBaMM 26.4.2 中，直接用于 OCP 磁滞的模型有三种。

1. `current sigmoid`
2. `one-state hysteresis`
3. `one-state differential capacity hysteresis`

旧代码中可能看到 `Axen` 和 `Wycisk`，它们现在只是兼容名称。新代码应使用上面的正式 option。

三种模型都可以用于 SPM、SPMe 和 DFN，区别主要在于磁滞状态如何切换，以及是否记住此前的充放电历史。

# 三种模型共用的 OCP 表达

首先需要准备三条 OCP 曲线：

```text
U_lith(z)    ：嵌锂方向 OCP
U_delith(z)  ：脱锂方向 OCP
U_eq(z)      ：平衡或平均 OCP
```

其中，`z = c_s,surf / c_s,max`，表示颗粒表面化学计量比。

PyBaMM 使用一个范围约为 `[-1, 1]` 的内部状态 `h`，在两条分支之间进行插值：

![OCP 磁滞插值方程](https://mmbiz.qpic.cn/mmbiz_png/ZdliaEzUicuN6ia2oParKatOxxzvcKMLWpDmCr1YAzoTvRHZ0bicGoppjC5nUuooDxEExgicPKHQM3Hkj2ZKAicNNrsqUaF0Ld5Px3ic9xWrNHbI6g/640?from=appmsg)

因此：

- `h = +1`：完全位于 delithiation branch。
- `h = -1`：完全位于 lithiation branch。
- `h = 0`：位于两条 OCP 的中点。

磁滞模型不会凭空改变颗粒中的锂含量。它改变的是：在相同化学计量比下，模型应该采用哪一条 OCP 路径。

# 方法一：current sigmoid

这是最简单的实现，本质上是一套“根据电流方向选择 OCP 分支”的平滑开关。

以只在 LFP 正极开启磁滞为例：

```python
options = {
    "open-circuit potential": (
        "single",
        "current sigmoid",
    ),
}

model = pybamm.lithium_ion.DFN(options=options)
```

tuple 的顺序始终是：

```text
(negative electrode, positive electrode)
```

当前源码中的磁滞状态近似为：

![Current sigmoid 磁滞状态方程](https://mmbiz.qpic.cn/mmbiz_png/ZdliaEzUicuN6hwvhm2e8cgRAibRUafzrplQPfsrVBnibpAphZhmKyB0PBdlLejucW2u5KPibPsSVEyDKB1N1KBFDTSRrqrib8KpJKs584lId9BfI/640?from=appmsg)

其中，PyBaMM 会根据正负极自动转换 `i_lith` 的方向。

这意味着：

- 发生 lithiation 时，OCP 迅速切向 lithiation branch。
- 发生 delithiation 时，OCP 迅速切向 delithiation branch。
- 电流为零时，`h = 0`，OCP 回到两条曲线中间。

它的优点是简单、稳定、几乎没有新增待辨识参数。

但它没有状态方程，也不保存历史。只要电流换向，OCP 就几乎立即切换。因此它不适合描述：

- 不完整充放电形成的 minor loop；
- 电流换向后的渐进过渡；
- 静置期间仍保留的路径记忆。

它更适合用作双 OCP 是否必要的快速诊断模型。

# 方法二：one-state hysteresis

这是工程上最值得优先使用的通用磁滞模型。

开启方式为：

```python
options = {
    "open-circuit potential": (
        "single",
        "one-state hysteresis",
    ),
}
```

定义：

```text
s = sign(i_vol)
```

其中，`i_vol` 是发生磁滞的活性材料相的 volumetric interfacial current density。

PyBaMM 的局部约定为：

```text
i_vol < 0 ：lithiation
i_vol > 0 ：delithiation
```

方向相关的磁滞转换参数为：

![方向相关的磁滞转换参数](https://mmbiz.qpic.cn/sz_mmbiz_png/ZdliaEzUicuN40RTtAajXfhvyM0WtoEUZD7Pphcunl8hYACLcZXtSCNDq6FmbMp6Wq0YUbODBKW4xxicadH274ib9fIzrsXMicekm6K3bZkJ2Ribk/640?from=appmsg)

当前版本源码实际求解的状态方程为：

![One-state hysteresis 控制方程](https://mmbiz.qpic.cn/mmbiz_png/ZdliaEzUicuN4l9h5FcpiaDbqYhT1ibwp17O6QngvPl9Brseicxw1ktqT8Jqib5q24WWjSN7x4uePd3cDUQmu4rdlrL144xsu8kGndXXiahZTsMusI/640?from=appmsg)

这里：

- `F` 是 Faraday constant。
- `c_s,max` 是活性材料最大锂浓度。
- `epsilon_s` 是该活性相体积分数。
- `gamma_lith` 和 `gamma_delith` 分别控制两个方向的磁滞切换速度。

其中：

![局部嵌锂脱锂速率尺度](https://mmbiz.qpic.cn/sz_mmbiz_png/ZdliaEzUicuN7ibpfVoQ6gdoFCUO1MtugOpkRP3HBRhBExMFuU0JMvSQgevgfneScdejMh1Wf5HYM3ULh8ugpF5EnuhKCsmJhrJNN647ttgeeM/640?from=appmsg)

可以理解为局部活性材料嵌锂或脱锂的速率尺度。

当 `i_vol > 0` 时，`h` 会逐渐趋向 `+1`，也就是 delithiation branch；当 `i_vol < 0` 时，`h` 会逐渐趋向 `-1`，也就是 lithiation branch。

所以它不是在电流换向瞬间跳转，而是根据反向通过的电量逐渐切换。

这带来了真正的“历史记忆”：

- `gamma` 越大，少量反向容量就能完成分支切换。
- `gamma` 越小，原有路径保持得越久。
- 两个方向使用不同的 gamma，可以表达嵌锂和脱锂的不对称性。

# 方法三：差分容量磁滞

正式名称为：

```text
one-state differential capacity hysteresis
```

开启方式：

```python
options = {
    "open-circuit potential": (
        "single",
        "one-state differential capacity hysteresis",
    ),
}
```

它在 one-state hysteresis 的基础上，引入了局部差分容量：

![局部差分容量方程](https://mmbiz.qpic.cn/mmbiz_png/ZdliaEzUicuN6j7nPQibsxJtng5GtRqdh56XlK2h2hiboH2znrONa8vgU2NwBqt5l7MpJR5dicqsiba1MyjZ45hHTEDOF3gAANAuKTQuCy7qTVRbQ/640?from=appmsg)

再让磁滞转换速率随差分容量变化：

![差分容量磁滞转换速率](https://mmbiz.qpic.cn/sz_mmbiz_png/ZdliaEzUicuN54GnIq1xSjbEzBvOjTAc2QnqZKgvGKSKbCzgGGicEnhy2aMpvZysHgTiceYeK09AYib4o4Dlh6ibM6ez1iactWoRmryoFgzh2wNuz8/640?from=appmsg)

最终的 `dh/dt` 形式与 one-state hysteresis 相同，只是 `gamma` 不再是简单常数，而是随 SOC、温度和 OCP 斜率变化。

当 `x > 0` 时：

- OCP 平台很平，`|dU/dz|` 较小，差分容量较大，磁滞状态转换较慢。
- OCP 斜坡较陡，差分容量较小，磁滞状态转换较快。

这对于 LFP 平台区、Si 多阶段相变等问题更加灵活。

它的代价是参数更多、数值敏感性更高。由于模型需要计算 `dU_eq/dz`，平均 OCP 必须足够平滑并能够被 PyBaMM 符号求导。带有噪声、尖点或不连续插值的 OCP 很容易放大为异常差分容量。

# 参数应该怎样提供？

以只在正极开启 one-state hysteresis 为例：

```python
import pybamm

parameter_values = pybamm.ParameterValues("Chen2020")


def U_lith(sto):
    # 替换成实验辨识的 lithiation OCP
    return 3.40 + 0.05 * sto


def U_delith(sto):
    # 替换成实验辨识的 delithiation OCP
    return 3.43 + 0.05 * sto


def U_eq(sto):
    return 0.5 * (U_lith(sto) + U_delith(sto))


parameter_values.update(
    {
        "Positive electrode lithiation OCP [V]": U_lith,
        "Positive electrode delithiation OCP [V]": U_delith,
        "Positive electrode OCP [V]": U_eq,
        "Positive particle lithiation hysteresis decay rate": 20.0,
        "Positive particle delithiation hysteresis decay rate": 20.0,
        "Initial hysteresis state in positive electrode": 0.0,
    },
    check_already_exists=False,
)
```

然后正常建立 Simulation：

```python
model = pybamm.lithium_ion.SPMe(
    options={
        "open-circuit potential": (
            "single",
            "one-state hysteresis",
        ),
    }
)

experiment = pybamm.Experiment(
    [
        "Discharge at 0.2C for 1 hour",
        "Rest for 30 minutes",
        "Charge at 0.2C for 1 hour",
        "Rest for 30 minutes",
    ]
)

simulation = pybamm.Simulation(
    model,
    parameter_values=parameter_values,
    experiment=experiment,
    solver=pybamm.IDAKLUSolver(),
)

solution = simulation.solve(calc_esoh=False)
```

# Composite electrode 怎样配置？

`Chen2020_composite` 的负极包含 graphite primary phase 和 silicon secondary phase。

如果只在 Si 相开启磁滞：

```python
options = {
    "particle phases": ("2", "1"),
    "open-circuit potential": (
        (
            "single",
            "one-state hysteresis",
        ),
        "single",
    ),
}
```

它表示：

```text
负极 primary graphite  ：single
负极 secondary silicon ：one-state hysteresis
正极 primary NMC       ：single
```

对应参数需要增加 `Secondary:` 前缀：

```python
parameter_values.update(
    {
        "Secondary: Negative electrode lithiation OCP [V]": U_lith,
        "Secondary: Negative electrode delithiation OCP [V]": U_delith,
        "Secondary: Negative electrode OCP [V]": U_eq,
        "Secondary: Negative particle lithiation hysteresis decay rate": 20.0,
        "Secondary: Negative particle delithiation hysteresis decay rate": 20.0,
        "Secondary: Initial hysteresis state in negative electrode": 0.0,
    },
    check_already_exists=False,
)
```

# 初始磁滞状态怎样选择？

常用约定为：

```text
h_init = +1 ：初态来自 delithiation 路径
h_init = -1 ：初态来自 lithiation 路径
h_init =  0 ：初始历史未知，暂取两分支中间
```

长期使用 `h_init = 0` 可能掩盖真实的初始历史。

更好的办法是先跑一段完整充电或放电 conditioning，再把得到的 solution 作为后续实验的 `starting_solution`，让磁滞状态由预处理过程自然建立。

# 磁滞是否会产生热？

会。

当 thermal model 开启时，PyBaMM 会计算：

![磁滞产热方程](https://mmbiz.qpic.cn/sz_mmbiz_png/ZdliaEzUicuN434kib9DPq21IRC2qAhL5icW3SOyTkj9yntMNtG1ITsyWtDA6IksibDK08Z0LTA5iaF7633EdQ6zMcKMItBEwCL8uAbHg6a8iaH5oE/640?from=appmsg)

并把它加入总产热：

![总产热方程](https://mmbiz.qpic.cn/sz_mmbiz_png/ZdliaEzUicuN5P8Oib79bhAosfIVbysI0aP1J1gZZFpVuSAXcKNvXfDT0yEZ6O7HnjVcTCsOPGDbjnricChjKVzJZCL2l6GvmzJPkhxEwxYpSAo/640?from=appmsg)

要让磁滞产热进一步反馈到温度和电化学参数，可同时开启：

```python
options = {
    "open-circuit potential": (
        "single",
        "one-state hysteresis",
    ),
    "thermal": "lumped",
}
```

可以直接读取：

```python
solution["Hysteresis electrochemical heating [W]"]
solution["Volume-averaged hysteresis electrochemical heating [W.m-3]"]
```

# 参数辨识应该按什么顺序？

建议遵循下面的顺序。

1. 用低倍率准 OCV 或 GITT 数据辨识 `U_lith(z)` 和 `U_delith(z)`。
2. 先用 `current sigmoid` 判断“双 OCP”能否解释主要电压差。
3. 有电流换向、静置和部分循环数据后，再升级到 `one-state hysteresis`。
4. 先固定双 OCP 曲线，再拟合 `gamma_lith` 和 `gamma_delith`。
5. 如果不同 SOC 区域的切换速度明显不同，再采用差分容量磁滞模型拟合 `Gamma` 和 `x`。

只依靠 full-cell voltage，同时自由拟合正负极磁滞、扩散系数、交换电流密度和接触电阻，会出现严重的参数不可辨识。

更可靠的数据组合是：

- 低倍率完整充放电；
- 充分静置或 GITT；
- 多个 SOC 的电流换向；
- 不同深度的 minor loop；
- 条件允许时增加三电极或半电池 OCP。

# 工程选择建议

如果只是快速判断是否需要双 OCP，使用 `current sigmoid`。

如果要模拟电流换向、静置和部分循环，优先使用 `one-state hysteresis`。

只有实验明确显示平台区与斜坡区的磁滞转换速度不同，才升级到 `one-state differential capacity hysteresis`。

对于典型 LFP 大电芯，建议从下面的配置起步：

```text
正极：one-state hysteresis
负极：single
模型：SPMe 或 DFN
数据：低倍率双 OCP + 电流换向 + minor loop
```

最后再强调一次：磁滞是路径相关的平衡电位问题，欧姆、动力学和扩散是有限电流下的极化问题。只有先把这两类机制分开，PyBaMM 的参数才会真正具有清楚的物理意义。
