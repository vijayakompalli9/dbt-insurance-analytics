from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import duckdb
import pytest

from insurance_analytics.exceptions import MartMissingError, WarehouseNotFoundError
from insurance_analytics.exporter import MartExporter, to_markdown
from insurance_analytics.logging_utils import KeyValueFormatter
from insurance_analytics.snapshot_history import month_ends


def test_month_ends_cover_inclusive_range() -> None:
    ends = list(month_ends(date(2024, 1, 31), date(2024, 4, 30)))
    assert ends == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31), date(2024, 4, 30)]


def test_month_ends_crosses_year() -> None:
    assert list(month_ends(date(2024, 12, 1), date(2025, 1, 5))) == [
        date(2024, 12, 31),
        date(2025, 1, 31),
    ]


def test_to_markdown_renders_table() -> None:
    md = to_markdown(["a", "b"], [(1, None), ("x", 2.5)])
    assert md.splitlines() == ["| a | b |", "| --- | --- |", "| 1 |  |", "| x | 2.5000 |"]


def test_exporter_requires_warehouse(tmp_path: Path) -> None:
    with pytest.raises(WarehouseNotFoundError):
        MartExporter(tmp_path / "missing.duckdb")


def test_exporter_reports_missing_marts(tmp_path: Path) -> None:
    db = tmp_path / "empty.duckdb"
    duckdb.connect(str(db)).close()
    with pytest.raises(MartMissingError):
        MartExporter(db).export(tmp_path / "out")


def test_key_value_formatter_includes_extras() -> None:
    record = logging.LogRecord("t", logging.INFO, "", 0, "hello world", None, None)
    record.rows = 5
    line = KeyValueFormatter().format(record)
    assert 'msg="hello world"' in line and "rows=5" in line and "level=INFO" in line
