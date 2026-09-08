# 复现说明

1. 核对 `03_输入数据/config.yaml`。
2. 在 `02_模型/` 中打开任务 Notebook，运行唯一代码单元；或执行：

   ```powershell
   python .\run_peak_power_charge_20C_98SOC_MIC_uses_587_v4.py
   ```

3. 脚本采用 `mode="W"` 并显式开启 `contact resistance`。
4. MIC 的六项动力学参数仅在内存中从 `params587` 复制。
5. 两个电芯分别使用全新的 `pybamm.ParameterValues("OKane2022")`。
6. 本次确认并发布的 run：
   `20260728_171744_MIC_override_587_contact_on_20C_98SOC_10s_charge_peak_power`。

## 独立复跑校验

- 587Ah：2.16688 kW，在 9.9995 s 达到 3.650000 V。
- MIC：4.01434 kW，运行至 10.0 s，末端 3.648895 V。
- 两组首末端 `|V × I|` 均与恒功率设定一致。
