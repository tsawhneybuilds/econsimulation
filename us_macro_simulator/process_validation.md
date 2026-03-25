# How Testing and Validation Works

This document explains the full testing and validation pipeline for the U.S. macro simulator — from Julia simulation output through Python quality checks to the final HTML/JSON report.

---

## Overview

The system runs in two stages. First, the Julia engine produces forecasts. Then Python validates those forecasts against a battery of checks. Failures are classified as either **hard** (block release) or **soft** (generate a warning).

```
Raw FRED Data / Fixtures
        ↓
[Julia: BeforeIT.jl simulation]
        ↓ 6 artifact files
[Python: Backtest + Validation]
        ↓
JSON + HTML Report
```

---

## Stage 1: What Julia Produces (The Bundle)

After every simulation run, Julia writes 6 files to an output directory:

| File | Contents |
|---|---|
| `manifest.json` | Run metadata — model version, calibration date, origins, seeds, runtime |
| `observed_dataset.csv` | Historical FRED data used by Julia, vintage-masked per origin (no leakage) |
| `simulator_forecasts.csv` | Quarterly forecasts: `origin, period, variable, mean, p10, p50, p90` |
| `initial_measurements.json` | Reference state at calibration date: GDP, C, I, G, NX, unemployment, price level |
| `cross_section_summary.csv` | Income/consumption shares by household tier; output shares by sector |
| `scenario_bundle.json` | Baseline vs. shocked outputs for rate shock and import price shock |

Python's `JuliaArtifactBundle` loader reads all 6 files, validates they are all present, and exposes them for downstream checks.

---

## Stage 2: The Backtest Runner

Before running validation gates, the system runs a **pseudo-real-time backtest** over multiple quarterly origins (default: 2017Q1 through 2019Q4).

### What "pseudo-real-time" means

For each forecast origin (e.g., 2017Q1):
1. Only data that was actually available on that date is shown to the model — a **vintage mask** enforces this. FRED data released after the origin date is hidden.
2. A 4-quarter-ahead forecast is generated.
3. The forecast is evaluated against what actually happened (actuals loaded without masking).

This prevents the model from "cheating" by using data it wouldn't have had in real time.

### Benchmark models

The same origin/horizon grid is run through 5 benchmark models for comparison:

| Name | Description |
|---|---|
| `random_walk` | Forecast = last observed value, held flat |
| `ar4` | AR(4) model fit via OLS, iterated multi-step |
| `local_mean` | Mean of the last 8 observed quarters |
| `factor_model` | PCA extracts 2 factors; each modeled with AR(2) |
| `semi_structural` | Phillips curve + Okun's law + Taylor rule (OLS-fit) |

### Metrics computed per origin per variable

- **RMSE** — Root Mean Squared Error (primary accuracy metric)
- **MAE** — Mean Absolute Error
- **Directional accuracy** — % of forecasts with correct sign
- **Relative RMSE** — RMSE / random walk RMSE (1.0 = matches the naive baseline)
- **Coverage** — % of actuals falling inside the 50% and 90% prediction intervals (when density forecasts available)

All metrics are averaged across origins to produce summary statistics used in the gates below.

---

## Stage 3: The 7 Validation Checks

The `ValidationHarness` runs 7 categories of checks. Each produces one or more `ValidationCheck` objects with `passed`, `severity`, and a detail dict.

### 1. Data Quality
*Checker: `DataQualityChecker`, `BundleVintageChecker`*

| Check | Severity | What it tests |
|---|---|---|
| Required series present | Hard | GDP, CPI, unemployment, fed funds, consumption, investment, FCI all exist |
| No duplicate timestamps | Hard | Observed dataset has a clean monotonic index |
| Vintage leakage | Hard | No post-vintage data appears for any origin |
| Missingness ratio | Soft | Fraction of NaN values ≤ 35% |

### 2. Accounting Identities
*Checker: `IdentityChecker`, `BundleIdentityChecker`*

| Check | Severity | What it tests |
|---|---|---|
| No NaN/Inf | Hard | State variables are finite |
| GDP expenditure identity | Hard | C + I + G + NX ≈ GDP (within 1e-6 relative tolerance) |
| Labour force accounting | Soft | Employed ≤ Labour force |

### 3. Forecast Quality Gates
*Checker: `ForecastEvaluator`*

| Check | Severity | Gate |
|---|---|---|
| RMSE for GDP | Hard | Average RMSE ≤ 3.0 percentage points |
| RMSE for CPI | Hard | Average RMSE ≤ 2.0 percentage points |
| Coverage at 50% | Soft | ≥ 35% of actuals inside 50% interval |
| Coverage at 90% | Soft | ≥ 75% of actuals inside 90% interval |
| Relative RMSE vs. random walk | Soft | Average ≤ 2.0× the random walk baseline |

### 4. Cross-Sectional Realism
*Checker: `CrossSectionChecker`, `BundleCrossSectionChecker`*

Compares simulated household income/consumption distributions and sector output shares to observed benchmark values from FRED fixtures.

| Check | Severity | Gate |
|---|---|---|
| Income shares (low/middle/high) | Soft | Max absolute deviation ≤ 20 percentage points |
| Consumption shares | Soft | Max absolute deviation ≤ 20 percentage points |
| Sector GVA shares (mfg/construction/services) | Soft | Max absolute deviation ≤ 25 percentage points |

### 5. Performance Budget
*Checker: `PerformanceChecker`*

| Check | Severity | Gate |
|---|---|---|
| Runtime | Hard | Backtest completes within 300 seconds |
| Memory | Soft | Peak usage ≤ 2048 MB |

### 6. Scenario Response (Directional)
*Checker: `BundleScenarioChecker`*

Verifies that the model responds in economically sensible directions to two shocks baked into the scenario bundle:

| Shock | Expected direction |
|---|---|
| Rate shock (+0.5%) | Policy rate rises |
| Import price shock (+10%) | Average firm prices rise |

### 7. Deterministic Replay
*Checker: `ReplayEpisodeChecker`*

Reruns the simulation from the same initial state with the same seed and confirms numerical agreement. Ensures reproducibility.

---

## Gate Configuration

All thresholds live in one YAML file:

```
us_macro_simulator/configs/validation/gates.yaml
```

Current values:
```yaml
hard_gates:
  accounting_identity_tolerance: 1.0e-6
  nan_inf_allowed: false
  vintage_leakage_allowed: false
  reproducibility_required: true

performance_gates:
  max_runtime_seconds: 300
  max_memory_mb: 2048

forecast_gates:
  max_rmse_gdp: 3.0
  max_rmse_cpi: 2.0
  min_coverage_50pct: 0.35
  min_coverage_90pct: 0.75

benchmark_gates:
  must_beat_random_walk: false   # soft: warn only
  relative_rmse_threshold: 2.0

dsge_gates:
  must_beat_dsge: false          # soft: warn only in Stage 1
  max_relative_rmse_vs_dsge: 3.0
```

---

## Script Entry Points

```
run_smoke.py          → Single deterministic forecast, quick sanity check
run_stage1.py         → Full pipeline: bundle load + backtest + validation + reports
run_validation.py     → Validation only (assumes backtest already done)
fetch_dsge_data.py    → Download NY Fed DSGE historical forecasts to data/external/
```

### Typical full run

```bash
# 1. Bootstrap Julia and run the simulation
bash scripts/run_stage1.sh

# 2. (or) Run Python pipeline on an existing bundle
python us_macro_simulator/scripts/run_stage1.py \
  --bundle-dir julia_bundle \
  --output-dir outputs/stage1
```

---

## Outputs

Two report files are written to the output directory:

**`validation_report.json`** — Machine-readable structured data:
- `overall_passed`: true/false
- `checks`: list of all check results with name, severity, passed, details
- `summary`: counts of hard failures, soft failures, comparison rows

**`validation_report.html`** — Human-readable dashboard:
- Check results color-coded pass/fail
- Time-series charts: simulator forecasts vs. actuals vs. benchmarks
- Benchmark comparison table (RMSE, relative RMSE, coverage per variable)
- DSGE comparison section (when dsge_nyfed benchmark is active)
- Metadata panels (run ID, calibration date, seeds)

---

## What "Hard" vs "Soft" Means

| Severity | Meaning |
|---|---|
| **Hard** | Failure blocks the run. `overall_passed = false`. Data integrity, numeric correctness, runtime. |
| **Soft** | Warning added to report. Run still passes. Forecast accuracy, realism, distributional checks. |

The idea: you should never produce a forecast with corrupt data or broken accounting. But underperforming a DSGE benchmark by 2× is worth knowing about — not necessarily a showstopper.

---

## Test Hierarchy

Unit tests verify individual components in isolation; integration tests run the full pipeline.

```
tests/unit/
  test_schema.py           — FRED schema and series registry
  test_calibration.py      — Calibration bundle construction
  test_initialization.py   — Model state initialization
  test_julia_bundle.py     — Bundle loading and parsing
  test_validation_layers.py — Harness runs and produces correct report
  test_benchmarks.py       — All benchmark models (including dsge_nyfed)
  test_fred_loader.py      — FRED live loader (15 unit + 2 smoke tests)

tests/integration/
  test_smoke.py            — 8-quarter run: no NaN, plausible ranges, reproducibility
  test_backtest.py         — Multi-origin backtest with vintage masking verification
  test_stage1_pipeline.py  — End-to-end bash script execution
```

Run the full suite:
```bash
cd us_macro_simulator
pytest tests/ -v
```
