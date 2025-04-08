from pydantic import BaseModel, Field
import uuid
from typing import Optional
from datetime import datetime

# Schema for the memory query request body
class MemoryQueryRequest(BaseModel):
    query_text: str = Field(..., description="The text to search for similar memories.")

# Schema for returning memory query results
class MemoryQueryResult(BaseModel):
    memory_id: int # Using Integer ID from AgentLongTermMemory model
    memory_text: str
    # score: Optional[float] = None # Include similarity score if available
    created_at: datetime

    class Config:
        orm_mode = True
        # Pydantic V2: from_attributes = True 