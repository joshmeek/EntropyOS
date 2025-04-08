from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

from .simulation import Simulation
from .agent import Agent
from .event import Event
from .metrics import MetricSnapshot

class SimulationSnapshot(BaseModel):
    """
    Represents a complete snapshot of a simulation's state at a specific point in time.
    """
    simulation_details: Simulation
    agents: List[Agent]
    events: List[Event] # Potentially filter for active/relevant events?
    latest_metrics: Optional[MetricSnapshot] = None

    class Config:
        orm_mode = True # For Pydantic V1 or use from_attributes = True for V2
        # Pydantic V2: from_attributes = True 