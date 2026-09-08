import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile } from "@oai/artifact-tool";

const dir = "D:/Users/hez/Desktop/hithium/scratch/arc314_excel_read";
const files = (await fs.readdir(dir)).filter((name) => name.endsWith(".xlsx.b64"));

for (const name of files) {
  const encoded = await fs.readFile(path.join(dir, name), "utf8");
  const bytes = Buffer.from(encoded, "base64");
  const arrayBuffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const workbook = await SpreadsheetFile.importXlsx(arrayBuffer);
  console.log(`\n### ${name.replace(/\.b64$/, "")}`);
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 30000,
    tableMaxRows: 40,
    tableMaxCols: 20,
    tableMaxCellChars: 160,
  });
  console.log(summary.ndjson);

  for (const sheet of workbook.worksheets.items) {
    const render = await workbook.render({
      sheetName: sheet.name,
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
    const safeName = sheet.name.replace(/[<>:"/\\|?*]/g, "_");
    await fs.writeFile(
      path.join(dir, `${name.replace(/\.xlsx\.b64$/, "")}_${safeName}.png`),
      new Uint8Array(await render.arrayBuffer()),
    );
  }
}
