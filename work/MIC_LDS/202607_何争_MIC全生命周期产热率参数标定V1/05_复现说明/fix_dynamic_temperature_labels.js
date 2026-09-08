const fs = require("fs");

const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));

function replaceExact(text, from, to) {
  if (!text.includes(from)) {
    throw new Error(`Cannot find expected text: ${from}`);
  }
  return text.replace(from, to);
}

const runHeading = notebook.cells.find(
  (cell) => cell.cell_type === "markdown"
    && (cell.source || []).join("").includes("## 2. 运行三温度、两接触电阻案例"),
);
if (runHeading) {
  runHeading.source = ["## 2. 运行配置温度与两接触电阻案例\n"];
}

const excelCell = notebook.cells.find(
  (cell) => cell.cell_type === "code"
    && (cell.source || []).join("").includes("def write_summary_matrix"),
);
if (!excelCell) {
  throw new Error("Cannot find Excel export cell");
}
let excelSource = excelCell.source.join("");
excelSource = replaceExact(
  excelSource,
  '    title = (\n        f"MIC 1175Ah 25℃/35℃/45℃不同温度下"\n',
  '    temperature_label = "/".join(f"{value:g}℃" for value in AGING_TEMPERATURES_C)\n'
    + '    title = (\n        f"MIC 1175Ah {temperature_label}下"\n',
);
excelSource = replaceExact(
  excelSource,
  '    workbook = OUTPUT_ROOT / (\n        f"{CELL_NAME}_25-35-45℃_0.25P统一老化_多倍率产热_"\n',
  '    temperature_tag = "-".join(f"{value:g}" for value in AGING_TEMPERATURES_C)\n'
    + '    workbook = OUTPUT_ROOT / (\n'
    + '        f"{CELL_NAME}_{temperature_tag}℃_0.25P统一老化_多倍率产热_"\n',
);
excelCell.source = excelSource.split(/(?<=\n)/);

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
console.log(`Updated temperature labels: ${notebookPath}`);
