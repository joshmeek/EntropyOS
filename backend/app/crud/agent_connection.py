from sqlalchemy.orm import Session
import uuid
from typing import Optional, List

from app.models.agent import AgentConnection

# Create a new agent connection
def create_agent_connection(
    db: Session,
    source_agent_id: uuid.UUID,
    target_agent_id: uuid.UUID,
    influence_factor: float,
    relationship_type: Optional[str] = None
) -> AgentConnection:
    db_connection = AgentConnection(
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        influence_factor=influence_factor,
        relationship_type=relationship_type
    )
    db.add(db_connection)
    # Commit is handled by the calling function (e.g., after batch creation)
    # db.commit()
    # db.refresh(db_connection)
    return db_connection

# Get connections for a specific agent (outgoing or incoming)
def get_agent_connections(
    db: Session,
    agent_id: uuid.UUID,
    direction: str = "outgoing", # "outgoing" or "incoming"
    limit: int = 100
) -> List[AgentConnection]:
    query = db.query(AgentConnection)
    if direction == "outgoing":
        query = query.filter(AgentConnection.source_agent_id == agent_id)
    elif direction == "incoming":
        query = query.filter(AgentConnection.target_agent_id == agent_id)
    else:
        # Or raise error
        return []
    return query.limit(limit).all() 