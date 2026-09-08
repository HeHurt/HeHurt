import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "C:/HithiumSSD/hithium/outputs/doe_pouch_bridge_20260728";
const finalPath = `${outputDir}/扣电-单层软包-3Ah软包_第一轮DOE_精简版_正负极各3种材料.xlsx`;
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("精简DOE");
sheet.showGridLines = false;

const C = {
  navy: "#17365D",
  blue: "#1F4E78",
  lightBlue: "#D9EAF7",
  green: "#E2F0D9",
  purple: "#E4DFEC",
  orange: "#FCE4D6",
  gray: "#F2F2F2",
  border: "#B8C2CC",
  white: "#FFFFFF",
};

sheet.getRange("A1:H1").merge();
sheet.getRange("A1:H1").values = [["扣电—单层软包—3Ah软包不一致性：第一轮精简DOE（正负极各3种材料）"]];
sheet.getRange("A1:H1").format = {
  fill: C.navy,
  font: { bold: true, color: C.white, size: 17 },
  verticalAlignment: "center",
  horizontalAlignment: "left",
};
sheet.getRange("A1:H1").format.rowHeight = 36;

sheet.getRange("A2:H2").merge();
sheet.getRange("A2:H2").values = [[
  "材料组合采用十字设计：正A/负A、正B/负A、正C/负A、正A/负B、正A/负C，共5种；机理扰动选择正A/负A、正B/负A、正A/负B共3种关键组合。",
]];
sheet.getRange("A2:H2").format = {
  fill: C.lightBlue,
  font: { color: C.navy },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.border },
};
sheet.getRange("A2:H2").format.rowHeight = 28;

sheet.getRange("A4:H4").values = [[
  "类别", "制样组", "样品配置", "第一轮测试", "材料范围", "组内设计", "数量", "主要目的",
]];
sheet.getRange("A4:H4").format = {
  fill: C.blue,
  font: { bold: true, color: C.white },
  wrapText: true,
  verticalAlignment: "center",
  horizontalAlignment: "center",
  borders: { preset: "all", style: "thin", color: C.border },
};
sheet.getRange("A4:H4").format.rowHeight = 30;

sheet.getRange("A5:H11").values = [
  ["材料参数", "H1/H2", "正极3种＋负极3种，分别做粉末半电和同批极片半电", "OCV/无极化曲线、25℃GITT或低倍率动力学测试", "正极3种＋负极3种", "6种材料×2类半电×n=3", 36, "分离正负极材料本征差异与制片工艺差异"],
  ["扣电基准", "C0", "当前扣电SOP", "化成曲线、dQ/dV、25℃容量/倍率、EIS、DCR、25℃短循环", "5种十字组合", "5组合×n=3", 15, "获得各正负极材料组合的当前扣电—软包总体偏差"],
  ["扣电标准化", "C1", "同批极片＋固定堆叠间隙＋柔性均压＋匹配N/P、注液和化成", "与C0相同；压力纸记录均值、CV和中心/边缘比", "5种十字组合", "5组合×n=3", 15, "判断扣电标准化后能否逼近软包并保持材料排序"],
  ["扣电单因素", "C2～C6", "压力、注液量、N/P、化成、制片方式分别单独改变", "与C1相同；45℃只做初步差异较大的组", "3种关键组合", "5因素×3组合×n=2", 30, "分别检查正极变化和负极变化下的机理贡献"],
  ["扣电几何", "C7～C9", "等宽overhang、等比例overhang、大面积扣电", "与C1相同；增加长静置OCV/容量恢复、厚度和压力", "3种关键组合", "3几何组×3组合×n=2", 18, "识别面积和overhang效应是否依赖正极或负极材料"],
  ["单层软包", "S1", "与3Ah软包相同平面尺寸、极耳和overhang，仅为单层", "化成曲线、dQ/dV、25℃容量/倍率、EIS、DCR、短循环、测厚", "5种十字组合", "5组合×n=3", 15, "建立5种正负极组合从扣电到大面积单层结构的桥梁"],
  ["3Ah软包", "P1", "标准3Ah多层软包", "与S1相同；同步记录厚度和实际温度", "5种十字组合", "5组合×n=3", 15, "验证正负极材料排序及多层堆叠效应"],
];
sheet.getRange("A5:H11").format = {
  wrapText: true,
  verticalAlignment: "center",
  borders: {
    insideHorizontal: { style: "thin", color: C.border },
    insideVertical: { style: "thin", color: C.border },
    bottom: { style: "thin", color: C.border },
    left: { style: "thin", color: C.border },
    right: { style: "thin", color: C.border },
  },
};
sheet.getRange("A5:C5").format.fill = C.green;
sheet.getRange("A6:C9").format.fill = C.lightBlue;
sheet.getRange("A10:C10").format.fill = C.purple;
sheet.getRange("A11:C11").format.fill = C.orange;
sheet.getRange("A5:B11").format.horizontalAlignment = "center";
sheet.getRange("E5:G11").format.horizontalAlignment = "center";
sheet.getRange("G5:G11").format.numberFormat = "0";
sheet.getRange("A5:H11").format.rowHeight = 48;

sheet.getRange("A13:F13").merge();
sheet.getRange("A13:F13").values = [["第一轮样品总数"]];
sheet.getRange("G13").formulas = [["=SUM(G5:G11)"]];
sheet.getRange("H13").values = [["采用5种十字组合；未铺开正负极3×3的9种全组合"]];
sheet.getRange("A13:H13").format = {
  fill: C.navy,
  font: { bold: true, color: C.white },
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: C.navy },
};
sheet.getRange("G13").format.numberFormat = "0";
sheet.getRange("G13").format.horizontalAlignment = "center";
sheet.getRange("A13:H13").format.rowHeight = 30;

sheet.getRange("A15:H15").merge();
sheet.getRange("A15:H15").values = [["第一轮设计逻辑"]];
sheet.getRange("A15:H15").format = {
  fill: C.blue,
  font: { bold: true, color: C.white },
  verticalAlignment: "center",
};

const logic = [
  "5种十字组合：正A/负A为基准；正B、正C分别替换正极；负B、负C分别替换负极，不在第一轮铺开9种全组合。",
  "C0 → C1：判断当前扣电总体偏差中，有多少可通过压力、N/P、注液、化成和同批极片标准化消除。",
  "C1 → C2～C9：在基准、一个正极近邻和一个负极近邻组合上拆分制备、面积与overhang贡献。",
  "C1 → S1 → P1：对5种十字组合依次拆开大面积单层结构，以及层数、堆叠、层间一致性和热累积效应。",
  "第一轮输出：正极与负极材料排序、材料×结构交互、标准化扣电SOP，以及需要P4D修正的剩余差异。",
];
for (let i = 0; i < logic.length; i += 1) {
  const row = 16 + i;
  sheet.getRange(`A${row}`).values = [[i + 1]];
  sheet.getRange(`B${row}:H${row}`).merge();
  sheet.getRange(`B${row}:H${row}`).values = [[logic[i]]];
}
sheet.getRange("A16:H20").format = {
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: C.border },
};
sheet.getRange("A16:A20").format = {
  fill: C.lightBlue,
  font: { bold: true, color: C.navy },
  horizontalAlignment: "center",
};
sheet.getRange("A16:H20").format.rowHeight = 32;

sheet.freezePanes.freezeRows(4);
const widths = { A: 15, B: 12, C: 34, D: 44, E: 17, F: 25, G: 10, H: 35 };
for (const [col, width] of Object.entries(widths)) {
  sheet.getRange(`${col}:${col}`).format.columnWidth = width;
}

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(finalPath);

const preview = await workbook.render({
  sheetName: "精简DOE",
  range: "A1:H20",
  scale: 0.8,
  format: "png",
});
await fs.writeFile(
  `${outputDir}/preview_simple_doe.png`,
  new Uint8Array(await preview.arrayBuffer()),
);

const check = await workbook.inspect({
  kind: "table",
  sheetId: "精简DOE",
  range: "A4:H13",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 8,
  maxChars: 5000,
});
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

const finalExport = await SpreadsheetFile.exportXlsx(workbook);
await finalExport.save(finalPath);
console.log(`FINAL_PATH=${finalPath}`);
