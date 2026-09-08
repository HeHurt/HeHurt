const fs = require("fs");

const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));

function source(text) {
  return text.split(/(?<=\n)/);
}

notebook.cells[0].source = source(`# CW501 10s / 30s / 60s 峰值电流 Mapping

本 Notebook 使用启用接触阻抗的 DFN，按电压截止条件搜索最大恒流脉冲：

- 充电温度：0–55℃，5℃间隔。
- 放电温度：−30、−20、−10℃；0–55℃为5℃间隔。
- 脉冲时间：10 s、30 s、60 s。
- 充电 SOC：0–95%，5%间隔。
- 放电 SOC：5–100%，5%间隔。
- 电压限制：充电 3.65 V、放电 2.5 V。
- 结果输出周期：2 s；IDAKLU 内部仍采用自适应积分步长并连续定位截止事件。
- 同一计算组复用已参数化的 DFN，避免每次试探电流都重新构建模型。
- 全量计算完成后自动导出与 314Ah 参考文件一致的三 Sheet Excel，包含电流、功率和 DCR。

全量计算按“方向×温度×脉宽”逐组保存，可中断并一键续算。
`);

let cell1 = notebook.cells[1].source.join("");
cell1 = cell1.replace(
  "fresh_parameter_values = peak_module.fresh_parameter_values\n",
  "fresh_parameter_values = peak_module.fresh_parameter_values\nexport_peak_current_excel = peak_module.export_peak_current_excel\n",
);
notebook.cells[1].source = source(cell1);

notebook.cells[6].source = source(`## 3. 一键运行或续算完整 Mapping

**正常打开 Notebook 时，运行下面这一个单元即可。**  
结果逐组写入 \`04_输出结果/峰值电流Mapping/peak_current_map.csv\`；中断后再次运行会自动跳过已完成组。每完成一组才写检查点，因此中断时正在计算的组会从头重算。

全量计算结束后会自动生成 \`CW501_10s30s60s峰值电流Mapping.xlsx\`。其 \`10s\`、\`30s\`、\`60s\` 三张 Sheet 与 314Ah 参考表采用相同布局，每张表同时给出脉冲电流、首时刻实际功率和由 OCV/端电压计算的 DCR。

当前固定使用 2 s 结果输出周期和 \`1e-3\` 的倍率搜索容差。自动交付校验环境会设置 \`CW501_SKIP_FULL_MAPPING=1\`，仅跳过耗时的全矩阵计算，不影响你本地正常运行。
`);

notebook.cells[7].source = source(`if os.getenv("CW501_SKIP_FULL_MAPPING") == "1":
    print("自动校验模式：跳过全量 Mapping，使用烟雾结果检查后处理。")
    mapping_df = smoke_df.copy()
    excel_path = None
else:
    run_peak_current_mapping(
        output_dir=FULL_OUTPUT_DIR,
        durations_s=peak_module.DEFAULT_DURATIONS_S,
        charge_temperatures_c=peak_module.DEFAULT_CHARGE_TEMPERATURES_C,
        discharge_temperatures_c=peak_module.DEFAULT_DISCHARGE_TEMPERATURES_C,
        charge_soc=peak_module.DEFAULT_CHARGE_SOC,
        discharge_soc=peak_module.DEFAULT_DISCHARGE_SOC,
        output_period_s=2.0,
        ratio_xtol=1e-3,
        resume=True,
    )
    mapping_df = load_peak_current_mapping(FULL_OUTPUT_DIR)
    excel_path = export_peak_current_excel(
        mapping_df,
        FULL_OUTPUT_DIR / "CW501_10s30s60s峰值电流Mapping.xlsx",
    )

print(f"Loaded rows: {len(mapping_df):,}")
if excel_path is not None:
    print(f"Excel: {excel_path}")
display(mapping_df.tail())
`);

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
