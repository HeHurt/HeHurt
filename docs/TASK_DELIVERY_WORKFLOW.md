# BatteryProject 任务交付工作流

## 核心原则

- `BatteryProject/examples/` 保存 canonical Notebook，只复制、不针对单次任务直接修改。
- `BatteryProject/src/` 保存可复用仿真和分析逻辑。
- `BatteryProject/output/runs/` 保存原始运行、中间产物和日志。
- `work/<cell>/<YYYYMM_何争_任务名称Vn>/` 是可直接上传、版本冻结的任务交付包。
- 任务开始前先创建交付包，不在仿真结束后再手工拼目录。

## 1. 创建任务

```powershell
python tools/task_delivery.py new-task `
  --cell 587Ah `
  --name "全生命周期产热0p5P" `
  --month 202608 `
  --template "BatteryProject/examples/统一老化路径_多倍率全生命周期产热.ipynb"
```

默认负责人是何争，默认版本是 V1，未指定月份时使用当前月份。工具创建：

```text
work/587Ah/202608_何争_全生命周期产热0p5PV1/
├─ 00_任务说明.md
├─ 01_仿真报告/
├─ 02_模型/
├─ 03_输入数据/
├─ 04_输出结果/
├─ 05_复现说明/
└─ task_manifest.json
```

模板被复制到 `02_模型/`；此后只修改任务副本。新增版本使用 `--version 2`，禁止覆盖 V1。

## 2. 配置并运行

任务 Notebook 只保存电芯、工况、数据路径等配置，核心逻辑继续调用 `BatteryProject/src/`。原始运行统一写入：

```text
BatteryProject/output/runs/<workflow>/<run_id>/
```

建议 `run_id` 使用：

```text
YYYYMMDD_HHMMSS_<cell>_<task>_<condition>
```

每个 run 至少保留 `config.json`、`run.log`、`metrics.csv`；图表和导出数据使用子目录。

## 3. 发布任务结果

```powershell
python tools/task_delivery.py publish-task `
  --task "work/587Ah/202608_何争_全生命周期产热0p5PV1" `
  --run "BatteryProject/output/runs/lifecycle_heat/20260818_143000_587Ah_0p5P"
```

默认 `selected` 模式只复制常用表格、图、配置、日志和报告文件。需要完整原始快照时显式使用：

```powershell
python tools/task_delivery.py publish-task ... --mode full
```

发布是复制和固化，不移动原始 run。相同 `run_id` 已存在时拒绝覆盖。文件清单和 SHA-256 自动写入 `05_复现说明/run_manifest.json`。

## 4. 报告与上传

- `01_仿真报告/`：Word、PDF、PPT 和结论说明。
- `02_模型/`：实际运行的 Notebook、脚本、配置覆盖以及 `source_manifest.json`。
- `03_输入数据/`：本次任务需要携带的数据或数据 registry 清单。
- `04_输出结果/`：通过 `publish-task` 固化的结果。
- `05_复现说明/`：运行步骤、环境、run 清单和校验哈希。

交付前确认 `00_任务说明.md` 中目标、验收标准和结论已填写，然后整包上传。上传后的 V1 冻结；正式返修建立 V2，不覆盖旧版。

## 5. 跨电芯与通用能力

- 单电芯任务：`work/314Ah/`、`work/587Ah/`、`work/MIC_1175Ah/` 等。
- 跨电芯比较：`work/cross_cell/`。
- 可复用模板：回收到 `BatteryProject/examples/`。
- 稳定核心能力：回收到 `BatteryProject/src/`，并按项目协议测试。

## 6. 历史目录

旧的 `work/**/notebooks/output`、`outputs` 和 `results/output` 属于 legacy。迁移前先按任务识别归属；无法确认任务、版本或数据来源的目录只登记清单，不直接合并或删除。
