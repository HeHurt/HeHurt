import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const files = process.argv.slice(2);

for (const file of files) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(file));
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table,region",
    maxChars: 24000,
    tableMaxRows: 20,
    tableMaxCols: 16,
    tableMaxCellChars: 120,
  });
  console.log(JSON.stringify({ file, summary: summary.ndjson }));

  for (const sheet of workbook.worksheets.items) {
    const used = sheet.getUsedRange();
    if (!used) continue;
    const detail = await workbook.inspect({
      kind: "table",
      sheetId: sheet.name,
      range: used.address,
      include: "values,formulas",
      maxChars: 100000,
      tableMaxRows: 300,
      tableMaxCols: 80,
      tableMaxCellChars: 160,
    });
    console.log(JSON.stringify({
      file,
      sheet: sheet.name,
      usedRange: used.address,
      detail: detail.ndjson,
    }));
  }
}
