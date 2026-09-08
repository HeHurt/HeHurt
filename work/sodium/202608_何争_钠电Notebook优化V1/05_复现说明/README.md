# 复现说明

1. 核对 `03_输入数据/config.yaml`；默认使用任务包内的实验数据快照。
2. 打开 `02_模型/钠电_多温度倍率对标_优化版.ipynb`。
3. Restart Kernel 后执行 Run All；Notebook 会先跑 25 ℃、0.1C 烟雾，再跑完整 54-case 矩阵。
4. 原始运行产物写入 `BatteryProject/output/runs/sodium_rate_benchmark/<run_id>/`。
5. 使用下列命令把确认后的 run 发布到任务包：

```powershell
python tools/task_delivery.py publish-task `
  --task work/sodium/202608_何争_钠电Notebook优化V1 `
  --run BatteryProject/output/runs/sodium_rate_benchmark/<run_id> `
  --mode full
```

本次最终验证与发布的 run 为 `20260813_155603_notebook`。原始 Notebook 的字节级备份保存在
`02_模型/钠电_原始备份.ipynb`，不得用优化版覆盖它。
