import logging
import numpy as np
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.simulation import Simulation
from app.models.agent import Agent as AgentModel
from app.models.metrics import MetricSnapshot
from app.crud import agent as crud_agent
from app.crud import metrics as crud_metrics

logger = logging.getLogger(__name__)

def calculate_gini(incomes: List[float]) -> Optional[float]:
    """Calculates the Gini coefficient for a list of incomes."""
    if not incomes:
        return None
    # Basic Gini calculation (source: Wikipedia/various)
    # Requires numpy
    try:
        array = np.array(incomes, dtype=np.float64)
        if np.amin(array) < 0:
            # Values cannot be negative:
            array -= np.amin(array)
        # Values cannot be 0:
        array += 0.0000001 # Adding epsilon to avoid division by zero if all incomes are 0
        # Sort ascending:
        array = np.sort(array)
        # Index:
        index = np.arange(1, array.shape[0] + 1)
        # Number of items:
        n = array.shape[0]
        # Gini coefficient:
        return ((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array)))
    except Exception as e:
        logger.error(f"Error calculating Gini coefficient: {e}")
        return None

def calculate_belief_variance(agents: List[AgentModel]) -> Optional[float]:
    """Calculates the average variance across all belief vector dimensions."""
    if not agents:
        return None
    try:
        belief_vectors = []
        for agent in agents:
            # Assuming agent.beliefs is a dict and contains 'political_ideology_vector'
            if isinstance(agent.beliefs, dict) and 'political_ideology_vector' in agent.beliefs:
                 vector = agent.beliefs['political_ideology_vector']
                 if isinstance(vector, list):
                     belief_vectors.append(vector)

        if not belief_vectors:
            return 0.0 # Or None if no valid vectors found

        belief_array = np.array(belief_vectors, dtype=np.float64)
        # Calculate variance along each dimension (axis=0)
        variances = np.var(belief_array, axis=0)
        # Return the average variance across dimensions
        avg_variance = np.mean(variances)
        return float(avg_variance)
    except Exception as e:
        logger.error(f"Error calculating belief variance: {e}")
        return None

def calculate_and_store_metrics(db: Session, simulation: Simulation):
    """Calculates and stores key metrics for the current simulation tick."""
    logger.info(f"Calculating metrics for simulation {simulation.id} at tick {simulation.current_tick}")
    agents = crud_agent.get_agents(db, simulation_id=simulation.id, limit=10000) # Get all agents

    if not agents:
        logger.warning(f"No agents found for simulation {simulation.id}. Skipping metric calculation.")
        return

    # 1. Calculate Gini Coefficient
    incomes = []
    for agent in agents:
        if isinstance(agent.demographics, dict) and 'income' in agent.demographics:
            incomes.append(float(agent.demographics['income']))
    gini_np = calculate_gini(incomes)
    gini = float(gini_np) if gini_np is not None else None
    logger.info(f"Calculated Gini: {gini}")

    # 2. Calculate Belief Variance
    belief_variance_np = calculate_belief_variance(agents)
    belief_variance = float(belief_variance_np) if belief_variance_np is not None else None
    logger.info(f"Calculated Belief Variance: {belief_variance}")

    # 3. Store Snapshot
    try:
        crud_metrics.create_metric_snapshot(
            db=db,
            simulation_id=simulation.id,
            tick=simulation.current_tick,
            gini_coefficient=gini,
            belief_variance=belief_variance
        )
        logger.info(f"Stored metric snapshot for simulation {simulation.id} tick {simulation.current_tick}")
    except Exception as e:
        logger.error(f"Failed to store metric snapshot: {e}")
        # Decide if this error should halt anything or just be logged 