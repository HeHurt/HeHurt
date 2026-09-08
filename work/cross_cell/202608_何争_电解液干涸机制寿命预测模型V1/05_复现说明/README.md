# 复现说明

在仓库根目录执行：

1. 生成 4 张报告图片：

   `python work/cross_cell/202608_何争_电解液干涸机制寿命预测模型V1/02_模型/generate_dryout_figures.py`

2. 使用 Codex bundled document Python 运行：

   `build_f413_2026_doc.py`

3. 用 Microsoft Word 打开生成的 DOCX，更新目录和全部域后保存。

4. 最终文件位置：

   `01_仿真报告/HC_TS_ISC_F413_2026《基于PyBaMM添加电解液干涸机制的寿命预测模型》.docx`

说明：图片脚本中的降阶示例调用当前 `DryoutTracker.update`，输入为受控 block 末态；它不替代目标电芯的
完整 DFN 寿命仿真。正式实算时，原始 run 仍应写入
`BatteryProject/output/runs/<workflow>/<run_id>/`，验证后再用 `publish-task` 固化到任务包。
