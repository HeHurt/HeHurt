const fs = require("fs");
const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));

notebook.cells[0].source = [
  "# CW501 10s / 30s / 60s 峰值电流 Mapping\n",
  "\n",
  "本 Notebook 使用启用接触阻抗的 DFN，按电压截止条件搜索最大恒流脉冲：\n",
  "\n",
  "- 充电温度：0–55℃，5℃间隔。\n",
  "- 放电温度：−30、−20、−10℃；0–55℃为5℃间隔。\n",
  "- 脉冲时间：10 s、30 s、60 s。\n",
  "- 充电 SOC：0–95%，5%间隔。\n",
  "- 放电 SOC：5–100%，5%间隔。\n",
  "- 电压限制：充电 3.65 V、放电 2.5 V。\n",
  "- 结果输出周期：2 s；IDAKLU 内部仍采用自适应积分步长并连续定位截止事件。\n",
  "- 同一计算组复用已参数化的 DFN，避免每次试探电流都重新构建模型。\n",
  "\n",
  "全量计算按“方向×温度×脉宽”逐组保存，可中断并一键续算。\n",
];

notebook.cells[3].source = notebook.cells[3].source
  .join("")
  .replace(
    '            "Upper cut-off [V]",\n            "Expected groups",',
    '            "Upper cut-off [V]",\n            "Output period [s]",\n            "Current-ratio tolerance",\n            "Expected groups",'
  )
  .replace(
    '            params_25c["Upper voltage cut-off [V]"],\n            3 * (12 + 15),',
    '            params_25c["Upper voltage cut-off [V]"],\n            peak_module.DEFAULT_OUTPUT_PERIOD_S,\n            peak_module.DEFAULT_RATIO_XTOL,\n            3 * (12 + 15),'
  )
  .split(/(?<=\n)/);

notebook.cells[4].source = [
  "## 2. 已验证的最小案例\n",
  "\n",
  "25℃、10 s、50% SOC 的充电和放电结果用于确认模型、接触阻抗、2 s 输出及截止事件正常。\n",
];

notebook.cells[6].source = [
  "## 3. 一键运行或续算完整 Mapping\n",
  "\n",
  "**正常打开 Notebook 时，运行下面这一个单元即可。**  \n",
  "输出逐组写入 `04_输出结果/峰值电流Mapping/peak_current_map.csv`；中断后再次运行会自动跳过已完成组。每完成一组才写检查点，因此中断时正在计算的组会从头重算。\n",
  "\n",
  "当前固定使用 2 s 结果输出周期和 `1e-3` 的倍率搜索容差。自动交付校验环境会设置 `CW501_SKIP_FULL_MAPPING=1`，仅跳过耗时的全矩阵计算，不影响你本地正常运行。\n",
];

notebook.cells[7].source = notebook.cells[7].source
  .join("")
  .replace(
    "        discharge_soc=peak_module.DEFAULT_DISCHARGE_SOC,\n        resume=True,",
    "        discharge_soc=peak_module.DEFAULT_DISCHARGE_SOC,\n        output_period_s=2.0,\n        ratio_xtol=1e-3,\n        resume=True,"
  )
  .split(/(?<=\n)/);

for (const cell of notebook.cells) {
  if (cell.cell_type === "code") {
    cell.outputs = [];
    cell.execution_count = null;
  }
}

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
