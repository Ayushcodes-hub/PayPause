"""Production-facing deterministic payment and scenario services.

Both services use canonical server-side rules and persistent repository
dependencies. They do not generate random or simulated production results.
"""
from backend.app.repositories.development.mock_duplicate_checker import (
    MockDuplicateChecker,
)
from backend.app.repositories.development.mock_scenario_validator import (
    MockScenarioValidator,
)


class ProductionDuplicateChecker(MockDuplicateChecker):
    """Rule-based duplicate detection backed by the supplied payment repository."""


class ProductionScenarioValidator(MockScenarioValidator):
    """Canonical server-side scenario validation for production."""
