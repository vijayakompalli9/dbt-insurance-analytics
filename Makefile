# Northwind Mutual Insurance (fictional) - dbt analytics project.
# All targets run fully offline against a local DuckDB file.

PYTHON ?= python
DBT    ?= dbt
DBT_ARGS = --profiles-dir . --project-dir .

.PHONY: install seeds history build dbt-build run test lint docs freshness export clean

install:  ## Install pinned runtime + dev dependencies and the helper package
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e . --no-deps

seeds:  ## Regenerate the deterministic synthetic seed CSVs
	$(PYTHON) scripts/generate_seeds.py --out seeds

history:  ## Fresh warehouse + seed + replay snap_policy over 24 month-ends (SCD2 history)
	$(PYTHON) scripts/build_snapshot_history.py --fresh

dbt-build:  ## Plain `dbt build` (seeds, models, snapshot, data + unit tests)
	$(DBT) build $(DBT_ARGS)

build: history dbt-build  ## Full local build: snapshot history then dbt build

export:  ## Write sample mart output to docs/sample_output
	$(PYTHON) scripts/export_marts.py --out docs/sample_output

run: build export  ## Build everything and export sample output

test:  ## pytest (unit + e2e; builds the warehouse if it does not exist)
	$(PYTHON) -m pytest

lint:  ## ruff (Python) + sqlfluff with the dbt templater (SQL)
	ruff check .
	ruff format --check .
	sqlfluff lint models data_tests/singular

docs:  ## Generate dbt docs (target/ is git-ignored); serve with `dbt docs serve --profiles-dir .`
	$(DBT) docs generate $(DBT_ARGS)

freshness:  ## Source freshness; reports STALE on the static synthetic data (informational)
	-$(DBT) source freshness $(DBT_ARGS)

clean:
	$(DBT) clean $(DBT_ARGS)
	rm -f warehouse/*.duckdb warehouse/*.wal
