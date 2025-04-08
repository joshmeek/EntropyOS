from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from typing import Optional, List

from app.models.metrics import MetricSnapshot as MetricsModel
from app.schemas.metrics import MetricSnapshotCreate # Only need Create schema here

# Create a new metrics snapshot
def create_metric_snapshot(
    db: Session,
    simulation_id: uuid.UUID,
    tick: int,
    gini_coefficient: Optional[float],
    belief_variance: Optional[float]
    # Add other metrics as parameters
) -> MetricsModel:
    db_snapshot = MetricsModel(
        simulation_id=simulation_id,
        tick=tick,
        gini_coefficient=gini_coefficient,
        belief_variance=belief_variance
        # Assign other metrics
    )
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot

# Get metrics snapshots for a simulation, ordered by tick
def get_metric_snapshots(
    db: Session,
    simulation_id: uuid.UUID,
    skip: int = 0,
    limit: int = 1000 # Default to a larger limit for time series
) -> List[MetricsModel]:
    return db.query(MetricsModel)\
             .filter(MetricsModel.simulation_id == simulation_id)\
             .order_by(MetricsModel.tick)\
             .offset(skip)\
             .limit(limit)\
             .all() 