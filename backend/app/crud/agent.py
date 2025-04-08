from sqlalchemy.orm import Session
import uuid
from typing import Optional

from app.models.agent import Agent as AgentModel
from app.schemas.agent import AgentCreate, AgentUpdate

# Get a single agent by ID
def get_agent(db: Session, agent_id: uuid.UUID) -> Optional[AgentModel]:
    return db.query(AgentModel).filter(AgentModel.id == agent_id).first()

# Get multiple agents with pagination and optional simulation_id filter
def get_agents(db: Session, simulation_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> list[AgentModel]:
    query = db.query(AgentModel)
    if simulation_id:
        query = query.filter(AgentModel.simulation_id == simulation_id)
    return query.offset(skip).limit(limit).all()

# Create a new agent
def create_agent(db: Session, agent: AgentCreate) -> AgentModel:
    # Convert Pydantic schema components to dictionaries for JSON storage
    db_agent = AgentModel(
        archetype=agent.archetype,
        demographics=agent.demographics.model_dump(), # Use model_dump() for Pydantic v2
        behavioral_traits=agent.behavioral_traits.model_dump(),
        beliefs=agent.beliefs.model_dump(),
        # short_term_memory will use default factory in model
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

# Update an existing agent
def update_agent(db: Session, agent_id: uuid.UUID, agent_update: AgentUpdate) -> Optional[AgentModel]:
    db_agent = get_agent(db, agent_id=agent_id)
    if db_agent is None:
        return None

    update_data = agent_update.model_dump(exclude_unset=True) # Get only fields that were explicitly set

    for key, value in update_data.items():
        # If the field is a nested Pydantic model (like demographics), dump it to dict
        if hasattr(value, 'model_dump'):
            setattr(db_agent, key, value.model_dump())
        else:
            setattr(db_agent, key, value)

    db.add(db_agent) # Add the updated object to the session
    db.commit()
    db.refresh(db_agent)
    return db_agent

# Delete an agent (optional for now)
# def delete_agent(db: Session, agent_id: uuid.UUID) -> Optional[AgentModel]:
#     db_agent = get_agent(db, agent_id=agent_id)
#     if db_agent:
#         db.delete(db_agent)
#         db.commit()
#     return db_agent 