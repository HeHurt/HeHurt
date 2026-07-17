# COMSOL with MATLAB Lessons Learned

This file records failed runs, repairs, and prevention rules for COMSOL with MATLAB / LiveLink for MATLAB workflows.

Before starting a new COMSOL LiveLink task, read this file to avoid repeating previous mistakes.


## Failure Summary

- Date: 2026-06-29 08:29:57
- Script: D:\Users\hez\Desktop\hithium\scripts\run_case
- Model: 
- Error category: Missing baseline model issue
- Full error: No .mph baseline model found under D:\Users\hez\Desktop\hithium\models.
- Root cause: Baseline model was not available.
- Fix applied: No fix applied in this run.
- Verification result: Waiting for user-provided model or modeling requirements.
- Prevention rule: Provide a baseline .mph file, a COMSOL Desktop exported .m file, or complete modeling requirements.

## Failure Summary

- Date: 2026-06-29 08:36:14
- Script: D:\Users\hez\Desktop\hithium\scripts\check_env.m
- Model: 
- Error category: Environment/path/license issue
- Full error: `mphstart`, `mphload`, `mphsave`, `mphinterp`, and `mphglobal` were missing from the MATLAB R2021b `-batch` path.
- Root cause: MATLAB could start and import COMSOL Java packages, but the LiveLink MATLAB function path was not visible in this noninteractive batch session.
- Fix applied: No environment fix applied in this run.
- Verification result: Environment check completed and wrote `logs/env_check.log`; LiveLink function availability remains failed.
- Prevention rule: Before running COMSOL cases from Codex, ensure the same MATLAB command path can resolve all required `mph*` functions, or add the COMSOL LiveLink MATLAB path in startup/config.

## Failure Summary

- Date: 2026-06-29 08:36:14
- Script: D:\Users\hez\Desktop\hithium\scripts\postprocess_case.m
- Model: 
- Error category: Postprocessing/export issue
- Full error: `metrics.csv` was read as `%TSD-Header-###%` ciphertext by MATLAB/PowerShell, while Python could read the plaintext.
- Root cause: Trend Micro DLP protected generated `.csv` output in this workspace; non-whitelisted readers can see ciphertext.
- Fix applied: Added a DLP fallback in `postprocess_case.m` that detects `%TSD-Header-###%` and reads the file through Python.
- Verification result: Re-running `postprocess_case.m` printed plaintext metrics successfully.
- Prevention rule: When generated result files show `%TSD-Header-###%`, read them through Python instead of debugging encoding.

## Failure Summary

- Date: 2026-06-29 09:10:17
- Script: D:\Users\hez\Desktop\hithium\scripts\check_env.m
- Model: 
- Error category: Environment/path/license issue
- Full error: Bare MATLAB R2021b batch sessions did not include COMSOL LiveLink MATLAB functions on the path.
- Root cause: The working LiveLink installation is under `D:\Program Files\COMSOL\COMSOL64\Multiphysics`, but `D:\Program Files\COMSOL\COMSOL64\Multiphysics\mli` was not automatically added to MATLAB path.
- Fix applied: Added COMSOL root auto-detection and `mli` path setup to `check_env.m` and `run_case.m`; `run_case.m` now starts/connects mphserver only after a baseline `.mph` is found.
- Verification result: `check_env.m` found all required `mph*` functions, started mphserver on port 2036, connected to COMSOL Multiphysics 6.4, and returned success.
- Prevention rule: For Codex-driven MATLAB batch runs, always add the COMSOL `mli` directory and pass the COMSOL root to `mphstartcomsolmphserver`.

## Failure Summary

- Date: 2026-06-29 09:08:51
- Script: D:\Users\hez\Desktop\hithium\scripts\run_case
- Model: 
- Error category: Missing baseline model issue
- Full error: No .mph baseline model found under D:\Users\hez\Desktop\hithium\models.
- Root cause: Baseline model was not available.
- Fix applied: No fix applied in this run.
- Verification result: Waiting for user-provided model or modeling requirements.
- Prevention rule: Provide a baseline .mph file, a COMSOL Desktop exported .m file, or complete modeling requirements.
