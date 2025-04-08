from sqlalchemy.orm import Session
import uuid
from typing import Optional, List

from app.models.event import Event as EventModel
from app.schemas.event import EventCreate

# Get a single event by ID
def get_event(db: Session, event_id: uuid.UUID) -> Optional[EventModel]:
    return db.query(EventModel).filter(EventModel.id == event_id).first()

# Get multiple events for a simulation, optionally filtering by status or tick
def get_events(
    db: Session,
    simulation_id: uuid.UUID,
    status: Optional[str] = None,
    tick: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[EventModel]:
    query = db.query(EventModel).filter(EventModel.simulation_id == simulation_id)
    if status:
        query = query.filter(EventModel.status == status)
    if tick is not None:
        # Get events scheduled for this tick or earlier that are pending
        # Modify this logic based on how event triggering works
        query = query.filter(EventModel.target_tick == tick)

    return query.order_by(EventModel.created_at).offset(skip).limit(limit).all()

# Create a new event
def create_event(db: Session, event: EventCreate, simulation_id: uuid.UUID) -> EventModel:
    db_event = EventModel(
        **event.model_dump(),
        simulation_id=simulation_id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

# Update an event (e.g., change status, set triggered_at)
def update_event_status(db: Session, event_id: uuid.UUID, status: str) -> Optional[EventModel]:
    db_event = get_event(db, event_id=event_id)
    if db_event:
        db_event.status = status
        if status == "triggered":
            from datetime import datetime, timezone
            db_event.triggered_at = datetime.now(timezone.utc)
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
    return db_event 