from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from app.db.database import get_db
from app.schemas.simulation import Simulation, SimulationCreate, SimulationUpdate
from app.schemas.seeding import SeedSimulationRequest
from app.schemas.event import Event as EventSchema, EventCreate
from app.crud import simulation as crud_simulation
from app.crud import agent as crud_agent # To check agent count
from app.crud import event as crud_event # Import event CRUD
from app.services import seeding_service
from app.services import event_service # <-- Import event service
from app.services import metrics_service # <-- Import metrics service
from app.services import simulation_service # <-- Import simulation service
from app.schemas.metrics import MetricSnapshot as MetricSnapshotSchema # Import metrics schema
from app.crud import metrics as crud_metrics # Import metrics CRUD
from app.schemas.snapshot import SimulationSnapshot
# Placeholder for simulation runner service
# from app.services import simulation_runner

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=Simulation, status_code=201)
def create_simulation_endpoint(
    simulation: SimulationCreate, db: Session = Depends(get_db)
):
    """Create a new simulation record."""
    return crud_simulation.create_simulation(db=db, simulation=simulation)

@router.post("/{simulation_id}/seed", status_code=202) # 202 Accepted for background task
def seed_simulation_endpoint(
    simulation_id: uuid.UUID,
    seed_request: SeedSimulationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Seed a simulation with agents based on the provided config.
    This runs as a background task.
    """
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if not db_simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Basic check: prevent reseeding if agents already exist?
    existing_agents = db.query(crud_agent.AgentModel).filter(crud_agent.AgentModel.simulation_id == simulation_id).count()
    if existing_agents > 0:
        raise HTTPException(status_code=400, detail="Simulation already contains agents. Reset simulation before seeding again.")

    logger.info(f"Adding seeding task for simulation {simulation_id} to background.")
    background_tasks.add_task(seeding_service.seed_simulation_agents,
                              db, db_simulation, seed_request.config)
    return {"message": "Simulation seeding started in background.", "simulation_id": simulation_id}

@router.get("/", response_model=List[Simulation])
def read_simulations_endpoint(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """Retrieve a list of simulations."""
    simulations = crud_simulation.get_simulations(db, skip=skip, limit=limit)
    return simulations

@router.get("/{simulation_id}", response_model=Simulation)
def read_simulation_endpoint(simulation_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieve a specific simulation by ID."""
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if db_simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return db_simulation

@router.put("/{simulation_id}/status", response_model=Simulation)
def update_simulation_status_endpoint(
    simulation_id: uuid.UUID,
    status_update: SimulationUpdate, # Reuse SimulationUpdate, maybe create specific StatusUpdate schema
    db: Session = Depends(get_db)
):
    """
    Update the status of a simulation (e.g., start, stop, reset).
    Placeholder - Actual start/stop logic will involve Hatchet tasks.
    """
    # Basic validation: only update allowed fields (status, maybe name/description)
    allowed_updates = SimulationUpdate(status=status_update.status)

    db_simulation = crud_simulation.update_simulation(
        db=db, simulation_id=simulation_id, simulation_update=allowed_updates
    )
    if db_simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # TODO: Trigger corresponding actions based on status change
    # if db_simulation.status == "running":
    #     # Trigger Hatchet workflow to start tick runner
    #     logger.info(f"Simulation {simulation_id} status changed to running. Triggering start...")
    # elif db_simulation.status == "stopped":
    #     # Trigger Hatchet workflow/task cancellation
    #     logger.info(f"Simulation {simulation_id} status changed to stopped. Triggering stop...")
    # elif db_simulation.status == "reset":
    #     # Delete agents, reset tick counter, etc.
    #     logger.info(f"Simulation {simulation_id} status changed to reset. Triggering reset...")
    #     # This might require more complex logic, potentially another background task

    return db_simulation


@router.post("/{simulation_id}/tick", response_model=Simulation)
def advance_tick_endpoint(simulation_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Manually advance the simulation by one tick.
    Includes processing events and calculating metrics for the CURRENT tick
    before advancing.
    Placeholder - Actual tick advancement will be orchestrated by Hatchet.
    """
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if db_simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    current_tick = db_simulation.current_tick
    logger.info(f"Processing tick {current_tick} for simulation {simulation_id}...")

    # 1. Process events for the CURRENT tick
    try:
        event_service.process_events_for_tick(db, db_simulation)
        logger.info(f"Finished processing events for tick {current_tick} in simulation {simulation_id}.")
    except Exception as e:
        logger.error(f"Error processing events for tick {current_tick} in simulation {simulation_id}: {e}")

    # 2. Calculate and store metrics for the CURRENT tick state
    try:
        metrics_service.calculate_and_store_metrics(db, db_simulation)
    except Exception as e:
        logger.error(f"Error calculating/storing metrics for tick {current_tick} in simulation {simulation_id}: {e}")

    # TODO: Trigger agent decision making / simulation update logic (Hatchet task)
    # simulation_runner.run_agent_updates(db, db_simulation)

    # 2. Run agent updates (LLM calls, state changes) - Synchronous for now
    try:
        simulation_service.run_agent_updates(db, db_simulation)
        logger.info(f"Finished agent updates for tick {current_tick} in simulation {simulation_id}.")
    except Exception as e:
        logger.error(f"Error running agent updates for tick {current_tick} in simulation {simulation_id}: {e}", exc_info=True)
        # Depending on severity, we might want to stop the tick advancement here
        # raise HTTPException(status_code=500, detail="Failed during agent update phase.") from e

    # 3. Calculate and store metrics AFTER agent updates
    try:
        metrics_service.calculate_and_store_metrics(db, db_simulation)
        logger.info(f"Finished calculating post-agent update metrics for tick {current_tick} in simulation {simulation_id}.")
    except Exception as e:
        logger.error(f"Error calculating/storing post-agent update metrics for tick {current_tick} in simulation {simulation_id}: {e}")

    # 4. Increment tick AFTER processing agents and metrics
    new_tick = current_tick + 1
    updated_sim = crud_simulation.update_simulation(db, simulation_id, SimulationUpdate(current_tick=new_tick))
    if not updated_sim:
        raise HTTPException(status_code=500, detail="Failed to update simulation tick")

    logger.info(f"Advanced simulation {simulation_id} to tick {updated_sim.current_tick}.")

    return updated_sim


@router.delete("/{simulation_id}", status_code=204)
def delete_simulation_endpoint(simulation_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a simulation and all associated agents."""
    deleted = crud_simulation.delete_simulation(db, simulation_id=simulation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return None # Return 204 No Content

@router.post("/{simulation_id}/events", response_model=EventSchema, status_code=201)
def inject_event_endpoint(
    simulation_id: uuid.UUID,
    event_data: EventCreate,
    db: Session = Depends(get_db)
):
    """
    Inject a new event into a simulation.
    The event processing logic itself will happen during tick execution.
    """
    # Validate simulation exists
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if not db_simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # TODO: Add validation for event_data.parameters based on event_data.event_type
    # Example for UBI:
    # if event_data.event_type == "ubi":
    #     try:
    #         UBIEventParams(**event_data.parameters)
    #     except ValidationError as e:
    #         raise HTTPException(status_code=422, detail=f"Invalid UBI parameters: {e}")

    created_event = crud_event.create_event(db=db, event=event_data, simulation_id=simulation_id)
    logger.info(f"Injected event {created_event.id} ({created_event.event_type}) into simulation {simulation_id}")
    return created_event


@router.get("/{simulation_id}/events", response_model=List[EventSchema])
def list_events_endpoint(
    simulation_id: uuid.UUID,
    status: Optional[str] = None,
    tick: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List events for a given simulation, with optional filters."""
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if not db_simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    events = crud_event.get_events(db, simulation_id, status, tick, skip, limit)
    return events

# TODO: Add endpoint for injecting events (/simulations/{simulation_id}/events)
# This comment seems redundant now 

# --- Metrics Endpoint --- #

@router.get("/{simulation_id}/metrics", response_model=List[MetricSnapshotSchema])
def get_metrics_snapshots_endpoint(
    simulation_id: uuid.UUID,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Retrieve metric snapshots for a simulation, ordered by tick."""
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if not db_simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    snapshots = crud_metrics.get_metric_snapshots(db, simulation_id, skip, limit)
    return snapshots

@router.get("/{simulation_id}/snapshot", response_model=SimulationSnapshot)
def get_simulation_snapshot_endpoint(
    simulation_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Retrieve a full snapshot of the simulation state."""
    # 1. Get Simulation Details
    db_simulation = crud_simulation.get_simulation(db, simulation_id=simulation_id)
    if not db_simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # 2. Get All Agents for the Simulation
    agents = crud_agent.get_agents(db, simulation_id=simulation_id, limit=10000) # Assume large limit for snapshot

    # 3. Get All Events for the Simulation (consider filtering later)
    events = crud_event.get_events(db, simulation_id=simulation_id, limit=10000) # Assume large limit

    # 4. Get Latest Metric Snapshot
    # Need to import crud_entropy, assuming it holds the latest snapshot logic
    try:
        from app.crud import entropy as crud_entropy # Temporary import inside function
        latest_metrics = crud_entropy.get_latest_metric_snapshot(db, simulation_id=simulation_id)
    except ImportError:
        logger.error("crud_entropy not found, cannot fetch latest metrics for snapshot.")
        latest_metrics = None
    except Exception as e:
        logger.error(f"Error fetching latest metrics for snapshot: {e}")
        latest_metrics = None

    # 5. Construct and return snapshot
    # Convert the SQLAlchemy model to the Pydantic schema
    simulation_details_schema = Simulation.from_orm(db_simulation)

    snapshot = SimulationSnapshot(
        simulation_details=simulation_details_schema, # Use the schema object
        agents=agents,
        events=events,
        latest_metrics=latest_metrics
    )

    return snapshot 