# Benchmark Protocol

## Scope

This protocol defines how the Stage 1 simulator is compared to baseline forecasting models.

## Models Included

- `random_walk`
- `ar4`
- `local_mean`
- `factor_model`
- `semi_structural`

## Data

- Aggregate quarterly fixture data or FRED-backed data loaded through `src/us/data_contracts/build_dataset.py`.
- Observed series are vintage-masked per origin using release-lag metadata.
- Actual realized values are transformed into Stage 1 target variables:
  - GDP growth
  - headline inflation
  - unemployment rate
  - fed funds rate
  - consumption growth
  - residential investment growth
  - financial conditions

## Forecast Origins And Horizons

- Origins are quarterly.
- Each origin uses only the information available as of that quarter-end vintage.
- Horizons are configured through `configs/stage1/backtest.yaml`.

## Comparison Rules

- The simulator and all benchmarks are scored on the same target variables.
- Benchmarks are fit only on history available at the same origin.
- The random walk benchmark is used as the default relative-RMSE reference.
- The semi-structural benchmark provides a small macro-system comparator beyond univariate baselines.

## Metrics

- RMSE
- MAE
- directional accuracy
- relative RMSE versus random walk when available

Coverage and CRPS are reserved for density-capable runs.

## Reporting

- `comparison_table.parquet` stores per-origin, per-model, per-variable metrics.
- `validation_report.json` aggregates hard gates and soft diagnostics.
- `validation_report.html` presents the auditable human-readable summary.
