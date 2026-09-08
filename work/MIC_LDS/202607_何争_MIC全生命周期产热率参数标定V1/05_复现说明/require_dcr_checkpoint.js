const fs = require("fs");

const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));

function findCell(marker) {
  const cell = notebook.cells.find(
    (item) => item.cell_type === "code" && (item.source || []).join("").includes(marker),
  );
  if (!cell) {
    throw new Error(`Cannot find cell containing: ${marker}`);
  }
  return cell;
}

function replaceExact(text, from, to) {
  if (!text.includes(from)) {
    throw new Error(`Cannot find expected text: ${from}`);
  }
  return text.replace(from, to);
}

const configCell = findCell("DCR_PULSE_DURATION_S = 30.0");
let configSource = configCell.source.join("");
configSource = replaceExact(
  configSource,
  "DCR_PULSE_DURATION_S = 30.0\n",
  "DCR_PULSE_DURATION_S = 30.0\nREQUIRE_DCR_DIAGNOSTICS = True\n",
);
configCell.source = configSource.split(/(?<=\n)/);

const runCell = findCell("checkpoint_status = json.loads");
let runSource = runCell.source.join("");
runSource = replaceExact(
  runSource,
  '            if checkpoint_reusable:\n                print(\n',
  [
    '            dcr_checkpoint_required = CHECKPOINT_DIR / (',
    '                f"R{resistance_mohm:.5f}mOhm_T{temperature_c:g}C_capacity_dcr_actual.csv"',
    '            )',
    '            checkpoint_reusable = checkpoint_reusable and (',
    '                not REQUIRE_DCR_DIAGNOSTICS or dcr_checkpoint_required.exists()',
    '            )',
    '            if checkpoint_reusable:',
    '                print(',
    '',
  ].join("\n"),
);
runCell.source = runSource.split(/(?<=\n)/);

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
console.log(`Updated checkpoint reuse rule: ${notebookPath}`);
