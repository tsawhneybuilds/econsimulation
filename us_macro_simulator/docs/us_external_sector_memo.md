# U.S. External-Sector And Policy Adaptation

The simulator core remains in Julia. The Stage 1 U.S. adaptation in this repo is intentionally narrow:

## Monetary policy

- The Taylor-rule input has been switched from foreign-area growth and inflation to domestic expected growth and inflation.
- This keeps the Julia policy block intact while making the policy reaction function U.S.-appropriate.

## External sector

- The rest-of-world block is still structurally the Julia block.
- For Stage 1, the `EA` state is reinterpreted as a coarse `global ex-U.S.` proxy.
- Export and import initial conditions are rebased off U.S.-style GDP shares during the origin-specific rebasing step.
- Foreign output and foreign-price proxy series are scaled off the observed U.S. aggregate fixture when building the U.S. calibration object.

## Calibration note

This implementation preserves the Julia structural calibration backbone and overlays U.S.-shaped macro time series plus U.S.-scale origin rebasing. It does not yet replace the full cross-sectional calibration inputs (`figaro` and the structural calibration dictionaries) with true U.S. national accounts tables.
