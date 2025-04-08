import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey('simulations.id'), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    parameters = Column(JSON, nullable=False, default=lambda: {})
    target_tick = Column(Integer, nullable=True, index=True) # Null if not scheduled
    status = Column(String, default="pending", nullable=False, index=True) # pending, triggered, processed, failed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    triggered_at = Column(DateTime(timezone=True), nullable=True) # When the event was actually triggered

    # Relationship to Simulation
    simulation = relationship("Simulation") # No back_populates needed if Sim doesn't track events directly

    def __repr__(self):
        return f"<Event(id={self.id}, type='{self.event_type}', status='{self.status}')>" 