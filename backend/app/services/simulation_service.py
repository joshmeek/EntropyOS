import logging
from sqlalchemy.orm import Session

from app.models.simulation import Simulation as SimulationModel
from app.models.agent import Agent as AgentModel
from app.crud import agent as crud_agent
# Assume LLM service and embedding utilities exist
from . import llm_service # Use the actual LLM service
# from . import embedding_service # Keep embedding commented for now
from app.schemas.llm import LLMDecision # Import the LLM decision schema
from sqlalchemy.orm.attributes import flag_modified # Import for JSON updates

logger = logging.getLogger(__name__)

def run_agent_updates(db: Session, simulation: SimulationModel):
    """
    Orchestrates the updates for all agents within a single simulation tick.
    Fetches agents, calls LLM for decisions, updates agent state (STM, LTM, beliefs).
    This is currently a SYNCHRONOUS implementation.
    """
    logger.info(f"Starting agent updates for tick {simulation.current_tick} in simulation {simulation.id}")

    agents = crud_agent.get_agents(db, simulation_id=simulation.id, limit=10000) # Activate all agents for now
    if not agents:
        logger.warning(f"No agents found for simulation {simulation.id}. Skipping agent updates.")
        return

    logger.info(f"Processing updates for {len(agents)} agents.")

    for agent in agents:
        try:
            logger.debug(f"Processing agent {agent.id}...")

            # 1. Construct prompt (Requires agent state, world context, etc.)
            # prompt = llm_service.construct_agent_prompt(agent, simulation.current_tick)
            prompt_placeholder = f"Prompt for agent {agent.id} at tick {simulation.current_tick}"
            logger.debug(f"Agent {agent.id} Prompt Placeholder: {prompt_placeholder}")

            # 2. Call LLM (Synchronous)
            # llm_response_text = llm_service.get_decision_sync(prompt)
            # decision: LLMDecision = llm_service.parse_decision(llm_response_text)
            llm_response_placeholder = {"action": "observe", "sentiment_shift": 0.1, "dialogue": f"Agent {agent.id} observed something."}
            logger.debug(f"Agent {agent.id} LLM Response Placeholder: {llm_response_placeholder}")
            # --- Replace Placeholder with Actual LLM Call --- #
            try:
                prompt = llm_service.construct_agent_prompt(agent, simulation)
                logger.debug(f"Agent {agent.id} Constructed Prompt:\n{prompt}") # Log the actual prompt
                llm_response_raw = llm_service.get_llm_decision_sync(prompt)
                logger.debug(f"Agent {agent.id} Raw LLM Response:\n{llm_response_raw}")
                decision = llm_service.parse_structured_decision(llm_response_raw, LLMDecision)
                logger.info(f"Agent {agent.id} Parsed Decision: {decision.dict()}")
            except Exception as llm_err:
                logger.error(f"LLM processing failed for agent {agent.id}: {llm_err}", exc_info=True)
                # On LLM/parsing failure, create a default decision to allow the simulation to proceed
                logger.warning(f"Using default 'observe' decision for agent {agent.id} due to LLM error.")
                decision = LLMDecision(action="observe_failed_llm", dialogue="LLM processing error.")
            # --- End LLM Call Replacement / Error Handling --- #

            # 3. Update Short-Term Memory (using actual or default decision)
            if not isinstance(agent.short_term_memory, dict):
                agent.short_term_memory = {"recent_events": [], "last_decisions": []}

            # Ensure 'last_decisions' key exists and is a list
            if not isinstance(agent.short_term_memory.get("last_decisions"), list):
                agent.short_term_memory["last_decisions"] = []

            # Append the actual decision/response
            agent.short_term_memory["last_decisions"].append({
                "tick": simulation.current_tick,
                "decision": decision.dict() # Store the parsed decision dict
            })

            # Mark as modified
            flag_modified(agent, "short_term_memory")
            logger.debug(f"Agent {agent.id} STM updated.")


            # 4. Update Beliefs/Traits based on decision (Example: sentiment shift)
            # Ensure beliefs is a dictionary
            if not isinstance(agent.beliefs, dict):
                agent.beliefs = {} # Initialize if None or not a dict

            agent_beliefs = agent.beliefs # Work with the dict
            agent_beliefs["sentiment"] = agent_beliefs.get("sentiment", 0.5) + decision.sentiment_shift
            # TODO: Implement updates for policy_opinion_shift and spending_ratio_shift
            # Mark as modified
            flag_modified(agent, "beliefs")
            logger.debug(f"Agent {agent.id} beliefs updated.")


            # 5. Update Long-Term Memory
            # memory_text = f"At tick {simulation.current_tick}, I decided to {decision.action}. Dialogue: {decision.dialogue}"
            # memory_embedding = embedding_service.get_embedding(memory_text)
            # crud_agent.add_long_term_memory(db, agent_id=agent.id, simulation_id=simulation.id, memory_text=memory_text, memory_embedding=memory_embedding)
            memory_text_placeholder = f"Tick {simulation.current_tick}: Action={decision.action}, Dialogue='{decision.dialogue}'"
            # Fake embedding for now
            # memory_embedding_placeholder = [0.0] * 768 # Match dimension from migration
            # crud_agent.add_long_term_memory(db, agent_id=agent.id, simulation_id=simulation.id, memory_text=memory_text_placeholder, memory_embedding=memory_embedding_placeholder)
            logger.debug(f"Agent {agent.id} LTM update placeholder skipped (needs embedding): {memory_text_placeholder}")


            # Mark the agent object as modified if necessary (especially for JSON)
            # from sqlalchemy.orm.attributes import flag_modified
            # flag_modified(agent, "short_term_memory")
            # flag_modified(agent, "beliefs")

            logger.info(f"Successfully processed agent {agent.id}")

        except Exception as e:
            logger.error(f"Error processing agent {agent.id} in simulation {simulation.id}: {e}", exc_info=True)
            # Decide whether to continue with other agents or raise/rollback
            # For now, just log and continue
            continue

    # Committing changes will happen when the main route handler's DB session context closes
    logger.info(f"Finished agent updates for tick {simulation.current_tick} in simulation {simulation.id}") 