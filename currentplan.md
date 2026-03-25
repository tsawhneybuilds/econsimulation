# Julia-First U.S. Stage 1

## Summary
- Keep simulation, calibration, initialization, shocks, and recursive forecast generation in `BeforeIT.jl`.
- Make the U.S. adaptation in Julia only: U.S. calibration inputs, Fed rule inputs, and the external-sector reinterpretation from small open economy to U.S. large open economy.
- Turn `us_macro_simulator` into a file-based benchmark, validation, and reporting shell around Julia outputs.
- Use a file handoff boundary. Julia writes the canonical bundle. Python reads it. The default Stage 1 workflow no longer runs a duplicate Python simulator.

## Interfaces
- Add a Julia CLI entrypoint at `BeforeIT.jl/scripts/run_us_stage1.jl` with `--calibration-date`, `--start-origin`, `--end-origin`, `--horizon`, `--n-sims`, `--data-mode {fixture,real}`, and `--output-dir`.
- Add a top-level orchestrator at `scripts/run_stage1.sh` that runs the Julia exporter first and the Python validator/reporter second against the same output directory.
- Add a Python `ArtifactBundle` loader in `us_macro_simulator` and make the validation/reporting scripts accept `--bundle-dir` instead of Python `SimulationState` or `BacktestResult`.
- Make Julia write `manifest.json` with model version, country=`US`, calibration date, origin grid, horizon, seeds, runtime, data provenance, and content hashes.
- Make Julia write `observed_dataset.csv` with the leakage-safe quarterly series actually used by the Julia run.
- Make Julia write `simulator_forecasts.csv` with one row per `origin, horizon, variable` and columns `mean`, `p10`, `p50`, `p90`.
- Make Julia write `initial_measurements.json` with GDP, C, I, G, X, M, NX, unemployment, policy rate, price level, and numeric-sanity flags.
- Make Julia write `cross_section_summary.csv` with low/middle/high income shares, low/middle/high consumption shares, and broad sector output shares.
- Make Julia write `scenario_bundle.json` with baseline-vs-shocked outputs for the validation replay/scenario checks.
- Keep benchmark models in Python. They must read `observed_dataset.csv` and use the origin/horizon grid from `manifest.json`.

## Implementation Changes
- Create a `US_CALIBRATION` object in Julia using the same `CalibrationData` schema the package already expects, so the core engine and calibration pipeline stay Julia-native.
- Build the U.S. calibration inputs from processed U.S. data with fixture-backed equivalents for tests; keep the Julia schema identical to the Italy/Austria path rather than inventing a new U.S.-only structure.
- Keep Julia’s investment block unchanged. Firm investment and household investment remain behavioral and market-cleared, and total investment is measured from realized `I_i` and `I_h`.
- Keep the current Julia rest-of-world machinery, but reinterpret the `EA` block as `global ex-U.S.` for compatibility and recalibrate the export/import shares plus foreign-demand and foreign-price processes from U.S. data.
- Change the Julia Taylor rule to use domestic lagged expectations `agg.gamma_e` and `agg.pi_e` instead of `rotw.gamma_EA` and `rotw.pi_EA`.
- Add Julia-side export code that converts existing calibration, simulation, and prediction outputs into the CSV/JSON artifact bundle above. Do not make Python read JLD2.
- Remove the Python engine path from the default runnable Stage 1 flow. Python should no longer initialize, step, or forecast the simulator in the main pipeline.
- Replace Python identity checks with artifact-based checks over `initial_measurements.json`.
- Replace Python cross-sectional checks with artifact-based checks over `cross_section_summary.csv`.
- Replace Python scenario/replay execution with validation over `scenario_bundle.json`.
- Keep Python data-quality checks, benchmark evaluation, scorecards, comparison tables, JSON report generation, and HTML report generation.
- Add a Julia artifact-contract doc and update the benchmark and validation protocol docs so the simulator of record is Julia and Python is the validator/reporting layer.

## Test Plan
- Add Julia tests proving `US_CALIBRATION` builds params and initial conditions for at least one reference U.S. quarter.
- Add a Julia regression test proving the Fed rule responds to domestic expected inflation and growth rather than foreign-area series.
- Add a Julia test proving the exported `initial_measurements.json` satisfies the accounting identity at the reference state.
- Add a Julia export test proving the recursive backtest bundle contains the expected origins, horizons, variables, and manifest metadata.
- Add a Python loader test that rejects missing files, schema mismatches, and bad manifest versions.
- Add a Python benchmark test proving the simulator and all benchmarks use the same origin/horizon grid and the same observed history constraints from the Julia bundle.
- Add a Python validation test proving hard failures trigger on identity, leakage, and benchmark-gate violations from a synthetic bad bundle.
- Add a Python report test proving HTML and JSON reports generate from a saved Julia bundle without importing the Python engine.
- Add an end-to-end fixture-backed test for `scripts/run_stage1.sh` that produces the full bundle and final report.
- Add an end-to-end leakage test proving each exported origin only sees data available at that vintage.
- Add an end-to-end scenario test proving Julia-generated rate-shock and import-price-shock outputs satisfy the expected sign checks.

## Assumptions
- Julia `1.9+` is a hard prerequisite. The current environment does not have Julia installed and the repo has no PyJulia or JuliaCall bridge.
- File handoff is the canonical boundary. Python does not embed Julia and Julia does not depend on Python internals.
- Existing Python time-series and semi-structural benchmarks remain the Stage 1 benchmark suite.
- Internal Julia identifiers may keep `EA` names for compatibility, but exported files and docs must label the block as `foreign` or `global_ex_us`.
- CI uses fixture-backed U.S. calibration data. Real U.S. runs use processed U.S. calibration inputs through the same Julia schema and the same artifact contract.
