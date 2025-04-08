import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.database import Base

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey('simulations.id'), nullable=False, index=True)
    tick = Column(Integer, nullable=False, index=True)

    # Store calculated metrics
    gini_coefficient = Column(Float, nullable=True)
    belief_variance = Column(Float, nullable=True)
    # Add other metric columns

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to Simulation
    simulation = relationship("Simulation")

    # Add unique constraint for simulation_id and tick?
    # __table_args__ = (UniqueConstraint('simulation_id', 'tick', name='_simulation_tick_uc'),)

    def __repr__(self):
        return f"<MetricSnapshot(simulation={self.simulation_id}, tick={self.tick})>" 