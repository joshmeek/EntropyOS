import logging
import json
import re
from typing import Type, TypeVar

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.models.agent import Agent as AgentModel
from app.models.simulation import Simulation as SimulationModel
from app.schemas.llm import LLMDecision
from app.core.llm_client import get_llm_client # Import the function to get the client instance

logger = logging.getLogger(__name__)

# Define a generic type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

def construct_agent_prompt(agent: AgentModel, simulation: SimulationModel) -> str:
    """Constructs a detailed prompt for the LLM based on agent and simulation state."""

    # Ensure JSON serializability (convert UUIDs, handle complex types if any)
    def safe_json_dump(data):
        return json.dumps(data, indent=2, default=str)

    # Simplified context for now
    # Extract last_decisions safely, handling potential None or non-dict STM
    last_decisions = []
    if isinstance(agent.short_term_memory, dict):
        last_decisions = agent.short_term_memory.get('last_decisions', [])[-3:] # Last 3 decisions

    agent_profile = {
        "id": str(agent.id),
        "demographics": agent.demographics,
        "behavioral_traits": agent.behavioral_traits,
        "beliefs": agent.beliefs,
        "short_term_memory": last_decisions
    }

    simulation_context = {
        "current_tick": simulation.current_tick,
        "status": simulation.status,
        "name": simulation.name
    }

    # TODO: Add relevant world context, events, social graph info later

    # Use standard f-string with triple quotes. Define the JSON structure clearly.
    prompt = f"""
You are an agent within the "{simulation_context['name']}" simulation at tick {simulation_context['current_tick']}.
Your current status:
{safe_json_dump(agent_profile)}

Simulation status: {simulation_context['status']}

Based on your profile and recent memory, decide your next action and state changes.
Think step-by-step about your current situation, motivations, and potential actions.

Finally, provide your decision ONLY as a valid JSON object matching this structure:
{{
  "action": "<string: concise description of your chosen action>",
  "dialogue": "<string or null: any spoken words or internal monologue related to the action>",
  "sentiment_shift": <float: change in your overall sentiment, -1.0 to 1.0, default 0.0>,
  "policy_opinion_shift": {{ "<string: policy_name>": <float: change in opinion, -1.0 to 1.0>, ... }},
  "spending_ratio_shift": <float or null: change in your spending propensity, -1.0 to 1.0>
}}

IMPORTANT: Ensure the output is ONLY the JSON object, starting with {{ and ending with }}. Pay close attention to using correct JSON syntax, especially commas between key-value pairs and ensuring all strings are enclosed in double quotes ("). Do not include any introductory text, explanations, or markdown formatting like ```json.

JSON Decision:
"""

    return prompt

def get_llm_decision_sync(prompt: str) -> str:
    """Synchronously calls the LLM and returns the raw text response."""
    llm_client = get_llm_client()
    if not llm_client:
        logger.error("LLM client not initialized.")
        # Return an empty JSON string to allow parsing attempt, preventing hard crash
        return "{}"
        # Or re-raise: raise RuntimeError("LLM client not available.")

    try:
        logger.debug("Sending prompt to LLM...")
        # Configure safety settings to be less restrictive if needed, e.g.,
        # safety_settings = {
        #     HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        #     # ... other categories
        # }
        # response = llm_client.generate_content(prompt, safety_settings=safety_settings)
        response = llm_client.generate_content(prompt)

        # Check for blocked response or empty candidates more robustly
        if not response.candidates:
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Unknown"
            logger.warning(f"LLM response was blocked or empty. Reason: {block_reason}. Prompt: '{prompt[:200]}...'")
            return "{}" # Return empty JSON on block/empty

        # Handle potential multi-part responses (though unlikely for this use case)
        if not response.candidates[0].content or not response.candidates[0].content.parts:
             logger.warning(f"LLM response missing expected content parts. Response: {response}")
             return "{}" # Return empty JSON on unexpected structure

        raw_text = response.text
        logger.debug(f"Received raw response from LLM (length {len(raw_text)}): {raw_text[:500]}...") # Log snippet
        return raw_text
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}", exc_info=True)
        # Return empty JSON to allow parsing attempt
        return "{}"
        # Or re-raise: raise

def parse_structured_decision(raw_response: str, schema: Type[T]) -> T:
    """Parses the raw LLM string response into the specified Pydantic schema."""
    try:
        # Attempt to find JSON block, remove potential markdown fences
        raw_response = raw_response.strip().removeprefix("```json").removesuffix("```").strip()

        # Basic extraction: find the first JSON object-like structure
        match = re.search(r'\{[\s\S]*?\}', raw_response)
        if not match:
            logger.error(f"Could not find JSON object in LLM response: {raw_response}")
            # Return default/empty schema object instead of raising error?
            # Or raise specific error:
            raise ValueError("No JSON object found in response.")

        json_str = match.group(0)
        logger.debug(f"Extracted JSON string: {json_str}")

        # Load the JSON string into a Python dict
        data = json.loads(json_str)

        # Validate the data against the Pydantic schema
        parsed_decision = schema.model_validate(data) # Pydantic V2
        return parsed_decision

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from LLM response: {e}\nResponse: {raw_response}")
        # Option: Return default object instead of raising?
        # return schema() # Requires default values in schema
        raise ValueError(f"Invalid JSON format: {e}") from e
    except ValidationError as e:
        logger.error(f"LLM response failed Pydantic validation: {e}\nResponse: {raw_response}")
        # Option: Return default object?
        # return schema()
        raise ValueError(f"Schema validation failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM decision: {e}\nResponse: {raw_response}", exc_info=True)
        # Option: Return default object?
        # return schema()
        raise # Re-raise unexpected errors 