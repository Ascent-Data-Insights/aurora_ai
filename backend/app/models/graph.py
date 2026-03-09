"""Information graph models for the guided assessment workflow.

These models represent everything the agent needs to learn about a user,
their organization, and the initiative being evaluated. All fields are
nullable — completeness drives conversation phase transitions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.scores import RingScores


class OrganizationInfo(BaseModel):
    name: str | None = None
    industry: str | None = None
    size: str | None = None  # e.g. "500 employees", "Series B startup"
    description: str | None = None


class UserInfo(BaseModel):
    role: str | None = None
    decision_authority: str | None = None  # e.g. "VP-level, owns budget"


class InitiativeInfo(BaseModel):
    name: str | None = None
    description: str | None = None


class ValueAssessment(BaseModel):
    revenue_impact: str | None = None
    cost_savings: str | None = None
    strategic_positioning: str | None = None
    time_reclaimed: str | None = None


class FeasibilityAssessment(BaseModel):
    technical_complexity: str | None = None
    team_capability: str | None = None
    infrastructure_readiness: str | None = None
    timeline: str | None = None
    dependencies: str | None = None


class ScalabilityAssessment(BaseModel):
    replicability: str | None = None
    marginal_cost: str | None = None
    organizational_readiness: str | None = None


class SessionState(BaseModel):
    """Complete state of what we know about this assessment session."""

    organization: OrganizationInfo = Field(default_factory=OrganizationInfo)
    user: UserInfo = Field(default_factory=UserInfo)
    initiative: InitiativeInfo = Field(default_factory=InitiativeInfo)
    value_assessment: ValueAssessment = Field(default_factory=ValueAssessment)
    feasibility_assessment: FeasibilityAssessment = Field(
        default_factory=FeasibilityAssessment
    )
    scalability_assessment: ScalabilityAssessment = Field(
        default_factory=ScalabilityAssessment
    )
    scores: RingScores = Field(default_factory=RingScores)

    def filled_field_count(self, model: BaseModel) -> int:
        """Count non-None fields on a sub-model."""
        return sum(1 for v in model.model_dump().values() if v is not None)

    def total_field_count(self, model: BaseModel) -> int:
        """Total fields on a sub-model."""
        return len(model.model_fields)
