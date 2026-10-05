"""Thin wrapper around `insurance_analytics.seed_generator` (run from the repo root)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from insurance_analytics.seed_generator import main

if __name__ == "__main__":
    raise SystemExit(main())
