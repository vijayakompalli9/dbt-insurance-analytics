from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from insurance_analytics.seed_generator import (
    GeneratorConfig,
    SeedGenerator,
    add_months,
)

EXPECTED_TABLES = {
    "product_lines",
    "customers",
    "policies",
    "policy_changes",
    "premiums",
    "claims",
    "claim_payments",
}


@pytest.fixture(scope="module")
def tables() -> dict[str, list[dict]]:
    return SeedGenerator(GeneratorConfig()).generate()


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2024, 1, 31), 1, date(2024, 2, 29)),  # leap-year clamp
        (date(2025, 1, 31), 1, date(2025, 2, 28)),
        (date(2024, 11, 15), 2, date(2025, 1, 15)),  # year rollover
        (date(2024, 3, 10), 12, date(2025, 3, 10)),
    ],
)
def test_add_months_clamps_and_rolls_over(start: date, months: int, expected: date) -> None:
    assert add_months(start, months) == expected


def test_generator_is_deterministic(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    SeedGenerator(GeneratorConfig(seed=7)).write(a)
    SeedGenerator(GeneratorConfig(seed=7)).write(b)
    for name in EXPECTED_TABLES:
        assert (a / f"{name}.csv").read_bytes() == (b / f"{name}.csv").read_bytes()


def test_committed_seeds_match_generator(tmp_path: Path) -> None:
    """The CSVs in seeds/ must be exactly what the default generator produces."""
    SeedGenerator(GeneratorConfig()).write(tmp_path)
    seeds = Path(__file__).resolve().parents[1] / "seeds"
    for name in EXPECTED_TABLES:
        assert (tmp_path / f"{name}.csv").read_bytes() == (seeds / f"{name}.csv").read_bytes()


def test_all_tables_present_and_small(tables: dict[str, list[dict]]) -> None:
    assert set(tables) == EXPECTED_TABLES
    assert all(rows for rows in tables.values())
    assert max(len(rows) for rows in tables.values()) < 6000


def test_injected_data_issues_exist(tables: dict[str, list[dict]]) -> None:
    policy_ids = {p["policy_id"] for p in tables["policies"]}
    orphans = [c for c in tables["claims"] if c["policy_id"] not in policy_ids]
    assert len(orphans) == 4
    customer_ids = [c["customer_id"] for c in tables["customers"]]
    assert len(customer_ids) > len(set(customer_ids)), "expected stale duplicate customers"
    premium_ids = [p["premium_id"] for p in tables["premiums"]]
    assert len(premium_ids) > len(set(premium_ids)), "expected re-sent premium rows"
    assert any("/" in c["loss_date"] for c in tables["claims"]), "expected messy date formats"


def test_premium_installments_never_exceed_twelve(tables: dict[str, list[dict]]) -> None:
    assert max(int(p["installment_number"]) for p in tables["premiums"]) <= 12


def test_recoveries_are_negative_and_others_positive(tables: dict[str, list[dict]]) -> None:
    for p in tables["claim_payments"]:
        if p["payment_type"] == "RECOVERY":
            assert p["amount_cents"] < 0
        else:
            assert p["amount_cents"] >= 0


def test_only_reserved_example_domains(tmp_path: Path) -> None:
    SeedGenerator(GeneratorConfig()).write(tmp_path)
    with (tmp_path / "customers.csv").open() as fh:
        emails = [row["email"].lower() for row in csv.DictReader(fh)]
    assert all(e.endswith("example.com") for e in emails)
