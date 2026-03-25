# U.S. Macro Simulator: Technical Plan, Validation Harness, and Test Strategy

## 1. Objective

Build a U.S.-specific macro simulation system that starts as a runnable forecasting engine and evolves into a digital-twin style updating system. The implementation should preserve as much of the existing engine as possible at the start, while adding a rigorous validation harness from day one so that model credibility is earned through disciplined testing rather than post-hoc explanation.

This document is written so an implementation agent can use it as a build spec.

---

## 2. Product goals and non-goals

### Goals

* Run a first end-to-end U.S. baseline simulation with one reference-quarter initialization.
* Produce recursive pseudo-real-time forecasts.
* Compare performance against simple benchmark models.
* Validate both aggregate behavior and coarse cross-sectional behavior.
* Extend the baseline in a phased way toward external-sector, housing, finance, expectations, and then digital-twin functionality.
* Make every run reproducible, versioned, and testable.

### Non-goals for the first version

* No deep learning core replacing the economic engine.
* No full HANK rewrite.
* No rich finance superstructure before the baseline runs cleanly.
* No policy RL inside the simulator.
* No premature optimization that sacrifices transparency.

---

## 3. Design principles

1. **Preserve the core engine first.** The first U.S. version should be as close as possible to the current engine, with only the minimum wrappers required for U.S. data, calibration, measurement, and evaluation.
2. **Treat validation as a first-class subsystem.** The harness is not an appendix. It is part of the product.
3. **Separate latent state from observed data.** The simulator produces latent internal states; a measurement layer maps these to observed U.S. macro series.
4. **Use pseudo-real-time evaluation from the beginning.** Never evaluate only on final revised data if the intended use is forecasting.
5. **Fail on accounting inconsistencies before scoring forecast performance.** If identities fail, forecast metrics are not meaningful.
6. **Prefer modular blocks with explicit interfaces.** External sector, housing, finance, expectations, and assimilation should be swappable modules.
7. **Every important object must be serializable.** State, config, calibration, seeds, forecast outputs, diagnostics, and validation artifacts must all be storable and reloadable.
8. **Benchmarks are mandatory.** The simulator must beat or at least complement simpler alternatives.

---

## 4. Phased roadmap

## Stage 1: Runnable U.S. baseline + validation harness

### Purpose

Prove the stack is real. Get a crude but functioning U.S. version running end-to-end.

### Deliverables

* First U.S. smoke-test simulation.
* One reference-quarter initialization.
* Aggregate national-accounting spine.
* U.S. calibration object.
* Simple U.S. household / firm / sector mapping.
* Monte Carlo forecast runner.
* Recursive pseudo-real-time forecasting workflow.
* Baseline benchmark suite.
* Dashboards and validation report generation.
* Basic cross-sectional validation by coarse bins.

### Acceptance criteria

* A single command runs the U.S. baseline from raw processed inputs to a forecast report.
* All Stage 1 hard tests pass.
* Forecasts are reproducible given a fixed seed and data vintage.
* Benchmark report is generated automatically.
* Validation report includes aggregate metrics, identity checks, and cross-sectional sanity checks.

## Stage 2: U.S.-critical transmission blocks

### Purpose

Fix the mechanisms that are structurally wrong for the U.S.

### New blocks

* Large-open-economy external sector.
* Housing and mortgage block.
* Broader finance block.
* Multi-speed expectations system.
* Optional ML components for selected subproblems.

### Deliverables

* Materially better performance in at least some key variables.
* Believable rate transmission for U.S. episodes.
* Better cross-sectional realism.
* Sensible episode replays for inflation/hiking-cycle periods.

## Stage 3: Digital twin mode

### Purpose

Turn the simulator into an updating system rather than only a research model.

### New capabilities

* Explicit data assimilation.
* Hidden-state nowcasting.
* Cross-sectional state updating.
* Ensemble reweighting.
* Faster scenario mode.
* Separation between research mode and production twin mode.

### Deliverables

* Rolling monthly/quarterly update process.
* Density forecasts with calibration checks.
* Credible scenario analysis.
* Outputs answering who gets hit by sector / region / household bin.

---

## 5. Repository structure

```text
repo/
  configs/
    base/
    stage1/
    stage2/
    stage3/
    benchmarks/
    validation/
  data/
    raw/
    interim/
    processed/
    vintages/
    fixtures/
  src/
    engine/
      core/
      transitions/
      shocks/
      expectations/
      measurement/
    us/
      calibration/
      mapping/
      initialization/
      data_contracts/
      sector_blocks/
    forecasting/
      runners/
      monte_carlo/
      benchmarks/
      evaluation/
    validation/
      data_quality/
      identities/
      invariants/
      forecast/
      cross_section/
      scenario/
      replay/
      performance/
      reports/
    assimilation/
    dashboards/
    utils/
  tests/
    unit/
    property/
    integration/
    regression/
    golden/
    performance/
  notebooks/
  scripts/
    build_dataset.py
    run_smoke.py
    run_backtest.py
    run_benchmarks.py
    run_validation.py
    generate_report.py
  ci/
  docs/
```

---

## 6. System architecture

## 6.1 Core layers

### A. Engine layer

Responsible for latent state transition logic.

Key interfaces:

* `SimulationState`
* `TransitionContext`
* `ShockProcess`
* `SectorBlock`
* `MeasurementMapper`
* `ForecastRunner`

### B. U.S. adaptation layer

Wraps the original engine with U.S.-specific calibration, mappings, and observed-data measurement rules.

Key responsibilities:

* U.S. calibration object.
* Sectoral and household bin definitions.
* Initialization from one reference quarter.
* Mapping between model objects and observed series.

### C. Data layer

Produces clean, versioned, vintage-aware datasets.

Key responsibilities:

* Raw ingestion.
* Unit standardization.
* Frequency harmonization.
* Vintage management.
* Feature assembly.
* Cross-sectional bin construction.

### D. Forecasting layer

Runs recursive pseudo-real-time experiments.

Key responsibilities:

* Expanding-window or rolling-window backtests.
* Monte Carlo paths.
* Benchmark generation.
* Metric calculation.
* Forecast artifact storage.

### E. Validation layer

Checks whether the model is internally coherent and externally useful.

Key responsibilities:

* Data QA.
* Identity tests.
* Initialization checks.
* Historical replay tests.
* Forecast evaluation.
* Cross-sectional validation.
* Scenario and sensitivity testing.
* Reproducibility and performance tests.

### F. Reporting layer

Builds dashboards and validation reports.

Outputs:

* HTML report.
* JSON metrics bundle.
* CSV tables.
* Episode replay charts.
* Test pass/fail summary.

---

## 6.2 Core domain objects

### `SimulationState`

Fields should include at minimum:

* `time_index`
* `aggregate_state`
* `household_state`
* `firm_state`
* `sector_state`
* `financial_state`
* `expectations_state`
* `latent_shocks`
* `rng_state`

### `CalibrationBundle`

* Structural parameters.
* Mapping parameters.
* Measurement parameters.
* Initial distributions.
* Hyperparameters for stochastic simulation.
* Version hash.

### `ObservedDataset`

* Vintage timestamp.
* Frequency.
* Series metadata.
* Transform metadata.
* Release lag metadata.

### `ForecastArtifact`

* Config hash.
* Calibration hash.
* Data vintage hash.
* Seed.
* Forecast origin.
* Horizon.
* Point forecasts.
* Density forecast summaries.
* Validation summaries.

---

## 7. Stage 1 implementation plan

## Epic 0: Project scaffold and contracts

### Tasks

* Create repo scaffold.
* Define configuration system.
* Define canonical data schemas.
* Define serialization format for state and outputs.
* Add experiment IDs and run manifests.

### Acceptance tests

* Example config validates.
* Empty smoke pipeline runs through all major steps with fixture data.
* All outputs are written to deterministic locations.

## Epic 1: U.S. data contracts and processed dataset builder

### Tasks

* Build loaders for core aggregate U.S. macro series.
* Implement transform registry.
* Implement vintage-aware dataset builder.
* Build reference-quarter snapshot generator.
* Create fixture datasets for CI.

### Acceptance tests

* Processed dataset is reproducible from raw inputs.
* Missing-value policy enforced.
* Frequency alignment tested.
* Release-lag metadata present for real-time evaluation.

## Epic 2: National accounting spine

### Tasks

* Implement aggregate accounting identity layer.
* Map model aggregates to NIPA-style observed series.
* Build consistency checks for expenditure, income, and sector balances where feasible.

### Acceptance tests

* Accounting tests pass on initialization.
* Accounting tests pass after one transition step.
* Measurement layer emits interpretable observed variables.

## Epic 3: U.S. calibration object

### Tasks

* Create `CalibrationBundle` for the U.S. baseline.
* Include aggregate ratios, initialization shares, shock process defaults, coarse household bins, and coarse firm/sector bins.
* Separate directly observed calibrations from assumed values.

### Acceptance tests

* Calibration object can be loaded from config.
* Each parameter has provenance metadata.
* Calibration checksum stable across runs.

## Epic 4: Reference-quarter initialization

### Tasks

* Build initialization routine from a selected reference quarter.
* Populate aggregate state and coarse distributions.
* Create a validator for impossible initial states.

### Acceptance tests

* No negative stocks where forbidden.
* Coarse cross-sectional shares sum to one.
* Derived ratios lie in admissible ranges.

## Epic 5: Baseline forecast runner

### Tasks

* Wrap the existing engine in a U.S. runner.
* Add Monte Carlo path generation.
* Add deterministic and stochastic modes.
* Save full run artifacts.

### Acceptance tests

* One end-to-end baseline run completes successfully.
* Stochastic mode is reproducible with a fixed seed.
* Forecast shapes are correct for all horizons.

## Epic 6: Recursive pseudo-real-time backtesting

### Tasks

* Implement expanding-window evaluation loop.
* Freeze each forecast origin to a valid vintage.
* Support multiple horizons.
* Persist all origin-level outputs.

### Acceptance tests

* No leakage from future revisions.
* Backtest produces origin-by-horizon metric tables.
* Evaluation works on fixture data in CI and full data offline.

## Epic 7: Benchmark suite

### Required benchmarks

* Random walk where appropriate.
* AR and ARIMA-class baselines.
* Local mean / drift benchmarks.
* Factor model benchmark.
* Small semi-structural benchmark for key macro variables.

### Acceptance tests

* Benchmarks run under the same vintage protocol.
* Metric comparison tables generated automatically.
* Simulator and benchmark forecasts are directly comparable.

## Epic 8: Validation and dashboard reporting

### Tasks

* Generate an HTML validation report.
* Generate machine-readable JSON output.
* Include metrics, identities, cross-sectional checks, and episode replays.

### Acceptance tests

* Report generation succeeds after every full backtest.
* Failures are surfaced clearly.
* Charts render without manual work.

---

## 8. Stage 2 implementation plan

## Epic 9: External sector block

### Scope

* Large-open-economy trade structure.
* Import exposure.
* External prices.
* Exchange-rate-sensitive channels.

### Validation focus

* Import price pass-through.
* Trade sensitivity to external demand and exchange rate.
* Reasonable response under dollar appreciation / commodity shocks.

## Epic 10: Housing and mortgage block

### Scope

* Owner vs renter split.
* Mortgage cohorts / vintages.
* Refinance and lock-in effects.
* Residential investment.

### Validation focus

* Mortgage payment distributions.
* Refi waves around rate changes.
* House-price / rate / investment co-movement.
* Lock-in behavior under sharp rate increases.

## Epic 11: Broader finance block

### Scope

* Bank credit.
* Term and spread transmission.
* Financial conditions.
* Basic nonbank spillovers.
* Decompose institutions at least into GSIBs, regionals, credit unions, and selected shadow/nonbank categories.

### Validation focus

* Loan growth response to policy and spreads.
* Spread widening episodes.
* Bank vs nonbank transmission differences.
* Simple balance-sheet stress propagation.

## Epic 12: Multi-speed expectations

### Scope

* Households: adaptive / survey-like.
* Firms: extrapolative with input-cost sensitivity.
* Finance: market-implied.
* Policy: rule-based.

### Validation focus

* Different sectors should react at different speeds.
* Expectations should improve certain episode replays even if unconditional forecast gains are modest.

## Epic 13: Optional ML augmentations

### Allowed early use cases

* Mortgage cohort behavior models.
* Firm stress classifiers.
* Regime detection.
* Ensemble reweighting.

### Guardrails

* ML components must be optional and swappable.
* Each ML component must have its own benchmark and ablation tests.
* Do not hide major structural weaknesses behind black-box residual fixes.

---

## 9. Stage 3 implementation plan

## Epic 14: Data assimilation layer

### Scope

* Kalman-style or ensemble-style state updating where feasible.
* Hidden-state nowcasting.
* Updating distributions, not only aggregates.

### Acceptance criteria

* Twin mode can ingest a new release and update hidden state without full recalibration.
* Posterior state updates are logged and explainable.

## Epic 15: Research mode vs twin mode separation

### Requirement

Two explicit modes:

* `research_mode`: slower, more flexible, experimental.
* `twin_mode`: constrained, versioned, updateable, operational.

### Acceptance criteria

* Shared interfaces but separate configs.
* Twin mode forbids future-data leakage by construction.

---

## 10. Data inventory

This section is exhaustive by category. Not every source is needed on day one, but the system should be designed so these data classes can be added without schema changes.

## 10.1 Aggregate macro backbone

### Highest priority

* Real GDP and components.
* Nominal GDP and deflators.
* Personal consumption expenditures.
* Gross private domestic investment.
* Residential investment.
* Government spending.
* Net exports.
* Disposable personal income.
* Personal saving rate.
* Corporate profits.
* Labor income measures.
* CPI, core CPI, PCE, core PCE.
* Unemployment, employment, labor-force participation, hours, wages.
* Federal funds rate and short rates.
* Treasury yield curve.

### Why these matter

These series define the aggregate accounting spine, the policy environment, and the baseline transmission targets. Without them, the simulator cannot even be judged on the variables policymakers and forecasters care about.

## 10.2 Monetary and financial conditions

### Priority data

* Treasury yields across maturities.
* Corporate spreads.
* Mortgage rates.
* Bank lending aggregates.
* Financial conditions index.
* Credit growth.
* Loan officer survey indicators.
* Equity price indices.
* House prices.
* Volatility / stress indicators.

### Why these matter

Stage 2 depends on a credible U.S. transmission mechanism. Rate transmission in the U.S. does not work through one policy rate alone; it works through mortgage markets, spreads, bank credit, term structure, and broader financial conditions.

## 10.3 External sector

### Priority data

* Imports and exports by category.
* Import and export price indices.
* Exchange rates / broad dollar index.
* Commodity prices.
* Foreign demand proxies.
* External inflation proxies.

### Why these matter

A small-open-economy external block will not map cleanly to the U.S. The U.S. needs a large-open-economy treatment with import exposure and external-price pass-through.

## 10.4 Housing and mortgages

### Priority data

* House price indices.
* Mortgage rates.
* Mortgage originations and refinance shares.
* Housing starts and permits.
* Existing/new home sales.
* Residential investment.
* Owner/renter shares.
* Mortgage debt service indicators.

### Why these matter

The U.S. has fixed-rate mortgages, mortgage vintages, and lock-in effects. Those features matter for monetary transmission and make simple representative-agent housing blocks misleading.

## 10.5 Household cross-sectional data

### Priority data classes

* Wealth distribution by broad bins.
* Income distribution by broad bins.
* Consumption shares by broad bins.
* Debt holdings by type.
* Homeownership and mortgage incidence.
* Liquid vs illiquid asset shares.
* Demographic / regional splits where available.

### Candidate sources

* SCF.
* CPS ASEC.
* ACS.
* CEX.
* Consumer-credit panel style data if accessible.
* Public survey expectations data.

### Why these matter

Even Stage 1 should validate against coarse bins. A model can look good in aggregates while being nonsensical across households. Coarse binning is enough at first.

## 10.6 Firm and sector data

### Priority data classes

* Sectoral output shares.
* Sectoral employment shares.
* Price / wage sensitivity proxies.
* Investment intensity.
* Leverage / financing mix proxies.
* Input-cost exposure.
* Trade exposure.

### Candidate sources

* Input-output tables.
* Industry accounts.
* Census business statistics.
* Public corporate panel proxies where needed.

### Why these matter

Stage 2 requires heterogeneity in cost exposure, trade exposure, and financing conditions. Even if the first pass is coarse, the schema should support richer sector structure.

## 10.7 Expectations data

### Priority data

* Household inflation expectations.
* Firm pricing / cost expectations where available.
* Professional forecaster expectations.
* Market-implied paths.
* Policy-rule assumptions.

### Why these matter

The plan explicitly calls for multi-speed expectations. This cannot be validated with a single generic expectation proxy.

## 10.8 Real-time and vintage data

### Required metadata even if true vintage data are incomplete

* Release date.
* Period covered.
* Revision date.
* Availability lag.
* Transformation used.

### Why these matter

Pseudo-real-time evaluation is not valid unless each forecast origin only sees what would have been available then.

## 10.9 Synthetic and fixture datasets

These are essential for testing even if they are not economically interesting.

### Required synthetic datasets

* Tiny aggregate fixture with 20 time points and known identities.
* Small cross-sectional fixture with 3 household bins and 3 sectors.
* Synthetic mortgage-cohort fixture with deterministic amortization.
* Synthetic financial-network fixture with known propagation behavior.
* Synthetic assimilation fixture with known hidden state.

### Why these matter

Real macro data are too messy for many unit and property tests. You need small deterministic fixtures where expected outputs are known exactly.

---

## 11. Validation harness architecture

The validation harness should be a separate subsystem, not scattered ad hoc assertions.

## 11.1 Layers of validation

### Layer 1: Data quality validation

Checks raw and processed inputs.

### Layer 2: Initialization validation

Checks whether the starting state is economically and mathematically admissible.

### Layer 3: One-step transition validation

Checks a single simulated transition before full backtests.

### Layer 4: Historical replay validation

Checks whether the model behaves sensibly in known episodes.

### Layer 5: Forecast validation

Checks point and density forecast performance.

### Layer 6: Cross-sectional validation

Checks coarse distributional realism.

### Layer 7: Structural and scenario validation

Checks whether impulse and scenario responses have the right sign, timing, and relative magnitudes.

### Layer 8: Reproducibility and performance validation

Checks determinism, runtime, memory, and artifact completeness.

---

## 11.2 Validation run modes

### PR mode

* Uses small fixtures.
* Runs fast.
* Gating for merges.

### Nightly mode

* Uses larger subsets.
* Runs benchmark suite.
* Produces updated validation report.

### Full research mode

* Runs full pseudo-real-time backtests.
* Produces episode replays and deeper diagnostics.

### Release mode

* Requires all hard checks to pass and performance thresholds not to degrade beyond tolerance.

---

## 12. Exhaustive test catalog

## 12.1 Data ingestion and preprocessing tests

### Schema tests

* Required columns exist.
* Column dtypes are correct.
* Keys are unique where required.
* Time index monotonicity.
* No duplicate timestamps.

**Why:** Prevent silent corruption before modeling starts.

### Unit and transform tests

* Levels vs growth rates correctly tagged.
* Percent vs fraction consistency.
* Annualized vs non-annualized consistency.
* Log / difference transforms verified against known values.

**Why:** Many macro failures are unit mistakes disguised as model failures.

### Frequency alignment tests

* Monthly to quarterly aggregation rules correct.
* Quarterly to monthly carry/interpolation rules explicitly tagged.
* Mixed-frequency joins never use future values.

**Why:** Frequency mistakes create fake forecasting skill and fake dynamics.

### Missingness tests

* Missing-value policy explicit by series.
* Missing blocks detected before runtime.
* Imputation rules logged.

**Why:** Macro data release patterns and gaps are unavoidable; hidden imputation is dangerous.

### Vintage and release-lag tests

* Forecast origin only sees series available by that origin.
* Release lag table applied correctly.
* No revised data leakage.

**Why:** This is the difference between a real forecasting system and an overfit historical reconstruction.

### Outlier and anomaly tests

* Extreme jumps flagged.
* Known crisis periods whitelisted where appropriate.
* Impossible values rejected.

**Why:** Some jumps are real, others are ingestion errors.

## 12.2 Calibration tests

### Parameter schema tests

* All required parameters present.
* Bounds enforced.
* Provenance metadata present.

### Stability tests

* Tiny perturbations of nuisance parameters do not explode the system.
* Invalid parameter combinations fail early.

### Calibration consistency tests

* Ratios implied by calibration match initialization targets within tolerance.
* Shares sum to one.

**Why:** Calibration errors are often subtle and contaminate everything downstream.

## 12.3 Initialization tests

### Accounting initialization tests

* Aggregate resource constraints hold.
* Sector shares sum correctly.
* Stocks and flows consistent where they must be.

### Distribution initialization tests

* Household bin masses sum to one.
* Asset and debt shares nonnegative and sensible.
* Mortgage cohort balances reconcile with totals.

### Admissibility tests

* No impossible state values.
* No NaNs or infinities.
* State within configured domains.

**Why:** A large share of “forecast failures” are really just bad initial states.

## 12.4 One-step transition tests

### Deterministic transition tests

* Given a fixed state and zero shocks, one step produces exactly known outputs on fixtures.

### Shock direction tests

* Contractionary-rate shock should tighten financial conditions, reduce interest-sensitive demand over time, and not create sign reversals that violate model logic.
* Import-price shock should raise inflation-sensitive observables.
* Housing-rate shock should affect mortgage-sensitive cohorts more strongly.

### Conservation tests

* Bookkeeping identities preserved after a transition.

**Why:** If one-step logic is wrong, multi-step forecasts are uninterpretable.

## 12.5 Property-based tests

These are especially valuable.

### Examples

* Shares must remain in [0,1].
* Stocks constrained to be nonnegative stay nonnegative unless signed by design.
* Mass conservation for distributions.
* Deterministic subroutines are invariant to irrelevant column order.
* Serializing and deserializing state preserves value.

**Why:** Property tests catch whole classes of bugs better than one-off examples.

## 12.6 Monte Carlo tests

### Reproducibility tests

* Fixed seed gives identical path ensemble.
* Different seeds yield different but distributionally similar ensembles.

### Distribution sanity tests

* Variance grows or behaves as expected with horizon.
* Quantile ordering preserved.
* No impossible path values due solely to simulation noise.

### Sampling tests

* Shock sampler moments match targets on large draws.

**Why:** Density forecasts are only credible if stochastic plumbing is correct.

## 12.7 Forecast evaluation tests

### Point forecast metrics

* RMSE.
* MAE.
* MAPE or sMAPE when appropriate.
* Relative RMSE vs benchmark.
* Directional accuracy.

### Density forecast metrics

* Coverage of predictive intervals.
* CRPS or similar proper scoring rule.
* Tail-event calibration.
* Sharpness vs calibration tradeoff.

### Horizon-conditional tests

* Metrics by horizon, not only averaged.
* Early horizons vs long horizons separated.

### Origin stability tests

* Metrics not driven by a single origin.
* Rolling degradation tracked.

**Why:** A model can look good on average while failing exactly where the use case matters.

## 12.8 Benchmark comparison tests

### Requirements

* Every forecast run includes benchmark scores.
* Simulator gains must be reported both in absolute and relative terms.
* Benchmarks evaluated under the same vintage protocol.

### Tests

* Benchmark pipeline parity test.
* Metric comparability test.
* Regression test that benchmark definitions do not drift silently.

**Why:** Without fair benchmarks, simulator success is impossible to interpret.

## 12.9 Cross-sectional validation tests

### Coarse household bins

* Wealth-bin asset shares.
* Debt incidence by bin.
* Homeownership incidence.
* MPC-style sensitivity proxies if available.
* Exposure of interest-sensitive spending to rate changes.

### Coarse sector bins

* Sector output shares.
* Sector employment shares.
* Relative exposure to external demand, input costs, and finance.

### Distributional metrics

* Absolute share errors.
* Wasserstein or KS-style distribution distance where useful.
* Calibration plots for bin-level shares.

**Why:** Aggregate realism with distributional nonsense is not enough for policy or scenario use.

## 12.10 Historical replay tests

### Required episodes for Stage 1

* A calm pre-shock period.
* A tightening episode.
* An inflationary episode.

### Required episodes for Stage 2

* 2021–2023 inflation surge.
* 2022–2023 hiking cycle.
* One housing-sensitive episode.
* One credit-stress episode.

### What to test

* Sign and timing of key responses.
* Relative magnitude across channels.
* Whether the model gives a coherent story rather than only a low average error.

**Why:** Macro models are often used precisely during unusual periods. Average historical fit is not enough.

## 12.11 Scenario and structural tests

### Scenario tests

* Policy-rate shock.
* Oil/import-price shock.
* Housing demand shock.
* Credit spread shock.
* External demand slowdown.

### Checks

* Sign restrictions.
* Relative sensitivity by sector and household bin.
* Peak timing within a plausible band.
* No explosive or absurd oscillatory dynamics under moderate shocks.

**Why:** Even before full identification, the model should at least move in sensible directions.

## 12.12 Assimilation tests for Stage 3

### State update tests

* New data release updates only permitted latent states.
* Posterior uncertainty shrinks when informative releases arrive.
* Assimilation does not use unavailable releases.

### Synthetic recovery tests

* On synthetic data with known latent state, assimilation recovers the hidden state within tolerance.

**Why:** A digital twin is only as good as its update mechanism.

## 12.13 ML component tests

For any optional ML module.

### Data leakage tests

* Time-based split enforced.
* No future labels in features.

### Benchmark tests

* Compare against simple statistical baseline.
* Compare against “no ML module” version.

### Stability tests

* Feature perturbation sensitivity.
* Retrain drift monitoring.

### Calibration tests

* Classifier probability calibration where relevant.

**Why:** ML modules can add flexibility but also hidden fragility.

## 12.14 Regression and golden tests

### Golden tests

* Canonical fixture run produces known summary outputs.
* Canonical small backtest produces stable metric tables within tolerance.

### Why

These protect against silent drift when refactoring.

## 12.15 Performance and scalability tests

### Tests

* Runtime budget for PR fixture run.
* Runtime budget for nightly backtest.
* Memory ceiling tests.
* Parallel Monte Carlo scaling test.

**Why:** A validation harness that is too slow will stop being used.

## 12.16 Reproducibility tests

### Tests

* Same config + same data vintage + same seed = identical artifact hash.
* Environment capture included in manifest.
* All charts and tables reproducible from stored artifacts.

**Why:** Reproducibility is non-negotiable for model credibility.

## 12.17 Robustness and adversarial tests

### Examples

* Drop one noncritical series and ensure graceful degradation.
* Corrupt one feature column and verify detection.
* Stress parameters near admissible bounds.
* Run under a structural break window.

**Why:** Real data pipelines and real-time forecasting environments are imperfect.

---

## 13. Hard gates vs soft diagnostics

## Hard gates

These should fail the run.

* Data schema failure.
* Vintage leakage detected.
* Accounting identity failure above tolerance.
* Impossible initialized state.
* Serialization failure.
* Reproducibility failure for fixed seed.
* Missing benchmark outputs.

## Soft diagnostics

These should not necessarily fail the run but must be surfaced prominently.

* Forecast underperformance vs benchmark.
* Cross-sectional miss beyond warning band.
* Poor interval coverage.
* Runtime regression.
* Scenario response that is directionally plausible but poorly timed.

---

## 14. Metrics and scorecards

## Aggregate forecast scorecard

For each variable and horizon:

* RMSE
* MAE
* relative RMSE vs benchmark
* directional accuracy
* coverage of 50/80/95 percent intervals
* CRPS or equivalent

## Cross-sectional scorecard

For each household / sector bin:

* share error
* incidence error
* distance metric
* ranking consistency

## Structural scorecard

* sign correctness
* peak timing band
* peak magnitude band
* persistence band

## Reliability scorecard

* reproducibility pass/fail
* runtime
* memory
* artifact completeness
* percent tests passed

---

## 15. Test data plan

## 15.1 Fixture tiers

### Tier A: tiny deterministic fixtures

Used in unit and property tests.

### Tier B: medium synthetic history

Used in integration and replay tests.

### Tier C: reduced real-data slice

Used in CI nightly tests.

### Tier D: full real-data backtest set

Used in research and release runs.

## 15.2 Golden artifacts to store

* Processed dataset snapshot.
* Reference-quarter initialized state.
* One-step transition output.
* Small Monte Carlo forecast bundle.
* Small backtest metric report.

---

## 16. Reporting requirements

Each full run should produce:

* Run manifest with hashes and timestamps.
* Pass/fail summary by validation layer.
* Aggregate forecast table.
* Benchmark comparison table.
* Cross-sectional validation table.
* Historical replay figures.
* Scenario response plots.
* Calibration provenance appendix.
* Warning section with soft diagnostics.

---

## 17. CI / automation plan

## Pull request checks

* Lint/type checks.
* Unit tests.
* Property tests.
* Tiny fixture smoke test.
* Serialization/golden test.

## Nightly checks

* Medium data integration test.
* Benchmark suite.
* Reduced pseudo-real-time backtest.
* HTML validation report.

## Weekly or release checks

* Full backtest.
* Episode replays.
* Performance benchmarks.
* Calibration drift review.

---

## 18. Recommended build order for an implementation agent

1. Scaffold repo, config, schemas, manifests.
2. Build processed data pipeline with vintage-aware contracts.
3. Implement reference-quarter initialization.
4. Implement accounting spine and measurement mapping.
5. Wrap baseline engine for U.S. run.
6. Add Monte Carlo runner and artifact persistence.
7. Add pseudo-real-time backtest loop.
8. Add benchmark suite.
9. Add validation harness and HTML reporting.
10. Only after Stage 1 is stable, add external sector.
11. Then add housing/mortgages.
12. Then finance decomposition.
13. Then multi-speed expectations.
14. Then assimilation / twin mode.

---

## 19. Codex-oriented task decomposition

Each task should be issued with:

* objective
* files to create or modify
* required interfaces
* tests to add
* acceptance criteria
* example command demonstrating completion

### Example task template

```text
Task: Build the vintage-aware processed dataset builder.
Create:
- src/us/data_contracts/schema.py
- src/us/data_contracts/vintages.py
- src/us/data_contracts/build_dataset.py
- tests/unit/test_schema.py
- tests/integration/test_vintage_builder.py
Requirements:
- enforce series metadata
- enforce release lags
- prohibit future leakage
- output a versioned parquet dataset and manifest
Acceptance criteria:
- all tests pass
- command `python scripts/build_dataset.py --config configs/stage1/data.yaml` writes dataset + manifest
```

This task format should be used for every epic.

---

## 20. Open design decisions that must be made explicitly

* Which exact variables define the minimum Stage 1 target set?
* Which reference quarter will be the default initializer?
* Which benchmark set is mandatory for each variable class?
* What identity tolerances are acceptable for hard failure?
* Which household and sector bins are the first coarse schema?
* How much real-time vintage fidelity is available now versus approximated through release lags?
* Which finance subinstitutions are in-scope in the first finance decomposition?
* What is the first acceptable assimilation method for Stage 3?

These should be written into config, not left implicit.

---

## 21. Minimum viable Stage 1 target variables

Recommended initial target set:

* Real GDP growth.
* Headline inflation.
* Core inflation.
* Unemployment rate.
* Policy rate / short rate.
* Consumption growth.
* Residential investment growth.
* Credit / financial conditions proxy.

Reasoning:
This set is small enough to be tractable but rich enough to expose whether the U.S. transmission story is coherent.

---

## 22. What success looks like

Stage 1 success is not “the model explains everything.”

Stage 1 success means:

* the U.S. baseline runs cleanly,
* the data and calibration pipeline are disciplined,
* validation is automated,
* there is no leakage,
* internal identities mostly hold,
* cross-sectional outputs are at least directionally credible,
* and the model can be fairly compared against simple benchmarks.

Stage 2 success means the model becomes more recognizably U.S.-specific.

Stage 3 success means it becomes an updating system rather than only a research artifact.

---

## 23. Final recommendation

The most important engineering decision is to treat the simulator and validation harness as one product.

If the simulator gets built first and validation later, you will almost certainly end up with a sophisticated system that is hard to trust. If the harness is built alongside the simulator, every subsequent structural extension becomes easier to evaluate, debug, and justify.
