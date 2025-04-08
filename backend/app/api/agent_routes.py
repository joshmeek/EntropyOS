from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from app.db.database import get_db
from app.models.agent import Agent as AgentModel # Rename to avoid conflict
from app.schemas.agent import Agent as AgentSchema, AgentCreate, AgentUpdate # Use schemas
from app.schemas.memory import MemoryQueryRequest, MemoryQueryResult # Need to create these schemas

# Placeholder for CRUD operations (to be implemented in a separate service/crud layer later)
from app.crud import agent as crud_agent
from app.core.llm_client import generate_agent_decision, generate_embedding # Added embedding fn
from app.crud import memory as crud_memory # Import memory CRUD

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=AgentSchema, status_code=201)
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    """
    Create a new agent.
    (Note: Agent creation will typically happen via the seeding system,
     but this endpoint allows manual creation/testing).
    """
    # Placeholder: Check for existing agent? (e.g., based on some unique identifier if needed)
    # db_agent = crud_agent.get_agent_by_email(db, email=agent.email) # Example check
    # if db_agent:
    #     raise HTTPException(status_code=400, detail="Email already registered")
    return crud_agent.create_agent(db=db, agent=agent)

@router.get("/", response_model=List[AgentSchema])
def read_agents(
    simulation_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of agents, optionally filtering by simulation_id.
    """
    agents = crud_agent.get_agents(db, simulation_id=simulation_id, skip=skip, limit=limit)
    return agents

@router.get("/{agent_id}", response_model=AgentSchema)
def read_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve a specific agent by ID.
    """
    db_agent = crud_agent.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.put("/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: uuid.UUID,
    agent: AgentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing agent.
    """
    db_agent = crud_agent.update_agent(db=db, agent_id=agent_id, agent_update=agent)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.post("/{agent_id}/query_memory", response_model=List[MemoryQueryResult])
async def query_agent_memory(
    agent_id: uuid.UUID,
    query: MemoryQueryRequest,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    Query an agent's long-term memory using vector similarity search.
    """
    db_agent = crud_agent.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 1. Generate embedding for the query text
    query_embedding = await generate_embedding(query.query_text)

    if not query_embedding:
        raise HTTPException(status_code=500, detail="Failed to generate embedding for query text")

    # 2. Perform similarity search
    relevant_memories = crud_memory.get_relevant_long_term_memories(
        db=db,
        agent_id=agent_id,
        query_embedding=query_embedding,
        limit=limit
    )

    # 3. Format results (optional, could define MemoryQueryResult schema)
    results = [
        MemoryQueryResult(
            memory_id=mem.id,
            memory_text=mem.memory_text,
            # Add similarity score if needed/calculated
            # score=... # Requires calculating score during/after query
            created_at=mem.created_at
        )
        for mem in relevant_memories
    ]

    return results

# Temporary test endpoint for LLM decision AND memory storage
@router.post("/{agent_id}/decide", response_model=dict)
async def test_agent_decision(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    TEMPORARY: Fetches agent, calls LLM, generates/stores LTM, updates STM.
    """
    db_agent = crud_agent.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Prepare context
    agent_profile = {
        "demographics": db_agent.demographics,
        "behavioral_traits": db_agent.behavioral_traits,
        "beliefs": db_agent.beliefs
    }
    # Make a copy to avoid modifying the object before LLM call if needed
    current_stm = db_agent.short_term_memory.copy() if isinstance(db_agent.short_term_memory, dict) else {"recent_events": [], "last_decisions": []}

    # 1. Get LLM Decision
    decision = await generate_agent_decision(
        agent_profile=agent_profile,
        short_term_memory=current_stm
    )

    if "error" in decision:
        return decision

    memory_stored_flag = False
    # 2. Create a memory summary
    memory_text = f"Decided to '{decision.get('action', 'unknown action')}'. Feeling '{decision.get('sentiment', 'unknown')}'. Spending ratio: {decision.get('spending_ratio', 'unknown')}."

    # 3. Generate Embedding
    embedding = await generate_embedding(memory_text)

    # 4. Store Long-Term Memory
    if embedding:
        try:
            crud_memory.add_long_term_memory(
                db=db,
                agent_id=agent_id,
                simulation_id=db_agent.simulation_id,
                memory_text=memory_text,
                memory_embedding=embedding
            )
            logger.info(f"Stored long-term memory for agent {agent_id}")
            memory_stored_flag = True
        except Exception as e:
            logger.error(f"Failed to store long-term memory for agent {agent_id}: {e}")
            decision["_memory_error"] = str(e)
    else:
        logger.warning(f"Could not generate embedding for memory of agent {agent_id}. Memory not stored.")

    decision["_memory_stored"] = memory_stored_flag

    # 5. Update Agent's Short-Term Memory Log
    try:
        # Ensure 'last_decisions' is a list
        if not isinstance(current_stm.get('last_decisions'), list):
            current_stm['last_decisions'] = []

        # Append the new decision (add timestamp if needed)
        # from datetime import datetime, timezone
        # decision_log_entry = decision.copy()
        # decision_log_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        current_stm['last_decisions'].append(decision) # Append the raw decision dict

        # Limit STM log size (optional)
        max_stm_decisions = 10
        if len(current_stm['last_decisions']) > max_stm_decisions:
            current_stm['last_decisions'] = current_stm['last_decisions'][-max_stm_decisions:]

        # Update the agent model in the database
        db_agent.short_term_memory = current_stm
        db.add(db_agent) # Add to session to mark as dirty
        db.commit()
        db.refresh(db_agent) # Refresh to get potentially updated state
        logger.info(f"Updated short-term memory for agent {agent_id}")
        decision["_stm_updated"] = True
    except Exception as e:
        logger.error(f"Failed to update short-term memory for agent {agent_id}: {e}")
        db.rollback() # Rollback STM update if it fails
        decision["_stm_updated"] = False
        decision["_stm_error"] = str(e)

    return decision

@router.get("/{agent_id}/decisions", response_model=List[dict])
def get_agent_decisions(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve the recent decision history for a specific agent.
    Decisions are stored in the agent's short_term_memory field.
    """
    db_agent = crud_agent.get_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if short_term_memory and last_decisions exist and are the correct type
    if isinstance(db_agent.short_term_memory, dict):
        decisions = db_agent.short_term_memory.get("last_decisions", [])
        if isinstance(decisions, list):
            return decisions
        else:
            logger.warning(f"Agent {agent_id} short_term_memory['last_decisions'] is not a list.")
            return [] # Return empty list if structure is wrong
    else:
        logger.warning(f"Agent {agent_id} short_term_memory is not a dictionary.")
        return [] # Return empty list if structure is wrong

# Add more agent-specific endpoints later:
# - Get/set profile parts
# - Fetch decision history
# - Query memory
# - Get social connections 