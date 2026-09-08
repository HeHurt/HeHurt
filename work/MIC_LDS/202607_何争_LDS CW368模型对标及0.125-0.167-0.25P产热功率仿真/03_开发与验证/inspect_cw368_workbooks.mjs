import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputDir = process.argv[2];
const outputDir = process.argv[3];
await fs.mkdir(outputDir, { recursive: true });

for (const name of ["设计参数.bin", "实测汇总.bin", "00029原始.bin", "00030原始.bin"]) {
  const sourcePath = path.join(inputDir, name);
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
  const overview = await workbook.inspect({
    kind: "workbook,sheet,table,region",
    maxChars: 16000,
    tableMaxRows: 18,
    tableMaxCols: 18,
    tableMaxCellChars: 100,
  });
  await fs.writeFile(
    path.join(outputDir, `${name}.inspect.ndjson`),
    overview.ndjson,
    "utf8",
  );
  const sheetInfo = await workbook.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 8000,
  });
  console.log(`--- ${name} ---`);
  console.log(sheetInfo.ndjson);
}
