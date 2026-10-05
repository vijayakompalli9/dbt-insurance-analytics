"""Replay the policy snapshot over month-end as-of dates to build SCD2 history.

A dbt snapshot only records history it actually observes: run once against a
fresh warehouse, every policy gets a single version. In production the snapshot
runs on a schedule and history accumulates naturally. To reproduce that locally,
this helper invokes dbt programmatically (``dbtRunner``) once per month-end,
setting ``as_of_date`` so ``int_policy_state_as_of`` shows the book as it looked
on that day, then runs ``dbt snapshot`` on it.

Typical use (what ``make build`` does)::

    python -m insurance_analytics.snapshot_history --fresh
    dbt build --profiles-dir .
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

from insurance_analytics.exceptions import DbtInvocationError
from insurance_analytics.logging_utils import get_logger

log = get_logger("snapshot_history")

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_START = date(2024, 1, 31)
DEFAULT_END = date(2025, 12, 31)


def month_ends(start: date, end: date) -> Iterator[date]:
    """Yield every month-end date from ``start``'s month through ``end``'s month."""
    current = date(start.year, start.month, 1)
    while current <= end:
        nxt = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        yield nxt - timedelta(days=1)
        current = nxt


def _invoke(args: list[str]) -> None:
    # Imported lazily so unit tests of the pure helpers do not need dbt installed.
    from dbt.cli.main import dbtRunner

    result = dbtRunner().invoke(
        [*args, "--project-dir", str(PROJECT_DIR), "--profiles-dir", str(PROJECT_DIR), "--quiet"]
    )
    if not result.success:
        raise DbtInvocationError(f"dbt {' '.join(args)} failed: {result.exception}")


def warehouse_path() -> Path:
    """Resolve the DuckDB file path the same way profiles.yml does."""
    raw = os.environ.get("DBT_DUCKDB_PATH", "warehouse/insurance.duckdb")
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_DIR / path


def replay(start: date, end: date, fresh: bool = False) -> int:
    """Seed, then snapshot policy state at each month-end. Returns snapshots taken."""
    db = warehouse_path()
    if fresh and db.exists():
        log.info("removing existing warehouse", extra={"path": db})
        db.unlink()
    db.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    _invoke(["seed"])
    # Build the policy-state lineage once; the as-of view is re-created per month.
    _invoke(["run", "--select", "+int_policy_state_as_of"])
    count = 0
    for as_of in month_ends(start, end):
        vars_arg = f"{{as_of_date: '{as_of.isoformat()}'}}"
        _invoke(["run", "--select", "int_policy_state_as_of", "--vars", vars_arg])
        _invoke(["snapshot", "--select", "snap_policy", "--vars", vars_arg])
        count += 1
        log.info("snapshot taken", extra={"as_of_date": as_of.isoformat()})
    log.info(
        "snapshot history complete",
        extra={"snapshots": count, "seconds": round(time.perf_counter() - started, 1)},
    )
    return count


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Replay snap_policy over month-ends.")
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument(
        "--fresh", action="store_true", help="delete the local DuckDB warehouse first (recommended)"
    )
    args = parser.parse_args(argv)
    try:
        replay(args.start, args.end, fresh=args.fresh)
    except DbtInvocationError as exc:
        log.error("snapshot replay failed", extra={"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
