# Repo Status

Status as of 2026-03-25.

This file is a current snapshot for collaborators. It is not the build spec. The main source-of-truth spec remains `us_macro_simulator_source_of_truth_build.md`.

## Overview

This repo is now split into three practical layers:

- `BeforeIT.jl` is the Julia-first simulation layer. It owns calibration, initialization, recursive forecast generation, and the canonical Stage 1 artifact bundle.
- `us_macro_simulator` is the Python benchmark, validation, and reporting shell. It reads the Julia bundle, recomputes benchmarks on the same origin grid, builds scorecards, and emits validation/report artifacts.
- Repo-root docs such as `us_macro_simulator_source_of_truth_build.md`, `currentplan.md`, `validation.md`, and `fixingjulia.md` explain intent, roadmap, and recent debugging work.

The default runnable flow is Julia bundle export first, then Python evaluation over that same bundle.

## Current Status

- The recent Julia Stage 1 retargeting fixes are in place, and the focused `2019Q1` plausibility regression now passes.
- The full Stage 1 benchmark shell runs end-to-end: Julia can export the bundle, and Python can score it against the current benchmark suite and generate reports.
- The documentation set is substantial, but it is fragmented across repo-root planning docs, `us_macro_simulator/docs/`, `us_macro_simulator/process_validation.md`, and the upstream `BeforeIT.jl` docs.
- The old nested `us_macro_simulator/STATUS.md` was stale enough to be actively misleading, because it still described major subsystems as unbuilt even though the corresponding modules are present and runnable.

## Current Problems

Short-horizon plausibility is fixed, but the full benchmark comparison is still weak.

Latest measured comparison from `/tmp/julia_stage1_eval_current/comparison_table.parquet`:

- `us_macro_simulator` core macro mean RMSE: `3.130802`
- `us_macro_simulator` GDP RMSE: `7.603543`
- Best core-macro comparator: `local_mean` at `0.900629`
- Best GDP comparator: `local_mean` at `1.209049`

Additional context:

- The current Julia bundle evaluator compares against `random_walk`, `ar4`, `local_mean`, `factor_model`, and `semi_structural`.
- It does not currently emit a `dsge_nyfed` row in the comparison table.
- Documentation duplication and staleness are also active problems. The deleted nested status page was the clearest example, but the broader docs set still needs consolidation and consistent updating.

## Docs Overview

### Root Planning / Spec Docs

- `us_macro_simulator_source_of_truth_build.md`: primary build specification and long-range intent document.
- `validation.md`: high-level technical roadmap for the simulator plus validation harness; closer to an architectural plan than an operator guide.
- `currentplan.md`: current implementation-direction memo for the Julia-first Stage 1 approach.
- `fixingjulia.md`: targeted debugging memo for the U.S. Julia calibration and retargeting failures.

### Python Shell Operational Docs

- `us_macro_simulator/process_validation.md`: end-to-end operator explainer for the Julia bundle -> Python backtest -> validation -> report flow.
- `us_macro_simulator/docs/benchmark_protocol.md`: benchmark-scope and scoring rules document.
- `us_macro_simulator/docs/julia_bootstrap.md`: local setup and happy-path run instructions for the Julia-first workflow.
- `us_macro_simulator/docs/julia_artifact_contract.md`: file contract for the canonical Julia Stage 1 bundle consumed by Python.
- `us_macro_simulator/docs/engine_adaptation_memo.md`: architecture memo describing how the current stack wraps or reuses the engine.
- `us_macro_simulator/docs/us_external_sector_memo.md`: narrow adaptation memo for Stage 1 monetary-policy and external-sector treatment.

### Upstream Julia Docs

- `BeforeIT.jl/README.md`: upstream package overview and basic local usage guide.
- `BeforeIT.jl/docs/src/index.md`: upstream user-facing documentation index.
- `BeforeIT.jl/docs/src/api.md`: upstream API reference.

## What To Trust First

If you only open a few files, use this order:

1. `us_macro_simulator_source_of_truth_build.md` — primary build and intent spec.
2. `currentplan.md` — current implementation direction for the Julia-first architecture.
3. `us_macro_simulator/process_validation.md` — current runtime and validation mechanics.
4. `us_macro_simulator/docs/julia_artifact_contract.md` — Julia/Python file boundary and bundle schema.
5. `fixingjulia.md` — current bug context and the calibration/retargeting debugging trail.

## Next Problems To Solve

- Improve full backtest RMSE against the benchmark suite, especially on GDP and the broader Stage 1 variable set.
- Decide whether the Julia-bundle evaluator should be extended to include `dsge_nyfed`, or whether that benchmark should remain outside the default bundle path.
- Reduce documentation fragmentation and keep this root `status.md` as the single status entrypoint rather than recreating multiple drifting status pages.
