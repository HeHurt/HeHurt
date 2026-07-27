# examples workflow canonical 验收记录

日期：2026-07-23

## Canonical 模板

| 分析类型 | Canonical Notebook | Headless 入口 | 说明 |
|---|---|---|---|
| 循环老化 | `BatteryProject/examples/workflows/循环老化.ipynb` | `src.workflows.cycle.run_cycle_workflow` | 保留容量/SOH、Sim vs Exp、膨胀、深度分析、产热分析 |
| 全生命周期产热 | `BatteryProject/examples/workflows/全生命周期产热.ipynb` | `src.workflows.lifecycle_heat.run_lifecycle_heat_workflow` | 保留多电芯/多倍率、SOH 诊断、接触电阻、熵热校准、外推 |
| 阻抗分析 | `BatteryProject/examples/workflows/阻抗分析.ipynb` | `src.workflows.eis.run_eis_workflow` | EIS 独立，不与脉冲或调频合并 |
| 插入脉冲 | `BatteryProject/examples/workflows/插入脉冲.ipynb` | `src.workflows.pulse.run_pulse_workflow` | 脉冲独立，不与调频合并 |
| 调频 | `BatteryProject/examples/workflows/调频.ipynb` | `src.workflows.frequency.run_frequency_workflow` | 调频独立，不与脉冲合并 |
| 粒径分布 | `BatteryProject/examples/workflows/粒径分布.ipynb` | `src.workflows.psd.run_psd_workflow` | PSD 拟合/材料对比/COMSOL 转换独立，不与耦合老化合并 |
| 区域并联耦合老化 | `BatteryProject/examples/workflows/区域并联耦合老化.ipynb` | `src.workflows.regional_coupled_aging.run_regional_coupled_aging_workflow` | 区域并联/耦合老化独立 |

## 作图规范

新增和重构出的 canonical notebook / reporting 入口统一使用：

```python
plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"
```

## 归档

被 `examples/workflows/` 取代的旧根目录模板已归档到：

`D:\Users\hez\Desktop\hithium-外移\cold-archive\examples-canonical-20260723\workflow-family\`

归档目录包含 `manifest.json`，记录原路径、归档路径、大小和 SHA256。

## 验证

- `python -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503` 通过
- `python -m pytest BatteryProject/tests/ -q` 通过，含 1 个既有 skipped
- 定向 workflow 测试通过：循环老化、全生命周期产热、阻抗分析、插入脉冲、调频、粒径分布、区域并联耦合老化
