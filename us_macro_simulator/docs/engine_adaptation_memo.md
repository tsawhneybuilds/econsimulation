# Engine Adaptation Memo

## Purpose

This repository adapts the vectorised BeforeIT-style transition loop into a U.S. Stage 1 macro simulation stack without rewriting the engine core.

## Current Wrapper Strategy

- `src/engine/core/state.py` defines the Python-native state contracts used throughout the Stage 1 system.
- `src/engine/core/engine.py` preserves the ordered transition loop and exposes a single `USMacroEngine.step()` wrapper.
- `src/us/calibration` provides the structural parameter bundle.
- `src/us/initialization/initializer.py` maps calibration plus observed data into a runnable `SimulationState`.
- `src/engine/measurement/nipa_mapper.py` maps latent model state back to Stage 1 observables.

## Stage 1 Design Choices

- Structural parameters remain anchored to the 2019Q4 U.S. calibration bundle.
- Observed aggregate data is vintage-masked per forecast origin and used to refresh the initialization baseline.
- The benchmark suite mixes simple univariate models, a factor model, and a reduced semi-structural comparator.
- Validation is treated as a first-class subsystem instead of an afterthought.

## Known Stage 1 Limits

- Initialization uses observed aggregate targets, not a full latent-state filtering system.
- Household bins are still coarse diagnostics derived from the worker distribution rather than explicit model-state cohorts.
- The semi-structural benchmark is a reduced comparator, not a research-grade DSGE estimation stack.

## Why This Is Acceptable For Stage 1

Stage 1 is intended to make the simulator runnable, measurable, benchmarkable, and auditable. The current wrapper keeps the original engine logic intact while adding the minimum data, forecast, benchmark, validation, and reporting surface needed to evaluate the model honestly.
