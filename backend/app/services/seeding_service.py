from sqlalchemy.orm import Session
import random
import numpy as np # For generating distributions
import uuid
import logging
from typing import List

from app.schemas.seeding import SeedingConfig
from app.schemas.agent import AgentCreate, AgentDemographics, AgentBehavioralTraits, AgentBeliefs
from app.crud import agent as crud_agent
from app.crud import agent_connection as crud_connection # Import connection CRUD (needs creation)
from app.models.simulation import Simulation # Import Simulation model
from app.models.agent import Agent # Import Agent model directly for typing

logger = logging.getLogger(__name__)

def _generate_value(mean: float, stddev: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Generates a normally distributed value clipped within bounds."""
    value = random.gauss(mean, stddev)
    return max(min_val, min(max_val, value))

def _generate_agent_data(config: SeedingConfig) -> AgentCreate:
    """Generates data for a single agent based on configuration."""
    # Demographics
    age = int(max(0, random.gauss(config.demographics.age_mean, config.demographics.age_stddev)))
    income = max(0.0, random.gauss(config.demographics.income_mean, config.demographics.income_stddev))
    # TODO: Add generation for other demographic fields
    demographics = AgentDemographics(
        age=age,
        income=income,
        household_size=random.randint(1, 5) # Example
    )

    # Behavioral Traits
    conformity = _generate_value(config.traits.conformity_mean, config.traits.conformity_stddev)
    risk_aversion = _generate_value(config.traits.risk_aversion_mean, config.traits.risk_aversion_stddev)
    # TODO: Add generation for other traits
    traits = AgentBehavioralTraits(
        conformity=conformity,
        risk_aversion=risk_aversion,
        empathy=_generate_value(0.5, 0.2), # Example defaults
        social_susceptibility=_generate_value(0.5, 0.2),
        consumption_preference=_generate_value(0.5, 0.3)
    )

    # Beliefs
    economic_optimism = _generate_value(config.beliefs.economic_optimism_mean, config.beliefs.economic_optimism_stddev)
    # TODO: Add generation for political vector, trust, policy support
    beliefs = AgentBeliefs(
        political_ideology_vector=[random.random() for _ in range(5)], # Example: 5 random dimensions
        economic_optimism=economic_optimism,
        institutional_trust=_generate_value(0.5, 0.2),
        policy_support_index={} # Start empty
    )

    return AgentCreate(
        demographics=demographics,
        behavioral_traits=traits,
        beliefs=beliefs
        # archetype can be added based on config.archetype_distribution later
    )

def _create_random_connections(db: Session, agents: List[Agent], connection_probability: float = 0.1):
    """Creates random, directed connections between agents."""
    if not agents or len(agents) < 2:
        return

    logger.info(f"Creating random connections for {len(agents)} agents with probability {connection_probability}")
    agent_ids = [agent.id for agent in agents]
    created_count = 0

    for source_agent in agents:
        for target_agent_id in agent_ids:
            if source_agent.id == target_agent_id:
                continue # No self-loops

            if random.random() < connection_probability:
                try:
                    crud_connection.create_agent_connection(
                        db=db,
                        source_agent_id=source_agent.id,
                        target_agent_id=target_agent_id,
                        influence_factor=random.uniform(0.1, 0.9), # Example random influence
                        relationship_type="random"
                    )
                    created_count += 1
                except Exception as e:
                    # Log error but continue trying to create other connections
                    logger.error(f"Failed to create connection from {source_agent.id} to {target_agent_id}: {e}")
                    db.rollback() # Rollback failed connection attempt

    try:
        db.commit() # Commit all successful connections
        logger.info(f"Created {created_count} random agent connections.")
    except Exception as e:
        logger.error(f"Failed to commit agent connections: {e}")
        db.rollback()

def seed_simulation_agents(db: Session, simulation: Simulation, config: SeedingConfig):
    """Seeds a simulation with agents and generates connections."""
    logger.info(f"Seeding simulation {simulation.id} with {config.population_size} agents.")
    created_agent_models = [] # Store created models to get IDs
    for i in range(config.population_size):
        try:
            agent_data: AgentCreate = _generate_agent_data(config)

            # Manually set simulation_id before passing to CRUD (as it's not in AgentCreate schema)
            db_agent_model = crud_agent.AgentModel(
                simulation_id=simulation.id,
                archetype=agent_data.archetype,
                demographics=agent_data.demographics.model_dump(),
                behavioral_traits=agent_data.behavioral_traits.model_dump(),
                beliefs=agent_data.beliefs.model_dump(),
            )
            db.add(db_agent_model)
            created_agent_models.append(db_agent_model) # Keep track of models
            if i % 100 == 0 or i == config.population_size - 1:
                try:
                    db.commit()
                    logger.info(f"Committed batch of agents up to index {i} for simulation {simulation.id}")
                    # Refresh models in the batch to get IDs (needed for connections)
                    for agent_model in created_agent_models[-(i%100 + 1):]:
                         db.refresh(agent_model)
                except Exception as e:
                    logger.error(f"Commit failed during agent batch creation at index {i}: {e}")
                    db.rollback()
                    raise

        except Exception as e:
            logger.error(f"Failed to create agent {i+1} for simulation {simulation.id}: {e}")
            db.rollback() # Rollback the current transaction batch on error
            raise # Re-raise the exception to halt seeding

    logger.info(f"Successfully seeded {config.population_size} agents for simulation {simulation.id}.")

    # Generate connections after all agents have IDs
    if created_agent_models:
        _create_random_connections(db, created_agent_models, connection_probability=0.05) # Lower probability for testing
    else:
        logger.warning("No agents were created, skipping connection generation.")

    # TODO: Implement social graph generation here (after agents are created and have IDs)
    # e.g., create_social_network(db, simulation, config.social_network_config) 