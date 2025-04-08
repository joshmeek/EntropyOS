from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Define configuration for generating agent properties
class DemographicDistribution(BaseModel):
    age_mean: float = 35.0
    age_stddev: float = 10.0
    income_mean: float = 50000.0
    income_stddev: float = 15000.0
    # Add more distribution parameters as needed (e.g., for education, location)

class TraitDistribution(BaseModel):
    conformity_mean: float = 0.5
    conformity_stddev: float = 0.2
    risk_aversion_mean: float = 0.5
    risk_aversion_stddev: float = 0.2
    # Add more trait distributions

class BeliefDistribution(BaseModel):
    # Example: Define how initial beliefs are set
    # political_vector_dimensions: int = 10 # Example
    economic_optimism_mean: float = 0.5
    economic_optimism_stddev: float = 0.2
    # Add more belief distributions

# Overall seeding configuration
class SeedingConfig(BaseModel):
    population_size: int = Field(..., ge=1, le=1000) # Example limits
    # archetype_distribution: Dict[str, float] = {"default": 1.0} # Example: 100% default archetype
    demographics: DemographicDistribution = Field(default_factory=DemographicDistribution)
    traits: TraitDistribution = Field(default_factory=TraitDistribution)
    beliefs: BeliefDistribution = Field(default_factory=BeliefDistribution)
    # Add social network config later (e.g., connection probability, type)

# Schema for the seeding request body
class SeedSimulationRequest(BaseModel):
    config: SeedingConfig 