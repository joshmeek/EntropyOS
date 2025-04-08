import uuid
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
# Import Base from the correct location (assuming db/database.py)
from app.db.database import Base

# Import Simulation model for relationship
from .simulation import Simulation

# Placeholder for potential Simulation model dependency
# from .simulation import Simulation

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey('simulations.id'), nullable=False)
    archetype = Column(String, nullable=True)

    # Store complex structures as JSONB
    # Note: Ensure PostgreSQL JSONB support
    demographics = Column(JSON, nullable=False)
    behavioral_traits = Column(JSON, nullable=False)
    beliefs = Column(JSON, nullable=False) # Includes political_ideology_vector (as list), optimism, trust, policy_support
    short_term_memory = Column(JSON, nullable=False, default=lambda: {"recent_events": [], "last_decisions": []})

    # Relationships
    simulation = relationship("Simulation", back_populates="agents")
    long_term_memories = relationship("AgentLongTermMemory", back_populates="agent", cascade="all, delete-orphan")
    # outgoing_connections = relationship("AgentConnection", foreign_keys="[AgentConnection.source_agent_id]", back_populates="source_agent", cascade="all, delete-orphan")
    # incoming_connections = relationship("AgentConnection", foreign_keys="[AgentConnection.target_agent_id]", back_populates="target_agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent(id={self.id}, archetype='{self.archetype}')>"

# Separate table for social connections (represents directed graph edges)
class AgentConnection(Base):
    __tablename__ = "agent_connections"

    id = Column(Integer, primary_key=True, index=True)
    source_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete="CASCADE"), nullable=False, index=True)
    target_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete="CASCADE"), nullable=False, index=True)
    influence_factor = Column(Float, nullable=False)
    relationship_type = Column(String, nullable=True)

    # Relationships to link back to Agent models
    # source_agent = relationship("Agent", foreign_keys=[source_agent_id])
    # target_agent = relationship("Agent", foreign_keys=[target_agent_id])

    def __repr__(self):
        return f"<AgentConnection(from={self.source_agent_id} to={self.target_agent_id}, influence={self.influence_factor})>"

# Potential separate table for long-term vector memories (using pgvector)
# class AgentLongTermMemory(Base):
#     __tablename__ = "agent_long_term_memories"
#     id = Column(Integer, primary_key=True, index=True)
#     agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False, index=True)
#     memory_embedding = Column(Vector(embedding_dim)) # Requires pgvector setup
#     memory_text = Column(Text, nullable=True)
#     timestamp = Column(DateTime, default=datetime.utcnow)
#     agent = relationship("Agent", back_populates="long_term_memories") 