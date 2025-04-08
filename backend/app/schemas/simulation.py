from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime

# Assuming AgentSchema exists in schemas.agent
from .agent import Agent as AgentSchema

class SimulationBase(BaseModel):
    name: Optional[str] = "Default Simulation"
    description: Optional[str] = None
    current_tick: int = Field(default=0, ge=0)
    status: str = Field(default="initialized") # e.g., initialized, running, stopped, completed

class SimulationCreate(SimulationBase):
    # Add any specific fields needed only on creation, e.g., seeding config
    population_size_target: Optional[int] = None # Can be used by seeding

class SimulationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    current_tick: Optional[int] = None
    status: Optional[str] = None

class Simulation(SimulationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Potentially include a summary of agents or link to agent list endpoint
    # agents: List[AgentSchema] = [] # This might be too large, prefer separate endpoint

    class Config:
        from_attributes = True # Pydantic V2 required
        # orm_mode = True # Deprecated in V2 