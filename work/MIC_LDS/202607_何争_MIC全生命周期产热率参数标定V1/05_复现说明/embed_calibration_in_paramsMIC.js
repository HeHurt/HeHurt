const fs = require("fs");

const paramsPath = process.argv[2];
const notebookPath = process.argv[3];
const calibrationScriptPath = process.argv[4];

function replaceExact(source, from, to, label) {
  if (!source.includes(from)) {
    throw new Error(`Cannot find ${label}: ${from}`);
  }
  return source.replace(from, to);
}

let paramsSource = fs.readFileSync(paramsPath, "utf8");
paramsSource = replaceExact(
  paramsSource,
  '"Negative electrode LAM constant proportional term [s-1]":2 * 1e-7 * t_factor,',
  '"Negative electrode LAM constant proportional term [s-1]": 7e-8 * t_factor,',
  "MIC LAM parameter",
);
paramsSource = replaceExact(
  paramsSource,
  '"SEI kinetic rate constant [m.s-1]": 4.8e-14 * k_sei * t_factor,',
  '"SEI kinetic rate constant [m.s-1]": 2.4e-14 * k_sei * t_factor,',
  "MIC SEI kinetic parameter",
);
paramsSource = replaceExact(
  paramsSource,
  '"EC diffusivity [m2.s-1]": 3.5e-22 * D_sei * t_factor,',
  '"EC diffusivity [m2.s-1]": 1.75e-22 * D_sei * t_factor,\n'
    + '        "SEI resistivity [Ohm.m]": 2e5,',
  "MIC EC diffusivity parameter",
);
fs.writeFileSync(paramsPath, paramsSource, "utf8");

const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));
const configCell = notebook.cells.find(
  (cell) => cell.cell_type === "code" && (cell.source || []).join("").includes("CALIBRATION = {"),
);
if (!configCell) {
  throw new Error("Cannot find notebook CALIBRATION cell");
}
let configSource = configCell.source.join("");
configSource = replaceExact(configSource, '"sei_scale": 0.50', '"sei_scale": 1.0', "notebook SEI scale");
configSource = replaceExact(configSource, '"lam_scale": 0.35', '"lam_scale": 1.0', "notebook LAM scale");
configSource = replaceExact(
  configSource,
  '"source_run": "mic_lifecycle_calibration/20260730_scan_v2",',
  '"source_run": "mic_lifecycle_calibration/20260730_scan_v2",\n'
    + '    "embedded_in": "paramsMIC.py",',
  "notebook calibration source",
);
configCell.source = configSource.split(/(?<=\n)/);
fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");

let scriptSource = fs.readFileSync(calibrationScriptPath, "utf8");
scriptSource = replaceExact(
  scriptSource,
  '"sei_scale": 0.5,\n                "lam_scale": 0.5,',
  '"sei_scale": 1.0,\n                "lam_scale": 1.0,',
  "smoke candidate",
);
scriptSource = replaceExact(
  scriptSource,
  "for sei_scale in (0.35, 0.5, 0.7)\n        for lam_scale in (0.35, 0.6)",
  "for sei_scale in (0.8, 1.0, 1.2)\n        for lam_scale in (0.8, 1.0, 1.2)",
  "stage-one scan range",
);
scriptSource = replaceExact(
  scriptSource,
  "for resistivity_scale in (2.0, 4.0, 8.0):",
  "for resistivity_scale in (0.8, 1.0, 1.2):",
  "stage-two scan range",
);
fs.writeFileSync(calibrationScriptPath, scriptSource, "utf8");

console.log(`Updated params: ${paramsPath}`);
console.log(`Updated notebook: ${notebookPath}`);
console.log(`Updated calibration script: ${calibrationScriptPath}`);
