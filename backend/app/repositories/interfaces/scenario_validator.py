"""Interface for backend scenario validation in Flagsmith experiments.

The frontend must NEVER evaluate answers or determine correctness.
This interface defines the backend correctness validator contract.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of validating an experiment scenario submission."""

    scenario_id: str = Field(..., description="Identifier of the scenario")
    is_correct: bool = Field(..., description="Backend validated correctness")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Score achieved")
    feedback: str = Field(..., description="Educational explanation for the participant")
    risk_signal_identified: bool = Field(
        default=False, description="Whether participant correctly spotted risk signal"
    )
    appropriate_action_selected: bool = Field(
        default=False, description="Whether recommended verification action was chosen"
    )
    details: dict[str, Any] = Field(default_factory=dict)


class ScenarioValidatorInterface(ABC):
    """Contract for scenario validation."""

    @abstractmethod
    def get_public_scenarios(self) -> list[dict[str, Any]]:
        """Return available experiment scenarios WITHOUT exposing expected answers."""
        pass

    @abstractmethod
    def get_public_scenario(self, scenario_id: str) -> Optional[dict[str, Any]]:
        """Return a single scenario without expected answers."""
        pass

    @abstractmethod
    def validate_answer(
        self, scenario_id: str, selected_answer: str, selected_action: Optional[str] = None
    ) -> ValidationResult:
        """Validate participant's answer against canonical criteria."""
        pass
