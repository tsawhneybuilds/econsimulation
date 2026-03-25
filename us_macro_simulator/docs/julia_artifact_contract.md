# Julia Artifact Contract

The Julia runner writes a canonical Stage 1 bundle. Python consumes this bundle and does not run the simulator in the default path.

## Files

- `manifest.json`
- `observed_dataset.csv`
- `simulator_forecasts.csv`
- `initial_measurements.json`
- `cross_section_summary.csv`
- `scenario_bundle.json`

## `manifest.json`

Required fields:

- `schema_version`
- `run_id`
- `country`
- `simulator`
- `data_mode`
- `calibration_date`
- `start_origin`
- `end_origin`
- `origins`
- `horizon`
- `n_sims`
- `seed`
- `variables`
- `runtime_seconds`
- `observed_origin_label`

## `observed_dataset.csv`

Wide vintage-safe panel with:

- `origin`
- `period`
- raw observed series columns such as `GDPC1`, `CPIAUCSL`, `UNRATE`, `FEDFUNDS`, `PCECC96`, `PRFI`, `FCI`

`origin=full_actuals` is reserved for the unmasked actual history used in benchmark scoring.

## `simulator_forecasts.csv`

Tidy forecast table with:

- `origin`
- `horizon`
- `period`
- `variable`
- `mean`
- `p10`
- `p50`
- `p90`

Python benchmarks and scorecards use `mean` as the point forecast.

## `initial_measurements.json`

Reference-state measurements for identity and numeric checks:

- `gdp_real`
- `consumption_real`
- `investment_real`
- `government_real`
- `exports_real`
- `imports_real`
- `net_exports_real`
- `unemployment_rate`
- `policy_rate`
- `price_level`
- `no_nan_inf`

## `cross_section_summary.csv`

One-row coarse summary for:

- `income_low`, `income_middle`, `income_high`
- `consumption_low`, `consumption_middle`, `consumption_high`
- `gva_mfg`, `gva_construction`, `gva_services`

## `scenario_bundle.json`

Directional scenario payload with at least:

- `rate_shock`
- `import_price_shock`

Each scenario contains `baseline_last_row`, `shocked_last_row`, and `deltas`.
