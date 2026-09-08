# Hithium 电池仿真项目

基于 PyBaMM 的电芯电化学仿真平台，用于 Hithium 电芯的性能预测、老化建模与实验对标。
面向 AI Agent 的 harness 规范见 [AGENTS.md](./AGENTS.md)；本 README 面向人类 onboarding。

## 环境（本机已配置，换机按此重建）

### 解释器

项目真实运行环境是**系统 Python 3.11**，不是 shell 里的默认 `python`：

```
C:/Users/hez/AppData/Local/Programs/Python/Python311/python.exe
```

- 关键依赖版本：pytest 9.0.3 / flake8 7.3.0 / pybamm 26.4.2 / fastapi 0.115.14
- shell 默认 `python` 是 WorkBuddy 自带 3.13，**没有 pytest/flake8/pybamm**，不能用于本项目
- `.venv`（fastapi/numpy，无 pybamm）与 `.venv-liionpack`（pybamm 24.9.0 + liionpack + casadi，无 pytest）都是历史遗留，均不能完整跑测试，保留作参考
- `pyproject.toml` 只声明了 agent 工具链（`sim-cli-core` 等），**未声明** pybamm/numpy/pandas/fastapi 等实际依赖，重建环境时需手动安装

### 运行验证

```bash
PY=「上面的 Python311 绝对路径」
$PY -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503
$PY -m pytest BatteryProject/tests/ -q
$PY BatteryProject/src/data_registry.py summary
```

## DLP 加密注意（本机 Trend Micro）

- 绝大多数工程文件在磁盘上是**明文**，白名单 Python 可正常读写；只有极少数文件
  （如 `BatteryProject/examples/参数敏感性与实测对标.ipynb`）是真正静态加密的。
- 读写文件一律用 Python（`open().read()/write()`），不要用 PowerShell / 文本编辑器桥。
- **禁止执行 `git gc` / `git prune` / `git repack`** —— 会摧毁对象库（2026-09-08 事故）。
- GitHub 远端是 private（`HeHurt/HeHurt`）。公司网络下 `git fetch/push` 需走代理并换
  OpenSSL 后端：

```bash
git -c http.sslBackend=openssl \
    -c http.proxy=http://127.0.0.1:7897 \
    -c https.proxy=http://127.0.0.1:7897 \
    fetch origin
```

## 目录结构

| 目录 | 内容 |
|------|------|
| `BatteryProject/src/` | 核心仿真代码（simulation facade、plotting、analysis、data_registry 等） |
| `BatteryProject/api/` | Studio 后端（FastAPI + SQLite），`JOB_TYPES` 10 类 |
| `params/` | 电芯参数文件，`load_cell_params("MIC"/"314"/"587"/...)` 统一入口 |
| `data_raw/` `data_processed/` | 实验数据；索引见根目录 `datasets.json` |
| `work/` | 任务交付区，`YYYYMM_何争_任务名称Vn/` 为完整交付单元 |
| `COMSOL/` | COMSOL/MATLAB 闭环工作目录 |
| `docs/` | 工作流文档与评估报告 |
| `archive/` | 归档的 legacy 脚本 |

## 数据查询

```bash
$PY BatteryProject/src/data_registry.py ls --cell MIC --temp 25 --test 倍率充电
$PY BatteryProject/src/data_registry.py scan      # 新数据入库后登记
```

> registry 机器推断字段（temperature_C/rate/test_type）识别率约 50–65%，查询可能
> 静默漏数据，关键查询请交叉核对 `data_raw/` 目录。

## 任务交付

新任务用 `python tools/task_delivery.py new-task` 创建标准任务包，
验证后 `publish-task` 固化到 `04_输出结果/`。详见 `docs/TASK_DELIVERY_WORKFLOW.md`。
