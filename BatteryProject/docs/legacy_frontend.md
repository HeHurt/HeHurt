# Legacy Streamlit Frontend

旧 Streamlit 前端仍可使用，但不再作为 README 首页推荐入口。当前推荐 UI 是 Battery Sim Studio。

## 文件位置

旧前端已归档到：

- `BatteryProject/legacy/frontend.py`
- `BatteryProject/legacy/run_frontend.py`
- `BatteryProject/legacy/run_frontend.bat`

## 启动方式

```bash
python -m streamlit run legacy/frontend.py
```

或：

```bash
python legacy/run_frontend.py --port 8501
```

Windows 也可以双击：

```text
legacy/run_frontend.bat
```

## 页面功能

- 实验数据：加载 CSV 文件夹并预览 retention / efficiency。
- 参数配置：保存循环性能或峰值电流扫描请求。
- 运行仿真：执行已保存的请求。
- 结果分析：查看指标、图表、CSV 导出与 Sim-Exp 对比。

## 维护边界

- 只做兼容性维护和必要 bug 修复。
- 新 UI 能力优先进入 Studio。
- `api/` 目录当前服务 Studio，不承诺兼容旧 Streamlit 的外部调用方式。
