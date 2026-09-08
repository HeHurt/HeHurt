import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputJsonPath = process.argv[2];
const outputXlsxPath = process.argv[3];
const previewDir = process.argv[4] || null;

if (!inputJsonPath || !outputXlsxPath) {
  throw new Error(
    "Usage: node build_cw501_pulse_map_excel.mjs input.json output.xlsx [previewDir]",
  );
}

const payload = JSON.parse(await fs.readFile(inputJsonPath, "utf8"));
const rows = payload.rows || [];
if (rows.length === 0) {
  throw new Error("No peak-current rows were provided");
}

const durations = [10, 30, 60];
const temperatures = [-30, -20, -10, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];
const socValues = Array.from({ length: 21 }, (_, index) => 100 - index * 5);
const metricBlocks = [
  { startCol: 0, key: "peak_current_a", label: "电流(A)", numberFormat: "0" },
  { startCol: 18, key: "pulse_power_w", label: "功率(W)", numberFormat: "0" },
  { startCol: 36, key: "pulse_dcr_mohm", label: "内阻(mΩ)", numberFormat: "0.00" },
];
const colorScale = {
  colors: ["#63BE7B", "#FFEB84", "#F8696B"],
  thresholds: ["min", "50%", "max"],
};

function keyFor(direction, duration, temperature, soc) {
  return `${direction}|${duration}|${Number(temperature)}|${Number(soc)}`;
}

const rowIndex = new Map();
for (const row of rows) {
  rowIndex.set(
    keyFor(row.direction, row.duration_s, row.temperature_c, row.soc_pct),
    row,
  );
}

function matrixFor(direction, duration, metricKey) {
  return socValues.map((soc) => [
    soc,
    ...temperatures.map((temperature) => {
      const row = rowIndex.get(keyFor(direction, duration, temperature, soc));
      const value = row?.[metricKey];
      return Number.isFinite(value) ? value : null;
    }),
  ]);
}

function styleBlock(sheet, startCol, titleRow, headerRow, dataStartRow, metric) {
  const fullRange = sheet.getRangeByIndexes(titleRow, startCol, 23, 16);
  fullRange.format = {
    font: { name: "Calibri", size: 10, color: "#000000" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: "#000000" },
  };
  fullRange.format.rowHeight = 14.25;

  const titleRange = sheet.getRangeByIndexes(titleRow, startCol, 1, 16);
  titleRange.merge();
  titleRange.format = {
    font: { name: "Calibri", size: 10, color: "#000000" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: "#000000" },
  };

  const headerRange = sheet.getRangeByIndexes(headerRow, startCol, 1, 16);
  headerRange.format = {
    fill: "#BFBFBF",
    font: { name: "Calibri", size: 10, color: "#000000" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "all", style: "medium", color: "#000000" },
  };

  const socRange = sheet.getRangeByIndexes(dataStartRow, startCol, 21, 1);
  socRange.format = {
    fill: "#BFBFBF",
    font: { name: "Calibri", size: 10, color: "#000000" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "all", style: "medium", color: "#000000" },
    numberFormat: "0",
  };

  const dataRange = sheet.getRangeByIndexes(dataStartRow, startCol + 1, 21, 15);
  dataRange.format = {
    font: { name: "Calibri", size: 10, color: "#000000" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "all", style: "medium", color: "#000000" },
    numberFormat: metric.numberFormat,
  };
  dataRange.conditionalFormats.add("colorScale", colorScale);
}

const workbook = Workbook.create();

for (const duration of durations) {
  const sheet = workbook.worksheets.add(`${duration}s`);
  sheet.getRange("A1:AZ49").format.columnWidth = 13;

  for (const metric of metricBlocks) {
    const dischargeTitle = sheet.getRangeByIndexes(2, metric.startCol, 1, 16);
    dischargeTitle.values = [[`${duration}s脉冲放电${metric.label}`]];
    const dischargeHeader = sheet.getRangeByIndexes(3, metric.startCol, 1, 16);
    dischargeHeader.values = [["SOC/温度", ...temperatures]];
    const dischargeData = sheet.getRangeByIndexes(4, metric.startCol, 21, 16);
    dischargeData.values = matrixFor("discharge", duration, metric.key);
    styleBlock(sheet, metric.startCol, 2, 3, 4, metric);

    const chargeTitle = sheet.getRangeByIndexes(26, metric.startCol, 1, 16);
    chargeTitle.values = [[`${duration}s脉冲充电${metric.label}`]];
    const chargeHeader = sheet.getRangeByIndexes(27, metric.startCol, 1, 16);
    chargeHeader.values = [["SOC/温度", ...temperatures]];
    const chargeData = sheet.getRangeByIndexes(28, metric.startCol, 21, 16);
    chargeData.values = matrixFor("charge", duration, metric.key);
    styleBlock(sheet, metric.startCol, 26, 27, 28, metric);
  }
}

const keyRange = await workbook.inspect({
  kind: "table",
  range: "10s!A3:P10",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 16,
  maxChars: 6000,
});
console.log(keyRange.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
if (errors.ndjson.includes('"kind":"match"')) {
  throw new Error(`Formula error found: ${errors.ndjson}`);
}

if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const duration of durations) {
    const preview = await workbook.render({
      sheetName: `${duration}s`,
      autoCrop: "all",
      scale: 1.2,
      format: "png",
    });
    await fs.writeFile(
      path.join(previewDir, `${duration}s.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
}

await fs.mkdir(path.dirname(outputXlsxPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputXlsxPath);
console.log(outputXlsxPath);
