from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
import uuid
from datetime import datetime

# Base schema for any event
class EventBase(BaseModel):
    event_type: str = Field(..., description="Identifier for the type of event (e.g., 'ubi', 'market_shock')")
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Event-specific parameters")
    target_tick: Optional[int] = Field(None, ge=0, description="Tick number when the event should trigger (if scheduled)")
    status: Literal["pending", "triggered", "processed", "failed"] = Field(default="pending")

# Schema for creating a new event instance
class EventCreate(EventBase):
    pass # Inherits all fields from base

# Schema for reading/returning an event instance
class Event(EventBase):
    id: uuid.UUID
    simulation_id: uuid.UUID
    created_at: datetime
    triggered_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        # Pydantic V2: from_attributes = True

# Specific example for UBI Event parameters
class UBIEventParams(BaseModel):
    amount_per_agent: float = Field(..., ge=0)
    duration_ticks: Optional[int] = Field(None, ge=1, description="How many ticks the UBI lasts (None for permanent)") 