"""End-to-end: run scripts/export_marts.py against the dbt-built warehouse."""

from __future__ import annotations

import csv
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def export_dir(built_warehouse: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("sample_output")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "export_marts.py"),
            "--db",
            str(built_warehouse),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return out


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def test_export_writes_all_artifacts(export_dir: Path) -> None:
    expected = {
        "loss_ratio_by_product_line.csv",
        "loss_ratio_monthly_recent.csv",
        "claims_aging.csv",
        "dim_policy_scd2_example.csv",
        "summary.md",
    }
    assert expected <= {p.name for p in export_dir.iterdir()}
    assert "Mart row counts" in (export_dir / "summary.md").read_text()


def test_loss_ratio_extract_is_sane_and_reconciles(export_dir: Path, built_warehouse: Path) -> None:
    rows = _read(export_dir / "loss_ratio_by_product_line.csv")
    assert {r["product_line_code"] for r in rows} == {"PAUTO", "HOME", "RENT", "CPROP", "GLIAB"}
    for r in rows:
        assert float(r["earned_premium"]) <= float(r["written_premium"])
        assert 0 <= float(r["incurred_loss_ratio"]) < 3
    with duckdb.connect(str(built_warehouse), read_only=True) as con:
        earned = con.execute(
            "select sum(earned_premium) from analytics_marts.fct_premium_earned"
        ).fetchone()[0]
    assert sum(float(r["earned_premium"]) for r in rows) == pytest.approx(float(earned), abs=0.05)


def test_scd2_example_has_contiguous_history(export_dir: Path) -> None:
    rows = _read(export_dir / "dim_policy_scd2_example.csv")
    assert [int(r["version_number"]) for r in rows] == [1, 2, 3]
    for prev, nxt in pairwise(rows):
        assert prev["effective_to"] == nxt["effective_from"]
    assert [r["is_current"] for r in rows] == ["False", "False", "True"]


def test_aging_buckets_only_hold_open_claims(export_dir: Path, built_warehouse: Path) -> None:
    rows = _read(export_dir / "claims_aging.csv")
    with duckdb.connect(str(built_warehouse), read_only=True) as con:
        open_claims = con.execute(
            "select count(*) from analytics_marts.fct_claims where is_open"
        ).fetchone()[0]
    assert sum(int(r["open_claim_count"]) for r in rows) == open_claims
