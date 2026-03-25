# Source of Truth for Codex: Build the U.S. Macro Simulator, Calibrate It to the U.S., Benchmark It Against DSGE Baselines, and Build the Validation Harness Alongside It

## 0. Purpose of this document

This is the implementation document Codex should treat as the primary build specification.

The objective is not to produce a vague research prototype. The objective is to build a disciplined, testable, versioned U.S. macro simulation system that:

1. **adapts the current simulator to the U.S. economy**,
2. **calibrates the simulator to U.S. macro structure and coarse cross-sectional facts**,
3. **compares the simulator fairly against standard DSGE-style baseline models and simpler time-series benchmarks**,
4. **builds the full validation and testing harness from the beginning rather than after the fact**, and
5. **creates a clean path toward a fuller digital-twin style forecasting system in later stages**.

This document is intentionally detailed. Codex should follow it literally unless doing so would obviously break correctness, reproducibility, or software quality. When there is ambiguity, Codex should choose the design that is more modular, more testable, more reproducible, and more compatible with the long-run roadmap described here.

---

# 1. High-level mission

Build a U.S.-specific macro simulation platform in three stages.

## Stage 1: U.S. baseline system

The first priority is to **get the existing simulator to run as a U.S. economy simulator** with a defensible calibration, a coherent measurement layer, recursive pseudo-real-time forecasting, a benchmark comparison framework, and a full validation harness.

This is the first non-negotiable milestone. The build is not successful unless Stage 1 is working.

## Stage 2: U.S.-critical structural upgrades

After Stage 1 is stable, extend the simulator in the areas where a non-U.S. base model is structurally inadequate for the United States:
- external sector,
- housing and mortgages,
- finance and credit transmission,
- multi-speed expectations,
- selected optional ML augmentations.

## Stage 3: digital twin mode

Convert the simulator from a research model into a continuously updating forecast and scenario system with explicit data assimilation and hidden-state updating.

---

# 2. What Codex must prioritize first

The first major goal is:

> **Update the simulator to represent the U.S. economy, calibrate it to U.S. data, compare it against current DSGE-style baselines and simpler forecasting baselines, and build all necessary validation and tests along the way.**

That means the initial build order should be:

1. understand and wrap the current simulator,
2. build U.S. data contracts,
3. build a U.S. calibration bundle,
4. build a U.S. reference-state initializer,
5. map latent simulator variables to observed U.S. macro variables,
6. run U.S. forecasts,
7. compare the simulator to DSGE baselines and simpler benchmarks,
8. validate the simulator aggressively,
9. only then extend the structure.

Codex should **not** begin by rewriting the engine from scratch.

The working assumption is:
- preserve as much of the current simulator as possible in Stage 1,
- wrap and adapt first,
- only replace structural blocks after the U.S. baseline and the validation harness exist.

---

# 3. Product definition

The system being built is a **macro simulation and forecasting platform** with the following modes.

## 3.1 Research mode

A slower, more transparent environment used to test structures, calibrations, scenarios, and validation protocols.

## 3.2 Forecast mode

A disciplined pseudo-real-time forecasting workflow that only uses information available at each forecast origin.

## 3.3 Scenario mode

A mode that applies controlled shocks or policy paths and tracks aggregate and cross-sectional responses.

## 3.4 Twin mode (future)

A mode that updates hidden states with incoming releases and produces continuously refreshed nowcasts and forecasts.

---

# 4. Non-negotiable principles

These are hard rules.

## 4.1 Validation is part of the build, not a later add-on

The simulator and the validation harness are one product.

## 4.2 Version everything

The following must be versioned and hashable:
- code,
- config,
- calibration bundle,
- processed dataset,
- vintage snapshot,
- simulation seed,
- forecast artifacts,
- reports.

## 4.3 No future leakage

Pseudo-real-time evaluation must be real. The system must not use revised or unavailable information at a forecast origin.

## 4.4 Preserve the core until Stage 1 proves what is wrong

Do not prematurely replace large parts of the engine before the U.S. baseline is running and measurable.

## 4.5 Distinguish latent state from measured observables

The engine evolves latent state variables. A separate measurement layer maps these to observed U.S. macro series.

## 4.6 Internal consistency before forecast scoring

If accounting, state admissibility, or conservation logic fails, forecast metrics are secondary. The run should fail early.

## 4.7 Benchmarks are mandatory

Every forecast result must be interpreted against:
- DSGE-style baselines,
- simple statistical baselines,
- and a small semi-structural baseline where feasible.

## 4.8 Modularity matters

External, housing, finance, expectations, assimilation, and optional ML components must be modular blocks with explicit interfaces.

---

# 5. Concrete success criteria

The project is successful only if the following statements become true.

## 5.1 Stage 1 success criteria

- A single command runs the U.S. baseline from processed data to validation report.
- The simulator initializes from a U.S. reference period and produces coherent latent and observed outputs.
- The system runs recursive pseudo-real-time forecasts over a specified historical sample.
- The forecast outputs are compared automatically against DSGE-style baselines and simpler time-series benchmarks.
- The validation harness checks data integrity, internal consistency, forecast quality, and coarse cross-sectional realism.
- Runs are reproducible with fixed seed and fixed vintage.
- The build includes dashboards or reports that make results auditable.

## 5.2 Stage 2 success criteria

- U.S.-specific rate transmission is materially more believable.
- External-sector transmission is no longer modeled as if the U.S. were a small open economy.
- Housing and mortgage dynamics show fixed-rate, cohort, refinance, and lock-in behavior.
- The finance block captures at least a coarse breakdown of rate and spread transmission.
- Cross-sectional scenario behavior improves.

## 5.3 Stage 3 success criteria

- The system can update hidden state as new data arrives.
- Nowcasts and forecasts can be refreshed on a monthly or quarterly cadence.
- Density forecasts are calibrated and evaluated.
- Scenario analysis can answer who gets hit: by household bin, region, and sector.

---

# 6. What Codex should assume about the current simulator

Codex should start by treating the current simulator as an engine that likely already contains:
- a latent state transition mechanism,
- a set of structural blocks,
- expectations formation logic,
- stochastic simulation machinery,
- and perhaps some initialization/calibration logic tied to another economy.

Codex should first inspect and document:
- the engine state representation,
- transition functions,
- shock interfaces,
- expectations modules,
- data dependencies,
- outputs,
- and any existing calibration assumptions.

The first deliverable should include a brief **engine adaptation memo** inside the repo that answers:
- what can be reused unchanged,
- what must be wrapped,
- what must be mapped,
- what must be replaced later.

This memo should be generated automatically or written once and saved under `docs/engine_adaptation_memo.md`.

---

# 7. Core build strategy

Codex should build the system in layers.

## Layer A: engine wrapper and state contracts

Create explicit interfaces for:
- simulation state,
- transition context,
- shocks,
- measurements,
- forecast runner,
- scenario runner,
- and validation hooks.

The goal is not to rewrite the engine but to make it callable in a disciplined way.

## Layer B: U.S. data and calibration layer

Create:
- U.S. data contracts,
- processed datasets,
- metadata tables,
- calibration objects,
- reference-period initialization routines,
- measurement mappings.

## Layer C: forecasting and benchmark layer

Create:
- recursive pseudo-real-time backtests,
- Monte Carlo forecast generation,
- benchmark forecast models,
- comparative evaluation.

## Layer D: validation harness

Create a dedicated validation subsystem with hard gates and soft diagnostics.

## Layer E: reporting layer

Create machine-readable and human-readable outputs.

---

# 8. Repository architecture Codex should build

```text
repo/
  configs/
    base/
    stage1/
    stage2/
    stage3/
    benchmarks/
    validation/
    experiments/
  data/
    raw/
    interim/
    processed/
    vintages/
    fixtures/
    golden/
  docs/
    engine_adaptation_memo.md
    calibration_notes.md
    benchmark_protocol.md
    validation_protocol.md
    scenario_protocol.md
  scripts/
    inspect_engine.py
    build_dataset.py
    build_reference_state.py
    run_smoke.py
    run_backtest.py
    run_benchmarks.py
    run_validation.py
    run_scenarios.py
    generate_report.py
  src/
    engine/
      core/
      transitions/
      shocks/
      expectations/
      measurement/
      wrappers/
    us/
      data_contracts/
      preprocessing/
      calibration/
      initialization/
      mappings/
      sectors/
      households/
      finance/
      external/
      housing/
      expectations/
    forecasting/
      runners/
      monte_carlo/
      backtests/
      benchmarks/
      metrics/
      dsge_baselines/
    validation/
      data_quality/
      initialization/
      identities/
      invariants/
      forecast/
      benchmarking/
      cross_section/
      replay/
      scenarios/
      stochastic/
      performance/
      reproducibility/
      reports/
    assimilation/
    reports/
    utils/
  tests/
    unit/
    property/
    integration/
    regression/
    golden/
    performance/
    end_to_end/
  outputs/
    manifests/
    forecasts/
    reports/
    comparisons/
```

---

# 9. Stage 1 in full detail: build the U.S. baseline system

This is the first target Codex must complete.

## 9.1 Stage 1 objective

Adapt the simulator to the U.S. economy and make it runnable, measurable, benchmarkable, and testable.

## 9.2 Stage 1 scope

### Must include
- existing engine wrapped and runnable,
- U.S. aggregate macro dataset,
- U.S. calibration bundle,
- one reference-quarter initializer,
- aggregate accounting spine,
- coarse household and sector bins,
- measurement layer from latent variables to observed variables,
- recursive pseudo-real-time forecasting,
- benchmark comparison,
- validation harness,
- report generation.

### Must not include yet
- full HANK rewrite,
- large black-box forecasting core,
- policy RL inside the simulator,
- overcomplicated finance architecture,
- premature deep regional disaggregation,
- unvalidated ML patching over structural problems.

## 9.3 Stage 1 minimum target variables

The baseline Stage 1 system should target at least the following observed variables:
- real GDP growth,
- headline inflation,
- core inflation,
- unemployment rate,
- short policy rate or equivalent short rate,
- consumption growth,
- residential investment growth,
- credit or financial conditions proxy,
- optionally hours or wage growth if mapping is clean enough.

These variables are enough to expose whether the U.S. baseline has a coherent demand, inflation, labor, rate-transmission, and housing-sensitive structure.

## 9.4 Stage 1 coarse cross-sectional structure

Do not aim for rich micro structure yet. Use coarse bins.

### Household bins
At minimum:
- low-wealth / low-liquidity households,
- middle households,
- top-wealth households,
- homeowners with mortgages,
- homeowners without mortgages,
- renters.

The exact representation can overlap or use a product of bin systems, but the initialization and validation layers must be able to express these broad categories.

### Sector bins
At minimum:
- interest-sensitive sectors,
- housing-related sectors,
- tradable sectors,
- non-tradable service sectors,
- government-linked sectors,
- finance-sensitive sectors.

The first pass can be coarse. The schema should still allow later expansion.

---

# 10. U.S. data architecture

Codex should build a U.S. data layer with clear contracts.

## 10.1 Data categories

### Aggregate macro backbone
Required categories:
- real GDP and components,
- nominal GDP and deflators,
- PCE and core PCE,
- CPI and core CPI,
- government spending,
- net exports,
- labor market variables,
- wages or earnings proxy,
- disposable income,
- saving,
- policy rate and yield curve.

### Financial conditions and credit
Required categories:
- Treasury rates,
- mortgage rates,
- credit spreads,
- bank lending aggregates,
- financial conditions index,
- house prices,
- equity prices,
- stress indicators.

### External sector
Required categories:
- import and export quantities or values,
- import and export prices,
- broad dollar or exchange-rate proxies,
- commodity prices,
- foreign demand proxies.

### Housing and mortgages
Required categories:
- house price indices,
- mortgage rates,
- housing starts and permits,
- residential investment,
- home sales or activity proxies,
- originations / refinance shares if available,
- owner/renter splits if available.

### Cross-sectional household data
Required categories:
- wealth shares,
- income shares,
- debt shares,
- homeownership incidence,
- mortgage incidence,
- liquid versus illiquid asset shares,
- basic expectation measures if available.

### Sector and firm exposure data
Required categories:
- output shares,
- employment shares,
- trade exposure,
- interest sensitivity proxies,
- leverage or financing mix proxies,
- cost exposure proxies.

## 10.2 Data contracts

Each processed series must have metadata fields including:
- series name,
- source,
- frequency,
- transform,
- units,
- release lag,
- revision behavior if known,
- first valid date,
- last valid date,
- missingness handling policy.

This metadata should be part of the processed dataset manifest.

## 10.3 Vintage-aware design

Codex should build the data layer so that pseudo-real-time evaluation can be performed correctly.

If true historical vintages are unavailable for some series, the system should still include:
- release-date assumptions,
- release lags,
- revision flags,
- and explicit approximations.

The system must never silently treat final revised data as real-time data.

## 10.4 Fixture data

Codex must create small deterministic fixture datasets for testing:
- tiny aggregate macro dataset with known identities,
- tiny household-bin dataset,
- tiny sector dataset,
- tiny mortgage cohort fixture,
- tiny stochastic fixture with known moments.

These fixtures are essential for CI.

---

# 11. U.S. calibration strategy

Codex should create a formal `CalibrationBundle` for the U.S. baseline.

## 11.1 Calibration object requirements

The calibration object must contain:
- structural parameters,
- initialization parameters,
- household share targets,
- sector share targets,
- measurement parameters,
- stochastic shock parameters,
- parameter bounds,
- provenance metadata,
- version hash.

## 11.2 Calibration philosophy

Separate three classes of parameters:

### A. Directly observed or tightly targeted parameters
Examples:
- expenditure shares,
- income shares,
- unemployment or participation anchors,
- housing or mortgage incidence,
- wealth share targets.

### B. Parameters inferred or weakly identified by matching macro moments
Examples:
- persistence parameters,
- adjustment frictions,
- expectation speeds,
- pass-through coefficients.

### C. Placeholder parameters for Stage 1
These should be labeled clearly as provisional.

Codex should never hide the difference between measured targets and assumptions.

## 11.3 Calibration outputs

The build should generate:
- a machine-readable calibration file,
- a calibration provenance table,
- and a calibration notes markdown document explaining what is observed, inferred, assumed, and deferred.

## 11.4 Calibration validation

Calibration should fail if:
- required parameters are missing,
- shares do not sum to one,
- values violate bounds,
- implied state ratios are nonsensical,
- initialization produced from the calibration is inadmissible.

---

# 12. Initialization strategy

The U.S. baseline should initialize from one reference quarter or reference period.

## 12.1 Why reference-period initialization is used first

This is the fastest path to making the simulator runnable in a disciplined way.

It avoids the complexity of fully estimating a latent state from long history before the U.S. adaptation is even operational.

## 12.2 What initialization must populate

The initializer must produce:
- aggregate macro state,
- household-bin state,
- sector state,
- finance state if present,
- expectations state,
- stochastic state,
- measurement mapping state.

## 12.3 Initialization checks

The following must be checked automatically:
- no forbidden negative stocks,
- no NaNs or infinities,
- household masses sum to one,
- sector weights sum to one,
- mortgage and housing quantities reconcile with totals,
- latent states lie inside configured domains,
- accounting balances hold within tolerance.

---

# 13. Measurement layer requirements

The current simulator likely evolves latent variables that do not line up one-to-one with observed U.S. macro series. Codex must therefore build a formal measurement layer.

## 13.1 Measurement layer responsibilities

- map latent state to observed variables,
- apply necessary transformations,
- enforce unit consistency,
- separate state transition logic from observed data logic,
- make forecast evaluation possible without contaminating the engine.

## 13.2 Measurement outputs

At minimum the measurement layer should emit:
- observed aggregate forecast series,
- component series where possible,
- bin-level cross-sectional observables,
- and intermediate diagnostic variables.

## 13.3 Measurement tests

Measurement mapping must be tested independently from the engine.

Examples:
- if latent inflation state maps to observed PCE inflation, test known cases,
- if latent housing state maps to residential investment growth, test transform correctness,
- if latent labor state maps to unemployment, test bounds and invertibility where relevant.

---

# 14. Forecasting system requirements

Codex must build a forecasting layer that supports both deterministic and stochastic runs.

## 14.1 Forecast runner

The forecast runner should support:
- deterministic mode,
- stochastic Monte Carlo mode,
- scenario mode with specified shocks or policy paths,
- forecast horizon configuration,
- origin-by-origin backtests,
- artifact persistence.

## 14.2 Recursive pseudo-real-time backtesting

This is mandatory.

For each forecast origin:
- construct the appropriate data vintage,
- initialize or update the state using only available information,
- run forecasts at specified horizons,
- save point and density outputs,
- evaluate against realized outcomes,
- store metrics.

## 14.3 Forecast artifact schema

Each forecast artifact must record:
- run ID,
- forecast origin,
- data vintage hash,
- config hash,
- calibration hash,
- seed,
- simulation mode,
- target variable list,
- forecast horizon list,
- point forecasts,
- predictive intervals or sampled paths,
- diagnostics.

---

# 15. Benchmark comparison framework

This is a central requirement.

The simulator must be compared against both **DSGE-style baselines** and **simpler forecasting baselines**.

## 15.1 Why this matters

A simulation model is not impressive merely because it is structurally rich. It must earn credibility by outperforming or complementing simpler models under a fair protocol.

## 15.2 Benchmark categories

### Category A: simple univariate and multivariate time-series benchmarks
These should include as appropriate:
- random walk,
- drift benchmark,
- AR,
- ARIMA or related baseline,
- rolling mean,
- factor-based model,
- VAR-style baseline if appropriate.

### Category B: small semi-structural benchmark
Where feasible, create a small macro benchmark using a limited system for key variables.

### Category C: DSGE-style baselines
Codex should implement or wrap a set of **current DSGE-style baseline models** for comparison.

This does not require building a giant research-grade estimation stack at first. It does require a fair and explicit protocol for comparison.

At minimum, the DSGE comparison framework should support:
- a baseline New Keynesian style model or reduced DSGE-style representation,
- consistent target variables,
- same forecast origins,
- same horizons,
- same pseudo-real-time information constraints,
- same scoring metrics.

## 15.3 Principle for DSGE comparison

The goal is not to win every metric immediately. The goal is to answer:
- where does the simulator beat DSGE-style baselines,
- where does it lag,
- where is it adding value through scenario richness or cross-sectional detail even if point forecasts are similar,
- and whether the extra structure is justified.

## 15.4 Benchmark protocol requirements

Codex must create `docs/benchmark_protocol.md` describing:
- benchmark definitions,
- data used,
- target variables,
- horizons,
- estimation windows,
- pseudo-real-time rules,
- scoring metrics,
- reporting format.

## 15.5 Comparison outputs

Each backtest should produce:
- simulator score tables,
- benchmark score tables,
- relative score tables,
- charts by variable and horizon,
- stability over time,
- origin-by-origin comparison plots,
- summary wins/losses by variable.

---

# 16. Validation harness: full architecture

Codex must build the validation harness as a dedicated subsystem.

## 16.1 Validation philosophy

There are four broad classes of failure the harness must catch:

1. **data problems**,
2. **internal model inconsistency**,
3. **forecast weakness**,
4. **distributional or structural implausibility**.

## 16.2 Validation run modes

### Pull request mode
Fast fixture-based tests.

### Nightly mode
Reduced real-data runs and benchmark updates.

### Full research mode
Longer pseudo-real-time and scenario analyses.

### Release mode
Full gating mode for stable releases.

---

# 17. Full test catalog Codex must build

The following tests are required. This is the authoritative checklist.

## 17.1 Data quality tests

### Schema tests
- required columns exist,
- dtypes correct,
- no duplicate timestamps,
- monotonic time index,
- keys unique where needed.

### Units and transform tests
- percent vs fraction checked,
- annualized vs non-annualized checked,
- level vs growth tags checked,
- log transform correctness,
- differencing correctness,
- aggregation rule correctness.

### Missingness tests
- allowed missing blocks explicit,
- disallowed missing values fail,
- imputation strategy logged and tested.

### Release lag and vintage tests
- each forecast origin only sees allowed releases,
- revision leakage tests fail if future revisions are used,
- transformed features do not use future values.

### Outlier and anomaly tests
- impossible values rejected,
- extreme jumps flagged,
- crisis periods handled explicitly rather than silently filtered.

## 17.2 Calibration tests

- calibration file schema validation,
- parameter bounds enforced,
- provenance fields present,
- shares sum to one,
- implied initialization targets valid,
- checksum stable,
- perturbation tests for stability around baseline.

## 17.3 Initialization tests

- aggregate balances hold,
- cross-sectional masses sum correctly,
- no forbidden negative stocks,
- no NaNs,
- household and sector states within bounds,
- housing and mortgage state consistent with totals,
- expectations state admissible.

## 17.4 One-step transition tests

These are crucial.

- deterministic fixture transition equals expected output,
- bookkeeping identities preserved after one step,
- controlled shocks move variables in the expected broad direction,
- no explosive behavior under zero or small shock input,
- serializing and restoring state before a step gives identical result.

## 17.5 Invariant and property-based tests

Examples:
- shares remain in [0, 1],
- masses conserved,
- nonnegative stocks stay nonnegative unless explicitly signed,
- path quantiles ordered correctly,
- deterministic routines independent of irrelevant input ordering,
- serialization is lossless.

## 17.6 Monte Carlo and stochastic tests

- fixed seed reproduces identical paths,
- different seeds produce distinct but statistically compatible ensembles,
- shock sampler moments match target moments on large draws,
- variance behavior with horizon is sensible,
- predictive interval ordering valid,
- no impossible simulation values due solely to sampling logic.

## 17.7 Forecast evaluation tests

### Point forecast metrics
- RMSE,
- MAE,
- relative RMSE,
- directional accuracy,
- horizon-specific metrics.

### Density forecast metrics
- interval coverage,
- CRPS or proper scoring rule,
- sharpness,
- calibration by horizon,
- tail event coverage.

### Stability tests
- results are not driven by one origin,
- rolling windows detect degradation,
- metrics stored by origin and by horizon.

## 17.8 Benchmark parity tests

- simulator and benchmarks use the same data constraints,
- same forecast origins and horizons,
- same scoring pipeline,
- same target definitions,
- benchmark code changes trigger regression checks.

## 17.9 Cross-sectional validation tests

This is required even in Stage 1.

### Household-bin checks
- wealth share error,
- debt share error,
- homeownership incidence error,
- mortgage incidence error,
- liquid asset share error,
- direction of rate sensitivity by household type.

### Sector checks
- output share error,
- employment share error,
- relative interest sensitivity,
- relative trade exposure,
- relative cost-shock exposure.

### Distributional scoring
Use appropriate error or distance metrics such as:
- absolute share error,
- weighted absolute error,
- distribution distance measures where appropriate.

## 17.10 Historical replay tests

Codex should create a replay framework for key historical episodes.

### Stage 1 minimum episode classes
- calm period,
- tightening period,
- inflationary period.

### Stage 2 priority episodes
- 2021 to 2023 inflation surge,
- 2022 to 2023 hiking cycle,
- housing-sensitive episode,
- credit-stress episode.

### Replay evaluation should track
- sign correctness,
- timing,
- rough relative magnitude,
- narrative coherence,
- channel decomposition where possible.

## 17.11 Scenario and structural tests

Codex must build scenario tests for:
- policy-rate shock,
- commodity or import-price shock,
- external-demand slowdown,
- mortgage-rate shock,
- credit-spread shock,
- housing demand shock.

The tests should verify:
- broad sign restrictions,
- timing bands,
- no absurd oscillation,
- no explosive divergence under moderate shocks,
- stronger effects on plausibly more exposed bins.

## 17.12 Regression and golden tests

Store canonical outputs for:
- processed fixture dataset,
- reference-state initialization,
- one-step transition,
- tiny Monte Carlo run,
- tiny backtest metric bundle,
- representative report artifacts.

Golden tests should allow tolerances where necessary but protect against silent drift.

## 17.13 Performance tests

- runtime budget for PR fixture run,
- runtime budget for nightly reduced backtest,
- memory budget,
- parallel Monte Carlo scaling sanity.

## 17.14 Reproducibility tests

- identical config + data vintage + calibration + seed => identical artifacts,
- environment captured in run manifest,
- report reproducible from stored outputs.

## 17.15 Robustness tests

- missing noncritical series handled gracefully,
- corrupted feature detected early,
- parameters near bounds handled safely,
- structural-break windows do not crash the system,
- partial benchmark failures surface clearly.

## 17.16 Future assimilation tests

Reserve interfaces and placeholder tests for Stage 3:
- latent-state recovery on synthetic data,
- posterior uncertainty contraction,
- no unavailable releases in updates.

---

# 18. Hard gates vs soft diagnostics

## 18.1 Hard gates

These failures should stop the run.

- data schema failure,
- future leakage detected,
- missing benchmark outputs,
- initialization inadmissible,
- accounting identity failure above tolerance,
- serialization failure,
- fixed-seed reproducibility failure,
- corrupted manifests or hashes.

## 18.2 Soft diagnostics

These should be surfaced prominently but do not always fail the run.

- forecast underperformance vs benchmark,
- cross-sectional miss beyond warning band,
- poor density calibration,
- runtime regression,
- scenario response timing issues,
- large uncertainty or instability in selected modules.

---

# 19. Reporting requirements

Every substantial run should produce both machine-readable and human-readable outputs.

## 19.1 Required machine-readable outputs

- run manifest JSON,
- calibration bundle JSON or YAML,
- forecast artifacts,
- metric tables,
- benchmark comparison tables,
- validation status bundle,
- scenario outputs.

## 19.2 Required human-readable outputs

- HTML report,
- markdown summary,
- comparison plots,
- episode replay plots,
- warning section,
- calibration provenance appendix.

## 19.3 Report sections

A full report should include:
- summary status,
- data and version info,
- initialization diagnostics,
- aggregate forecast performance,
- DSGE and benchmark comparisons,
- cross-sectional checks,
- historical replays,
- scenario responses,
- reproducibility/performance summary,
- open warnings.

---

# 20. Exact Stage 1 implementation plan Codex should execute

This section is intentionally operational.

## Epic 0: inspect the current simulator and write adaptation interfaces

### Objective
Understand the engine without rewriting it.

### Build tasks
- inspect current state objects,
- inspect transition loop,
- inspect calibration assumptions,
- identify country-specific dependencies,
- create wrapper interfaces,
- write `docs/engine_adaptation_memo.md`.

### Deliverables
- engine wrapper module,
- adaptation memo,
- interface definitions.

### Tests
- engine can be instantiated from a tiny fixture config,
- wrapper can call one transition step.

## Epic 1: build U.S. data contracts and processed dataset pipeline

### Objective
Create the full U.S. dataset layer with metadata and vintage logic.

### Build tasks
- define series registry,
- build ingestion and transform pipeline,
- add release lag metadata,
- build vintage snapshots,
- write processed outputs,
- create fixture datasets.

### Deliverables
- processed dataset builder,
- manifest generator,
- fixture datasets.

### Tests
- schema validation,
- transform correctness,
- vintage leakage tests,
- fixture generation tests.

## Epic 2: build the U.S. calibration bundle

### Objective
Create a disciplined calibration package.

### Build tasks
- define calibration schema,
- implement observed target loading,
- implement assumptions layer,
- compute derived ratios,
- store parameter provenance,
- generate calibration notes.

### Deliverables
- `CalibrationBundle`,
- provenance table,
- calibration notes doc.

### Tests
- bounds and completeness,
- share sums,
- derived-ratio admissibility,
- stable checksum.

## Epic 3: build the reference-period initializer

### Objective
Initialize the U.S. simulator from one reference state.

### Build tasks
- construct aggregate state,
- construct household-bin state,
- construct sector state,
- construct expectations state,
- validate state domains,
- serialize reference state.

### Deliverables
- reference state builder,
- serialized state artifact,
- initialization diagnostics.

### Tests
- no impossible states,
- mass conservation,
- accounting consistency,
- serialization roundtrip.

## Epic 4: build the measurement layer

### Objective
Map latent simulator outputs to U.S. observables.

### Build tasks
- define measurement contracts,
- implement target mappings,
- implement transformations,
- expose diagnostics,
- decouple evaluation from engine internals.

### Deliverables
- measurement module,
- mapping config,
- mapping tests.

### Tests
- unit correctness,
- transform correctness,
- expected outputs on fixtures.

## Epic 5: build the forecast runner

### Objective
Run deterministic and stochastic U.S. forecasts.

### Build tasks
- deterministic runner,
- Monte Carlo runner,
- artifact persistence,
- scenario hooks,
- configuration support.

### Deliverables
- forecast runner,
- forecast artifact schema,
- run manifest.

### Tests
- fixed-seed reproducibility,
- path dimensionality checks,
- artifact completeness.

## Epic 6: build recursive pseudo-real-time backtesting

### Objective
Run genuine backtests.

### Build tasks
- origin scheduler,
- vintage constructor,
- expanding or rolling protocol,
- forecast execution per origin,
- metric collection.

### Deliverables
- backtest runner,
- metric tables,
- origin-level artifact storage.

### Tests
- no future leakage,
- correct origin-horizon grids,
- compatibility with fixtures and reduced real data.

## Epic 7: build benchmark and DSGE comparison suite

### Objective
Compare the simulator fairly.

### Build tasks
- implement simple statistical baselines,
- implement factor or small-system baseline,
- implement DSGE-style comparison baseline,
- ensure shared evaluation pipeline,
- generate relative scorecards.

### Deliverables
- benchmark modules,
- benchmark protocol doc,
- comparison report outputs.

### Tests
- same data constraints across models,
- same forecast origins/horizons,
- score reproducibility,
- regression tests for benchmark definitions.

## Epic 8: build the validation harness

### Objective
Make the build trustworthy.

### Build tasks
- create validation registry,
- implement hard gates,
- implement soft diagnostics,
- implement data/identity/forecast/cross-section/scenario checks,
- aggregate status into one report.

### Deliverables
- validation subsystem,
- validation configs,
- machine-readable status outputs,
- HTML report generator.

### Tests
- each validator unit tested,
- end-to-end validation run on fixtures,
- report generation tested.

## Epic 9: build reporting and dashboards

### Objective
Make outputs auditable and usable.

### Build tasks
- report templates,
- plot generators,
- summary tables,
- comparison dashboards,
- warning surfaces.

### Deliverables
- HTML report,
- markdown summary,
- figure bundle.

### Tests
- all charts render,
- report sections present,
- links to artifacts valid.

---

# 21. Stage 2 implementation roadmap: what Codex should do after Stage 1 works

The future work should be included in the design now even if not fully implemented immediately.

## 21.1 External sector upgrade

### Why
A baseline built for another economy will likely mis-handle the U.S. external block.

### Build goals
- replace the inherited rest-of-world logic with a large-open-economy external structure,
- incorporate import exposure,
- add import-price and external-price pass-through,
- allow exchange-rate-sensitive transmission,
- add foreign-demand sensitivity.

### Validation goals
- import-price shock replay,
- external-demand scenario,
- exchange-rate scenario,
- trade share consistency.

## 21.2 Housing and mortgage block

### Why
U.S. mortgage structure and lock-in matter enormously for transmission.

### Build goals
- owner/renter state,
- mortgage cohorts or vintages,
- refinance option logic,
- lock-in effect,
- residential investment channel,
- debt-service mapping.

### Validation goals
- housing-sensitive replay,
- refinance wave behavior,
- differential effect of rate shocks on borrowers and renters,
- coherence with residential investment and house prices.

## 21.3 Finance and credit block

### Why
The U.S. transmission mechanism is broader than a single banking channel.

### Build goals
- coarse breakdown of banks and nonbank credit channels,
- term/spread/financial-conditions transmission,
- credit supply indicators,
- basic stress propagation,
- shadow credit or nonbank spillover placeholders.

### Validation goals
- spread shock scenarios,
- credit stress replays,
- differentiated sector sensitivity.

## 21.4 Multi-speed expectations

### Why
Expectations are heterogeneous in reality.

### Build goals
- households: adaptive or survey-like,
- firms: extrapolative with input-cost sensitivity,
- finance: market-implied,
- policy: rule-based.

### Validation goals
- better replay in inflation and hiking episodes,
- reasonable speed differences by agent group,
- stability under scenario analysis.

## 21.5 Optional ML augmentations

These should be modular and optional.

### Candidate uses
- mortgage cohort behavior model,
- firm stress classifier,
- regime detection,
- ensemble reweighting,
- surrogate speedups.

### Rules
- never use ML to hide structural incoherence,
- benchmark every ML block against a simpler alternative,
- enforce time-based leakage-safe validation,
- keep ML switchable.

---

# 22. Stage 3 roadmap: digital twin mode

Codex should build the interfaces for this now even if the implementation is later.

## 22.1 Twin-mode goals

- update latent states with new releases,
- nowcast missing current-period quantities,
- update coarse distributions not just aggregates,
- produce refreshed forecasts quickly,
- support faster scenario mode.

## 22.2 Assimilation options

The exact method can be decided later, but the architecture should support:
- Kalman-style updates,
- ensemble filtering,
- particle or approximate sequential methods where necessary,
- posterior state storage and diagnostics.

## 22.3 Twin-mode outputs

- monthly or quarterly update package,
- revised latent state,
- nowcast summary,
- updated predictive density,
- scenario deltas relative to baseline.

---

# 23. Definition of done for Codex tasks

Each task Codex performs should follow one template.

## 23.1 Task specification template

For each task, Codex should define:
- objective,
- files to create or modify,
- interfaces to implement,
- tests to add,
- acceptance criteria,
- command showing completion.

## 23.2 Example task format

```text
Task: Build the U.S. calibration bundle.
Objective:
Create a versioned calibration object for the U.S. baseline simulator.
Files:
- src/us/calibration/schema.py
- src/us/calibration/build_bundle.py
- src/us/calibration/provenance.py
- tests/unit/test_calibration_schema.py
- tests/integration/test_calibration_bundle.py
Requirements:
- support observed targets, inferred parameters, and provisional assumptions
- store provenance for each parameter
- compute a stable hash
Acceptance criteria:
- tests pass
- a calibration bundle and provenance report are written to outputs/
Command:
python scripts/build_reference_state.py --config configs/stage1/us_baseline.yaml
```

Codex should use this structure consistently.

---

# 24. CI and automation requirements

Codex should wire the repository so the harness is usable continuously.

## 24.1 Pull request pipeline

Must run:
- lint and type checks,
- unit tests,
- property tests,
- tiny fixture smoke tests,
- golden serialization tests.

## 24.2 Nightly pipeline

Must run:
- reduced real-data integration tests,
- reduced pseudo-real-time backtest,
- benchmark comparisons,
- validation report generation.

## 24.3 Release pipeline

Must run:
- full backtest,
- full comparison suite,
- scenario set,
- historical replay set,
- performance checks,
- final report bundle.

---

# 25. Open decisions Codex should make explicit rather than implicit

These must be written into config or docs and never buried in code.

- Which exact observed variables are in the Stage 1 target set?
- Which reference quarter is the default initializer?
- Which benchmark models are mandatory for each target variable?
- Which DSGE-style baseline(s) are in scope for the first comparison?
- What tolerances define hard failure for identities?
- Which household and sector bins define the first coarse structure?
- What real-time vintage fidelity is available and what is approximated?
- What is the first acceptable Stage 3 assimilation method?

---

# 26. What not to do

Codex should avoid the following.

- Do not rewrite the simulator before understanding it.
- Do not add fancy model structure before the validation harness exists.
- Do not compare the simulator to benchmarks using inconsistent information sets.
- Do not hard-code calibration assumptions without provenance.
- Do not treat final revised data as pseudo-real-time data.
- Do not report average forecast performance only; report by variable and horizon.
- Do not ignore cross-sectional validation because the aggregates look fine.
- Do not allow ML modules to become untestable black boxes.
- Do not produce outputs that cannot be reproduced from manifests.

---

# 27. Why this build order is correct

The reason for this sequencing is simple.

A macro simulator can fail in three distinct ways:

1. it can be **software-fragile**,
2. it can be **economically incoherent**,
3. it can be **forecast-useless**.

If Codex starts by adding more structure before building the wrapper, data layer, calibration bundle, benchmark comparison, and validation harness, it will become much harder to tell which failure mode is responsible when results disappoint.

By contrast, the build order in this document isolates the problems cleanly:
- first make the engine callable,
- then make the U.S. mapping explicit,
- then make the calibration explicit,
- then make forecasting real,
- then compare against DSGE and simpler models,
- then validate aggressively,
- then extend structure.

That is the highest-leverage path.

---

# 28. Final instruction to Codex

Build the U.S. macro simulator as a disciplined forecasting and scenario platform.

Your first priority is to adapt the current simulator to the U.S. economy, calibrate it cleanly, benchmark it fairly against DSGE-style and simpler baseline models, and build the validation harness at the same time.

Do not treat testing as peripheral. Do not treat benchmark comparison as optional. Do not treat future digital-twin functionality as an excuse to skip the U.S. baseline.

A successful Stage 1 build should make it possible to answer, with evidence:
- does the simulator run coherently as a U.S. model,
- how was it calibrated,
- does it forecast competitively,
- where does it beat DSGE-style baselines,
- where does it lose,
- are its internal mechanics trustworthy,
- and what should be built next.

That is the objective this repository should be optimized for.

