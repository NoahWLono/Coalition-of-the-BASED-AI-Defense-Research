#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_root"
export PYTHONPATH="$project_root/src"
python3 -m unittest discover -s tests -v
python3 -m prozorro_compare report
python3 -m prozorro_compare demo
python3 scripts/reconcile.py
python3 scripts/verify_artifacts.py
