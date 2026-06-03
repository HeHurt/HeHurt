---
applyTo: "**/*.java"
description: "COMSOL Multiphysics 6.4 battery model Java workflow for exported Li-ion models, including liion, ht, electrochemical-thermal coupling, CC/CP operation, and parameter sweeps."
---

# COMSOL Java Battery Modeling Instructions

You are working with COMSOL Multiphysics 6.4 battery models exported as `.java` files.
Treat the `.java` file as the only trustworthy source of model structure.

## Scope

- Chemistry: primarily LFP / Graphite Li-ion cells
- Geometry: 1D P2D, or 1D electrochemistry + 3D thermal multiscale coupling
- Operating modes: CC, CP, parameter sweeps, thermal coupling
- Source of truth: exported `.java`, not `.mph`

## Mandatory Workflow

When asked to modify a COMSOL Java model, do these steps in order.
Do not jump straight to code generation.

### Step 1: Build a mental map first

Search the current source for:
- `Model model = ModelUtil.create`
- `model.component(`
- `.geom(`
- `model.param().set`
- `physics().create`
- `multiphysics().create`
- `extrudedim` / `genext` / `aveop`
- `model.study(...).create`
- `feature("param")`
- `GlobalEquations` / `ge1`
- `result().numerical`

Then summarize the model briefly before proposing any change.

### Step 2: Plan before code

List these 4 items before generating snippets:
1. What to change
2. What to preserve
3. What to add
4. What side effects may occur

If the target section is unclear, ask for the relevant source section instead of guessing.

### Step 3: Generate snippets, not full files

Default output must be snippet-oriented and include:
- Insert location
- New tags
- Dependencies
- Risks
- Java snippet
- Paste instructions

Only generate a full `.java` file if the user explicitly asks for one.

## Hard Rules

1. Never invent COMSOL tags. Reuse or extend the source file's naming pattern.
2. Never guess COMSOL API property names. Mirror existing usage in the same source file.
3. Keep dependency order intact: parameters, geometry, selections, materials, physics, mesh, study, solver, results.
4. Always include units in numeric COMSOL expressions.
5. Match the source file's existing formatting and comment style.

## Thermal and CP Rules

1. Do not use `ElectromagneticHeating` as a replacement for battery electrochemical heating unless the source model is clearly coupling structural Electric Currents Joule heating.
2. Constant power is not a native liion boundary condition. Prefer Global Equations or the source model's existing CP mechanism.
3. For newly generated standardized parameter sweeps, prefer Study parametric sweep under `model.study(...).feature("param")` rather than `model.batch()`.

## Sanity Checks

Before returning code, check:
- voltage limits are realistic for LFP
- CP vs CC mode is not mixed accidentally
- thermal source comparison uses the correct quantity and units
- 1D to 3D coupling does not silently change component ownership

## On-Demand References In This Repo

Load these files when needed:
- `COMSOL/files/comsol_java_anatomy.md`
- `COMSOL/files/liion_lfp_reference.md`
- `COMSOL/files/multiscale_1d_3d_coupling.md`
- `COMSOL/files/parameter_sweep_patterns.md`
- `COMSOL/files/matlab_livelink_patterns.md`
- `COMSOL/files/comsol_64_api_notes.md`
- `COMSOL/files/team_workflow.md`

## If Unsure

Stop and ask for the relevant source block.
Wrong tags and guessed API names are worse than asking one clarification question.