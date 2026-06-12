---
name: hithium-batteryproject-frontend
description: Use for BatteryProject frontend and UI productization tasks: screenshot-to-UI implementation, Streamlit vs standalone UI decisions, connecting fake UI panels to real PyBaMM/BatteryProject workflows, FastAPI/SQLite/uv architecture, local frontend packaging, and Playwright/Browser visual QA for the Hithium simulation studio.
---

# Hithium BatteryProject Frontend

Use this skill when the user wants the BatteryProject UI to look like a reference screenshot, stop being a mockup, connect to real PyBaMM workflows, or become shareable for colleagues.

## Boundaries

- Covers: `BatteryProject/studio`, `BatteryProject/api`, `BatteryProject/run_frontend.py`, project-specific frontend/backend wiring, local database decisions, UI-to-simulation data contracts.
- Does not cover general browser automation; use Browser or `playwright-interactive` for execution and QA.
- Does not cover PyBaMM model debugging beyond the API contract; use `hithium-pybamm-debugging` for simulation correctness.

## Start With A Reality Inventory

Before changing UI code, list the visible features as one of:

- Real: calls BatteryProject/PyBaMM code and returns actual data.
- Mock: static demo data or hard-coded chart.
- Shell: button/control exists but no backend behavior.
- Broken: intended real behavior but currently fails.

Do not present a mock as production behavior. If the user asks to "make it real", convert the most important shell/mock path first.

## Workflow

1. Inspect the existing stack:
   - Framework: Streamlit, static studio, FastAPI, or other.
   - Current routes, API modules, state storage, style variables, and launch command.
   - Existing design tokens/components before adding new CSS or components.
2. Decide implementation mode:
   - Screenshot parity only: match layout, spacing, hierarchy, and responsive behavior.
   - Productization: wire controls to real project config, data import/export, solver jobs, and result charts.
   - Architecture migration: justify FastAPI/SQLite/uv only if the current stack blocks real workflows.
3. Define the UI-to-simulation contract:
   - Cell type and parameter source.
   - Model options, aging toggles, dry-out switch, solver settings.
   - Experiment protocol: C/P rate, voltage cutoffs, rest time, cycle count, temperature.
   - Outputs: voltage, capacity retention, discharge capacity, energy efficiency, DCR, heat, swelling, logs, export files.
4. Implement in the existing style:
   - Reuse current components, colors, spacing, and route/state patterns.
   - Do not build a parallel design system.
   - Keep controls dense and operational; this is an engineering tool, not a landing page.
5. Make long-running simulation explicit:
   - Provide job status, logs, cancel/failure state, and output path.
   - Keep smoke/test cycle count visibly separate from user-requested full cycle count.

## Visual And Functional QA

Use `playwright-interactive` or Browser for local verification when a UI changes. Check at least:

- Desktop and a narrow/mobile viewport.
- Main workflow controls do not overflow or overlap.
- Buttons that claim to run/export/import actually call the real path.
- Charts update when inputs change, or the UI clearly marks that a rerun is required.
- The result area has enough room for plots and logs.

Before finalizing, capture the URL/launch command and summarize what was verified.

## Output Shape

Return:

- What changed from mock/shell to real behavior.
- Which UI areas remain mock or intentionally deferred.
- Local run command and URL.
- QA evidence: browser/tool used, viewport(s), and any unresolved visual issues.
