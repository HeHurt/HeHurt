const fs = require("fs");

const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));

function replaceInCell(marker, replacements) {
  const cell = notebook.cells.find(
    (item) => item.cell_type === "code" && (item.source || []).join("").includes(marker),
  );
  if (!cell) {
    throw new Error(`Cannot find cell containing: ${marker}`);
  }
  let source = cell.source.join("");
  for (const [from, to] of replacements) {
    if (!source.includes(from)) {
      throw new Error(`Cannot find expected notebook text: ${from}`);
    }
    source = source.replace(from, to);
  }
  cell.source = source.split(/(?<=\n)/);
}

replaceInCell("import json", [
  ["import json\n", "import hashlib\nimport json\n"],
]);

replaceInCell('RUN_MODE = "study"', [
  ["AGING_TEMPERATURES_C = (25.0, 35.0, 45.0)", "AGING_TEMPERATURES_C = (25.0,)"],
  [
    '    / "20260730_params_v2"\n',
    '    / "20260730_calibrated_capacity_dcr_v1"\n',
  ],
  [
    'MODEL_OPTIONS = dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)\n',
    [
      'CALIBRATION = {',
      '    "sei_scale": 0.50,',
      '    "lam_scale": 0.35,',
      '    "sei_resistivity_scale": 1.0,',
      '    "source_run": "mic_lifecycle_calibration/20260730_scan_v2",',
      '}',
      'PARAMETER_FINGERPRINT = hashlib.sha256(',
      '    json.dumps(CALIBRATION, sort_keys=True).encode("utf-8")',
      ').hexdigest()[:12]',
      '',
      'MODEL_OPTIONS = dict(FULL_PULSE_LIFECYCLE_MODEL_OPTIONS)',
      '',
    ].join("\n"),
  ],
]);

replaceInCell("base_get_hithium_params = params_module.get_hithium_params", [
  [
    "calibrated_base_loader = build_calibrated_parameter_loader(\n    base_get_hithium_params,\n",
    [
      "def capacity_dcr_calibrated_loader(t_factor=1, temperature=298.15):",
      "    values = base_get_hithium_params(t_factor, temperature=temperature)",
      '    values["EC diffusivity [m2.s-1]"] *= CALIBRATION["sei_scale"]',
      '    values["SEI kinetic rate constant [m.s-1]"] *= CALIBRATION["sei_scale"]',
      '    values["Negative electrode LAM constant proportional term [s-1]"] *= CALIBRATION["lam_scale"]',
      '    values["SEI resistivity [Ohm.m]"] = 200_000.0 * CALIBRATION["sei_resistivity_scale"]',
      "    return values",
      "",
      "calibrated_base_loader = build_calibrated_parameter_loader(",
      "    capacity_dcr_calibrated_loader,",
      "",
    ].join("\n"),
  ],
  [
    '        "solver_root_tol": bundle.get("solver_root_tol", 1e-6),\n',
    '        "solver_root_tol": bundle.get("solver_root_tol", 1e-6),\n'
      + '        "parameter_fingerprint": PARAMETER_FINGERPRINT,\n',
  ],
  [
    '    if bundle.get("run_status") in {"completed", "target_not_reached"}:\n',
    '    if bundle.get("parameter_fingerprint") != PARAMETER_FINGERPRINT:\n'
      + '        return False\n'
      + '    if bundle.get("run_status") in {"completed", "target_not_reached"}:\n',
  ],
  [
    '            checkpoint_reusable = checkpoint_status.get("run_status") in {"completed", "target_not_reached"}\n',
    '            checkpoint_reusable = (\n'
      + '                checkpoint_status.get("parameter_fingerprint") == PARAMETER_FINGERPRINT\n'
      + '                and checkpoint_status.get("run_status") in {"completed", "target_not_reached"}\n'
      + '            )\n',
  ],
  [
    '        bundle["solver_root_method"] = SOLVER_ROOT_METHOD\n',
    '        bundle["parameter_fingerprint"] = PARAMETER_FINGERPRINT\n'
      + '        bundle["solver_root_method"] = SOLVER_ROOT_METHOD\n',
  ],
]);

fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");
console.log(`Patched and saved: ${notebookPath}`);
