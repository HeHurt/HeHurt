---
applyTo: "**/*.java"
description: COMSOL Multiphysics 6.4 LFP/Graphite battery model Java workflow
---

# COMSOL Java Battery Modeling Instructions

You are helping with COMSOL 6.4 Li-ion battery models (LFP/Graphite chemistry).
Each .java file in this repo is exported from an encrypted .mph file.
You CANNOT read the .mph; only the .java is your source of truth.

## Configuration

- **COMSOL Version**: 6.4 (NOT 5.x — API differs)
- **Chemistry**: LFP cathode / Graphite anode
- **Geometry**: 1D P2D, possibly with 3D thermal coupling
- **Operating Modes**: CC (constant current) AND CP (constant power)
- **No aging models** (no SEI/Li-plating/mechanical stress)

## Mandatory 5-Step Workflow

When asked to modify a model, execute these steps **in order**.
Do NOT skip Step 2-3 and jump to coding.

### Step 1 (already done by user)
The user has exported .mph → .java via COMSOL Desktop's "Save As Model File for Java".

### Step 2: Build Mental Map BEFORE Coding
Grep the source file to locate (in this order):
1. `Model model = ModelUtil.create` → model variable name (usually `model`)
2. `model.component(` → components (comp1; possibly comp2 for 3D thermal)
3. `.geom(` → geometries (geom1 for 1D, geom2 for 3D)
4. `model.param().set` → existing parameters and naming convention
5. `physics().create` → physics interfaces (expect `liion` and `ht`)
6. `multiphysics().create` → couplings (expect `ElectrochemicalHeating`)
7. `extrudedim` / `genext` / `aveop` → multiscale 1D-3D coupling indicators
8. `model.study(.*).create` → existing studies
9. `feature("param")` → existing parameter sweeps
10. `ge1` / `GlobalEquations` → CP (constant power) mode indicator
11. `result().numerical` → postprocessing conventions

Then summarize in 1-2 sentences:
> "This is a [dimension] [chemistry] model with [physics list]. Main study is
> [transient/stationary]. Key parameters: [list]. Outputs: [list]."

### Step 3: Plan Before Generating Code
List 4 items explicitly to the user, ASK FOR CONFIRMATION:
1. **What to change** — which tags will be affected
2. **What to preserve** — explicit list of unchanged sections
3. **What to add** — new tag names (grep existing tags first, increment number)
4. **Side effects** — broken dependencies? (e.g., changing geom tag breaks physics)

### Step 4: Generate Snippet (NOT Full File)
Strict header format (use this verbatim):

```
**插入位置 (Insert location)**: <section name or line range in source>
**新建tags (New tags)**: <list of new tags this snippet creates>
**依赖项 (Dependencies)**: <tags assumed to exist in source>
**风险点 (Risks)**: <potential conflicts: tag collision, units, API version>

```java
// code snippet
```

**粘贴说明 (Paste instructions)**: <how to insert, any prerequisite COMSOL ops>
```

### Step 5 (user does this)
User pastes snippet, runs `comsolcompile`, verifies in COMSOL Desktop.

## Hard Rules (Absolute)

1. **NEVER invent tag names**. Always grep source first:
   `grep -oE 'model\.study\("std[0-9]+"\)\.create' source.java | sort -u`
   Then pick the next sequential number.

2. **NEVER guess COMSOL API method names**. Reference existing usage in the file.

3. **ALWAYS use COMSOL 6.4 syntax** (not 5.x):
   - `model.physics().create("liion", "LithiumIonBattery", ...)` ← NOT `"liionbattery"`
   - `physics("liion").prop("ModelInputs").set(...)` ← NOT direct `set` for inputs
   - `Eeq` (equilibrium potential) ← NOT `Ee`
   - `model.study("std1").feature("param")` for sweep ← NOT `model.batch()`

4. **NEVER use `ElectromagneticHeating` for battery thermal coupling**.
   Use `ElectrochemicalHeating`:
   ```java
   model.component("comp1").multiphysics().create("emh1", "ElectrochemicalHeating", -1);
   ```
   `ElectromagneticHeating` expects Electric Currents interface (busbar Joule heating),
   not `liion`. Using it for batteries silently produces wrong physics.

5. **CP (constant power) is NOT a native COMSOL feature**. Implement via Global Equations:
   ```java
   model.component("comp1").physics().create("ge", "GlobalEquations", "geom1");
   model.component("comp1").physics("ge").feature("ge1")
     .setIndex("name", "I_app_var", 0, 0)
     .setIndex("equation", "I_app_var*liion.E_cell-P_app", 0, 0)
     .setIndex("initialValueU", "P_app/3.2[V]", 0, 0)
     .setIndex("SIUnit", "A", 0, 0);
   // Then use I_app_var in ecs1.I_el
   ```
   ALWAYS add Stop Condition for CP to prevent low-voltage divergence:
   ```java
   model.study("std1").feature("time").set("usestopcond", true);
   model.study("std1").feature("time").set("stopcond",
     "(comp1.liion.E_cell<V_min)||(comp1.liion.E_cell>V_max)");
   ```

6. **All numeric values use bracket units**: `"280[A]"`, `"298.15[K]"`, `"560[W]"`.

7. **Follow source file's comment language and style**.

## LFP/Graphite Parameter Sanity Check

Reject (or warn) on:
- `V_max` > 3.7V or `V_min` < 2.4V (LFP windows: typically 2.5-3.65V)
- `Ds_pos` > 1e-15 m²/s (LFP solid diffusion is 2-3 orders SLOWER than NCM)
- `rp_pos` > 2e-6 m (LFP particles 0.1-1µm, MUCH smaller than NCM)
- Suggesting polynomial OCV fit (LFP needs interpolation table or Sphan-Newman exp form)
- `csmax_pos` near NCM value (~49000); LFP is **22806 mol/m³**

## Multi-Component (1D + 3D) Models

If grep shows `model.component("comp2")` or `extrudedim`/`genext`/`aveop`:
- comp1 = 1D electrochemistry (P2D)
- comp2 = 3D thermal field
- Cross-component references use `comp1.aveop1(liion.Qh)` syntax
- Use `ElectrochemicalHeating` coupling
- Modify electrochemistry params on `comp1`, thermal boundary conditions on `comp2`

## When in Doubt — Stop and Ask

If you cannot confirm a tag/parameter exists in source, STOP. Ask user to share that
section. Do not guess. Cost of asking << cost of guessing (wrong tag = compile failure;
invented method = immediate Java error).

## Output Mode: Snippets Only

Default output: code snippets with 4-section header. NEVER output a full modified .java
unless user explicitly asks ("生成完整文件" / "give me the complete file").

## Reference Documents (Load on Demand)

Tell the user to share content from these refs if the task needs:
- `liion_lfp_reference.md` — LFP/Gr params + CP Global Equation full template
- `multiscale_1d_3d_coupling.md` — for models with comp2 (3D thermal)
- `parameter_sweep_patterns.md` — for parameter sweeps + CSV export
- `matlab_livelink_patterns.md` — for MATLAB-driven sweeps
- `comsol_64_api_notes.md` — for 6.4-specific API differences
- `team_workflow.md` — for git/repo/naming conventions
