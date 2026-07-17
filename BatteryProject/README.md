# BatteryProject

Hithium 电池电化学仿真项目，基于 PyBaMM 做电芯性能预测、老化建模、实验对标和本地 Studio 工作流。

新 notebook 推荐使用统一第一格：

```python
from src.notebook import setup_notebook, load_params
from src.notebook_api import run_peak_current, get_discharge_capacity

ctx = setup_notebook(cell="MIC", style="science")
get_hithium_params = load_params("MIC")
```

`src.easy_imports` 保留为 legacy convenience。新 notebook 优先使用 `src.notebook`、`src.notebook_api`，需要长尾函数时再从 `src.simulation`、`src.analysis`、`src.plotting` 等子模块精确导入。

## 安装

推荐用 uv：

```bash
uv sync
```

或使用当前 Python 环境：

```bash
pip install -e ".[dev]"
```

## 我要做峰值电流 map

Notebook 模板：

- [examples/峰值电流.ipynb](examples/峰值电流.ipynb)

核心入口：

```python
from src.notebook import setup_notebook, load_params
from src.notebook_api import run_peak_current

ctx = setup_notebook(cell="MIC")
get_hithium_params = load_params("MIC")
```

常用函数：

- `run_peak_current(...)`
- 参数 registry: `load_params("MIC")`、`load_params("280")`、`load_params("314")`、`load_params("587")`

## 我要做循环老化

Notebook 模板：

- [examples/循环老化.ipynb](examples/循环老化.ipynb)
- [examples/MIC_1175Ah_0p25P_循环老化对标.ipynb](examples/MIC_1175Ah_0p25P_循环老化对标.ipynb)

核心入口：

```python
from src.notebook import setup_notebook, load_params
from src.notebook_api import run_dcr_and_power_test, get_discharge_capacity

ctx = setup_notebook(cell="MIC")
get_hithium_params = load_params("MIC")
```

常用函数：

- `run_dcr_and_power_test(...)`
- `perform_dcr_test(...)`
- `get_discharge_capacity(...)`

## 我要做实验对标

Notebook 模板：

- [examples/compare_demo.ipynb](examples/compare_demo.ipynb)
- [examples/analysis_demo.ipynb](examples/analysis_demo.ipynb)
- [examples/exp_loader_demo.ipynb](examples/exp_loader_demo.ipynb)

核心入口：

```python
from src.notebook import setup_notebook
from src.notebook_api import compare_all, calc_rrmse, BatteryPlotter

ctx = setup_notebook(cell="MIC")
```

常用函数：

- `compare_all(...)`
- `calc_rrmse(...)`
- `BatteryPlotter`
- `load_cycling_csv(...)` 和 `load_cycling_folder(...)` 从 `src.exp_loader` 精确导入

## 我要做调频或插入脉冲

Notebook 模板：

- [examples/调频.ipynb](examples/调频.ipynb)
- [examples/插入脉冲.ipynb](examples/插入脉冲.ipynb)

核心入口：

```python
from src.notebook import setup_notebook, load_params
from src.notebook_api import (
    prepare_pulse_lifecycle_scenarios,
    run_pulse_lifecycle_scenarios,
    summarize_pulse_lifecycle_results,
)

ctx = setup_notebook(cell="MIC")
get_hithium_params = load_params("MIC")
```

调频相关函数从 `src.simulation` 精确导入：

- `prepare_frequency_scenarios(...)`
- `run_frequency_scenarios(...)`
- `summarize_frequency_results(...)`

插入脉冲相关函数：

- `prepare_pulse_lifecycle_scenarios(...)`
- `run_pulse_lifecycle_scenarios(...)`
- `summarize_pulse_lifecycle_results(...)`

## 我要跑 Studio

Studio 是当前推荐的本地 UI。它使用静态 HTML/CSS/JS + FastAPI 后端，项目、数据集与任务索引写入 `output/studio.sqlite3`，大文件保存在 `output/` 对应目录。

启动：

```bash
uv run python run_studio.py --port 8601
```

或：

```bash
python run_studio.py --port 8601
```

访问：

- Studio UI: <http://127.0.0.1:8601/>
- FastAPI docs: <http://127.0.0.1:8601/docs>

说明：

- `api/` 当前是 Studio backend，不承诺作为稳定公共 API。
- 旧 Streamlit 前端已归档到 `legacy/`，说明见 [docs/legacy_frontend.md](docs/legacy_frontend.md)。

## 文档地图

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): 按任务组织的新用户指南。
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md): 精简 API 入口和函数清单。
- [docs/MIGRATION.md](docs/MIGRATION.md): Fun_HZ / Fun_NC 历史迁移说明。
- [docs/API.md](docs/API.md): 旧完整 API 目录，内容较全，适合查细节。

## 目录提示

- `src/notebook.py`: notebook 初始化、参数加载入口。
- `src/notebook_api.py`: 推荐给新 notebook 的收窄 API。
- `src/simulation.py`: 仿真 facade，长尾函数按任务精确导入。
- `src/analysis.py`: 容量、热、膨胀、误差指标。
- `src/plotting.py`: 绘图与 `BatteryPlotter`。
- `src/compare.py`: Sim-Exp 一站式对标。
- `params/`: 参数文件和 `load_cell_params` registry。
- `api/`: Studio backend。
- `legacy/`: 旧 Streamlit 前端。

## 测试

进入仓库根目录或 `BatteryProject/` 目录运行：

```bash
python -m pytest BatteryProject/tests/ -q
```

若需要覆盖率报告：

```bash
python -m pytest BatteryProject/tests/ --cov=src --cov-report=term-missing -q
```
