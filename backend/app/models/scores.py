from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    value: int = Field(default=0, ge=0, le=100)
    confidence: int = Field(default=0, ge=0, le=100)


class RingScores(BaseModel):
    value: DimensionScore = Field(default_factory=DimensionScore)
    feasibility: DimensionScore = Field(default_factory=DimensionScore)
    scalability: DimensionScore = Field(default_factory=DimensionScore)
