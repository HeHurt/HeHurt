# 2026-08-05 Studio 多任务接入(P0-A) Spec

## 目标
把 Studio 后端从「只有 cycle 一种任务」扩展到多 job_type:首批接入 **peak_current / eis / rate_benchmark**,
统一走 headless 运行时(`src/workflows/*.py` + `src/workflow_runtime.py`),同时保持现有 cycle 任务与前端查询接口完全向后兼容。
一句话:让 Studio 的"运行仿真"真正消费已建成的 8 个 workflow 运行时。

## 现状(已核实,2026-08-05)
- `api/jobs.py` `JOB_TYPES` 仅注册 `cycle`(normalize=normalize_request, worker=run_cycle_worker),worker 直接 `mp.Process` spawn,通过 `job_dir/status.json` 回写状态。
- `src/workflows/` 已有 8 个 workflow,`run_*_workflow(spec, *, project_root, workspace_root, run_id)` 统一签名,内部 `create_run_context` 写 `output/runs/<workflow_id>/<run_id>/`(config.json/summary.json/metrics/plots)。
- 与 `run_*_workflow` 完美契合:eis / cycle(workflow_id="cycle_aging")。峰值电流只有底层 `src/simulation_peak.run_peak_current(model, param, var_pts, ...)`,需补 workflow facade。
- 倍率对标 = 多倍率短循环仿真 vs 实验(指标 RRMSE),可复用 cycle workflow 的多 condition 能力,无需新模型代码。

## 适配层契约
```
POST /api/jobs {job_type, ...} 
  -> JOB_TYPES[job_type].normalize(request)      # 扁平参数字典(含 cycles 作为进度单位)
  -> JobManager.create_job: spawn worker(job_dir, normalized)
  -> worker(模块级函数,可 pickle):
       ensure_runtime_env + ensure_project_import_paths
       log_status(progress=10..32)                # 沿用现有回写
       spec = build_spec(normalized)              # 每类型一个构造器
       summary = run_*_workflow(spec, project_root=PROJECT_ROOT, run_id=job_id)
       result.json = {job_type, summary, run_dir, finished_at}
       log_status(status="completed", progress=100)
```
- **run 目录**:`output/runs/<workflow_id>/<job_id>/`,与 job_id 一一对应;run 的 manifest(spec 快照、PyBaMM 版本、血缘)由 workflow 层在 summary 补齐(P0-B 强化)。
- **向后兼容**:`cycle` 条目保持原 normalize/worker 不动;前端 `/api/jobs/{id}/results` 读 `job_dir/result.json` 的路径不变。
- **normalize 约定**:每个新类型返回扁平 dict,必须含 `cycles`(该类型进度单位:peak=扫描 SOC 点数,eis=频率点数,rate_benchmark=倍率组数)与 `cycles_requested`,供 status.json 显示。

## 首批三种的字段映射

### 1) peak_current(新建 `src/workflows/peak_current.py`)
| 输入 | 默认 | 说明 |
|---|---|---|
| cell | "314Ah" | 参数集(params registry) |
| temperature_c | 25.0 | 温度 |
| nominal_ah | 由参数文件推导 | 名义容量 |
| pulse_duration_s | 10 | 脉冲时长 |
| mode | "A" | A=恒流 / W=恒功率 |
| soc_list | [0.95, 0.85, 0.5, 0.2] | 扫描 SOC 点(progress 单位) |
| run_mode | "smoke" | smoke 收窄 SOC 点为 2 |

Facade:`PeakCurrentWorkflowSpec`(dataclass)+ `run_peak_workflow(spec, *, project_root, run_id)`,
内部 load_params → pybamm model(DFN, var_pts 标准配置)→ `run_peak_current` → 写 run 目录 + summary.json(按 SOC 的 peak current/C-rate/功率)。

### 2) eis(复用 `src/workflows/eis.py`)
| 输入 | 默认 | 说明 |
|---|---|---|
| cell | "314Ah" | |
| temperature_c | 25.0 | |
| soc | 0.5 | 测试 SOC |
| frequencies | [0.1, 1, 10, 100, 1000] Hz | 频率点(progress 单位) |
| run_lifecycle | false | 是否做生命周期 EIS 扫描 |

直接 `run_eis_workflow`(workflow_id="eis")。

### 3) rate_benchmark(复用 cycle workflow,多倍率 profile)
| 输入 | 默认 | 说明 |
|---|---|---|
| cell | "314Ah" | |
| rates | [0.33, 0.5, 1.0] | 倍率组(progress 单位) |
| cycles_per_rate | 1 | 每倍率圈数(smoke 用 1) |
| temperature_c | 25.0 | |
| compare_dataset | 可选 | registry 数据集,附加 RRMSE |

构造 `CycleWorkflowSpec(conditions=[{rate_p:r, temperature_c}...])` → `run_cycle_workflow`(workflow_id="cycle_aging",run 目录沿用,manifest 标注 profile=rate_benchmark)。

## 预期输出
- `api/jobs.py`:JOB_TYPES 扩展到 4 种;新增 3 个 normalize + 3 个 worker + 通用 helper。
- `src/workflows/peak_current.py`(新建):facade 供 headless 与 Studio 共用。
- 验证:每种类型 smoke run 通过,status.json 各阶段正确,result.json 可被 `/api/jobs/{id}/results` 读取。

## 约束
- 不修改 `run_cycle_worker` 与现有 cycle 行为。
- worker 保持模块级函数(spawn 可 pickle)。
- var_pts 标准配置 `{"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}`。
- smoke 用最小配置(单温度、少 SOC/频率点、1 圈)控制运行时间。
- 前端结果渲染按 job_type 分派属 P2,本轮只保证接口数据正确、前端不崩。

## 验收用例(smoke)
1. POST /api/jobs {job_type:"peak_current", cell:"314Ah", temperature_c:25, soc_list:[0.9,0.5], run_mode:"smoke"} → queued → running → completed;result.json 含 ≥2 个 SOC 的 peak current;`output/runs/peak_current/<job_id>/` 存在。
2. POST /api/jobs {job_type:"eis", cell:"314Ah", frequencies:[0.1,1,10], run_mode:"smoke"} → completed;`output/runs/eis/<job_id>/` 存在。
3. POST /api/jobs {job_type:"rate_benchmark", rates:[0.5,1.0], cycles_per_rate:1, run_mode:"smoke"} → completed;`output/runs/cycle_aging/<job_id>/` 存在。
4. 回归:POST {job_type:"cycle", cycles:1, run_mode:"smoke"} 行为与改造前一致。


---
## 实施记录(2026-08-05 已实现)

### 代码变更
- 新建 `BatteryProject/src/workflows/peak_current.py`:`PeakCurrentWorkflowSpec` + `run_peak_workflow`
  (对齐 output/runs/peak_current 历史 config 惯例,summary 含 pybamm_version)。
- 修改 `BatteryProject/api/jobs.py`(1239 行):
  - JOB_TYPES 扩展为 4 种:`cycle`(原样保留,向后兼容)+ `peak_current` / `eis` / `rate_benchmark`。
  - 新增 3 个 normalize(_normalize_run_mode 统一 smoke/production 收敛)+ 3 个 build_spec + 3 个 worker
    + 通用 `_run_workflow_job`(建 spec -> run_*_workflow(run_id=job_id) -> result.json
    {job_type, run_dir, metrics_path, summary, elapsed, finished_at} -> status completed)。
  - cell 别名映射 `_registry_cell`:hithium314->314 / hithium587->587 / hithium280->280 / mic1175->MIC1175
    (Studio PARAMETER_SETS 键 -> params registry `_CELL_PARAM_MODULES` 键)。
  - summary 为空时从 run_out.metrics 提取 {rows} 摘要。

### smoke 验收(8700 实例,2026-08-05)
| job_type | smoke 配置 | 结果 | 耗时 |
|---|---|---|---|
| peak_current | hithium314, 25C, soc[0.9,0.5], 10s, mode A | completed, results 4 行(charge+discharge x 2SOC), run_dir=output/runs/peak_current/<job_id> | 34.7s |
| eis | hithium314, 25C, freq[0.1,1,10] | completed, summary.rows=3, artifacts(quick_impedance.csv) | 1.6s |
| rate_benchmark | hithium314, rates[0.5,1.0] x 1圈 | completed, run_dir=output/runs/cycle_aging/<job_id>, metrics.csv | 10.3s |
| cycle(回归) | hithium314, 1圈, aging | completed, result.json 保持旧格式(series/cycle_curves/degradation_metrics 完整) | 15.4s |

### 遗留(P0-B / P2)
- run manifest 血缘字段(workflow_id 已有,pybamm 版本仅 peak 有;统一补进 P0-B)。
- 前端任务中心 UI / 按 job_type 渲染结果(依赖结果 schema 统一)。
- worker 持久化队列与恢复(P0-C)。


---

## P2 任务中心(2026-08-05 已实现,含于本 spec)

### 目标
前端任务中心:多类型任务「配置 → 提交 → 监控 → 结果」,schema 驱动动态表单,按 job_type 渲染结果。

### 代码变更
- `api/jobs.py`:`JOB_TYPES` 每类补 `schema`(字段 name/label/type/default/unit/desc/options/min/max/step);
  新增 `PLANNED_JOB_TYPES`(6 种未接入 workflow 的清单)。
- `run_studio.py`:新增 `GET /api/job-types`,返回 available + planned 全量注册表。
- `studio/index.html`:侧边导航 + module-tabs 新增「任务中心」入口;新增 `data-view="tasks"` 视图
  (左:任务类型列表;右:动态表单 + 监控 + 结果摘要)。
- `studio/app.js`:任务中心逻辑(loadTaskCenter / renderTaskTypeList / selectTaskType / renderTaskField /
  collectTaskRequest / runTask / pollTaskStatus / stopTask / applyTaskStatus / renderTaskResult);
  ROUTE_VIEWS 加 tasks;setRoute 进入 tasks 时加载。
- `studio/styles.css`:tasks-layout 双栏、task-type-item 卡片、field-desc 等样式(≤900px 单栏)。

### 验证(8700 实例)
- `GET /api/job-types`:10 种(4 available + 6 planned),schema 字段 cycle=11 / peak=7 / eis=6 / rate=6。
- 页面含 tasks 视图/导航/tab;JS 语法检查通过。
- 提交闭环沿用已验收的 smoke 用例(P0-A 三种 + cycle 回归)。


---

## 全量接入:JOB_TYPES 10 种(2026-08-05 已实现)

### 变更
- `api/jobs.py`:`JOB_TYPES` 扩到 **10 种**(新增 calendar_aging / frequency / pulse / lifecycle_heat / psd / regional_coupled_aging),
  `PLANNED_JOB_TYPES` 清空;每类配 normalize + build_spec + worker + schema。
- 复用 `_run_workflow_job` 通用 worker(建 spec -> run_*_workflow(run_id=job_id) -> result.json)。
- 新增 `_json_array_from_text`:前端 text 输入 JSON 数组(场景/材料/倍率)的解析。

### smoke 验收(8700 实例)
| job_type | 结果 | 耗时 | 备注 |
|---|---|---|---|
| calendar_aging | completed | 4.2s | MIC, activated 1月 |
| frequency | completed | 3.7s | 314, 1 天, 默认场景 |
| pulse | completed | 29.8s | 314, 2 圈(首轮秒挂:场景缺 charge_interval_minutes,已补默认) |
| regional_coupled_aging | completed | 1.4s | 314 默认配置 |
| lifecycle_heat | failed(预期) | - | registry 无熵校准数据,报错清晰:entropy query 0 match |
| psd | failed(预期) | - | 需 materials 配置,报错清晰 |

### 数据依赖说明
- **lifecycle_heat**:需要 registry 中的熵校准文件(DatasetQuery cell+test_type=熵);有数据后直接可用。
- **psd**:需要材料配置(materials JSON,如 [{name, d50_um, ...}]);有材料后直接可用。

### 待办
- P0-B run manifest 血缘字段统一。
- P0-C 独立 worker + 持久化队列。


---

## P0-B run manifest + P0-C 独立 worker(2026-08-05 已实现)

### P0-B:统一 run manifest 血缘
- `api/jobs.py` `_run_workflow_job`:完成后写 `run_dir/manifest.json` + result.json 含 `manifest`
  (workflow_id/job_type/job_id/run_mode/cell/**pybamm_version**/parameter_source/created_at/finished_at/elapsed_s/request 快照/run_dir)。
- cycle 保持旧 result 格式(向后兼容,不写 manifest)。

### P0-C:独立 worker + 持久化队列 + 恢复
- **新文件 `api/worker.py`**:常驻 worker,轮询 sqlite jobs 表(status='queued' 先到先得,CAS 防多 worker 抢占);
  每任务一个 spawn 子进程(委托 JOB_TYPES[job_type]['worker']),worker 监控子进程并检查 `cancel_requested`(1s 粒度);
  启动时 `_recover_stale`(running 且无进程 -> 重新排队 attempts+1,超 3 次标 failed;相对路径 job_dir 自动补全)。
- **`api/jobs.py` `JobManager` 入队化**:create_job 只写 status.json(queued)+ sqlite 入队,不再 spawn;
  stop_job 标记 canceled + cancel_requested=True(worker 终止子进程);get_status 直接读文件。
- **`run_studio.py`**:main() 默认以独立子进程拉起 api/worker.py;`--no-worker` 可关闭。
- Web/worker 分离:Web 只提交与查询;worker 崩溃后重启自动恢复未完成任务(带重试上限)。

### 验收(8700 实例)
1. POST /api/jobs -> queued -> worker 消费 -> completed(worker 日志确认);manifest.json 含 pybamm_version=26.4.2。
2. stop:提交 peak_current 4s 后停止 -> canceled(worker 日志"任务已被用户停止")。
3. 恢复:构造 stale running(attempts=0)-> _recover_stale -> queued attempts=1 -> worker 重新执行 -> completed。
4. 加固:worker 对相对 job_dir 自动补全(兼容历史记录)。

### 备注
- 多 worker 并存时第二个启动的 recover 会重排第一个正在跑的任务(单 worker 部署无此问题;多 worker 需 leader 选举,留待后续)。
- 8700 验证实例的 worker 为旧代码;正式 8601 重启后拉起新 worker。


---

## Sim–Exp 对标工作台(2026-08-05 已实现)

### 目标
仿真 vs 实测一站式对标:自动对齐、RRMSE/RMSE、异常区间定位、参数版本对比。

### 代码变更
- `api/compare.py`:`_anomaly_windows`(滑动窗口 RRMSE,超阈值区间合并,severity 中/高)、
  `bench_sim_exp`(复用 compare_job_to_dataset 对齐 + 异常区间 + manifest)、`bench_runs_manifest`(两 run manifest/request 字段 diff)。
- `run_studio.py`:`GET /api/bench/jobs`(已完成任务)、`GET /api/bench/sim-exp?job_id&dataset_id&threshold`、
  `GET /api/bench/runs?job_a&job_b`。
- 前端:侧边导航「对标工作台」(bench 视图)——仿真任务/数据集/阈值选择,RRMSE 指标卡 + echarts 叠图
  (异常区间红色阴影 markArea)+ 异常区间表 + manifest 表 + 双 Run 版本差异表。

### 验收(8700 实例)
- sim-exp:cycle(3 圈,加速 50 → 等效 50-150 圈)vs qa_synthetic(500 行):对齐 101 点,RRMSE 2.65%,RMSE 2.58;阈值 2% 触发异常区间 [75,149] 圈(3.72%,中)。
- runs:两个 eis 任务对比出 4 项差异(created_at/cycles/cycles_requested/frequencies_hz)。
- 说明:cycle 任务为旧格式(无 manifest),对标时 manifest 区显示提示;新 9 种任务带完整 manifest。

### 边界
- 实验数据目前用「项目已导入数据集」(datasets 表);registry 数据接入 v2。
- 异常区间只对保留率曲线计算(能效仅展示指标)。


---

## Run 对比与参数标定可辨识性(2026-08-05 已实现)

### Run 对比与复现
- `api/compare.py` `bench_runs_curve`:两个 Run 提取可比曲线(cycle_metrics 的保持率/能效/容量;peak summary 的 SOC-电流),
  同名曲线对齐(重叠区插值)+ 曲线间 RRMSE/RMSE(NaN 已过滤)+ 元信息(manifest 摘要)。
- `run_studio.py`:`GET /api/bench/runs-curve?job_a&job_b`。
- 前端:对标工作台「Run 对比与复现」区——对比曲线按钮(叠图 + RRMSE 卡 + Run 元信息)+ 版本差异按钮。

### 参数标定与可辨识性
- **新文件 `api/calibration.py`**:`normalize_calibration_request` + `run_calibration_worker`。
  - 复用 `build_aging_objective`(目标=fitness=1/loss, loss_type=cycle_line, t_factor 等效圈)。
  - `_build_simulate_fn`:任意参数修改 -> 短循环 DFN+老化仿真(cycles 圈)。
  - 优化:MO(SLSQP,记录每次评估 loss 历史,默认)/ DA(dual_annealing);BO/GO 扩展点(需 bayes-opt/pygad)。
  - 可辨识性:最优参数 ±1% 扰动敏感度(优化空间扰动,行值显示物理值)。
  - 落盘 `output/runs/calibration/<job_id>/`(manifest + result)。
- `api/jobs.py`:`JOB_TYPES["calibration"]`(label=参数标定,schema 8 字段),走统一 worker 队列。
- 前端:任务中心 renderTaskResult 增加 calibration 分支——损失收敛曲线(echarts)+ 标定结果表(参数/最优值/边界/敏感度/可辨识性评级)+ 敏感度条形图。

### 验收(8700 实例)
- runs-curve:两个 cycle(0.5C vs 1C)对比 3 对曲线:保持率 RRMSE 0.0%、能效 3.25%、容量 5.04%(NaN 修复后)。
- calibration:MO 8 迭代 23.5s 完成,success=True,best_params 物理值 1e-14,loss_history 2 点(SLSQP 快速收敛),
  sensitivity=0(1 圈 C/2 无老化条件下扩散系数不可辨识——可辨识性分析如实指示「弱(平坦方向)」,符合物理)。
- 说明:标定可辨识性依赖实验设计(圈数/倍率/老化);1 圈无老化对扩散不可辨识是预期物理结果。

### 边界
- loss_history 仅 MO(SLSQP)有;BO/GO 需额外依赖且无历史。
- 标定实验数据目前用「已导入数据集」(normalized.csv 的 cycle/capacity_ah)。
