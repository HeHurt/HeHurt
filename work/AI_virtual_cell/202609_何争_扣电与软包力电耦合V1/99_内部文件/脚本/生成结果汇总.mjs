import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const task = path.resolve(import.meta.dirname, "..", "..");
const jsonDir = path.join(task, "99_内部文件", "JSON");
const outputDir = path.join(task, "04_输出结果");
const previewDir = path.join(task, "99_内部文件", "运行记录");
const summary = JSON.parse(await fs.readFile(path.join(jsonDir, "coin_pouch_v8_quantitative_summary.json"), "utf8"));
const pouch = JSON.parse(await fs.readFile(path.join(jsonDir, "pouch_v8_full_cycle_comparison.json"), "utf8"));

const wb = Workbook.create();
const blue = "#1F4E78";
const lightBlue = "#D9EAF7";
const lightGray = "#F2F2F2";
const red = "#C00000";

function title(sheet, text, endCol) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange("A1").values = [[text]];
  sheet.getRange(`A1:${endCol}1`).format = {
    fill: blue,
    font: { bold: true, color: "#FFFFFF", size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange("A1").format.rowHeight = 30;
}

function header(range) {
  range.format = {
    fill: lightBlue,
    font: { bold: true, color: "#17365D" },
    borders: { preset: "all", style: "thin", color: "#A6A6A6" },
    verticalAlignment: "center",
    wrapText: true,
  };
}

const coin = summary.coin_coupled_100N;
const p100 = summary.pouch_coupled_100N;
const basis = summary.basis;

const compare = wb.worksheets.add("指标对比");
title(compare, "扣电与单层软包力电耦合结果汇总", "F");
compare.getRange("A3:F3").values = [["指标", "单位", "扣电100 N", "软包100 N", "软包-扣电", "说明"]];
header(compare.getRange("A3:F3"));
const compareRows = [
  ["额定容量", "Ah", basis.coin_i1C_A, basis.pouch_i1C_A, null, "各自按额定容量定义0.5C"],
  ["充电容量/额定容量", "%", coin.charge_capacity_pct_rated, p100.charge_capacity_pct_rated, null, "截止事件积分容量"],
  ["放电容量", "Ah", coin.discharge_capacity_Ah, p100.discharge_capacity_Ah, null, "恒流放电积分"],
  ["库仑效率", "%", coin.coulombic_efficiency_pct, p100.coulombic_efficiency_pct, null, "放电容量/充电容量"],
  ["能量效率", "%", coin.energy_efficiency_pct, p100.energy_efficiency_pct, null, "放电能量/充电能量"],
  ["充电截止SOC", "%", coin.maximum_charge_SOC_pct, p100.maximum_SOC_pct, null, "正负极归一化平均"],
  ["峰值压力", "kPa", coin.pressure_peak_MPa * 1000, p100.pressure_peak_kPa, null, "电极/隔膜最大值"],
  ["最大厚度增加", "μm", coin.thickness_expansion_peak_um, p100.thickness_expansion_peak_um, null, "相对初始预紧态，正值为膨胀"],
  ["石墨最大呼吸应变", "%", coin.maximum_graphite_breathing_pct, p100.maximum_graphite_breathing_pct, null, "非线性文献形状"],
  ["电解液浓度极差峰值", "mol/m³", coin.maximum_electrolyte_span_mol_m3, p100.maximum_electrolyte_span_mol_m3, null, "max(cl)-min(cl)"],
  ["集流体电流密度P99@50%SOC", "A/m²", coin.collector_current_density_p99_SOC50_A_m2, p100.collector_current_density_p99_SOC50_A_m2, null, "几何与量纲不同，主要用于各自非均匀性判断"],
];
compare.getRange(`A4:F${3 + compareRows.length}`).values = compareRows;
compare.getRange("E4").formulas = [["=D4-C4"]];
compare.getRange(`E4:E${3 + compareRows.length}`).fillDown();
compare.getRange(`C4:E${3 + compareRows.length}`).format.numberFormat = "0.000";
compare.getRange(`A4:F${3 + compareRows.length}`).format.borders = { preset: "inside", style: "thin", color: "#D9D9D9" };
compare.getRange("A:A").format.columnWidth = 28;
compare.getRange("B:B").format.columnWidth = 13;
compare.getRange("C:E").format.columnWidth = 16;
compare.getRange("F:F").format.columnWidth = 36;
compare.getRange("A3:F3").format.rowHeight = 34;
compare.freezePanes.freezeRows(3);

const pouchSheet = wb.worksheets.add("软包工况");
title(pouchSheet, "软包V8：0.13 Ah、0.5C工况对比", "E");
pouchSheet.getRange("A3:E3").values = [["指标", "单位", "0 N无耦合基线", "100 N完整耦合", "差值"]];
header(pouchSheet.getRange("A3:E3"));
const pb = pouch.cases.baseline.metrics;
const pc = pouch.cases.coupled_100N.metrics;
const pouchRows = [
  ["充电容量", "Ah", pb.charge_capacity_Ah, pc.charge_capacity_Ah, null],
  ["放电容量", "Ah", pb.discharge_capacity_Ah, pc.discharge_capacity_Ah, null],
  ["库仑效率", "%", pb.coulombic_efficiency_pct, pc.coulombic_efficiency_pct, null],
  ["能量效率", "%", pb.energy_efficiency_pct, pc.energy_efficiency_pct, null],
  ["充电截止SOC", "%", pb.maximum_SOC_pct, pc.maximum_SOC_pct, null],
  ["充电结束时间", "s", pb.charge_end_time_s, pc.charge_end_time_s, null],
  ["放电结束时间", "s", pb.discharge_end_time_s, pc.discharge_end_time_s, null],
  ["峰值压力", "kPa", pb.pressure_peak_kPa, pc.pressure_peak_kPa, null],
  ["最小孔隙率", "1", pb.minimum_porosity, pc.minimum_porosity, null],
  ["石墨最大呼吸应变", "%", pb.maximum_graphite_breathing_pct, pc.maximum_graphite_breathing_pct, null],
  ["最大厚度增加", "μm", pb.relative_thickness_change_range_um[1], pc.relative_thickness_change_range_um[1], null],
  ["电解液浓度极差峰值", "mol/m³", pb.maximum_electrolyte_span_mol_m3, pc.maximum_electrolyte_span_mol_m3, null],
];
pouchSheet.getRange(`A4:E${3 + pouchRows.length}`).values = pouchRows;
pouchSheet.getRange("E4").formulas = [["=D4-C4"]];
pouchSheet.getRange(`E4:E${3 + pouchRows.length}`).fillDown();
pouchSheet.getRange(`C4:E${3 + pouchRows.length}`).format.numberFormat = "0.000";
pouchSheet.getRange(`A4:E${3 + pouchRows.length}`).format.borders = { preset: "inside", style: "thin", color: "#D9D9D9" };
pouchSheet.getRange("A:A").format.columnWidth = 28;
pouchSheet.getRange("B:B").format.columnWidth = 13;
pouchSheet.getRange("C:E").format.columnWidth = 20;
pouchSheet.getRange("A18:E20").merge();
pouchSheet.getRange("A18").values = [["注意：这里的软包基线为0 N、coupling_on=0、breathing_mode=0；100 N工况同时开启压力反馈、接触电阻和呼吸，不能用于单独辨识呼吸效应。公平的呼吸对照还需补算100 N、coupling_on=1、breathing_mode=0。"]];
pouchSheet.getRange("A18:E20").format = { fill: "#FFF2CC", font: { color: red, bold: true }, wrapText: true, verticalAlignment: "center" };
pouchSheet.freezePanes.freezeRows(3);

const files = wb.worksheets.add("交付文件");
title(files, "正式交付文件清单", "C");
files.getRange("A3:C3").values = [["类别", "文件", "用途"]];
header(files.getRange("A3:C3"));
files.getRange("A4:C12").values = [
  ["模型", "02_模型/扣电_V9_非线性呼吸_100N_完整循环.mph", "扣电完整循环保存解"],
  ["模型", "02_模型/软包_V8_0p13Ah_0p5C_100N完整耦合.mph", "软包100 N完整耦合保存解"],
  ["模型", "02_模型/软包_V8_0p13Ah_0p5C_无耦合基线.mph", "软包0 N无耦合基线保存解"],
  ["图表", "04_输出结果/图表/01_voltage_cycle_coin_vs_pouch_v8.png", "电压与SOC对比"],
  ["图表", "04_输出结果/图表/02_performance_metrics_coin_vs_pouch_v8.png", "性能指标对比"],
  ["图表", "04_输出结果/图表/03_mechanics_coupling_coin_vs_pouch_v8.png", "力学耦合对比"],
  ["图表", "04_输出结果/图表/04_electrochemical_nonuniformity_coin_vs_pouch_v8.png", "电化学非均匀性"],
  ["图表", "04_输出结果/图表/05_pouch_collector_current_density_maps_v8.png", "软包集流体电流密度"],
  ["图表", "04_输出结果/图表/06_pouch_pressure_porosity_spatial_SOC50_v8.png", "软包局部压力与孔隙率"],
];
files.getRange("A4:C12").format.borders = { preset: "inside", style: "thin", color: "#D9D9D9" };
files.getRange("A:A").format.columnWidth = 12;
files.getRange("B:B").format.columnWidth = 68;
files.getRange("C:C").format.columnWidth = 28;
files.getRange("B4:B12").format.wrapText = true;
files.freezePanes.freezeRows(3);

const notes = wb.worksheets.add("口径说明");
title(notes, "模型与后处理口径说明", "B");
notes.getRange("A3:B3").values = [["项目", "说明"]];
header(notes.getRange("A3:B3"));
notes.getRange("A4:B10").values = [
  ["软包额定容量", "0.13 Ah；i_1C=0.13 A；0.5C电流为±0.065 A。"],
  ["充放电协议", "充电至3.65 V，静置600 s，放电至2.50 V，总计算时间18000 s。"],
  ["扣电厚度变化", "solid.disp为预紧态下的位移模长；统一定义为初始模长减当前模长，正值表示厚度增加。"],
  ["软包厚度变化", "上表面平均法向位移减下表面平均法向位移，再扣除初始预紧态，正值表示厚度增加。"],
  ["JSON与CSV", "均属于机器验收和作图的内部文件，已收纳至99_内部文件，不作为正式交付物。"],
  ["当前软包基线", "0 N无耦合基线与100 N完整耦合比较的是总耦合效应，不是单一呼吸效应。"],
  ["待补工况", "100 N、coupling_on=1、breathing_mode=0，用于与100 N、breathing_mode=2严格隔离呼吸效应。"],
];
notes.getRange("A4:B10").format.borders = { preset: "inside", style: "thin", color: "#D9D9D9" };
notes.getRange("A:A").format.columnWidth = 24;
notes.getRange("B:B").format.columnWidth = 88;
notes.getRange("B4:B10").format.wrapText = true;
notes.getRange("A4:B10").format.rowHeight = 38;
notes.freezePanes.freezeRows(3);

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["指标对比", "软包工况", "交付文件", "口径说明"]) {
  const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1.25, format: "png" });
  await fs.writeFile(path.join(previewDir, `工作簿预览_${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const check = await wb.inspect({ kind: "table", range: "指标对比!A1:F14", include: "values,formulas", tableMaxRows: 16, tableMaxCols: 8, maxChars: 5000 });
console.log(check.ndjson);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(outputDir, "结果汇总.xlsx"));
console.log(path.join(outputDir, "结果汇总.xlsx"));
