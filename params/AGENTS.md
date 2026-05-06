# params — 参数文件 Harness

## 这个区域是什么
每个 `paramsXXX.py` 封装一种电芯的 PyBaMM 参数。Notebook 和 src 模块通过调用 `get_hithium_params(t_factor, temperature)` 获取参数字典。

## 参数文件结构

每个文件必须导出：
```python
def get_hithium_params(t_factor=1, temperature=298.15) -> dict:
    """
    返回可用于 pybamm.ParameterValues.update() 的参数字典。
    
    参数:
        t_factor: 老化倍率因子
        temperature: 温度 (K)
    """
```

## 参数字典必须包含的关键项
- `"Nominal cell capacity [A.h]"`
- `"Lower voltage cut-off [V]"` / `"Upper voltage cut-off [V]"`
- OCP 函数（充/放电分别定义）
- 扩散系数函数（温度依赖）
- 交换电流密度函数（温度依赖）

## 温度依赖函数写法
```python
def LFP_diffusivity(sto, T):
    """正极扩散系数，必须接受 (sto, T) 两个参数"""
    D_ref = 1e-14
    E_D_s = 30000  # 活化能 J/mol
    return D_ref * np.exp(-E_D_s / pybamm.constants.R * (1/T - 1/298.15))
```

## 防参数污染规则（最重要的规则）
```python
# ✅ 正确: 每个温度循环内重新创建
for temp in temperature_list:
    params = pybamm.ParameterValues("OKane2022")
    params.update(get_hithium_params(1, temp), check_already_exists=False)

# ❌ 错误: 在循环外创建，循环内只 update
params = pybamm.ParameterValues("OKane2022")
for temp in temperature_list:
    params.update(get_hithium_params(1, temp))  # 上次的残留参数会污染
```

## 修改后验证
```python
# 快速检查脚本
from paramsMIC import get_hithium_params
p = get_hithium_params(1, 298.15)
assert "Nominal cell capacity [A.h]" in p
print(f"容量: {p['Nominal cell capacity [A.h]']} Ah")
```

## 现有文件映射
| 文件 | 电芯 | 容量(Ah) | 电压(V) |
|------|------|---------|---------|
| `paramsMIC.py` | MIC | 1175 | 2.5~3.65 |
| `paramsMICCW500.py` | MIC CW500 | 1175 | 2.5~3.65 |
| `params280.py` | 280 | 280 | 2.5~3.65 |
| `params587.py` | 587 | 587 | 2.5~3.65 |

## 禁止事项
- 不得在参数函数内 import `matplotlib` — 参数函数应是纯计算
- 不得在参数字典中使用字符串格式的数值（PyBaMM 需要 float 或函数）
- 创建新参数文件时，名字必须是 `params<电芯名>.py`
