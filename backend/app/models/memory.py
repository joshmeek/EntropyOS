import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector # Import Vector type

from app.db.database import Base

# Define the embedding dimension globally for consistency
# Adjust based on the embedding model used (e.g., Gemini embedding models)
EMBEDDING_DIM = 768 # Example dimension

class AgentLongTermMemory(Base):
    __tablename__ = "agent_long_term_memories"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False, index=True)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey('simulations.id'), nullable=False, index=True)

    memory_text = Column(Text, nullable=False) # The text content of the memory
    memory_embedding = Column(Vector(EMBEDDING_DIM), nullable=False) # The vector embedding

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    importance_score = Column(Integer, nullable=True) # Optional relevance score

    # Relationships
    agent = relationship("Agent", back_populates="long_term_memories") # Need to add back_populates to Agent model
    simulation = relationship("Simulation")

    def __repr__(self):
        return f"<AgentLongTermMemory(id={self.id}, agent_id={self.agent_id}, text='{self.memory_text[:30]}...')>" 