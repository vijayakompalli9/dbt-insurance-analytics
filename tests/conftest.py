"""Shared fixtures. The e2e fixture builds the dbt project if the warehouse is missing."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "warehouse" / "insurance.duckdb"


def _run(cmd: list[str]) -> None:
    # Subprocesses (not in-process dbtRunner) so no DuckDB file lock outlives the build.
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"{' '.join(cmd)} failed:\n{proc.stdout[-3000:]}{proc.stderr}"


@pytest.fixture(scope="session")
def built_warehouse() -> Path:
    """Path to a fully built DuckDB warehouse (runs the full build once if absent)."""
    if os.environ.get("DBT_DUCKDB_PATH"):
        pytest.skip("e2e tests use the default warehouse path; unset DBT_DUCKDB_PATH")
    if not WAREHOUSE.exists():
        dbt = shutil.which("dbt") or str(Path(sys.executable).parent / "dbt")
        _run([sys.executable, "scripts/build_snapshot_history.py", "--fresh"])
        _run([dbt, "build", "--profiles-dir", ".", "--project-dir", "."])
    return WAREHOUSE
