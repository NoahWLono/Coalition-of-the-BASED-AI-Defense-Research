#!/usr/bin/env python3
"""Trusted-checkout entry point; the same verifier is embedded in each package."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cedar.export import main

if __name__ == '__main__':
    raise SystemExit(main())
