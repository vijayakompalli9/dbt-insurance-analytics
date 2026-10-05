"""Python helpers for the Northwind Mutual Insurance (fictional) dbt project.

The dbt project is the main artifact. This package only:

* generates deterministic synthetic seed CSVs (``seed_generator``),
* replays the policy snapshot over a sequence of as-of dates so the SCD2
  dimension has real history (``snapshot_history``),
* exports sample mart output from the built DuckDB file (``exporter``).
"""

__version__ = "0.1.0"
