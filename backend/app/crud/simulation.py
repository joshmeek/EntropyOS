from sqlalchemy.orm import Session
import uuid
from typing import Optional, List
from datetime import datetime, timezone

from app.models.simulation import Simulation as SimulationModel
from app.schemas.simulation import SimulationCreate, SimulationUpdate

# Get a single simulation by ID
def get_simulation(db: Session, simulation_id: uuid.UUID) -> Optional[SimulationModel]:
    return db.query(SimulationModel).filter(SimulationModel.id == simulation_id).first()

# Get multiple simulations with pagination
def get_simulations(db: Session, skip: int = 0, limit: int = 100) -> List[SimulationModel]:
    return db.query(SimulationModel).offset(skip).limit(limit).all()

# Create a new simulation
def create_simulation(db: Session, simulation: SimulationCreate) -> SimulationModel:
    now = datetime.now(timezone.utc)
    db_simulation = SimulationModel(
        name=simulation.name,
        description=simulation.description,
        created_at=now,
        updated_at=now
    )
    db.add(db_simulation)
    db.commit()
    db.refresh(db_simulation)
    return db_simulation

# Update an existing simulation
def update_simulation(db: Session, simulation_id: uuid.UUID, simulation_update: SimulationUpdate) -> Optional[SimulationModel]:
    db_simulation = get_simulation(db, simulation_id=simulation_id)
    if db_simulation is None:
        return None

    update_data = simulation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_simulation, key, value)

    db.add(db_simulation)
    db.commit()
    db.refresh(db_simulation)
    return db_simulation

# Delete a simulation (includes cascading delete of agents)
def delete_simulation(db: Session, simulation_id: uuid.UUID) -> Optional[SimulationModel]:
    db_simulation = get_simulation(db, simulation_id=simulation_id)
    if db_simulation:
        db.delete(db_simulation)
        db.commit()
    return db_simulation 