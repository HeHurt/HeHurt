import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const ROOT = 'C:/Users/hez/AppData/Local/Temp/codex-hithium/calendar-excel-fix-20260806';
const INPUT = `${ROOT}/input.xlsx`;
const OUTPUT = `${ROOT}/587Ah_0to50C_50SOC_calendar_aging_14months_fixed.xlsx`;
const MATRIX_SHEETS = ['Retention_pct', 'Recovery_pct', 'Irreversible_loss_pct'];

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(INPUT));
await fs.mkdir(`${ROOT}/renders`, { recursive: true });

const before = {};
for (const sheetName of MATRIX_SHEETS) {
  const sheet = workbook.worksheets.getItem(sheetName);
  before[sheetName] = {
    headers: sheet.getRange('A1:D2').values,
    formulas: sheet.getRange('B2:D4').formulas,
    values: sheet.getRange('B2:D4').values,
  };
}
await fs.writeFile(`${ROOT}/before.json`, JSON.stringify(before, null, 2), 'utf8');

const monthNumbers = [Array.from({ length: 14 }, (_, index) => index + 1)];
for (const sheetName of MATRIX_SHEETS) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const header = sheet.getRange('B1:O1');
  header.values = monthNumbers;
  header.format.numberFormat = '"Month "0';
}

const after = {};
for (const sheetName of MATRIX_SHEETS) {
  const sheet = workbook.worksheets.getItem(sheetName);
  after[sheetName] = {
    headers: sheet.getRange('A1:D2').values,
    formulas: sheet.getRange('B2:D4').formulas,
    values: sheet.getRange('B2:D4').values,
  };
  const preview = await workbook.render({
    sheetName,
    range: 'A1:O12',
    scale: 1.5,
    format: 'png',
  });
  await fs.writeFile(
    `${ROOT}/renders/${sheetName}.png`,
    new Uint8Array(await preview.arrayBuffer()),
  );
}
await fs.writeFile(`${ROOT}/after.json`, JSON.stringify(after, null, 2), 'utf8');

const errors = await workbook.inspect({
  kind: 'match',
  searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',
  options: { useRegex: true, maxResults: 300 },
  summary: 'final formula error scan',
});
await fs.writeFile(`${ROOT}/formula-errors.ndjson`, errors.ndjson, 'utf8');

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT);
console.log(OUTPUT);
