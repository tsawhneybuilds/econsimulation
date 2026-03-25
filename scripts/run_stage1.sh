#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/outputs/stage1"
AGGREGATE_CSV=""
START_ORIGIN="2017Q1"
END_ORIGIN="2019Q4"
HORIZON="4"
N_SIMS="4"
SEED="42"
CALIBRATION_DATE="2016-12-31T00:00:00"
DATA_MODE="fixture"
FIXTURE_TIER="tier_b"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --aggregate-csv)
      AGGREGATE_CSV="$2"
      DATA_MODE="real"
      shift 2
      ;;
    --start-origin)
      START_ORIGIN="$2"
      shift 2
      ;;
    --end-origin)
      END_ORIGIN="$2"
      shift 2
      ;;
    --horizon)
      HORIZON="$2"
      shift 2
      ;;
    --n-sims)
      N_SIMS="$2"
      shift 2
      ;;
    --seed)
      SEED="$2"
      shift 2
      ;;
    --calibration-date)
      CALIBRATION_DATE="$2"
      shift 2
      ;;
    --fixture-tier)
      FIXTURE_TIER="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"
"${ROOT_DIR}/scripts/bootstrap_julia.sh"
export PATH="${HOME}/.juliaup/bin:${PATH}"
JULIA_BIN="$(command -v julia)"

if [[ -z "${AGGREGATE_CSV}" ]]; then
  INPUT_DIR="${OUTPUT_DIR}/inputs"
  mkdir -p "${INPUT_DIR}"
  python3 "${ROOT_DIR}/us_macro_simulator/scripts/export_fixture_inputs.py" \
    --fixture-tier "${FIXTURE_TIER}" \
    --output-dir "${INPUT_DIR}" >/tmp/us_fixture_path.txt
  AGGREGATE_CSV="$(tail -n 1 /tmp/us_fixture_path.txt)"
fi

BUNDLE_DIR="${OUTPUT_DIR}/julia_bundle"
mkdir -p "${BUNDLE_DIR}"

"${JULIA_BIN}" --project="${ROOT_DIR}/BeforeIT.jl" "${ROOT_DIR}/BeforeIT.jl/scripts/run_us_stage1.jl" \
  --aggregate-csv "${AGGREGATE_CSV}" \
  --output-dir "${BUNDLE_DIR}" \
  --calibration-date "${CALIBRATION_DATE}" \
  --start-origin "${START_ORIGIN}" \
  --end-origin "${END_ORIGIN}" \
  --horizon "${HORIZON}" \
  --n-sims "${N_SIMS}" \
  --seed "${SEED}" \
  --data-mode "${DATA_MODE}"

python3 "${ROOT_DIR}/us_macro_simulator/scripts/run_stage1.py" \
  --bundle-dir "${BUNDLE_DIR}" \
  --output-dir "${OUTPUT_DIR}"

printf '%s\n' "${OUTPUT_DIR}"
