"""Deterministic synthetic data generator for the dbt seeds.

Writes seven CSVs into ``seeds/`` that play the role of a raw landing zone for
Northwind Mutual Insurance (fictional). The same seed always produces
byte-identical files, so the CSVs can be committed and regenerated in CI to
prove determinism.

A small number of deliberate data-quality issues are injected so the staging
layer has real work to do (see ``DataIssues`` and the README).
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from insurance_analytics.exceptions import SeedGenerationError
from insurance_analytics.logging_utils import get_logger

log = get_logger("seed_generator")

AS_OF = date(2025, 12, 31)
WINDOW_START = date(2024, 1, 1)
LAST_EFFECTIVE = date(2025, 11, 30)


@dataclass(frozen=True)
class ProductLine:
    """Pricing and loss assumptions for one line of business."""

    code: str
    name: str
    line_of_business: str
    target_loss_ratio: float
    base_premium: float  # average annual premium in dollars
    frequency: float  # expected claims per policy-year
    severity: float  # mean ultimate loss per claim in dollars
    report_lag_days: float
    settle_days: float
    limits: tuple[int, ...]
    deductibles: tuple[int, ...]
    weight: float
    commercial: bool = False


PRODUCT_LINES: tuple[ProductLine, ...] = (
    ProductLine(
        "PAUTO",
        "Personal Auto",
        "Personal",
        0.68,
        1400,
        0.60,
        1350,
        6,
        70,
        (100_000, 250_000, 500_000),
        (500, 1000),
        0.34,
    ),
    ProductLine(
        "HOME",
        "Homeowners",
        "Personal",
        0.58,
        1800,
        0.50,
        1900,
        9,
        100,
        (300_000, 500_000, 750_000),
        (1000, 2500),
        0.25,
    ),
    ProductLine(
        "RENT",
        "Renters",
        "Personal",
        0.50,
        260,
        0.40,
        320,
        7,
        45,
        (25_000, 50_000),
        (250, 500),
        0.15,
    ),
    ProductLine(
        "CPROP",
        "Commercial Property",
        "Commercial",
        0.55,
        9500,
        0.80,
        6200,
        14,
        160,
        (1_000_000, 2_000_000),
        (5000, 10_000),
        0.13,
        commercial=True,
    ),
    ProductLine(
        "GLIAB",
        "General Liability",
        "Commercial",
        0.62,
        6800,
        0.60,
        6800,
        40,
        280,
        (1_000_000, 2_000_000),
        (0, 2500),
        0.13,
        commercial=True,
    ),
)

FIRST_NAMES = (
    "Avery",
    "Jordan",
    "Priya",
    "Mateo",
    "Lena",
    "Omar",
    "Grace",
    "Hiro",
    "Nia",
    "Samuel",
    "Ines",
    "Ravi",
    "Chloe",
    "Diego",
    "Maya",
    "Felix",
    "Zara",
    "Theo",
    "Anika",
    "Lucas",
    "Mira",
    "Kofi",
    "Elena",
    "Noah",
)
LAST_NAMES = (
    "Alvarez",
    "Brooks",
    "Chen",
    "Dubois",
    "Eriksen",
    "Fischer",
    "Gupta",
    "Hayes",
    "Ibrahim",
    "Jensen",
    "Kowalski",
    "Larsen",
    "Moreau",
    "Nakamura",
    "Okafor",
    "Patel",
    "Quinn",
    "Rossi",
    "Santos",
    "Tanaka",
    "Underwood",
    "Varga",
    "Walsh",
)
BIZ_WORDS = (
    "Harbor",
    "Summit",
    "Maple",
    "Granite",
    "Bluebird",
    "Copper",
    "Lakeside",
    "Prairie",
    "Redwood",
    "Lantern",
    "Orchard",
    "Meridian",
)
BIZ_KINDS = (
    "Bakery",
    "Logistics",
    "Dental",
    "Builders",
    "Outfitters",
    "Brewing",
    "Clinic",
    "Hardware",
    "Studios",
    "Farms",
)
STATES = ("TX", "OH", "GA", "AZ", "NC", "PA", "IL", "CO", "WA", "FL", "MN", "TN")
CAUSES = {
    "PAUTO": ("COLLISION", "COMPREHENSIVE", "LIABILITY", "GLASS"),
    "HOME": ("WATER", "WIND_HAIL", "FIRE", "THEFT"),
    "RENT": ("THEFT", "WATER", "FIRE"),
    "CPROP": ("FIRE", "WIND_HAIL", "WATER", "EQUIPMENT"),
    "GLIAB": ("SLIP_FALL", "PRODUCT", "PROPERTY_DAMAGE"),
}


@dataclass
class DataIssues:
    """Counters for injected data-quality problems (logged for transparency)."""

    counts: dict[str, int] = field(default_factory=dict)

    def bump(self, name: str) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1


@dataclass
class GeneratorConfig:
    """Volume knobs for the generator."""

    seed: int = 42
    n_individuals: int = 320
    n_businesses: int = 70
    n_policies: int = 480
    as_of: date = AS_OF


def add_months(d: date, months: int) -> date:
    """Add calendar months, clamping the day to the target month's length."""
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return date(year, month, min(d.day, (nxt - timedelta(days=1)).day))


def _ts(d: date, hour: int = 2) -> str:
    return datetime.combine(d, time(hour)).strftime("%Y-%m-%d %H:%M:%S")


def _poisson(rng: random.Random, lam: float) -> int:
    threshold, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def _rand_date(rng: random.Random, start: date, end: date) -> date:
    span = max((end - start).days, 0)
    return start + timedelta(days=rng.randint(0, span))


class SeedGenerator:
    """Builds every seed table in memory, then writes CSVs."""

    def __init__(self, config: GeneratorConfig) -> None:
        self.cfg = config
        self.rng = random.Random(config.seed)
        self.issues = DataIssues()
        self.tables: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------ customers
    def _customers(self) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        rng, rows = self.rng, []
        individuals, businesses = [], []
        total = self.cfg.n_individuals + self.cfg.n_businesses
        for i in range(1, total + 1):
            cid = f"CU{i:05d}"
            is_biz = i > self.cfg.n_individuals
            if is_biz:
                first, last = "", f"{rng.choice(BIZ_WORDS)} {rng.choice(BIZ_KINDS)} LLC"
                dob = ""
                email = f"office{i}@{last.split()[0].lower()}.example.com"
                businesses.append(cid)
            else:
                first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
                dob = _rand_date(rng, date(1950, 1, 1), date(2003, 12, 31)).isoformat()
                email = f"{first}.{last}{i}@example.com".lower()
                individuals.append(cid)
            state = rng.choice(STATES)
            if rng.random() < 0.05:
                state = f" {state.lower()} "
                self.issues.bump("customer_state_unclean")
            if rng.random() < 0.08:
                email = email.upper()
                self.issues.bump("customer_email_uppercase")
            since = _rand_date(rng, date(2012, 1, 1), date(2023, 12, 31))
            row = {
                "customer_id": cid,
                "first_name": first,
                "last_name": last,
                "email": email,
                "state_code": state,
                "date_of_birth": dob,
                "customer_since": since.isoformat(),
                "customer_type": "BUSINESS" if is_biz else "INDIVIDUAL",
                "_loaded_at": _ts(date(2024, 1, 2)),
            }
            if rng.random() < 0.03:  # stale earlier version of the same customer
                stale = dict(
                    row, email=f"old.{row['email'].lower()}", _loaded_at=_ts(date(2023, 6, 1))
                )
                rows.append(stale)
                self.issues.bump("customer_duplicate_version")
            rows.append(row)
        return rows, individuals, businesses

    # ------------------------------------------------------------------- policies
    def generate(self) -> dict[str, list[dict[str, Any]]]:
        """Generate all tables; returns ``{table_name: rows}``."""
        rng, as_of = self.rng, self.cfg.as_of
        customers, individuals, businesses = self._customers()
        policies, changes, premiums, claims, payments = [], [], [], [], []
        weights = [pl.weight for pl in PRODUCT_LINES]
        claim_seq = pay_seq = change_seq = 0

        for i in range(1, self.cfg.n_policies + 1):
            pl = rng.choices(PRODUCT_LINES, weights=weights)[0]
            pid = f"P{i:06d}"
            eff = _rand_date(rng, WINDOW_START, LAST_EFFECTIVE)
            exp = add_months(eff, 12)
            premium = round(pl.base_premium * rng.lognormvariate(0, 0.25), 2)
            limit, deductible = rng.choice(pl.limits), rng.choice(pl.deductibles)
            code = pl.code
            if rng.random() < 0.03:
                code = f" {code.lower()}"
                self.issues.bump("policy_product_code_unclean")
            policies.append(
                {
                    "policy_id": pid,
                    "policy_number": f"NWM-{pl.code}-{eff:%y}-{i:06d}",
                    "customer_id": rng.choice(businesses if pl.commercial else individuals),
                    "product_line_code": code,
                    "effective_date": eff.isoformat(),
                    "expiration_date": exp.isoformat(),
                    "annual_premium_cents": int(premium * 100),
                    "coverage_limit_cents": limit * 100,
                    "deductible_cents": deductible * 100,
                    "policy_status": rng.choice(("ACTIVE", "Active", "active ")),
                    "sales_channel": rng.choice(("AGENT", "DIRECT", "BROKER")),
                    "_loaded_at": _ts(eff),
                }
            )

            # Endorsements / cancellation (policy_changes feeds the SCD2 snapshot).
            events: list[tuple[date, str, float | None, int | None, int | None]] = []
            horizon = min(exp, as_of) - timedelta(days=1)
            if rng.random() < 0.40 and (horizon - eff).days > 40:
                d = _rand_date(rng, eff + timedelta(days=20), horizon)
                new_limit = rng.choice(pl.limits) if rng.random() < 0.5 else None
                new_ded = rng.choice(pl.deductibles) if rng.random() < 0.3 else None
                events.append((d, "ENDORSEMENT", rng.uniform(0.88, 1.25), new_limit, new_ded))
            cancel: date | None = None
            if rng.random() < 0.08 and (horizon - eff).days > 60:
                cancel = _rand_date(rng, eff + timedelta(days=45), horizon)
                events = [e for e in events if e[0] < cancel]
                events.append((cancel, "CANCELLATION", None, None, None))
            events.sort(key=lambda e: e[0])
            premium_timeline = [(eff, premium)]
            for d, ctype, factor, new_limit, new_ded in events:
                change_seq += 1
                new_prem = round(premium_timeline[-1][1] * factor, 2) if factor else None
                if new_prem is not None:
                    premium_timeline.append((d, new_prem))
                row = {
                    "change_id": f"CH{change_seq:06d}",
                    "policy_id": pid,
                    "change_effective_date": d.isoformat(),
                    "change_type": ctype,
                    "new_annual_premium_cents": int(new_prem * 100) if new_prem else "",
                    "new_coverage_limit_cents": new_limit * 100 if new_limit else "",
                    "new_deductible_cents": new_ded * 100 if new_ded else "",
                    "_loaded_at": _ts(d + timedelta(days=1)),
                }
                changes.append(row)
                if rng.random() < 0.04:
                    changes.append(dict(row))
                    self.issues.bump("policy_change_exact_duplicate")

            # Monthly premium installments, written at the start of each coverage month.
            for k in range(12):
                cs, ce = add_months(eff, k), add_months(eff, k + 1)
                if cs > as_of or (cancel and cs >= cancel):
                    break
                annual = [p for d, p in premium_timeline if d <= cs][-1]
                row = {
                    "premium_id": f"{pid}-{k + 1:02d}",
                    "policy_id": pid,
                    "installment_number": k + 1,
                    "coverage_start_date": cs.isoformat(),
                    "coverage_end_date": ce.isoformat(),
                    "written_premium_cents": round(annual * 100 / 12),
                    "_loaded_at": _ts(cs, 6),
                }
                premiums.append(row)
                if rng.random() < 0.01:
                    premiums.append(dict(row, _loaded_at=_ts(cs + timedelta(days=3), 6)))
                    self.issues.bump("premium_resent_duplicate")

            # Claims and payments.
            exposure_end = min(exp, cancel or exp, as_of)
            exposure_years = max((exposure_end - eff).days, 0) / 365.0
            for _ in range(_poisson(rng, pl.frequency * exposure_years)):
                loss = _rand_date(rng, eff, exposure_end - timedelta(days=1))
                reported = loss + timedelta(days=int(rng.expovariate(1 / pl.report_lag_days)))
                if reported > as_of:
                    continue  # IBNR: not yet known to the insurer
                claim_seq += 1
                claim, claim_pays = self._claim(pl, pid, claim_seq, loss, reported, limit)
                claims.extend(claim)
                for p in claim_pays:
                    pay_seq += 1
                    p["payment_id"] = f"PAY{pay_seq:07d}"
                    payments.append(p)
                    if rng.random() < 0.01:
                        payments.append(dict(p))
                        self.issues.bump("payment_exact_duplicate")

        self._inject_orphans(claims)
        self.tables = {
            "product_lines": [
                {
                    "product_line_code": pl.code,
                    "product_line_name": pl.name,
                    "line_of_business": pl.line_of_business,
                    "target_loss_ratio": pl.target_loss_ratio,
                    "is_active": "true",
                }
                for pl in PRODUCT_LINES
            ],
            "customers": customers,
            "policies": policies,
            "policy_changes": changes,
            "premiums": premiums,
            "claims": claims,
            "claim_payments": sorted(payments, key=lambda p: (p["_loaded_at"], p["payment_id"])),
        }
        return self.tables

    def _claim(
        self, pl: ProductLine, pid: str, seq: int, loss: date, reported: date, limit: int
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rng, as_of = self.rng, self.cfg.as_of
        sigma = 0.9
        ultimate = (
            0.0
            if rng.random() < 0.08
            else min(rng.lognormvariate(math.log(pl.severity) - sigma**2 / 2, sigma), limit)
        )
        settle = reported + timedelta(days=int(rng.expovariate(1 / pl.settle_days)) + 5)
        is_closed = settle <= as_of
        last_day = settle if is_closed else as_of
        span = max((last_day - reported).days, 1)
        n_pay = rng.randint(1, 4) if ultimate > 0 else 0
        frac = 1.0 if is_closed else min(span / max((settle - reported).days, 1), 0.9)
        weights = [rng.random() + 0.2 for _ in range(n_pay)]
        pays: list[dict[str, Any]] = []
        paid = 0
        for w in weights:
            pay_date = reported + timedelta(days=rng.randint(1, span))
            amount = round(ultimate * frac * w / sum(weights) * 100)
            paid += amount
            pays.append(self._payment(seq, pay_date, "INDEMNITY", amount))
        if ultimate > 0 and rng.random() < 0.6:
            pays.append(self._payment(seq, last_day, "EXPENSE", round(ultimate * 8)))
        if is_closed and pl.code == "PAUTO" and paid > 0 and rng.random() < 0.15:
            pays.append(self._payment(seq, last_day, "RECOVERY", -round(paid * 0.3)))
        reserve = 0 if is_closed else max(round(ultimate * 100) - paid, 0)
        status = "CLOSED" if is_closed else "OPEN"
        fmt_loss = self._messy_date(loss)
        if rng.random() < 0.012:  # reported before loss: keying error
            reported = loss - timedelta(days=rng.randint(1, 5))
            self.issues.bump("claim_reported_before_loss")
        if status == "OPEN" and rng.random() < 0.01:
            reserve = -reserve
            self.issues.bump("claim_negative_reserve")
        row = {
            "claim_id": f"C{seq:06d}",
            "claim_number": f"CLM-{loss:%Y}-{seq:06d}",
            "policy_id": pid,
            "loss_date": fmt_loss,
            "reported_date": reported.isoformat(),
            "claim_status": rng.choice((status, status.lower(), status.title() + " ")),
            "cause_of_loss": rng.choice(CAUSES[pl.code]),
            "case_reserve_cents": reserve,
            "closed_date": settle.isoformat() if is_closed else "",
            "_loaded_at": _ts(last_day + timedelta(days=1)),
        }
        rows = [row]
        if is_closed and rng.random() < 0.03:  # stale OPEN version still in the feed
            rows.insert(
                0,
                dict(
                    row,
                    claim_status="OPEN",
                    closed_date="",
                    case_reserve_cents=round(ultimate * 100),
                    _loaded_at=_ts(reported + timedelta(days=1)),
                ),
            )
            self.issues.bump("claim_stale_version")
        return rows, pays

    def _payment(self, seq: int, d: date, kind: str, cents: int) -> dict[str, Any]:
        return {
            "payment_id": "",
            "claim_id": f"C{seq:06d}",
            "payment_date": d.isoformat(),
            "payment_type": kind,
            "amount_cents": cents,
            "_loaded_at": _ts(d + timedelta(days=1)),
        }

    def _messy_date(self, d: date) -> str:
        r = self.rng.random()
        if r < 0.04:
            self.issues.bump("claim_date_slash_format")
            return d.strftime("%Y/%m/%d")
        if r < 0.06:
            self.issues.bump("claim_date_us_format")
            return d.strftime("%m/%d/%Y")
        return d.isoformat()

    def _inject_orphans(self, claims: list[dict[str, Any]]) -> None:
        for n in range(1, 5):
            src = self.rng.choice(claims)
            claims.append(
                dict(
                    src,
                    claim_id=f"C9{n:05d}",
                    claim_number=f"CLM-ORPHAN-{n}",
                    policy_id=f"P9{n:05d}",
                )
            )
            self.issues.bump("claim_orphan_policy")

    # ---------------------------------------------------------------------- write
    def write(self, out_dir: Path) -> dict[str, int]:
        """Write every table as ``<out_dir>/<name>.csv``; returns row counts."""
        if not self.tables:
            self.generate()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            counts = {}
            for name, rows in self.tables.items():
                path = out_dir / f"{name}.csv"
                with path.open("w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(
                        fh, fieldnames=list(rows[0].keys()), lineterminator="\n"
                    )
                    writer.writeheader()
                    writer.writerows(rows)
                counts[name] = len(rows)
                log.info("wrote seed", extra={"table": name, "rows": len(rows)})
        except (OSError, IndexError) as exc:
            raise SeedGenerationError(f"failed writing seeds to {out_dir}: {exc}") from exc
        log.info("injected data issues", extra=self.issues.counts)
        return counts


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m insurance_analytics.seed_generator``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("seeds"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--policies", type=int, default=GeneratorConfig.n_policies)
    args = parser.parse_args(argv)
    SeedGenerator(GeneratorConfig(seed=args.seed, n_policies=args.policies)).write(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
