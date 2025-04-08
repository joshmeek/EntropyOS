import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from typing import List
from sqlalchemy.orm import Mapped

from app.db.database import Base

class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    current_tick = Column(Integer, default=0, nullable=False)
    status = Column(String, default="initialized", nullable=False) # e.g., initialized, running, stopped, completed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to Agents (One-to-Many)
    # Agents belonging to this simulation
    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="simulation", cascade="all, delete-orphan")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="simulation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Simulation(id={self.id}, name='{self.name}', status='{self.status}')>" 