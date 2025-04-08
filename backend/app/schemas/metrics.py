from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

class MetricSnapshotBase(BaseModel):
    tick: int = Field(..., ge=0)
    gini_coefficient: Optional[float] = None
    belief_variance: Optional[float] = None # Example: Avg variance across belief vector dimensions
    # Add other metrics as needed

class MetricSnapshotCreate(MetricSnapshotBase):
    pass

class MetricSnapshot(MetricSnapshotBase):
    id: uuid.UUID
    simulation_id: uuid.UUID
    timestamp: datetime

    class Config:
        orm_mode = True
        # Pydantic V2: from_attributes = True 