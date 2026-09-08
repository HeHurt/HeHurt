const fs = require("fs");

const paramsPath = process.argv[2];
const notebookPath = process.argv[3];

function replaceExact(source, from, to, label) {
  if (!source.includes(from)) {
    throw new Error(`Cannot find ${label}: ${from}`);
  }
  return source.replace(from, to);
}

let paramsSource = fs.readFileSync(paramsPath, "utf8");
paramsSource = replaceExact(
  paramsSource,
  '"Negative electrode LAM constant proportional term [s-1]": 7e-8 * t_factor,',
  '"Negative electrode LAM constant proportional term [s-1]": 2.058e-7 * t_factor,',
  "MIC LAM constant",
);
paramsSource = replaceExact(
  paramsSource,
  '"SEI kinetic rate constant [m.s-1]": 2.4e-14 * k_sei * t_factor,',
  '"SEI kinetic rate constant [m.s-1]": 2.16e-14 * k_sei * t_factor,',
  "MIC SEI kinetic constant",
);
paramsSource = replaceExact(
  paramsSource,
  '"EC diffusivity [m2.s-1]": 1.75e-22 * D_sei * t_factor,',
  '"EC diffusivity [m2.s-1]": 1.575e-22 * D_sei * t_factor,',
  "MIC EC diffusivity",
);
fs.writeFileSync(paramsPath, paramsSource, "utf8");

const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));
const configCell = notebook.cells.find(
  (cell) => cell.cell_type === "code"
    && (cell.source || []).join("").includes("CALIBRATION = {"),
);
if (!configCell) {
  throw new Error("Cannot find Notebook CALIBRATION cell");
}
let notebookSource = configCell.source.join("");
notebookSource = replaceExact(
  notebookSource,
  '    "embedded_in": "paramsMIC.py",',
  '    "embedded_in": "paramsMIC.py",\n'
    + '    "fixed_parameter_knee_version": "lam2p94_sei0p9_af50_15k",',
  "Notebook parameter fingerprint version",
);
configCell.source = notebookSource.split(/(?<=\n)/);
fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");

console.log(`Updated params: ${paramsPath}`);
console.log(`Updated Notebook fingerprint: ${notebookPath}`);
