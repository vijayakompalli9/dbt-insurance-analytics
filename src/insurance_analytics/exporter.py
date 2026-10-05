"""Export sample mart output from the dbt-built DuckDB warehouse.

Reads the marts in read-only mode and writes small CSV extracts plus a
markdown summary to ``docs/sample_output/``, so reviewers can see real output
without running anything.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from insurance_analytics.exceptions import MartMissingError, WarehouseNotFoundError
from insurance_analytics.logging_utils import get_logger

log = get_logger("exporter")

REQUIRED_MARTS = (
    "mart_loss_ratio_monthly",
    "mart_claims_aging",
    "fct_claims",
    "fct_premium_earned",
    "fct_claim_payments",
    "dim_policy",
    "dim_customer",
)


@dataclass(frozen=True)
class Extract:
    """A named query whose result is written to ``<name>.csv``."""

    name: str
    title: str
    sql: str


def build_extracts(schema: str) -> list[Extract]:
    """Return the extract definitions for a given marts schema."""
    s = schema
    return [
        Extract(
            "loss_ratio_by_product_line",
            "Loss ratio by product line (full period and trailing 12 months at as-of month)",
            f"""
            with totals as (
                select product_line_code, product_line_name,
                       sum(written_premium) as written_premium,
                       sum(earned_premium) as earned_premium,
                       sum(paid_loss) as paid_loss,
                       sum(incurred_loss) as incurred_loss,
                       sum(claim_count) as claim_count
                from {s}.mart_loss_ratio_monthly
                group by product_line_code, product_line_name
            ),
            latest as (
                select product_line_code, rolling_12m_loss_ratio, target_loss_ratio,
                       rolling_12m_variance_to_target
                from {s}.mart_loss_ratio_monthly
                where calendar_month = (select max(calendar_month) from {s}.mart_loss_ratio_monthly)
            )
            select t.product_line_code, t.product_line_name, t.written_premium,
                   t.earned_premium, t.paid_loss, t.incurred_loss, t.claim_count,
                   round(t.incurred_loss / nullif(t.earned_premium, 0), 4) as incurred_loss_ratio,
                   l.rolling_12m_loss_ratio, l.target_loss_ratio, l.rolling_12m_variance_to_target
            from totals t join latest l using (product_line_code)
            order by t.earned_premium desc
            """,
        ),
        Extract(
            "loss_ratio_monthly_recent",
            "Monthly loss ratio, last 3 months, all product lines",
            f"""
            select calendar_month, product_line_code, written_premium, earned_premium,
                   paid_loss, incurred_loss, claim_count, paid_loss_ratio,
                   incurred_loss_ratio, rolling_12m_loss_ratio
            from {s}.mart_loss_ratio_monthly
            where calendar_month > (
                select max(calendar_month) - interval 3 month from {s}.mart_loss_ratio_monthly)
            order by calendar_month, product_line_code
            """,
        ),
        Extract(
            "claims_aging",
            "Open-claim aging as of the business date (non-empty buckets)",
            f"""
            select as_of_date, product_line_code, aging_bucket, open_claim_count,
                   case_reserve, net_paid_to_date, avg_days_open, max_days_open
            from {s}.mart_claims_aging
            where open_claim_count > 0
            order by product_line_code, bucket_order
            """,
        ),
        Extract(
            "dim_policy_scd2_example",
            "SCD Type 2 history for one policy (from the snap_policy snapshot)",
            f"""
            select policy_id, version_number, policy_status, annual_premium,
                   coverage_limit, deductible, effective_from, effective_to, is_current
            from {s}.dim_policy
            where policy_id = (
                select min(policy_id) from {s}.dim_policy where version_number = 3)
            order by version_number
            """,
        ),
    ]


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    # Decimals keep their declared scale (money 2dp, ratios 4dp) via str().
    return str(value)


def to_markdown(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    """Render rows as a GitHub-flavoured markdown table."""
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(_cell(v) for v in row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


class MartExporter:
    """Runs extracts against the warehouse and writes CSV + markdown."""

    def __init__(self, db_path: Path, schema: str = "analytics_marts") -> None:
        if not db_path.exists():
            raise WarehouseNotFoundError(
                f"warehouse not found at {db_path}; run `make build` first"
            )
        self.db_path = db_path
        self.schema = schema

    def _check_marts(self, con: duckdb.DuckDBPyConnection) -> None:
        present = {
            r[0]
            for r in con.execute(
                "select table_name from information_schema.tables where table_schema = ?",
                [self.schema],
            ).fetchall()
        }
        missing = [m for m in REQUIRED_MARTS if m not in present]
        if missing:
            raise MartMissingError(f"missing marts in schema {self.schema}: {missing}")

    def export(self, out_dir: Path) -> dict[str, int]:
        """Write every extract and ``summary.md``; returns rows written per extract."""
        out_dir.mkdir(parents=True, exist_ok=True)
        counts: dict[str, int] = {}
        sections: list[str] = []
        with duckdb.connect(str(self.db_path), read_only=True) as con:
            self._check_marts(con)
            row_counts = [
                (m, con.execute(f"select count(*) from {self.schema}.{m}").fetchone()[0])
                for m in REQUIRED_MARTS
            ]
            for ex in build_extracts(self.schema):
                cur = con.execute(ex.sql)
                columns = [d[0] for d in cur.description]
                rows = cur.fetchall()
                with (out_dir / f"{ex.name}.csv").open("w", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh, lineterminator="\n")
                    writer.writerow(columns)
                    writer.writerows([_cell(v) for v in row] for row in rows)
                counts[ex.name] = len(rows)
                sections.append(f"## {ex.title}\n\n{to_markdown(columns, rows)}\n")
                log.info("wrote extract", extra={"extract": ex.name, "rows": len(rows)})
        summary = [
            "# Sample output - Northwind Mutual Insurance (fictional)\n",
            "Generated by `scripts/export_marts.py` from the dbt-built DuckDB warehouse. "
            "All data is synthetic.\n",
            "## Mart row counts\n",
            to_markdown(["relation", "rows"], row_counts) + "\n",
            *sections,
        ]
        (out_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")
        return counts


def main(argv: list[str] | None = None) -> int:
    """CLI entry point used by ``scripts/export_marts.py``."""
    parser = argparse.ArgumentParser(description="Export sample mart output.")
    parser.add_argument("--db", type=Path, default=Path("warehouse/insurance.duckdb"))
    parser.add_argument("--schema", default="analytics_marts")
    parser.add_argument("--out", type=Path, default=Path("docs/sample_output"))
    args = parser.parse_args(argv)
    try:
        MartExporter(args.db, args.schema).export(args.out)
    except (WarehouseNotFoundError, MartMissingError) as exc:
        log.error("export failed", extra={"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
