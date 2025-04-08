import logging
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.simulation import Simulation
from app.models.event import Event as EventModel
from app.models.agent import Agent as AgentModel
from app.schemas.event import UBIEventParams # To validate parameters
from app.crud import agent as crud_agent
from app.crud import event as crud_event

logger = logging.getLogger(__name__)

def apply_ubi_event(db: Session, simulation: Simulation, event: EventModel):
    """Applies the effects of a UBI event to all agents in a simulation."""
    logger.info(f"Applying UBI event {event.id} for simulation {simulation.id} at tick {simulation.current_tick}")

    try:
        # Validate parameters
        params = UBIEventParams(**event.parameters)
        amount = params.amount_per_agent
    except ValidationError as e:
        logger.error(f"Invalid parameters for UBI event {event.id}: {e}")
        crud_event.update_event_status(db, event_id=event.id, status="failed")
        return
    except KeyError:
        logger.error(f"Missing 'amount_per_agent' in parameters for UBI event {event.id}")
        crud_event.update_event_status(db, event_id=event.id, status="failed")
        return

    agents = crud_agent.get_agents(db, simulation_id=simulation.id, limit=10000) # Get all agents for the simulation

    updated_count = 0
    for agent in agents:
        try:
            # Assuming agent.demographics is a dict stored in JSONB
            if isinstance(agent.demographics, dict):
                current_income = agent.demographics.get('income', 0.0)
                # Create a mutable copy to update
                updated_demographics = agent.demographics.copy()
                updated_demographics['income'] = current_income + amount
                # Update the agent model - SQLAlchemy detects changes in mutable JSON types
                agent.demographics = updated_demographics
                # Add agent to session explicitly if modification tracking isn't perfect
                db.add(agent)
                updated_count += 1
            else:
                logger.warning(f"Agent {agent.id} demographics field is not a dictionary. Skipping UBI application.")

        except Exception as e:
            logger.error(f"Failed to apply UBI to agent {agent.id}: {e}")
            # Decide whether to fail the whole event or just skip the agent

    try:
        # Update event status
        crud_event.update_event_status(db, event_id=event.id, status="processed")
        db.commit() # Commit agent updates and event status change
        logger.info(f"Successfully applied UBI event {event.id} to {updated_count}/{len(agents)} agents.")
    except Exception as e:
        logger.error(f"Failed to commit changes or update event status for UBI event {event.id}: {e}")
        db.rollback()

# Placeholder for processing events for a tick
def process_events_for_tick(db: Session, simulation: Simulation):
    """
    Finds and processes pending events for the simulation's current tick.
    (This would eventually be orchestrated by Hatchet).
    """
    current_tick = simulation.current_tick
    pending_events = crud_event.get_events(
        db, simulation_id=simulation.id, status="pending", tick=current_tick, limit=100
    )

    logger.info(f"Found {len(pending_events)} pending events for tick {current_tick} in simulation {simulation.id}")

    for event in pending_events:
        # Mark as triggered (optional intermediate step)
        crud_event.update_event_status(db, event_id=event.id, status="triggered")
        db.commit()

        if event.event_type == "ubi":
            apply_ubi_event(db, simulation, event)
        # Add handlers for other event types here
        # elif event.event_type == "market_shock":
        #     apply_market_shock(db, simulation, event)
        else:
            logger.warning(f"Unknown event type '{event.event_type}' for event {event.id}. Marking as failed.")
            crud_event.update_event_status(db, event_id=event.id, status="failed")
            db.commit() 