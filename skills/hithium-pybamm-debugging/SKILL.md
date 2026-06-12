---
name: hithium-pybamm-debugging
description: Use for Hithium BatteryProject / PyBaMM debugging and benchmarking tasks: notebook errors, aging-cycle anomalies, capacity-retention jumps, heat-generation or swelling postprocessing, electrolyte dry-out options, experiment-vs-simulation comparison, and changes that touch BatteryProject/src, params, or Hithium study notebooks.
---

# Hithium PyBaMM Debugging

Use this skill when the user asks why a BatteryProject/PyBaMM result is wrong, asks to fix a notebook error, or asks to turn an ad hoc analysis into a reusable Hithium workflow.

## Boundaries

- Covers: `BatteryProject/src/`, `params/`, Hithium notebooks/scripts, PyBaMM DFN aging workflows, experiment comparison, Excel export from simulation results.
- Does not cover: COMSOL `.java` or `.mph` workflows; use `comsol-java-battery-modeling`.
- Does not cover patent drafting; use `battery-patent-disclosure`.
- Prefer project AGENTS rules over this file if there is a conflict.

## Required Context

Before changing files, read the nearest applicable harness file:

- Root: `D:\Users\hez\Desktop\hithium\AGENTS.md`
- Core code: `BatteryProject/src/AGENTS.md`
- Parameters: `params/AGENTS.md`
- Notebook area: nearest notebook workspace `AGENTS.md`
- Plans/specs: `.plans/AGENTS.md` for large scans or multi-file design work

If a file appears encrypted (`%TSD-Header-###%` or garbled content), do not spend time on encoding guesses. Use the project-approved Python/read bridge path or ask for the file through the editor context.

## Triage Workflow

1. Classify the issue:
   - Import/runtime error: missing export, stale symbol, wrong working directory, missing package.
   - Notebook state error: missing `sol_list`, stale `importlib.reload()`, cells run out of order.
   - Model anomaly: capacity retention, voltage, DCR, heat, swelling, dry-out, plating, SEI/LAM/crack outputs.
   - Data comparison issue: raw experiment parsing, alignment, correction factors, RRMSE/metric calculation.
2. Build a minimal reproduction:
   - Use one temperature, one SOC or one current/power point, and one or a few cycles.
   - Keep `var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}` unless the task proves mesh sensitivity.
   - Do not start with a full matrix sweep.
3. Check parameter contamination:
   - Every temperature switch must create a fresh `pybamm.ParameterValues("OKane2022")`.
   - Then call the Hithium `params.update()` path for that temperature.
   - Do not reuse a mutated `ParameterValues` across temperatures or cells.
4. For notebook fixes:
   - After modifying `BatteryProject/src/`, notebook code must `importlib.reload()` the changed module and rebind imported symbols.
   - Prefer moving reusable logic into `src/`; do not define core functions only inside a notebook.
   - Make state-producing cells explicit (`sol_list`, labels, metrics tables) so later analysis cells are rerunnable.
5. For aging/result anomalies:
   - Compare raw model outputs before judging plotted postprocessing.
   - Separate mechanism terms: SEI, LAM, crack, plating, porosity, lithium inventory, heat terms, thickness/swelling where available.
   - State whether the likely cause is model physics, parameter values, experiment protocol, solver settings, or postprocessing.

## Implementation Rules

- Keep changes small and local. Avoid refactoring unrelated notebooks or legacy files.
- Legacy files listed in root AGENTS are read-only for reference; new code goes under `BatteryProject/src/`.
- For parameter files, preserve `get_hithium_params(t_factor, temperature)` and verify `"Nominal cell capacity [A.h]"` exists.
- When adding a new src function, update the module export/import path expected by `easy_imports.py` or caller notebooks.
- For manual correction factors such as `CW362*0.99`, prefer a named mapping/config and retain both raw and corrected outputs.

## Verification

After editing `BatteryProject/src/`:

```powershell
python -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503
python -m pytest BatteryProject/tests/ -q
```

If the change affects simulation behavior, also run a smoke case in the relevant notebook/script with minimal configuration and report the exact cell/script used.

After editing `params/`:

```powershell
python - <<'PY'
from params.paramsMIC import get_hithium_params
p = get_hithium_params(1, 298.15)
assert "Nominal cell capacity [A.h]" in p
print("params smoke ok")
PY
```

Adjust the import to the parameter file actually modified.

## Output Shape

Return:

- Root cause or strongest current hypothesis.
- Files changed and why.
- Verification run and result.
- Any remaining risk, especially if a full simulation was skipped.
