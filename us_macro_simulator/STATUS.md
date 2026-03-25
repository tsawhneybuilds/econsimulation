# U.S. Macro Simulator — Stage 1 Build Status

**Last updated:** 2026-03-24
**Reference:** `us_macro_simulator_source_of_truth_build.md`
**Root directory:** `/Users/tanushsawhney/Documents/econsimulation/us_macro_simulator/`

---

## Test Summary

```
50 tests total: 48 passed, 2 failed
```

### Failing Tests (need fixes)

| Test | File | Root Cause |
|---|---|---|
| `test_smoke_gdp_growth_plausible` | `tests/integration/test_smoke.py` | GDP growth blows up to 50% in Q2 — scaling issue in `NIPAMapper` (`_prev_gdp_real` starts at 0, causing division-by-zero on first real step). Fix: initialize `_prev_gdp_real` from state in `map()`. |
| `test_smoke_unemployment_plausible` | `tests/integration/test_smoke.py` | U-rate returns values > 30 — denominator in `NIPAMapper` uses `workers.n_workers` (1000) but only a fraction are in the labour force. Fix: use `H_act - H_inact` as denominator, or use `workers.O_h >= 0` count. |

### Warnings (non-blocking)

- `divide by zero` in `firms.py:107` — `revenue` can be zero before first production step; guarded by `np.where` but numpy still warns. Fix: use `np.errstate` or add eps to denominator.
- `datetime.utcnow()` deprecated in `manifest.py:16` — replace with `datetime.now(datetime.UTC)`.

---

## ✅ Completed Components

### Step 0 — Scaffold
| File | Status |
|---|---|
| `pyproject.toml` | ✅ |
| `configs/base/config.yaml` | ✅ |
| `configs/stage1/us_baseline.yaml` | ✅ |
| `configs/stage1/data.yaml` | ✅ |
| `configs/stage1/backtest.yaml` | ✅ |
| `configs/stage1/calibration.yaml` | ✅ |
| `configs/validation/gates.yaml` | ✅ |
| `configs/benchmarks/stage1.yaml` | ✅ |
| All `src/**/__init__.py` | ✅ |
| `src/utils/manifest.py` | ✅ (minor: fix `utcnow` deprecation) |
| `src/utils/serialization.py` | ✅ |

### Step 1 — Data Contracts & Fixtures
| File | Status |
|---|---|
| `src/us/data_contracts/schema.py` | ✅ |
| `src/us/data_contracts/vintages.py` | ✅ |
| `src/us/data_contracts/build_dataset.py` | ✅ |
| `src/us/data_contracts/loaders.py` | ✅ |
| `data/fixtures/tier_a_aggregate.parquet` | ✅ generated |
| `data/fixtures/tier_b_aggregate.parquet` | ✅ generated |
| `data/fixtures/tier_a_crosssection.parquet` | ✅ generated |
| `data/fixtures/generate_fixtures.py` | ✅ |

### Step 2 — Calibration
| File | Status |
|---|---|
| `src/us/calibration/us_calibration.py` | ✅ |
| `src/us/calibration/us_baseline_2019q4.py` | ✅ |
| `src/us/calibration/provenance.py` | ✅ |
| `src/us/calibration/__init__.py` | ✅ |

### Step 3 — Initialization
| File | Status |
|---|---|
| `src/engine/core/state.py` | ✅ (all agent dataclasses) |
| `src/us/initialization/initializer.py` | ✅ |
| `src/us/initialization/validators.py` | ✅ |
| `src/us/initialization/__init__.py` | ✅ |

### Step 4 — Transitions (33-step loop)
| File | Status |
|---|---|
| `src/engine/transitions/expectations.py` | ✅ |
| `src/engine/transitions/central_bank.py` | ✅ |
| `src/engine/transitions/firms.py` | ✅ (minor: div/zero warning) |
| `src/engine/transitions/credit_market.py` | ✅ |
| `src/engine/transitions/labour_market.py` | ✅ |
| `src/engine/transitions/household_budgets.py` | ✅ |
| `src/engine/transitions/government.py` | ✅ |
| `src/engine/transitions/trade.py` | ✅ |
| `src/engine/transitions/goods_market.py` | ✅ |
| `src/engine/transitions/accounting.py` | ✅ |

### Step 4b — Measurement
| File | Status |
|---|---|
| `src/engine/measurement/nipa_mapper.py` | ✅ (minor: first-step scaling bug, see failing tests) |
| `src/engine/measurement/identities.py` | ✅ |
| `src/engine/shocks/shock_protocol.py` | ✅ (`NoShock`, `RateShock`, `ImportPriceShock`) |

### Step 5 — Engine & Runners
| File | Status |
|---|---|
| `src/engine/core/engine.py` | ✅ (full 33-step loop) |
| `src/forecasting/runners/us_runner.py` | ✅ |
| `src/forecasting/monte_carlo/mc_runner.py` | ✅ |

### Tests Written
| File | Status |
|---|---|
| `tests/unit/test_calibration.py` | ✅ 12/12 pass |
| `tests/unit/test_schema.py` | ✅ 9/9 pass |
| `tests/unit/test_initialization.py` | ✅ 12/12 pass |
| `tests/unit/test_one_step.py` | ✅ 8/8 pass |
| `tests/integration/test_smoke.py` | ⚠️ 4/6 pass (2 fail, see above) |

---

## ❌ Not Yet Built

### Step 6 — Backtest Runner
| File | Status |
|---|---|
| `src/forecasting/runners/backtest_runner.py` | ❌ |
| `src/forecasting/evaluation/metrics.py` | ❌ |
| `src/forecasting/evaluation/scorecard.py` | ❌ |
| `scripts/run_backtest.py` | ❌ |
| `tests/integration/test_backtest.py` | ❌ |

### Step 7 — Benchmark Suite
| File | Status |
|---|---|
| `src/forecasting/benchmarks/random_walk.py` | ❌ |
| `src/forecasting/benchmarks/ar_benchmark.py` | ❌ |
| `src/forecasting/benchmarks/local_mean.py` | ❌ |
| `src/forecasting/benchmarks/factor_model.py` | ❌ |
| `src/forecasting/benchmarks/registry.py` | ❌ |
| `scripts/run_benchmarks.py` | ❌ |
| `tests/unit/test_benchmarks.py` | ❌ |

### Step 8 — Validation Harness
| File | Status |
|---|---|
| `src/validation/data_quality/checker.py` | ❌ |
| `src/validation/identities/checker.py` | ❌ |
| `src/validation/forecast/evaluator.py` | ❌ |
| `src/validation/cross_section/checker.py` | ❌ |
| `src/validation/replay/episode_checker.py` | ❌ |
| `src/validation/scenario/scenario_runner.py` | ❌ |
| `src/validation/performance/checker.py` | ❌ |
| `src/validation/harness.py` | ❌ |
| `src/validation/reports/html_report.py` | ❌ |
| `src/validation/reports/json_report.py` | ❌ |
| `scripts/run_validation.py` | ❌ |
| `scripts/generate_report.py` | ❌ |
| `tests/unit/test_validation_layers.py` | ❌ |

### Step 9 — Dashboards & Reports
| File | Status |
|---|---|
| `src/dashboards/templates/report.html.j2` | ❌ |
| `src/dashboards/charts.py` | ❌ |
| `src/dashboards/builder.py` | ❌ |

### CLI Scripts
| File | Status |
|---|---|
| `scripts/build_dataset.py` | ❌ |
| `scripts/run_smoke.py` | ❌ |

### Missing Tests
| File | Status |
|---|---|
| `tests/unit/test_identities.py` | ❌ |
| `tests/integration/test_vintage_builder.py` | ❌ |

### CI Config
| File | Status |
|---|---|
| `configs/ci/pr.yaml` | ❌ |
| `configs/ci/nightly.yaml` | ❌ |
| `configs/ci/release.yaml` | ❌ |

---

## Known Bugs to Fix First

1. **`nipa_mapper.py` — first-step GDP growth blowup**
   In `NIPAMapper.map()`, `self._prev_gdp_real` is `None` on first call, so the fallback is `agg.gamma_e` (correct). But `_prev_gdp_real` is then set to `gdp_real` after the first call. The issue is the *second* call computes growth from step 0 → step 1, which may be huge because `gdp_real` starts very small (Y/P_bar where P_bar ≈ 1 but Y is the per-firm-scaled sum, not the real economy level). **Fix**: scale GDP consistently — either always use `agg.Y_real` from state (already computed in `accounting.py:set_gross_domestic_product`) rather than recomputing in the mapper.

2. **`nipa_mapper.py` — unemployment rate denominator**
   Currently: `u_rate = unemployed / max(H_act, 1) * 100` where `H_act = 1000`.
   This gives ~0 because most `O_h` entries are 0 (unassigned) only for the small unemployed fraction.
   **Fix**: count `O_h == 0` as unemployed, `O_h > 0` as employed, labour force = `O_h >= 0` count.
   `u_rate = unemployed / max(employed + unemployed, 1) * 100`

3. **`manifest.py:16` — `utcnow()` deprecation**
   Replace `datetime.utcnow()` with `datetime.now(datetime.UTC)`.

4. **`firms.py:107` — divide by zero warning**
   Wrap with `np.errstate(divide='ignore', invalid='ignore')` or add `+ 1e-30` to revenue denominator.

---

## Architecture Notes for Continuation

- **State**: All agent arrays live in `SimulationState` dataclass (`src/engine/core/state.py`). Numpy vectorised over I=100 firms, H=1000 active workers, H_inact=200.
- **Engine loop**: `USMacroEngine.step()` in `engine/core/engine.py` calls all 33 transition functions in BeforeIT.jl order.
- **Calibration**: `build_us_2019q4_calibration()` returns a `CalibrationBundle` with 2019Q4 BEA/BLS/Fed values.
- **Measurement**: `NIPAMapper.map(state)` → `ObservableSnapshot` with annualised GDP growth, CPI, unemployment, FFR, etc.
- **Forecasting**: `USForecastRunner.run(state, T)` → `ForecastArtifact` with `point_forecasts` DataFrame (PeriodIndex, cols = variable names).
- **MC**: `MCRunner.run(state, T, n_sims)` → `MCForecastArtifact` with quantile density summaries.
- **Key variable names** used throughout: `gdp_growth`, `cpi_inflation`, `core_cpi_inflation`, `unemployment_rate`, `fed_funds_rate`, `consumption_growth`, `residential_inv_growth`, `fci`.

---

## Suggested Next Steps (in priority order)

1. **Fix the 2 failing tests** (30 min) — see bugs above
2. **Build metrics + backtest** (`metrics.py`, `scorecard.py`, `backtest_runner.py`) — needed for validation
3. **Build benchmark suite** (5 models + registry) — needed for relative RMSE gates
4. **Build validation harness** (8 layers + `ValidationHarness`) — the central pass/fail gate
5. **Build CLI scripts** (`run_smoke.py`, `run_backtest.py`, `run_validation.py`, `generate_report.py`, `build_dataset.py`)
6. **Build dashboards** (Jinja2 HTML report + matplotlib charts)
7. **CI config** (3 YAML files)
8. **Final end-to-end test** of all 5 verification commands from the build plan
