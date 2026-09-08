import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "D:/Users/hez/Desktop/hithium/outputs/doe_pouch_bridge_20260728";
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const doe = workbook.worksheets.add("01_DOE制样表");
const tests = workbook.worksheets.add("02_测试矩阵");
const params = workbook.worksheets.add("03_参数记录");
const compare = workbook.worksheets.add("04_结果比较");
const summary = workbook.worksheets.add("05_样品数汇总");

const colors = {
  navy: "#17365D",
  blue: "#1F4E78",
  brightBlue: "#1B66E3",
  lightBlue: "#D9EAF7",
  green: "#70AD47",
  lightGreen: "#E2F0D9",
  orange: "#ED7D31",
  lightOrange: "#FCE4D6",
  purple: "#7030A0",
  lightPurple: "#E4DFEC",
  gray: "#7F8C8D",
  lightGray: "#F2F2F2",
  border: "#C7CED6",
  white: "#FFFFFF",
  red: "#C00000",
  lightRed: "#F4CCCC",
};

function title(sheet, range, text) {
  range.merge();
  range.values = [[text]];
  range.format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, size: 16 },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  range.format.rowHeight = 34;
}

function sectionHeader(range) {
  range.format = {
    fill: colors.blue,
    font: { bold: true, color: colors.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: colors.border },
  };
}

function dataBody(range) {
  range.format = {
    font: { size: 10 },
    verticalAlignment: "center",
    wrapText: true,
    borders: {
      insideHorizontal: { style: "thin", color: colors.border },
      insideVertical: { style: "thin", color: colors.border },
      bottom: { style: "thin", color: colors.border },
    },
  };
}

function setWidths(sheet, widths) {
  for (const [col, width] of Object.entries(widths)) {
    sheet.getRange(`${col}:${col}`).format.columnWidth = width;
  }
}

for (const sheet of [doe, tests, params, compare, summary]) {
  sheet.showGridLines = false;
}

// ---------------------------------------------------------------------------
// 01_DOE制样表
// ---------------------------------------------------------------------------
title(doe, doe.getRange("A1:L1"), "扣电—单层软包—3Ah软包不一致性机理拆解：第一轮DOE制样表");
doe.getRange("A2:L4").values = [
  ["设计目标", "第一轮即识别压力、电解液、N/P、化成、制片、极片面积、overhang和层数造成的扣电—软包偏差，并判断是否导致材料排序反转", null, null, null, null, null, null, null, null, null, null],
  ["材料选择", "M1/M2：性能接近、最可能发生排序反转；M3：差异明显的正对照", null, null, null, null, null, null, null, null, null, null],
  ["统计约定", "n为每种材料、每组的平行样数量；核心桥接组覆盖M1/M2/M3，机理扰动组优先覆盖M1/M2", null, null, null, null, null, null, null, null, null, null],
];
doe.getRange("A2:A4").format = {
  fill: colors.lightBlue,
  font: { bold: true, color: colors.navy },
  verticalAlignment: "center",
};
for (const row of [2, 3, 4]) {
  doe.getRange(`B${row}:L${row}`).merge();
}
doe.getRange("A2:L4").format.wrapText = true;
doe.getRange("A2:L4").format.borders = { preset: "all", style: "thin", color: colors.border };
doe.getRange("A2:L4").format.rowHeight = 28;

doe.getRange("A6:L6").values = [[
  "模块", "组别", "电芯类型", "电芯/制样方案", "与标准化基准C1相比的唯一变化",
  "材料范围", "平行样n", "材料数", "样品数", "主要识别机制", "优先级", "执行备注",
]];
sectionHeader(doe.getRange("A6:L6"));
doe.getRange("A7:L20").values = [
  ["参数测试", "H1", "扣电半电", "粉末半电池", "粉末直接制片", "M1/M2/M3", 3, 3, null, "材料本征OCV、扩散和动力学", "核心", "反电极及测试条件保持一致"],
  ["参数测试", "H2", "扣电半电", "同批极片半电池", "使用软包同批极片", "M1/M2/M3", 3, 3, null, "制片工艺对孔隙、传输和界面的影响", "核心", "与H1形成粉末—极片配对"],
  ["现状基准", "C0", "扣电全电", "当前扣电SOP", "当前弹片、注液、N/P、化成和制片方法", "M1/M2/M3", 3, 3, null, "当前扣电—软包综合偏差", "核心", "不得同时改变现行SOP"],
  ["标准化基准", "C1", "扣电全电", "标准化扣电", "同批极片、恒间隙均匀压力、匹配N/P、E/C和化成", "M1/M2/M3", 3, 3, null, "工艺标准化后能否逼近软包", "核心", "所有单因素扰动均以C1为参照"],
  ["压力扰动", "C2", "扣电全电", "弹片扣电", "C1仅改回当前弹片", "M1/M2", 2, 2, null, "压力分布、接触阻抗、孔隙压缩", "核心", "记录平均面压及压力纸分布"],
  ["电解液扰动", "C3", "扣电全电", "过量电解液扣电", "C1仅改回当前扣电注液方式", "M1/M2", 2, 2, null, "E/C、浸润和电解液储量", "扩展", "同时记录E/C与E/A"],
  ["配平扰动", "C4", "扣电全电", "当前N/P扣电", "C1仅改回当前扣电N/P", "M1/M2", 2, 2, null, "容量配平、初始锂库存和析锂边界", "扩展", "同时计算N/P_overlap与N/P_total"],
  ["化成扰动", "C5", "扣电全电", "当前化成扣电", "C1仅改回当前扣电化成及静置制度", "M1/M2", 2, 2, null, "SEI、首效和早期阻抗", "扩展", "温度、倍率、截止和静置均需记录"],
  ["制片扰动", "C6", "扣电全电", "粉末重制扣电", "C1仅将同批极片改为粉末重新制片", "M1/M2", 2, 2, null, "涂布、压实、孔隙率和导电网络", "扩展", "面容量与压实密度尽量匹配"],
  ["Overhang扰动", "C7", "扣电全电", "等宽overhang扣电", "overhang绝对宽度与3Ah一致", "M1/M2", 2, 2, null, "绝对边缘宽度是否控制储锂效应", "核心", "正极面积及重叠区N/P保持不变"],
  ["Overhang扰动", "C8", "扣电全电", "等比例overhang扣电", "overhang面积占比与3Ah一致", "M1/M2", 2, 2, null, "overhang面积比例是否控制不一致", "核心", "记录绝对宽度和面积比例"],
  ["面积扰动", "C9", "扣电全电", "大面积扣电", "增大重叠面积，保持overhang比例和平均面压一致", "M1/M2", 2, 2, null, "极片面积、周长/面积比和空间平均效应", "核心", "面积增大范围以壳体和夹具可实现为准"],
  ["尺度桥梁", "S1", "单层软包", "大面积单层软包", "平面尺寸、极耳、overhang及极片与3Ah一致，仅为单层", "M1/M2/M3", 3, 3, null, "扣电到大面积单层结构的跨越", "核心", "通过夹具/垫片控制单层面压与E/C"],
  ["目标电芯", "P1", "3Ah软包", "标准3Ah多层软包", "标准3Ah结构", "M1/M2/M3", 3, 3, null, "最终预测对象及多层堆叠效应", "核心", "与S1使用同批极片及相同平面设计"],
];
doe.getRange("I7").formulas = [["=G7*H7"]];
doe.getRange("I7:I20").fillDown();
dataBody(doe.getRange("A7:L20"));
doe.getRange("G7:I20").format.numberFormat = "0";
doe.getRange("G7:I20").format.horizontalAlignment = "center";
doe.getRange("B7:C20").format.horizontalAlignment = "center";
doe.getRange("F7:H20").format.horizontalAlignment = "center";
doe.getRange("K7:K20").format.horizontalAlignment = "center";
doe.getRange("A7:A8").format.fill = colors.lightGreen;
doe.getRange("A9:E10").format.fill = colors.lightBlue;
doe.getRange("A11:E19").format.fill = colors.lightGray;
doe.getRange("A19:E19").format.fill = colors.lightPurple;
doe.getRange("A20:E20").format.fill = colors.lightOrange;
doe.getRange("K7:K20").conditionalFormats.add("containsText", {
  text: "核心",
  format: { fill: colors.lightGreen, font: { bold: true, color: "#274E13" } },
});
doe.getRange("K7:K20").conditionalFormats.add("containsText", {
  text: "扩展",
  format: { fill: colors.lightOrange, font: { color: "#9C5700" } },
});
doe.getRange("K7:K20").dataValidation = { rule: { type: "list", values: ["核心", "扩展"] } };
doe.getRange("A22:H22").merge();
doe.getRange("A22:H22").values = [["样品总数（按上述材料范围与平行样数自动计算）"]];
doe.getRange("I22").formulas = [["=SUM(I7:I20)"]];
doe.getRange("J22:L22").merge();
doe.getRange("J22:L22").values = [["如历史重复性CV较高，机理扰动组n由2增至3"]];
doe.getRange("A22:L22").format = {
  fill: colors.navy,
  font: { bold: true, color: colors.white },
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: colors.navy },
};
doe.getRange("I22").format.numberFormat = "0";
doe.getRange("I22").format.horizontalAlignment = "center";
doe.freezePanes.freezeRows(6);
doe.freezePanes.freezeColumns(2);
setWidths(doe, { A: 14, B: 9, C: 13, D: 21, E: 38, F: 14, G: 10, H: 9, I: 10, J: 31, K: 10, L: 31 });
doe.getRange("A7:L20").format.rowHeight = 44;

// ---------------------------------------------------------------------------
// 02_测试矩阵
// ---------------------------------------------------------------------------
title(tests, tests.getRange("A1:R1"), "第一轮测试矩阵：用快速机理指纹替代三温度全量铺开");
tests.getRange("A2:R3").values = [
  ["使用规则", "“必做”用于第一轮归因；“选做”用于关键组确认；“—”表示第一轮不安排。所有全电测试均使用同一批次和统一SOC定义。", null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null],
  ["测试原则", "同一格式内按C-rate比较产品表现；跨面积格式另增加相同面电流密度对照，避免极片面积差异被倍率定义掩盖。", null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null],
];
for (const row of [2, 3]) {
  tests.getRange(`B${row}:R${row}`).merge();
}
tests.getRange("A2:A3").format = { fill: colors.lightBlue, font: { bold: true, color: colors.navy } };
tests.getRange("A2:R3").format.wrapText = true;
tests.getRange("A2:R3").format.borders = { preset: "all", style: "thin", color: colors.border };
tests.getRange("A5:R5").values = [[
  "测试阶段", "测试项目", "H1", "H2", "C0", "C1", "C2", "C3", "C4", "C5",
  "C6", "C7", "C8", "C9", "S1", "P1", "测试条件/核心输出", "主要目的",
]];
sectionHeader(tests.getRange("A5:R5"));
const B = "必做";
const O = "选做";
const N = "—";
tests.getRange("A6:R19").values = [
  ["材料参数", "OCV/无极化曲线", B, B, O, O, N, N, N, N, N, N, N, N, B, B, "25℃；获得SOC—OCV关系", "材料热力学与全电SOC映射"],
  ["材料参数", "GITT或等效扩散测试", B, O, N, N, N, N, N, N, N, N, N, N, N, N, "25℃；扩散系数随SOC变化", "提取固相扩散参数"],
  ["化成诊断", "首效/不可逆容量/完整曲线", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "统一化成截止条件", "锂库存与SEI差异"],
  ["化成诊断", "dQ/dV及静置OCV", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "充满/放空后记录弛豫曲线", "识别N/P、相变和overhang储锂"],
  ["几何诊断", "厚度/压力分布/极片错位", N, N, B, B, B, O, O, O, O, B, B, B, B, B, "压力纸或等效面压测量", "压力、接触与结构差异"],
  ["基准容量", "25℃低倍率容量", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "建议0.1C～0.2C", "建立容量与能量基准"],
  ["倍率测试", "相同C-rate倍率性能", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "统一SOC和截止条件", "产品层面的倍率和极化差异"],
  ["电流密度对照", "相同面电流密度测试", N, N, O, B, B, O, O, O, O, B, B, B, B, B, "按重叠面积换算A/m²", "分离面积与倍率定义影响"],
  ["阻抗测试", "50% SOC EIS", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "统一温度、SOC及静置时间", "欧姆、界面和扩散阻抗"],
  ["DCR", "10%/50%/90% SOC DCR", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "统一脉冲倍率和脉冲时长", "不同SOC下功率偏差"],
  ["Overhang诊断", "长静置OCV及容量恢复", N, N, N, B, N, N, O, N, N, B, B, B, B, B, "充满/放空后设置多时间点弛豫", "观察面内扩散与overhang储锂"],
  ["快速循环", "25℃短循环", N, N, B, B, B, B, B, B, B, B, B, B, B, B, "建议≥50圈或至前期斜率稳定", "早期容量、DCR及厚度增长斜率"],
  ["加速循环", "45℃短循环", N, N, B, B, O, B, O, B, O, O, O, O, B, B, "第一轮不铺开35℃循环", "放大E/C、SEI和界面差异"],
  ["拆解验证", "循环后拆解/边缘区观察", N, N, O, B, B, B, O, B, B, B, B, B, B, B, "优先选取差异最大的配对样", "验证压力、浸润、析锂及边缘效应"],
];
dataBody(tests.getRange("A6:R19"));
tests.getRange("C6:P19").format.horizontalAlignment = "center";
tests.getRange("C6:P19").conditionalFormats.add("containsText", {
  text: "必做",
  format: { fill: colors.lightGreen, font: { bold: true, color: "#274E13" } },
});
tests.getRange("C6:P19").conditionalFormats.add("containsText", {
  text: "选做",
  format: { fill: "#FFF2CC", font: { color: "#7F6000" } },
});
tests.getRange("C6:P19").conditionalFormats.add("containsText", {
  text: "—",
  format: { fill: colors.lightGray, font: { color: colors.gray } },
});
tests.freezePanes.freezeRows(5);
tests.freezePanes.freezeColumns(2);
setWidths(tests, {
  A: 15, B: 24, C: 7, D: 7, E: 7, F: 7, G: 7, H: 7, I: 7, J: 7,
  K: 7, L: 7, M: 7, N: 7, O: 7, P: 7, Q: 30, R: 31,
});
tests.getRange("A6:R19").format.rowHeight = 42;

// ---------------------------------------------------------------------------
// 03_参数记录
// ---------------------------------------------------------------------------
title(params, params.getRange("A1:H1"), "制样与测试参数记录字段：保证跨格式结果可追溯");
params.getRange("A3:H3").values = [[
  "类别", "字段名称", "推荐字段名", "单位", "填写对象", "必填", "定义/计算方法", "备注",
]];
sectionHeader(params.getRange("A3:H3"));
params.getRange("A4:H34").values = [
  ["标识", "样品编号", "sample_id", "—", "全部样品", "是", "唯一编号，不得重复", "建议包含材料、组别、重复号"],
  ["标识", "材料编号", "material_id", "—", "全部样品", "是", "M1/M2/M3", "M1/M2为近性能材料"],
  ["标识", "DOE组别", "doe_group", "—", "全部样品", "是", "H1～P1", "与01表保持一致"],
  ["标识", "极片批次", "electrode_batch", "—", "全电及H2", "是", "记录涂布/辊压批次", "C1/S1/P1必须同批"],
  ["结构", "电芯格式", "cell_format", "—", "全电", "是", "扣电/单层软包/3Ah软包", "禁止仅写“全电”"],
  ["结构", "层数", "layer_count", "层", "软包", "是", "有效正负极层数", "S1=1"],
  ["几何", "正极总面积", "cathode_area_total", "cm²", "全电", "是", "正极涂层总面积", "区分单双面"],
  ["几何", "正负极重叠面积", "overlap_area", "cm²", "全电", "是", "实际有效重叠面积", "倍率电流密度以此换算"],
  ["几何", "负极总面积", "anode_area_total", "cm²", "全电", "是", "包含overhang", "用于N/P_total"],
  ["几何", "Overhang宽度", "overhang_width", "mm", "全电", "是", "记录各边宽度及平均值", "圆形扣电记录径向宽度"],
  ["几何", "Overhang面积比", "overhang_area_ratio", "%", "全电", "是", "(负极总面积-重叠面积)/重叠面积", "不得只记录绝对宽度"],
  ["几何", "周长/面积比", "perimeter_area_ratio", "cm⁻¹", "全电", "是", "重叠区域周长/重叠面积", "表征边缘占比"],
  ["极片", "正极面容量", "cathode_areal_capacity", "mAh/cm²", "全电", "是", "低倍率实测或质量×比容量", "同批极片应复测"],
  ["极片", "负极面容量", "anode_areal_capacity", "mAh/cm²", "全电", "是", "低倍率实测或质量×比容量", "区分重叠区和总面积"],
  ["极片", "正极压实密度", "cathode_density", "g/cm³", "全电", "是", "面密度/涂层厚度", "记录测试方法"],
  ["极片", "负极压实密度", "anode_density", "g/cm³", "全电", "是", "面密度/涂层厚度", "记录测试方法"],
  ["极片", "正极孔隙率", "cathode_porosity", "%", "全电", "建议", "由真密度、面密度和厚度计算", "与压实密度配套"],
  ["极片", "负极孔隙率", "anode_porosity", "%", "全电", "建议", "由真密度、面密度和厚度计算", "与压实密度配套"],
  ["配平", "重叠区N/P", "np_overlap", "—", "全电", "是", "按正负极有效重叠容量计算", "跨格式比较的主要N/P"],
  ["配平", "总面积N/P", "np_total", "—", "全电", "是", "包含负极overhang总容量", "用于分析储锂与库存"],
  ["电解液", "注液量", "electrolyte_mass", "g", "全电", "是", "实际注液质量", "记录称量偏差"],
  ["电解液", "E/C", "electrolyte_capacity_ratio", "g/Ah", "全电", "是", "注液质量/名义容量", "单层软包不沿用3Ah绝对注液量"],
  ["电解液", "E/A", "electrolyte_area_ratio", "mg/cm²", "全电", "是", "注液质量/重叠面积", "跨面积格式辅助比较"],
  ["压力", "平均面压", "mean_stack_pressure", "MPa", "全电", "是", "有效面积上的平均压力", "不能只记录弹片或夹具型号"],
  ["压力", "压力均匀性", "pressure_uniformity", "%或CV", "全电", "是", "压力纸或传感器统计", "记录最大/最小/均值"],
  ["化成", "化成温度", "formation_temperature", "℃", "全电", "是", "记录实测温度", "与温箱设定值区分"],
  ["化成", "化成倍率", "formation_rate", "C", "全电", "是", "按实测容量定义", "记录电流值"],
  ["化成", "静置时间", "formation_rest_time", "h", "全电", "是", "各步骤静置时间", "影响浸润和SEI"],
  ["测试", "实际电芯温度", "cell_temperature", "℃", "全电", "是", "测试期间实测", "不能只记录环境温度"],
  ["测试", "面电流密度", "areal_current_density", "A/m²", "全电", "是", "电流/重叠面积", "与C-rate同时记录"],
  ["测试", "状态标记", "data_quality_flag", "—", "全部样品", "是", "正常/异常/待确认", "异常不得直接删除"],
];
dataBody(params.getRange("A4:H34"));
params.getRange("A4:A34").format.fill = colors.lightBlue;
params.getRange("F4:F34").format.horizontalAlignment = "center";
params.getRange("F4:F34").conditionalFormats.add("containsText", {
  text: "是",
  format: { fill: colors.lightGreen, font: { bold: true, color: "#274E13" } },
});
params.getRange("F4:F34").conditionalFormats.add("containsText", {
  text: "建议",
  format: { fill: "#FFF2CC", font: { color: "#7F6000" } },
});
params.freezePanes.freezeRows(3);
params.freezePanes.freezeColumns(2);
setWidths(params, { A: 12, B: 22, C: 28, D: 12, E: 18, F: 9, G: 42, H: 34 });
params.getRange("A4:H34").format.rowHeight = 34;

// ---------------------------------------------------------------------------
// 04_结果比较
// ---------------------------------------------------------------------------
title(compare, compare.getRange("A1:G1"), "第一轮结果比较与机理判定");
compare.getRange("A2:G2").merge();
compare.getRange("A2:G2").values = [[
  "统一定义：ΔY(A→B)=Y_B−Y_A；重点观察容量、能量效率、极化、DCR、EIS、厚度及前期衰减斜率，并同时检查M1/M2排序是否反转。",
]];
compare.getRange("A2:G2").format = {
  fill: colors.lightBlue,
  font: { color: colors.navy },
  wrapText: true,
  verticalAlignment: "center",
};
compare.getRange("A4:G4").values = [[
  "编号", "对比", "差值定义", "主要机制", "重点响应", "判定方法", "第一轮输出",
]];
sectionHeader(compare.getRange("A4:G4"));
compare.getRange("A5:G17").values = [
  ["R01", "C0－C1", "Y_C0−Y_C1", "当前扣电SOP综合偏差", "首效、容量、DCR、循环斜率", "标准化后偏差是否明显收窄", "现状偏差中可由标准化消除的部分"],
  ["R02", "C2－C1", "Y_C2−Y_C1", "弹片与压力分布", "接触阻抗、DCR、厚度、离散性", "效应是否超过组内重复性噪声", "压力贡献及材料交互"],
  ["R03", "C3－C1", "Y_C3−Y_C1", "E/C和浸润", "EIS、高温斜率、倍率极化", "不同材料的效应方向是否一致", "电解液贡献及材料交互"],
  ["R04", "C4－C1", "Y_C4−Y_C1", "N/P与初始锂库存", "OCV、dQ/dV、首效、充电末端极化", "M1/M2排序是否变化", "配平贡献及排序风险"],
  ["R05", "C5－C1", "Y_C5−Y_C1", "化成和SEI", "首效、EIS、前期衰减", "早期阻抗及衰减差异是否显著", "化成贡献及材料交互"],
  ["R06", "C6－C1", "Y_C6−Y_C1", "粉末重制与同批极片", "倍率、扩散阻抗、离散性", "H1/H2与C6/C1是否形成一致证据链", "制片工艺贡献"],
  ["R07", "C7－C1", "Y_C7−Y_C1", "overhang绝对宽度", "弛豫OCV、容量恢复、dQ/dV", "静置时间依赖是否改变", "绝对宽度尺度效应"],
  ["R08", "C8－C1", "Y_C8−Y_C1", "overhang面积比例", "弛豫OCV、容量恢复、循环斜率", "与C7比较哪个尺度指标更有效", "overhang比例效应"],
  ["R09", "C9－C1", "Y_C9−Y_C1", "面积及周长/面积比", "倍率、DCR、离散性", "面积增大是否系统性接近S1", "扣电内部面积尺度效应"],
  ["R10", "S1－C1", "Y_S1−Y_C1", "大面积、极耳、封装和单层结构", "容量、DCR、温升、分布差异", "标准化扣电到单层软包的剩余差值", "扣电→单层软包桥接关系"],
  ["R11", "P1－S1", "Y_P1−Y_S1", "层数、堆叠、层间一致性和热累积", "DCR、温升、厚度、循环斜率", "单层到多层差异是否稳定", "单层→3Ah桥接关系"],
  ["R12", "P1－C1", "Y_P1−Y_C1", "扣电到3Ah总跨尺度差异", "全部关键响应", "与R10+R11是否近似可加", "完整扣电→3Ah差异"],
  ["R13", "桥接闭合检查", "(P1−C1)−[(S1−C1)+(P1−S1)]", "数据配对与桥接一致性", "各响应的闭合残差", "同批、同SOC定义下应接近0", "数据和计算链路质量检查"],
];
dataBody(compare.getRange("A5:G17"));
compare.getRange("A5:A17").format.horizontalAlignment = "center";
compare.getRange("B5:C17").format.horizontalAlignment = "center";
compare.getRange("A19:G19").merge();
compare.getRange("A19:G19").values = [[
  "第一轮决策顺序：先判断重复性 → 再判断各机理主效应 → 检查材料×机理交互及M1/M2排序 → 最后把无法通过工艺标准化消除的尺寸/热/电流分布残差交给P4D。",
]];
compare.getRange("A19:G19").format = {
  fill: colors.navy,
  font: { bold: true, color: colors.white },
  wrapText: true,
  verticalAlignment: "center",
};
compare.freezePanes.freezeRows(4);
setWidths(compare, { A: 9, B: 18, C: 23, D: 29, E: 34, F: 36, G: 35 });
compare.getRange("A5:G17").format.rowHeight = 42;
compare.getRange("A19:G19").format.rowHeight = 42;

// ---------------------------------------------------------------------------
// 05_样品数汇总
// ---------------------------------------------------------------------------
title(summary, summary.getRange("A1:F1"), "第一轮DOE样品数汇总");
summary.getRange("A3:C3").values = [["电芯类型", "样品数", "说明"]];
sectionHeader(summary.getRange("A3:C3"));
summary.getRange("A4:A7").values = [["扣电半电"], ["扣电全电"], ["单层软包"], ["3Ah软包"]];
summary.getRange("B4").formulas = [[`=SUMIF('01_DOE制样表'!$C$7:$C$20,A4,'01_DOE制样表'!$I$7:$I$20)`]];
summary.getRange("B4:B7").fillDown();
summary.getRange("C4:C7").values = [
  ["粉末半电＋同批极片半电"],
  ["现状/标准化基准＋8个单因素扰动"],
  ["与3Ah同平面设计的单层桥梁"],
  ["最终目标电芯"],
];
summary.getRange("A8").values = [["合计"]];
summary.getRange("B8").formulas = [["=SUM(B4:B7)"]];
summary.getRange("C8").values = [["按3种材料及当前平行样数计算"]];
dataBody(summary.getRange("A4:C8"));
summary.getRange("A8:C8").format = {
  fill: colors.navy,
  font: { bold: true, color: colors.white },
  borders: { preset: "all", style: "thin", color: colors.navy },
};
summary.getRange("B4:B8").format.numberFormat = "0";
summary.getRange("B4:B8").format.horizontalAlignment = "center";

summary.getRange("E3:F3").values = [["方案", "样品数"]];
sectionHeader(summary.getRange("E3:F3"));
summary.getRange("E4:E6").values = [["核心方案"], ["扩展机理组"], ["完整第一轮"]];
summary.getRange("F4").formulas = [[`=SUMIF('01_DOE制样表'!$K$7:$K$20,"核心",'01_DOE制样表'!$I$7:$I$20)`]];
summary.getRange("F5").formulas = [[`=SUMIF('01_DOE制样表'!$K$7:$K$20,"扩展",'01_DOE制样表'!$I$7:$I$20)`]];
summary.getRange("F6").formulas = [["=SUM(F4:F5)"]];
dataBody(summary.getRange("E4:F6"));
summary.getRange("F4:F6").format.numberFormat = "0";
summary.getRange("F4:F6").format.horizontalAlignment = "center";
summary.getRange("E6:F6").format = {
  fill: colors.lightBlue,
  font: { bold: true, color: colors.navy },
  borders: { preset: "all", style: "thin", color: colors.border },
};

summary.getRange("A11:F11").merge();
summary.getRange("A11:F11").values = [["执行建议"]];
summary.getRange("A11:F11").format = {
  fill: colors.blue,
  font: { bold: true, color: colors.white },
  verticalAlignment: "center",
};
summary.getRange("A12:F15").values = [
  ["1", "优先完成C0、C1、C2、C7、C8、C9、S1和P1，以最快拆开压力、面积、overhang及层数效应。", null, null, null, null],
  ["2", "C3～C6用于电解液、N/P、化成和制片的扩展归因；资源不足时可在核心数据出来后滚动启动。", null, null, null, null],
  ["3", "第一轮取消35℃全量循环；45℃只覆盖基准组及初步识别出的关键扰动组。", null, null, null, null],
  ["4", "若历史重复性CV较高，优先增加机理扰动组平行样，而不是增加更多温度或测试项目。", null, null, null, null],
];
for (const row of [12, 13, 14, 15]) {
  summary.getRange(`B${row}:F${row}`).merge();
}
summary.getRange("A12:F15").format = {
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: colors.border },
};
summary.getRange("A12:A15").format = {
  fill: colors.lightBlue,
  font: { bold: true, color: colors.navy },
  horizontalAlignment: "center",
};
summary.getRange("A12:F15").format.rowHeight = 34;
setWidths(summary, { A: 17, B: 14, C: 43, D: 4, E: 19, F: 14 });

// Export a checkpoint before rendering so the workbook can be inspected even
// if a large preview is slow on this machine.
const finalPath = `${outputDir}/扣电-单层软包-3Ah软包_第一轮DOE.xlsx`;
const checkpoint = await SpreadsheetFile.exportXlsx(workbook);
await checkpoint.save(finalPath);
console.log(`CHECKPOINT_PATH=${finalPath}`);

// Render all populated ranges for QA.
const renderJobs = [
  ["01_DOE制样表", "A1:L22", "preview_01_doe.png"],
  ["02_测试矩阵", "A1:R19", "preview_02_tests.png"],
  ["03_参数记录", "A1:H34", "preview_03_params.png"],
  ["04_结果比较", "A1:G19", "preview_04_compare.png"],
  ["05_样品数汇总", "A1:F15", "preview_05_summary.png"],
];
for (const [sheetName, range, fileName] of renderJobs) {
  console.log(`RENDERING=${sheetName}`);
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 0.7,
    format: "png",
  });
  await fs.writeFile(`${outputDir}/${fileName}`, new Uint8Array(await preview.arrayBuffer()));
}

const inspectDoe = await workbook.inspect({
  kind: "table",
  sheetId: "01_DOE制样表",
  range: "A6:L22",
  include: "values,formulas",
  tableMaxRows: 22,
  tableMaxCols: 12,
  maxChars: 7000,
});
console.log("DOE_INSPECT");
console.log(inspectDoe.ndjson);

const inspectSummary = await workbook.inspect({
  kind: "table",
  sheetId: "05_样品数汇总",
  range: "A3:F8",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 6,
  maxChars: 3000,
});
console.log("SUMMARY_INSPECT");
console.log(inspectSummary.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(finalPath);
console.log(`FINAL_PATH=${finalPath}`);
