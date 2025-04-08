from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid

# --- Base Schemas --- #

class AgentBase(BaseModel):
    archetype: Optional[str] = None
    # Add other base fields if common across create/update/read

# --- Component Schemas --- #

class AgentDemographics(BaseModel):
    age: int = Field(..., ge=0)
    income: float = Field(..., ge=0)
    education_level: Optional[str] = None # e.g., "High School", "Bachelor's", "PhD"
    location: Optional[str] = None # e.g., "District A", "Sector 5"
    household_size: int = Field(..., ge=1)

class AgentBehavioralTraits(BaseModel):
    conformity: float = Field(..., ge=0, le=1)
    risk_aversion: float = Field(..., ge=0, le=1)
    empathy: float = Field(..., ge=0, le=1)
    social_susceptibility: float = Field(..., ge=0, le=1)
    consumption_preference: float = Field(..., ge=0, le=1) # e.g., 0=saver, 1=spender

class AgentBeliefs(BaseModel):
    political_ideology_vector: List[float] # Embedding representing ideology
    economic_optimism: float = Field(..., ge=0, le=1)
    institutional_trust: float = Field(..., ge=0, le=1)
    policy_support_index: Dict[str, float] = {} # Key: policy_id, Value: support (0-1)

class AgentMemoryShortTerm(BaseModel):
    recent_events: List[str] = [] # Log of recent event descriptions or IDs
    last_decisions: List[Dict] = [] # Log of recent structured decisions

# Note: Long-term memory (vector) might be handled separately or linked via ID

class AgentSocialConnection(BaseModel):
    target_agent_id: uuid.UUID
    influence_factor: float = Field(..., ge=0, le=1) # Strength of opinion sway
    relationship_type: Optional[str] = None # e.g., "friend", "coworker", "neighbor"

# --- Combined Agent Schemas --- #

class AgentCreate(AgentBase):
    demographics: AgentDemographics
    behavioral_traits: AgentBehavioralTraits
    beliefs: AgentBeliefs
    # Initial memory state can be set if needed
    # Initial social connections established separately or during seeding

class AgentUpdate(AgentBase):
    demographics: Optional[AgentDemographics] = None
    behavioral_traits: Optional[AgentBehavioralTraits] = None
    beliefs: Optional[AgentBeliefs] = None
    # Memory updates handled via specific actions/endpoints
    # Social graph updates handled via specific actions/endpoints

class Agent(AgentBase):
    id: uuid.UUID
    simulation_id: uuid.UUID # Link to the simulation it belongs to
    demographics: AgentDemographics
    behavioral_traits: AgentBehavioralTraits
    beliefs: AgentBeliefs
    # Memory representation (short-term log might be included here)
    short_term_memory: AgentMemoryShortTerm = Field(default_factory=AgentMemoryShortTerm)
    # Social connections likely fetched separately

    class Config:
        orm_mode = True # Pydantic V1 or from_attributes = True for V2
        # Pydantic V2: from_attributes = True

# Schema for representing the full agent state including relationships for API responses if needed
class AgentDetail(Agent):
    social_connections: List[AgentSocialConnection] = []
    # Add long-term memory summary or link if needed 