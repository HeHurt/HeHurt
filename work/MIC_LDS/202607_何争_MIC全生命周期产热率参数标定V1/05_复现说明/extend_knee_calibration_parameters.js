const fs = require("fs");

const scriptPath = process.argv[2];
let source = fs.readFileSync(scriptPath, "utf8");

function replaceExact(from, to) {
  if (!source.includes(from)) {
    throw new Error(`Cannot find expected text: ${from}`);
  }
  source = source.replace(from, to);
}

replaceExact(
  '    parser.add_argument("--cracking-rate-scale", type=float, default=1.0)\n',
  '    parser.add_argument("--cracking-rate-scale", type=float, default=1.0)\n'
    + '    parser.add_argument("--lam-scale", type=float, default=1.0)\n'
    + '    parser.add_argument("--sei-scale", type=float, default=1.0)\n',
);
replaceExact(
  "def build_parameter_loader(paris_m: float, reference_dk: float, cracking_rate_scale: float):\n",
  "def build_parameter_loader(\n"
    + "    paris_m: float,\n"
    + "    reference_dk: float,\n"
    + "    cracking_rate_scale: float,\n"
    + "    lam_scale: float,\n"
    + "    sei_scale: float,\n"
    + "):\n",
);
replaceExact(
  '    if paris_m <= 0 or reference_dk <= 0 or cracking_rate_scale <= 0:\n'
    + '        raise ValueError("Paris m, reference dK, and cracking-rate scale must be positive")\n',
  '    if min(paris_m, reference_dk, cracking_rate_scale, lam_scale, sei_scale) <= 0:\n'
    + '        raise ValueError("All calibration parameters must be positive")\n',
);
replaceExact(
  '        values["Negative electrode Paris\' law constant m"] = paris_m\n'
    + '        values["Negative electrode cracking rate"] = calibrated_cracking_rate\n',
  '        values["Negative electrode Paris\' law constant m"] = paris_m\n'
    + '        values["Negative electrode cracking rate"] = calibrated_cracking_rate\n'
    + '        values["Negative electrode LAM constant proportional term [s-1]"] *= lam_scale\n'
    + '        values["SEI kinetic rate constant [m.s-1]"] *= sei_scale\n'
    + '        values["EC diffusivity [m2.s-1]"] *= sei_scale\n',
);
replaceExact(
  "        args.cracking_rate_scale,\n    )\n",
  "        args.cracking_rate_scale,\n"
    + "        args.lam_scale,\n"
    + "        args.sei_scale,\n"
    + "    )\n",
);
replaceExact(
  '        "cracking_rate_scale": args.cracking_rate_scale,\n',
  '        "cracking_rate_scale": args.cracking_rate_scale,\n'
    + '        "lam_scale": args.lam_scale,\n'
    + '        "sei_scale": args.sei_scale,\n',
);

fs.writeFileSync(scriptPath, source, "utf8");
console.log(`Extended calibration parameters: ${scriptPath}`);
