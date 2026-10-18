#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m geolab.generate
python3 -m unittest discover -s tests -v
python3 -m geolab.evaluate
if command -v node >/dev/null; then
    node --check web/app.js
fi
if command -v rsvg-convert >/dev/null; then
    rsvg-convert reports/teaching.svg -o reports/teaching.png
fi
