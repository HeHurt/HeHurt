import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

Error.stackTraceLimit = 0;

const runDir = process.argv[2];
const outputPath = process.argv[3];
if (!runDir || !outputPath) {
  throw new Error("Usage: node build_complete_arc_workbook.mjs <runDir> <outputPath>");
}

const workbook = Workbook.create();
const notes = workbook.worksheets.add("说明");
notes.getRange("A1:B12").values = [
  ["314Ah ARC完整实测产热数据", ""],
  ["数据范围", "25°C，0.25P/0.5P恒功率充电与放电，实际放电截止约2.50V"],
  ["时间", "ARC Step Time，秒和分钟均保留"],
  ["容量", "测试柜充电容量或放电容量，按所选有效恒功率段起点归零"],
  ["电能", "测试柜累计能量差绝对值，按所选有效恒功率段起点归零"],
  ["电流/电压", "测试柜原始时序值；放电电流和电功率保留负号"],
  ["产热功率", "ARC原表Power(W)，源公式为dT/dt*Cp*质量/60"],
  ["电芯温度", "ARC原表Can Temp；C1、C2热电偶温度另列保留"],
  ["时间对齐", "ARC与测试柜按相对Step Time最近点匹配，容差1.1s，不做插值"],
  ["有效段", "从测试柜多个工步中选择与报告时间、容量最接近的恒功率段"],
  ["源文件1", "T3-20260627-0035-0.25PARC发热功率测试报告.xlsx"],
  ["源文件2", "T3-20260627-0035-0.5PARC发热功率测试报告.xlsx"],
];
notes.mergeCells("A1:B1");
notes.getRange("A1:B1").format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF", size: 15 },
  horizontalAlignment: "center",
};
notes.getRange("A2:A12").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
  verticalAlignment: "center",
};
notes.getRange("A2:B12").format.borders = { preset: "all", style: "thin", color: "#B4C7E7" };
notes.getRange("B2:B12").format.wrapText = true;
notes.getRange("A1:A12").format.columnWidth = 18;
notes.getRange("B1:B12").format.columnWidth = 82;
notes.getRange("A1:B12").format.rowHeight = 24;
notes.showGridLines = false;

const cases = [
  ["0.25P充电", "0.25P_充电_完整时序.json"],
  ["0.25P放电", "0.25P_放电_完整时序.json"],
  ["0.5P充电", "0.5P_充电_完整时序.json"],
  ["0.5P放电", "0.5P_放电_完整时序.json"],
];

function parseNumericCsv(csvText) {
  return csvText
    .replace(/^\uFEFF/, "")
    .trim()
    .split(/\r?\n/)
    .map((line, rowIndex) =>
      line.split(",").map((value) => {
        if (rowIndex === 0 || value === "") return value;
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : value;
      }),
    );
}

for (const [sheetName, fileName] of cases) {
  const csvText = await fs.readFile(path.join(runDir, fileName), "utf8");
  const values = parseNumericCsv(csvText);
  const sheet = workbook.worksheets.add(sheetName);
  sheet.getRangeByIndexes(0, 0, values.length, values[0].length).values = values;
  const rowCount = values.length;
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.getRange("A1:K1").format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  };
  sheet.getRange(`A2:K${rowCount}`).format.borders = {
    preset: "all",
    style: "thin",
    color: "#E7E6E6",
  };
  sheet.getRange(`A2:B${rowCount}`).format.numberFormat = "0.000";
  sheet.getRange(`C2:D${rowCount}`).format.numberFormat = "0.000000";
  sheet.getRange(`E2:H${rowCount}`).format.numberFormat = "0.000";
  sheet.getRange(`I2:K${rowCount}`).format.numberFormat = "0.000";
  sheet.getRange(`A1:A${rowCount}`).format.columnWidth = 13;
  sheet.getRange(`B1:B${rowCount}`).format.columnWidth = 13;
  sheet.getRange(`C1:D${rowCount}`).format.columnWidth = 15;
  sheet.getRange(`E1:H${rowCount}`).format.columnWidth = 14;
  sheet.getRange(`I1:K${rowCount}`).format.columnWidth = 18;
  sheet.getRange(`A1:K${rowCount}`).format.rowHeight = 18;
  sheet.getRange("A1:K1").format.rowHeight = 34;
  sheet.getRange(`A1:K${rowCount}`).format.verticalAlignment = "center";
}

const check = await workbook.inspect({
  kind: "table",
  range: "0.25P充电!A1:K8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 11,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const previewDir = path.join(runDir, "预览");
await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName] of cases) {
  const preview = await workbook.render({
    sheetName,
    range: "A1:K35",
    scale: 1.2,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}
const notesPreview = await workbook.render({
  sheetName: "说明",
  range: "A1:B12",
  scale: 1.2,
  format: "png",
});
await fs.writeFile(
  path.join(previewDir, "说明.png"),
  new Uint8Array(await notesPreview.arrayBuffer()),
);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
