from sqlalchemy.orm import Session
from sqlalchemy import select, desc
# from pgvector.sqlalchemy import L2Distance # Removed this import
import uuid
from typing import Optional, List

from app.models.memory import AgentLongTermMemory, EMBEDDING_DIM # Import model and dimension

# Add a new long-term memory
def add_long_term_memory(
    db: Session,
    agent_id: uuid.UUID,
    simulation_id: uuid.UUID,
    memory_text: str,
    memory_embedding: List[float],
    importance: Optional[int] = None
) -> AgentLongTermMemory:

    # Validate embedding dimension
    if len(memory_embedding) != EMBEDDING_DIM:
        raise ValueError(f"Embedding dimension mismatch. Expected {EMBEDDING_DIM}, got {len(memory_embedding)}")

    db_memory = AgentLongTermMemory(
        agent_id=agent_id,
        simulation_id=simulation_id,
        memory_text=memory_text,
        memory_embedding=memory_embedding, # Store the list directly
        importance_score=importance
    )
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    return db_memory

# Retrieve recent long-term memories for an agent
def get_recent_long_term_memories(
    db: Session,
    agent_id: uuid.UUID,
    limit: int = 10
) -> List[AgentLongTermMemory]:
    return db.query(AgentLongTermMemory)\
             .filter(AgentLongTermMemory.agent_id == agent_id)\
             .order_by(desc(AgentLongTermMemory.created_at))\
             .limit(limit)\
             .all()

# Retrieve long-term memories relevant to a query embedding
def get_relevant_long_term_memories(
    db: Session,
    agent_id: uuid.UUID,
    query_embedding: List[float],
    limit: int = 5
) -> List[AgentLongTermMemory]:
    # Note: Requires index on memory_embedding for performance.
    # Example index: CREATE INDEX ON agent_long_term_memories USING hnsw (memory_embedding vector_l2_ops);

    # Ensure the query_embedding list is the correct dimension
    if not query_embedding or len(query_embedding) != EMBEDDING_DIM:
        # Handle error or return empty list
        print(f"Warning: Query embedding dimension mismatch. Expected {EMBEDDING_DIM}, got {len(query_embedding)}. Returning empty list.")
        return []

    # Use scalar_all() for newer SQLAlchemy versions if needed
    results = db.scalars(
        select(AgentLongTermMemory)
        .filter(AgentLongTermMemory.agent_id == agent_id)
        # Use the distance operator directly on the column
        .order_by(AgentLongTermMemory.memory_embedding.l2_distance(query_embedding))
        .limit(limit)
    ).all()
    return results 