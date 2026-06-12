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

## 基座 builder（LFP 全系）

所有 LFP 参数文件的 `get_hithium_params` 内部统一调用
`common.build_lfp_cell_params(temperature, overrides)`：

- **基座**携带全库同值的 16 个脚手架条目（电压窗 2.5~3.65、Bruggeman 1.5×4、
  双电层 0、电解液传输函数、`Ambient temperature [K]` 跟随入参、
  plating 转移系数、SEI 初始厚度等）。
- **overrides** 携带每芯差异项（几何/浓度/孔隙率/动力学函数/老化常数）。
  overrides 里写同名键即可覆盖基座值。
- 改"全系共有"的值 → 改 `common.py` 基座；改"单芯"的值 → 改该芯 overrides。
- `paramsNa.py`（钠电，电压窗 2.0~3.65）化学差异大，**不走基座**，保持手写。

## 现有文件映射
| 文件 | 电芯 | 容量(Ah) | 电压(V) | 走基座 |
|------|------|---------|---------|--------|
| `params.py` | 314（基准） | 314 | 2.5~3.65 | ✓ |
| `params280.py` | 280 | 280 | 2.5~3.65 | ✓ |
| `params314_5plus3.py` | 314 5+3 | 314 | 2.5~3.65 | ✓ |
| `params50方壳.py` | 50 方壳 | 50 | 2.5~3.65 | ✓ |
| `params587.py` | 587 | 587 | 2.5~3.65 | ✓ |
| `params64150.py` | 64150 | 50 | 2.5~3.65 | ✓ |
| `paramsCW362_pouch.py` | CW362 软包 | 2.75 | 2.5~3.65 | ✓ |
| `paramsCW391_pouch.py` | CW391 软包 | 3.03 | 2.5~3.65 | ✓ |
| `paramsCW428_pouch.py` | CW428 软包 | 3.25 | 2.5~3.65 | ✓ |
| `paramsCW495_pouch.py` | CW495 软包 | 3.75 | 2.5~3.65 | ✓ |
| `paramsCW511_pouch.py` | CW511 软包 | 3.96 | 2.5~3.65 | ✓ |
| `paramsMIC.py` | MIC | 1175 | 2.5~3.65 | ✓ |
| `paramsMICCW500.py` | MIC CW500 | 1300 | 2.5~3.65 | ✓ |
| `paramsNa.py` | 钠电 | 162 | 2.0~3.65 | ✗ |

## 禁止事项
- 不得在参数函数内 import `matplotlib` — 参数函数应是纯计算
- 不得在参数字典中使用字符串格式的数值（PyBaMM 需要 float 或函数）
- 创建新参数文件时，名字必须是 `params<电芯名>.py`
- 字典字面量内不得出现重复键——Python 不报错、静默以最后一个为准，
  历史上曾因此让函数版 plating 交换电流密度被数值版静默覆盖（2026-06 已清理）
