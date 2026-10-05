"""Custom exceptions raised by the helper scripts."""


class InsuranceAnalyticsError(Exception):
    """Base class for all helper-script errors."""


class SeedGenerationError(InsuranceAnalyticsError):
    """Raised when synthetic seed data cannot be generated or written."""


class WarehouseNotFoundError(InsuranceAnalyticsError):
    """Raised when the DuckDB warehouse file does not exist (run ``make build`` first)."""


class MartMissingError(InsuranceAnalyticsError):
    """Raised when an expected mart relation is absent from the warehouse."""


class DbtInvocationError(InsuranceAnalyticsError):
    """Raised when a programmatic dbt invocation fails."""
