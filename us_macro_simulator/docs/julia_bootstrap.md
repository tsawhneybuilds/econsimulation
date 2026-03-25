# Julia Bootstrap

The default Stage 1 happy path now assumes the simulator runs in `BeforeIT.jl` and Python only evaluates the exported artifact bundle.

## Local bootstrap

Use the repo wrapper:

```bash
./scripts/bootstrap_julia.sh
```

Behavior:

- If a `julia` executable already exists on `PATH` and `VERSION >= 1.9`, the script keeps it and only runs `Pkg.instantiate()` for `BeforeIT.jl`.
- Otherwise it installs Julia through the official `juliaup` installer.
- The wrapper never removes or replaces an existing suitable Julia installation.

## Full pipeline

```bash
./scripts/run_stage1.sh --output-dir /tmp/us_stage1_demo
```

This bootstraps Julia if necessary, exports the Julia bundle, and then runs the Python benchmarking, validation, and reporting shell.
