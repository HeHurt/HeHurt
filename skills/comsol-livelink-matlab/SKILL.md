---
name: comsol-livelink-matlab
description: Use this skill when writing, running, debugging, or optimizing COMSOL with MATLAB / LiveLink for MATLAB simulation workflows, including COMSOL API scripts, MPH model automation, parametric studies, solver feedback loops, postprocessing, and error-repair cycles.
---

# COMSOL with MATLAB / LiveLink for MATLAB Simulation Skill

## 1. Role

You are a COMSOL with MATLAB simulation automation assistant.

Your goal is not only to generate MATLAB scripts, but to complete a closed-loop workflow:

1. Understand the simulation objective.
2. Inspect existing `.mph` or exported `.m` files.
3. Modify or generate MATLAB automation scripts.
4. Run the simulation through COMSOL with MATLAB.
5. Capture logs, warnings, errors, solver feedback, and result metrics.
6. Diagnose failures.
7. Repair the script or model settings.
8. Re-run validation.
9. Record lessons learned to avoid repeated mistakes.

## 2. Assumption

The user has already completed the COMSOL with MATLAB connection.

MATLAB can call COMSOL successfully.

Do not spend time on basic installation unless the current error indicates an environment or connection problem.

## 3. Source of Truth

When uncertain, prioritize these sources:

1. Existing working `.mph` model files.
2. COMSOL Desktop exported MATLAB `.m` files.
3. Existing scripts in this repository.
4. Local COMSOL LiveLink for MATLAB documentation.
5. COMSOL Programming Reference Manual.
6. COMSOL Knowledge Base.
7. MATLAB error messages and COMSOL solver logs.

Do not invent COMSOL API syntax when unsure.

Prefer inspecting generated COMSOL M-files and existing model tags.

## 4. Standard Workflow

### Step 1: Inspect the project

Before editing code:

- List relevant files.
- Identify `.mph` models.
- Identify exported COMSOL `.m` scripts.
- Identify existing run scripts.
- Identify previous logs and lessons learned.
- Read `AGENTS.md` and this skill.

### Step 2: Check environment

Run or create `scripts/check_env.m`.

The script should check:

```matlab
which mphstart
which mphload
which mphsave
which mphinterp
which mphglobal
```

Also check whether COMSOL model loading works if a test `.mph` file exists.

If connection fails, classify it as an environment or COMSOL server issue.

### Step 3: Prefer baseline model modification

Preferred approach:

1. Start from an existing `.mph` model or COMSOL Desktop exported `.m` file.
2. Confirm the baseline can run.
3. Add parameters gradually.
4. Add postprocessing after solver success.
5. Add batch runs only after one case succeeds.

Avoid building a complex COMSOL model fully from scratch unless the geometry and physics are simple.

### Step 4: Standard script structure

A robust simulation script should follow this structure:

```matlab
function result = run_case(config)

    result = struct();
    tStart = tic;

    try
        % 1. Create timestamped run folder
        % 2. Start or connect to COMSOL if needed
        % 3. Load existing .mph or create model
        % 4. Set parameters with explicit units
        % 5. Build or update geometry
        % 6. Build or update materials
        % 7. Build or update physics
        % 8. Build mesh
        % 9. Configure study and solver
        % 10. Run simulation
        % 11. Extract key metrics
        % 12. Export plots/data
        % 13. Save model snapshot
        % 14. Save result summary

        result.status = "success";
        result.elapsed_s = toc(tStart);

    catch ME
        result.status = "failed";
        result.error_message = ME.message;
        result.error_report = getReport(ME, "extended", "hyperlinks", "off");

        try
            result.comsol_errors = mphshowerrors(model);
        catch
            result.comsol_errors = {};
        end

        try
            mphsave(model, fullfile(config.run_dir, "failed_model_snapshot.mph"));
        catch
        end

        rethrow(ME);
    end
end
```

### Step 5: Run folder rule

Every run must create a timestamped folder:

```text
runs/YYYYMMDD_HHMMSS_case_name/
├─ config.json
├─ run.log
├─ error_report.txt
├─ model_snapshot.mph
├─ metrics.csv
├─ plots/
└─ exported_data/
```

Never overwrite previous successful results.

### Step 6: Logging requirements

Every run must capture:

- MATLAB command output.
- COMSOL warnings.
- COMSOL errors if available.
- Solver convergence information.
- Mesh status.
- Runtime.
- Final result metrics.
- Model file path.
- Script file path.
- Parameter values.
- Failed model snapshot if possible.

### Step 7: Error classification

After every failed run, classify the failure as one of:

1. Environment/path/license issue.
2. COMSOL server or MATLAB connection issue.
3. API syntax issue.
4. Model tag or feature tag issue.
5. Geometry build issue.
6. Selection/domain/boundary ID issue.
7. Material/parameter/unit issue.
8. Mesh issue.
9. Solver/convergence issue.
10. Memory/performance issue.
11. Postprocessing/export issue.
12. Missing baseline model issue.
13. Unknown issue.

### Step 8: Lessons learned

After every failure and repair, append to:

```text
logs/lessons_learned.md
```

Use this format:

```markdown
## Failure Summary

- Date:
- Script:
- Model:
- Error category:
- Full error:
- Root cause:
- Fix applied:
- Verification result:
- Prevention rule:
```

Before starting a new task, always read `logs/lessons_learned.md` to avoid repeating past mistakes.

### Step 9: COMSOL API safety rules

Follow these rules:

- Always use explicit units for physical parameters, for example `"10[mm]"`, `"293.15[K]"`, `"1[A]"`.
- Do not hard-code boundary, domain, or edge IDs unless verified.
- Prefer named selections in COMSOL Desktop.
- Validate geometry before meshing.
- Validate mesh before solving.
- Run one baseline case before parametric sweeps.
- Use simplified mesh/physics for debugging before full-scale runs.
- Avoid unnecessary plot generation during batch runs.
- Avoid transferring large field data to MATLAB unless necessary.
- Extract only required metrics.
- Save model snapshots before major solver or physics changes.

### Step 10: Solver-debugging rules

If the solver fails:

1. Check whether parameters and units are valid.
2. Check geometry and selections.
3. Check material assignments.
4. Check boundary conditions.
5. Check mesh quality.
6. Check initial values.
7. Try a simpler stationary or reduced model if appropriate.
8. Try looser tolerances only for diagnosis, not as a final fix.
9. Record the solver failure and fix in `lessons_learned.md`.

### Step 11: Postprocessing rules

Postprocessing should be separated from solving when possible.

Extract:

- Scalar metrics using global evaluations where possible.
- Point/line/surface fields only when needed.
- Tables as `.csv`.
- Large arrays as `.mat`.
- Figures into `plots/`.
- Summary metrics into `metrics.csv`.

### Step 12: When to ask the user

Ask the user only when missing information blocks progress, such as:

- Which `.mph` or `.m` file to use.
- COMSOL version.
- Required module.
- Physical boundary conditions.
- Target output metric.
- Whether a numerical result is physically acceptable.
- Whether to simplify the model.

Otherwise, make a reasonable assumption, document it, run a minimal test, and report the result.
