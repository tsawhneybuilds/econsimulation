Plan: Fix Julia BeforeIT US Calibration                                      

 Context

 The Julia BeforeIT model produces GDP growth -18% and unemployment 40% for the
  US, while the Python re-implementation achieves RMSE 0.934. The Julia model
 IS the published, validated BeforeIT — we must fix the calibration data, not
 weaken the model mechanics.

 The Python model "worked" by deviating from BeforeIT in stabilizing ways (no
 firing, adaptive expectations, no capital constraint on labor demand). These
 are model simplifications, not something we want to copy. The correct approach
  is to feed the Julia model properly calibrated data so it doesn't enter a
 deflationary spiral in step 1.

 ---
 Root Causes (Priority Order)

 1. Time Series Splice Discontinuity (PRIMARY CAUSE)

 build_us_calibration does:
 1. data = deepcopy(ITALY_CALIBRATION.data) — Italian time series in millions
 EUR (real_gdp_quarterly ≈ 404,433)
 2. _overlay_us_observables!(data, payload) — overwrites the last 20 quarters
 with US FRED data in billions USD SAAR (GDPC1 ≈ 19,254)

 This creates a 21x discontinuity at the splice point. The AR(1) estimator
 (estimations.jl:34) runs estimate_next_value(log.(Y)) on this series and
 estimates gamma_e << 0 (economy is collapsing). Then:
 - Q_s_i = Q_d_i * (1 + gamma_e) drops sharply
 - N_d_i = min(Q_s_i, K*kappa) / alpha drops below N_i
 - Julia fires workers immediately (search_and_matching_labour.jl:38)
 - 40% unemployment → consumption crash → GDP crash → spiral

 Fix: Scale ALL monetary level series in data and ea dicts by monetary_scale
 BEFORE the overlay.

 2. sqrt(scale) Bug in retarget_initial_conditions

 us_stage1.jl:499:
 init["N_s"] = max.(...base_init["N_s"] .* sqrt(scale), min_sector_workers)

 When scale ≈ 1.04, sqrt(1.04) ≈ 1.02 — workers barely scale while GDP scales
 by 4%. This creates a mismatch between production capacity and labor supply.

 Fix: Change sqrt(scale) to scale.

 3. Y_EA Hardcoded Multiplier

 us_stage1.jl:497: init["Y_EA"] = gdp_target * 3.0

 Decouples ROW GDP from the estimated AR(1) parameters. When domestic GDP
 changes, ROW should scale proportionally.

 Fix: init["Y_EA"] = base_init["Y_EA"] * scale

 ---
 Implementation (Single File: us_stage1.jl)

 Step 1: Add monetary key classifier (after line 34)

 function _is_monetary_level_key(key::String)::Bool
     key == "quarters_num" && return false
     occursin("unemployment_rate", key) && return false
     occursin("euribor", key) && return false
     occursin("deflator", key) && return false   # price indices = ratios
     occursin("growth", key) && return false      # growth rates =
 dimensionless
     startswith(key, "real_") && return true
     startswith(key, "nominal_") && return true
     startswith(key, "wages") && return true
     startswith(key, "compensation") && return true
     startswith(key, "operating_surplus") && return true
     return false
 end

 Rationale: data dict has ~60 keys. Monetary levels (real_gdp, nominal_gdp,
 wages, etc.) must be scaled; rates (unemployment, euribor), indices
 (deflators), and growth rates must NOT be.

 Step 2: Scale data and ea dicts BEFORE overlay

 In build_us_calibration, between deepcopy and overlay:

 # Compute monetary_scale = US/Italian unit conversion
 us_nominal_gdp_q = payload["nominal_gdp_quarterly"][end]        # ~21,756
 (billions USD)
 it_nominal_gdp_q = structural_base.data["nominal_gdp_quarterly"][end]  #
 ~450,324 (millions EUR)
 monetary_scale = us_nominal_gdp_q / it_nominal_gdp_q            # ≈ 0.0483

 # Scale data dict monetary levels → US units (eliminates splice discontinuity)
 for (key, val) in data
     if val isa AbstractArray{<:Number} && _is_monetary_level_key(key)
         data[key] = val .* monetary_scale
     end
 end

 # Scale ea dict with ROW-appropriate factor
 ea_scale = (payload["real_gdp_quarterly"][end] * 3.0) /
 structural_base.ea["real_gdp_quarterly"][end]
 for (key, val) in ea
     if val isa AbstractArray{<:Number} && _is_monetary_level_key(key)
         ea[key] = val .* ea_scale
     end
 end

 # NOW overlay US data on the tail (smooth transition, no discontinuity)
 _overlay_us_observables!(data, payload)

 Why this works: After scaling, Italian real_gdp_quarterly ≈ 404,433 × 0.0483 ≈
  19,534. US FRED overlay writes ~19,254 to the tail. Ratio ≈ 1.01 — smooth, no
  discontinuity. The AR(1) estimator sees a normal GDP series.

 Step 3: Fix sqrt(scale) (line 499)

 # BEFORE:
 init["N_s"] = max.(Vector{Float64}(base_init["N_s"]) .* sqrt(scale),
 min_sector_workers)
 # AFTER:
 init["N_s"] = max.(Vector{Float64}(base_init["N_s"]) .* scale,
 min_sector_workers)

 Step 4: Fix Y_EA (line 497)

 # BEFORE:
 init["Y_EA"] = gdp_target * 3.0
 # AFTER:
 init["Y_EA"] = Float64(base_init["Y_EA"]) * scale

 Step 5: EA overlay needs nominal GDP tail too

 After the ea scaling and data overlay, add:
 foreign_nominal_gdp = payload["nominal_gdp_quarterly"] .* 3.0 .*
 (payload["gdp_deflator_quarterly"] .* 1.02)
 _overwrite_tail!(ea, "nominal_gdp_quarterly", foreign_nominal_gdp)

 This ensures calibration.jl:151 (ea["gdp_deflator_quarterly"] =
 ea["nominal_gdp_quarterly"] ./ ea["real_gdp_quarterly"]) computes the correct
 EA deflator in the overlay region.

 ---
 Why Python Worked (Reference — NOT to copy)

 ┌──────────────┬────────────────────────────────┬─────────────────────────┐
 │  Mechanism   │    Julia BeforeIT (correct)    │   Python (simplified)   │
 ├──────────────┼────────────────────────────────┼─────────────────────────┤
 │ Firing       │ Immediate when N_d_i < N_i     │ No firing; only 1.5%    │
 │              │                                │ random separation       │
 ├──────────────┼────────────────────────────────┼─────────────────────────┤
 │ Expectations │ AR(1) regression on log(Y)     │ Adaptive: 0.8old +      │
 │              │ history                        │ 0.2new, default 0.5%    │
 ├──────────────┼────────────────────────────────┼─────────────────────────┤
 │ Labor demand │ min(Q_s, K*kappa) / alpha      │ Q_s / alpha             │
 │              │ (capital-constrained)          │ (unconstrained)         │
 ├──────────────┼────────────────────────────────┼─────────────────────────┤
 │ Wages        │ w_bar * min(1.5,               │ w * (1 + pi_e + noise)  │
 │              │ capacity/labor)                │ — always grows          │
 ├──────────────┼────────────────────────────────┼─────────────────────────┤
 │ Quantity     │ None (deterministic gamma_e)   │ Per-firm noise + floor  │
 │ noise        │                                │ at 0                    │
 └──────────────┴────────────────────────────────┴─────────────────────────┘

 The Python model's stability comes from removing the mechanisms that make
 BeforeIT realistic (firing, capital constraints, regression-based
 expectations). With correct calibration data, the Julia model should be stable
  on its own — it works perfectly for Italy and 27 EU countries.

 ---
 File to Modify

 BeforeIT.jl/src/utils/us_stage1.jl

 Changes:
 1. Add _is_monetary_level_key helper (~10 lines, after line 34)
 2. Restructure build_us_calibration to scale data/ea dicts before overlay (~20
  lines)
 3. One-line fix: sqrt(scale) → scale (line 499)
 4. One-line fix: Y_EA scaling (line 497)
 5. Add ea nominal GDP overlay for deflator consistency (~2 lines)

 No other files need changes.

 ---
 Verification

 cd BeforeIT.jl
 julia --project=. scripts/run_us_stage1.jl \
   --aggregate-csv data/us/aggregate_data.csv \
   --output-dir /tmp/julia_us_test \
   --start-origin 2019Q1 --end-origin 2019Q1 \
   --horizon 4 --n-sims 4 --seed 42 --scale 0.0001

 Success criteria:
 - unemployment_rate < 10% at h=1 (was 40%)
 - gdp_growth between -5% and +5% at h=1 (was -18%)
 - No NaN/Inf in any variable
 - p10-p90 range is reasonable (not spanning -90% to +90%)

 Full backtest:
 # Wire backtest_runner.py to call Julia (separate task)
 # Then: python scripts/run_backtest.py
 # Target: GDP RMSE < 1.5
