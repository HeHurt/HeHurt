# MPH Runtime Workflow

This reference covers targeted inspection, comparison, save-as editing, saved-model verification, and minimal solve checks for existing `.mph` files. The helper is `scripts/mph_tool.py`.

## Contents

1. Execution model
2. Audit
3. Diff
4. Patch and reload verification
5. Verify only
6. Minimal smoke solve
7. Configuration rules
8. Output and failure handling

## 1. Execution model

Only `diff` runs with ordinary Python. All actions that load a model must execute inside a healthy sim-cli COMSOL session because they import COMSOL's `ModelUtil`.

Check for an existing session first:

```powershell
uv run sim --json ps
```

Connect only when no healthy COMSOL session exists:

```powershell
uv run sim --json --no-interactive connect --solver comsol --ui-mode no_gui
```

Put one action in a UTF-8 JSON config. For `sim exec --file`, copy the active config to the workspace-local `.sim\mph_tool_config.json`; the sim-cli execution namespace does not forward a newly set shell environment variable and identifies itself as `builtins` rather than `__main__`:

```powershell
Copy-Item -LiteralPath 'D:\work\audit.json' -Destination '.sim\mph_tool_config.json'
uv run sim --json --session <session-id> --no-interactive exec --file 'C:\HithiumSSD\hithium\skills\comsol-java-battery-modeling\scripts\mph_tool.py'
```

Keep the original config in the task run directory as the durable record. `.sim\mph_tool_config.json` is only the active workspace pointer and should contain one task at a time. When running the tool directly with normal Python, use `--config` or the `MPH_TOOL_CONFIG` environment variable.

Keep source models unchanged. A `patch` config must name a different output path.

## 2. Audit

Use a narrow audit first. `include_all_properties` is intentionally false by default because full COMSOL property dumps are slow and noisy.

```json
{
  "action": "audit",
  "models": [
    {
      "path": "D:\\models\\charge.mph",
      "tag": "charge_audit",
      "parameters": ["A_cell", "L_all", "R_contact"],
      "variables": [
        {"component": "comp1", "group": "var1", "names": ["I_app", "P_total_gen"]}
      ],
      "features": [
        {"component": "comp1", "physics": "liion", "feature": "cd1", "properties": ["I0"]},
        {"component": "comp2", "physics": "ht", "feature": "hs1", "properties": ["Q0"]}
      ]
    }
  ],
  "output": "D:\\work\\charge_audit.json"
}
```

The audit always records model label, components, physics trees, studies, results, probes, and coupling tags. Requested parameter, variable, and feature-property values are added under `targeted`.

Large models are loaded and removed sequentially. Do not place two large `.mph` files in memory together merely to compare them.

## 3. Diff

Audit each model separately, then compare the JSON files offline:

```json
{
  "action": "diff",
  "left": "D:\\work\\charge_audit.json",
  "right": "D:\\work\\discharge_audit.json",
  "ignore_paths": ["models.0.path", "models.0.label"],
  "output": "D:\\work\\charge_vs_discharge.json"
}
```

Run without COMSOL:

```powershell
python scripts\mph_tool.py --config D:\work\diff.json
```

The result contains recursive `added`, `removed`, and `changed` paths. Use targeted audits so the diff reflects physics-relevant differences instead of model metadata noise.

## 4. Patch and reload verification

A patch is a short list of explicit operations. The helper saves to `output_model`, unloads it, reloads the saved file, and evaluates `assertions` against the reloaded model.

```json
{
  "action": "patch",
  "source": "D:\\models\\charge.mph",
  "output_model": "D:\\runs\\charge_fixed.mph",
  "operations": [
    {"op": "set_param", "name": "R_contact", "expr": "0.02[mohm]"},
    {"op": "set_variable", "component": "comp1", "group": "var1", "name": "P_contact", "expr": "I_app^2*R_contact"},
    {"op": "set_feature", "component": "comp2", "physics": "ht", "feature": "hs1", "property": "Q0", "value": "P_p2d/V_cell"}
  ],
  "assertions": [
    {"kind": "param_expr", "name": "R_contact", "equals": "0.02[mohm]"},
    {"kind": "variable_expr", "component": "comp1", "group": "var1", "name": "P_contact", "equals": "I_app^2*R_contact"},
    {"kind": "feature_property", "component": "comp2", "physics": "ht", "feature": "hs1", "property": "Q0", "equals": "P_p2d/V_cell"}
  ],
  "output": "D:\\runs\\patch_result.json"
}
```

Supported operations:

- `set_param`
- `set_variable`
- `set_feature`
- `create_heat_source`
- `create_probe`

For creation operations, use tags and selections confirmed by an audit or an exported Java model. Never guess domain or boundary IDs.

## 5. Verify only

Use `verify` to prove existing saved content without changing the model:

```json
{
  "action": "verify",
  "source": "D:\\runs\\charge_fixed.mph",
  "assertions": [
    {"kind": "param_expr", "name": "R_contact", "equals": "0.02[mohm]"},
    {"kind": "feature_exists", "component": "comp2", "physics": "ht", "feature": "hs1"}
  ],
  "output": "D:\\runs\\verify_result.json"
}
```

Supported assertions are `param_expr`, `variable_expr`, `feature_property`, `probe_expr`, and `feature_exists`. Expression comparisons are exact after surrounding whitespace is removed; use the exact saved COMSOL expression.

## 6. Minimal smoke solve

`smoke` changes study settings only in memory, runs the selected study, evaluates named expressions, records results, and never saves the modified study back to the model.

```json
{
  "action": "smoke",
  "source": "D:\\runs\\charge_fixed.mph",
  "study": "std1",
  "overrides": [
    {"study_feature": "param1", "property": "plistarr", "value": ["25", "25"]},
    {"study_feature": "time", "property": "tlist", "value": "range(0,10,60)"}
  ],
  "metrics": [
    {"name": "P_total_gen", "expression": "P_total_gen", "unit": "W"},
    {"name": "P_total_to_ht", "expression": "P_total_to_ht", "unit": "W"},
    {"name": "energy_balance_rel", "expression": "abs(P_total_to_ht-P_total_gen)/max(abs(P_total_gen),1e-9)"}
  ],
  "output": "D:\\runs\\smoke_result.json"
}
```

Use the smallest parameter slice and time range that can detect a broken expression, invalid selection, or solver regression. A successful smoke case is not evidence that a full production sweep ran.

## 7. Configuration rules

- Paths must be absolute for session execution.
- `patch.output_model` must differ from `patch.source` after path resolution.
- Physical parameters should carry explicit units.
- Tags in operations must already exist unless the operation explicitly creates the feature.
- Use `value` arrays only for COMSOL properties known to accept string arrays.
- Record contact heat, P2D heat, metal heat, mapped heat, and balance residual as separate metrics when auditing electrothermal conservation.

## 8. Output and failure handling

Each action writes its JSON result atomically enough for task use and also prints the same result between `MPH_TOOL_RESULT_BEGIN` and `MPH_TOOL_RESULT_END`. Prefer the output file over scraping terminal text.

On failure:

1. Keep the source and any previously successful output.
2. Read the exception and identify whether it is a tag, property, selection, unit, solver, license, or session problem.
3. Narrow the audit to the failing node.
4. Change only the justified operation or smoke override.
5. Append the failure and repair to the task's `logs/lessons_learned.md` when working under the standard COMSOL project workflow.
