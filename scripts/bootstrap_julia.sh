#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JULIAUP_BIN="${HOME}/.juliaup/bin"

find_existing_julia() {
  if command -v julia >/dev/null 2>&1; then
    command -v julia
    return 0
  fi
  if [[ -x "${JULIAUP_BIN}/julia" ]]; then
    printf '%s\n' "${JULIAUP_BIN}/julia"
    return 0
  fi
  return 1
}

if JULIA_BIN="$(find_existing_julia)"; then
  if "${JULIA_BIN}" -e 'exit(VERSION >= v"1.9" ? 0 : 1)' >/dev/null 2>&1; then
    "${JULIA_BIN}" --project="${ROOT_DIR}/BeforeIT.jl" -e 'using Pkg; Pkg.instantiate()'
    printf 'Using existing Julia at %s\n' "${JULIA_BIN}"
    exit 0
  fi
fi

echo "Installing Julia via juliaup"
curl -fsSL https://install.julialang.org | sh -s -- --yes
export PATH="${JULIAUP_BIN}:${PATH}"
"${JULIAUP_BIN}/juliaup" add release
"${JULIAUP_BIN}/juliaup" default release
"${JULIAUP_BIN}/julia" --project="${ROOT_DIR}/BeforeIT.jl" -e 'using Pkg; Pkg.instantiate()'
printf 'Installed Julia at %s/julia\n' "${JULIAUP_BIN}"
