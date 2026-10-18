#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$LAB_ROOT"
bash scripts/bootstrap.sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
LAB_OUTPUT=${1:-evidence/reproduced-$(date -u +%Y%m%dT%H%M%SZ)}
LAB_EXIT_STATUS=0
run_stage() {
  if "$@"; then
    return 0
  else
    local stage_status=$?
    printf 'Stage failed with exit %s; continuing evidence artifacts: %s\n' "$stage_status" "$*" >&2
    LAB_EXIT_STATUS=1
  fi
}
run_stage env PYTHONPATH=src .venv/bin/python scripts/suite.py --stage full --output "$LAB_OUTPUT"
run_stage env PYTHONPATH=src .venv/bin/python scripts/summarize.py "$LAB_OUTPUT"
run_stage env PYTHONPATH=src .venv/bin/python scripts/demo.py "$LAB_OUTPUT/4.5.6/01-gcs-loss/schedule-0.0"
run_stage .venv/bin/python scripts/inspect_dataflash.py "$LAB_OUTPUT/4.5.6/04-gcs-recovery/schedule-0.0" "$LAB_OUTPUT/4.5.6/09-gps-stale/schedule-0.0" "$LAB_OUTPUT/4.5.6/10-gcs-rc-compound/schedule-0.0" --output "$LAB_OUTPUT/trace-inspection.json"
run_stage .venv/bin/python scripts/audit_suite.py "$LAB_OUTPUT"
exit "$LAB_EXIT_STATUS"
