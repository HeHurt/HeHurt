# 复现说明

1. 核对 `03_输入数据/config.yaml` 中的实测 SOC-OCV 点。
2. 在项目根目录运行：
   `python work/MIC_LDS/202608_何争_MIC_CW363_SOC_OCV标定V1/02_模型/cw363_soc_ocv_calibration.py`
3. 原始结果写入 `BatteryProject/output/runs/cw363_soc_ocv/<run_id>/`。
4. 验证后用 `tools/task_delivery.py publish-task` 固化到 `04_输出结果/`。
