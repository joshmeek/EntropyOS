import google.generativeai as genai
from app.core.config import settings
import logging
import json
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# --- LLM Client Setup ---
llm_model: Optional[genai.GenerativeModel] = None # Initialize as None

def init_llm_client():
    """Initializes the global LLM client variable."""
    global llm_model
    if settings.GEMINI_API_KEY:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            llm_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Use flash model
            logger.info("Gemini client configured successfully during app startup.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client during app startup: {e}")
            llm_model = None
    else:
        logger.warning("GEMINI_API_KEY not found in settings. LLM client not configured.")

def get_llm_client() -> genai.GenerativeModel:
    """Returns the initialized Gemini GenerativeModel instance."""
    if llm_model is None:
        raise RuntimeError("Gemini client is not available. Check startup logs.")
    return llm_model

# --- Embedding Function ---
embedding_model_name = "models/embedding-001" # Or other suitable Gemini embedding model

async def generate_embedding(text: str) -> Optional[List[float]]:
    """Generates an embedding for the given text using Gemini."""
    try:
        result = await genai.embed_content_async(
            model=embedding_model_name,
            content=text,
            task_type="RETRIEVAL_DOCUMENT" # Or other task types like SEMANTIC_SIMILARITY
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding for text '{text[:50]}...': {e}")
        return None

# --- Structured Output Definition ---
# Corresponds to the output structure mentioned in the overview
class LLMAgentDecision(BaseModel):
    action: str = Field(..., description="The primary action the agent decides to take.")
    sentiment: str = Field(..., description="The agent's sentiment (e.g., hopeful, fearful, neutral).")
    policy_opinion_shift: float = Field(..., description="Shift in opinion towards a relevant policy (-1.0 to 1.0).")
    spending_ratio: float = Field(..., ge=0, le=1, description="Proportion of disposable income to spend (0.0 to 1.0).")

# --- Prompt Generation ---
def create_agent_prompt(agent_profile: Dict[str, Any],
                      short_term_memory: Dict[str, Any],
                      # Add other context parameters as needed later:
                      # social_context: Dict[str, Any],
                      # world_state: Dict[str, Any],
                      # current_events: List[Dict[str, Any]]
                     ) -> str:
    """Constructs the prompt for the LLM based on agent context."""

    # Basic prompt structure (can be significantly enhanced)
    prompt = f"""
You are an agent in a socio-economic simulation.
Your profile:
{json.dumps(agent_profile, indent=2)}

Your recent memory (events and decisions):
{json.dumps(short_term_memory, indent=2)}

Based on your profile and recent experiences, decide on your next course of action, your current sentiment, how your opinion on relevant policies might shift, and your spending propensity.

Output ONLY a valid JSON object with the following structure:
{{
  "action": "<string>",
  "sentiment": "<string>",
  "policy_opinion_shift": <float>,
  "spending_ratio": <float between 0.0 and 1.0>
}}
"""
    return prompt

# --- Decision Generation and Parsing ---
async def generate_agent_decision(agent_profile: Dict[str, Any],
                                  short_term_memory: Dict[str, Any],
                                  # Add other context parameters
                                 ) -> Dict[str, Any]:
    """Generates a structured agent decision using the LLM, including parsing."""
    llm_client = get_llm_client() # Raises runtime error if not configured

    prompt = create_agent_prompt(agent_profile, short_term_memory)
    logger.debug(f"Generated LLM Prompt:\n{prompt}")

    try:
        # Configure safety settings to be less restrictive if needed for JSON output
        safety_settings = {
            #   "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            #   "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            #   "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            #   "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }
        generation_config = genai.types.GenerationConfig(
            # response_mime_type="application/json", # Use if model supports direct JSON output
            temperature=0.7 # Add some variability
        )

        response = await llm_client.generate_content_async(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        raw_response_text = response.text
        logger.debug(f"LLM Raw Response Text: {raw_response_text}")

        # Attempt to parse the response as JSON
        try:
            # Clean potential markdown code fences
            cleaned_text = raw_response_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            decision_dict = json.loads(cleaned_text)

            # Validate the structure using Pydantic
            validated_decision = LLMAgentDecision(**decision_dict)
            logger.info(f"Successfully parsed and validated LLM decision: {validated_decision.model_dump()}")
            # Return the validated data as a dictionary
            return validated_decision.model_dump()

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode LLM response as JSON: {e}\nRaw response: {raw_response_text}")
            return {"error": "JSONDecodeError", "raw_response": raw_response_text}
        except ValidationError as e:
            logger.error(f"LLM JSON response failed validation: {e}\nRaw response: {raw_response_text}")
            # Attempt to return the raw parsed dict anyway, but flag it
            return {"error": "ValidationError", "parsed_dict": decision_dict, "raw_response": raw_response_text}
        except Exception as e:
             logger.error(f"Unexpected error parsing/validating LLM response: {e}\nRaw response: {raw_response_text}")
             return {"error": f"ParsingError: {e}", "raw_response": raw_response_text}

    except Exception as e:
        logger.error(f"Error during LLM call: {e}")
        # Check for specific Gemini API errors if possible
        # Example: if isinstance(e, genai.types.BlockedPromptException):
        #     logger.error(f"Prompt blocked: {e}")
        return {"error": f"LLM API Error: {str(e)}"}
